"""世界观构建 API。"""

import os
import uuid
import threading

from flask import request, jsonify

from . import world_build_bp
from app.config import Config
from app.models.world import WorldManager
from app.services.enhanced_world_extractor import EnhancedWorldExtractor
from app.utils.file_parser import FileParser
from app.utils.llm_client import LLMClient
from app.utils.logger import get_logger
logger = get_logger('mirofish.api.world_build')

# 提取任务进度存储
_extraction_tasks = {}
_tasks_lock = threading.Lock()


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


def _ensure_upload_dir():
    """确保上传目录存在"""
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


@world_build_bp.route('/create', methods=['POST'])
def create_world():
    """创建新的世界观"""
    try:
        data = request.json or {}
        world = WorldManager.create_world(
            name=data.get('name'),
            description=data.get('description', ''),
            era=data.get('era', ''),
            anchor_time=data.get('anchor_time', ''),
            settings=data.get('settings', {}),
            writing_style=data.get('writing_style', ''),
            reference_text=data.get('reference_text', '')
        )
        return jsonify({
            'success': True,
            'world_id': world.id,
            'world': world.to_dict(),
            'message': '世界观创建成功'
        })
    except Exception as e:
        logger.error(f"创建世界观失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'创建失败: {str(e)}'
        }), 500


@world_build_bp.route('/extract', methods=['POST'])
def extract_world():
    """从文本或上传文件提取世界观信息"""
    try:
        text = None
        uploaded_filenames = []
        direct_json_data = None

        # 处理文件上传（multipart/form-data）
        uploaded_files = request.files.getlist('files') if request.files else []
        logger.info(f"提取请求: files={len(uploaded_files)}, form_keys={list(request.form.keys())}, content_type={request.content_type}")

        if uploaded_files:
            _ensure_upload_dir()
            text_parts = []
            json_parts = []
            failed_files = []
            for file in uploaded_files:
                if not file or not file.filename:
                    continue
                filename = file.filename
                ext = os.path.splitext(filename)[1].lower().lstrip('.')
                if ext not in Config.ALLOWED_EXTENSIONS and ext != 'json':
                    logger.warning(f"不支持的文件格式: {filename} ({ext})")
                    continue

                import uuid
                import time
                safe_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{filename}"
                file_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
                file.save(file_path)
                logger.info(f"文件已保存: {filename} ({os.path.getsize(file_path)} bytes)")
                try:
                    if ext == 'json':
                        import json as json_module
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json_data = json_module.load(f)
                        if isinstance(json_data, dict):
                            json_parts.append(json_data)
                            uploaded_filenames.append(filename)
                    else:
                        extracted_text = FileParser.extract_text(file_path)
                        logger.info(f"文本提取成功: {filename} ({len(extracted_text)} 字符)")
                        text_parts.append(f"=== {filename} ===\n{extracted_text}")
                        uploaded_filenames.append(filename)
                except Exception as file_err:
                    logger.error(f"文件处理失败 {filename}: {file_err}")
                    failed_files.append(f"{filename}: {str(file_err)}")
                finally:
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass

            if text_parts:
                text = "\n\n".join(text_parts)
                logger.info(f"合并文本: {len(text_parts)} 个文件, 总计 {len(text)} 字符")

            if failed_files and not text_parts:
                return jsonify({
                    'success': False,
                    'message': f'所有文件处理失败: {"; ".join(failed_files)}'
                }), 400

            # 合并多个 JSON 文件
            if json_parts:
                direct_json_data = json_parts[0]
                for extra in json_parts[1:]:
                    if extra.get('entities'):
                        direct_json_data.setdefault('entities', []).extend(extra['entities'])
                    if extra.get('events'):
                        direct_json_data.setdefault('events', []).extend(extra['events'])
                    if extra.get('settings') and isinstance(extra['settings'], dict):
                        existing_settings = direct_json_data.setdefault('settings', {})
                        if isinstance(existing_settings, dict):
                            existing_settings.setdefault('items', []).extend(
                                extra['settings'].get('items') or [])
                            existing_settings.setdefault('calendars', []).extend(
                                extra['settings'].get('calendars') or [])

            # 也检查 form 中的 text 字段
            form_text = request.form.get('text', '').strip()
            if form_text:
                text = (text + "\n\n" + form_text) if text else form_text

        # 普通 JSON 请求
        if not text and direct_json_data is None:
            data = request.get_json(silent=True) or {}
            text = data.get('text', '').strip()
            # 支持直接 POST JSON 数据
            if not text and isinstance(data, dict) and (
                'world_info' in data or 'entities' in data or 'events' in data or 'settings' in data
            ):
                direct_json_data = data

        if not text and direct_json_data is None:
            logger.warning(f"提取请求无有效内容: has_files={len(uploaded_files) > 0}, has_text={bool(text)}, has_json={direct_json_data is not None}")
            return jsonify({
                'success': False,
                'message': '请提供文本内容或上传文件（支持 PDF、Markdown、TXT、JSON 格式）'
            }), 400

        # 如果只有 JSON 数据没有文本，直接返回，无需 LLM
        if direct_json_data is not None and not text:
            resp = {
                'success': True,
                'extracted_data': direct_json_data
            }
            if uploaded_filenames:
                resp['source_files'] = uploaded_filenames
            return jsonify(resp)

        # 有文本内容，需要 LLM 提取
        if not Config.get_llm_config('parser').get('api_key'):
            return jsonify({
                'success': False,
                'message': 'LLM API Key 未配置，请至少配置 Agent/SubAgent/解析 Agent 中的一组 LLM API。'
            }), 400

        # 捕获请求数据供后台线程使用（JSON 或 form 中的 world_id）
        request_data = request.get_json(silent=True) or {}
        if not isinstance(request_data, dict):
            request_data = {}
        # 也合并 form 数据
        if request.form:
            request_data.update(dict(request.form))

        # 启动后台提取任务，立即返回 task_id
        task_id = f"extract_{uuid.uuid4().hex[:12]}"
        with _tasks_lock:
            _extraction_tasks[task_id] = {
                'stage': 'starting',
                'progress': 0,
                'message': '正在启动提取...',
                'done': False,
                'result': None,
                'error': None,
            }

        def run_extraction():
            _rag_result = [None]
            _rag_thread = None

            try:
                def progress_cb(stage, progress, message, detail=None):
                    with _tasks_lock:
                        if task_id in _extraction_tasks:
                            _extraction_tasks[task_id].update({
                                'stage': stage,
                                'progress': max(0, min(int(progress), 100)),
                                'message': message,
                                'detail': detail or {},
                            })

                def rag_progress_cb(stage, progress, message, detail=None):
                    rag_payload = {
                        'stage': stage,
                        'progress': max(0, min(int(progress), 100)),
                        'message': message,
                        'detail': detail or {},
                    }
                    with _tasks_lock:
                        if task_id in _extraction_tasks:
                            task = _extraction_tasks[task_id]
                            task['rag_progress'] = rag_payload
                            # RAG 在后台并行，不直接覆盖 LLM 主进度；但在索引收尾阶段透传为主提示。
                            if task.get('stage') == 'indexing' or progress >= 90:
                                task.update({
                                    'stage': 'indexing',
                                    'progress': max(int(task.get('progress', 0)), min(95, 60 + int(progress * 0.35))),
                                    'message': f'向量索引：{message}',
                                    'detail': {'rag_progress': rag_payload},
                                })

                progress_cb('preparing', 5, '正在初始化...')

                # ── 启动 RAG 索引（与 LLM 提取并行）──
                world_id = request_data.get('world_id', '').strip()
                emb_config = Config.get_embedding_config()
                if world_id and text and emb_config.get('api_key'):
                    def _do_rag():
                        try:
                            from ..services.rag_service import RagService
                            rag = RagService(world_id)
                            doc_ids = rag.add_text_chunks(
                                text=text,
                                source="extraction",
                                metadata={"filename": ", ".join(uploaded_filenames) if uploaded_filenames else "direct_text"},
                                chunk_preset="novel",
                                progress_callback=rag_progress_cb,
                            )
                            stats = rag.get_stats()
                            _rag_result[0] = {
                                'rag_indexed': True,
                                'rag_added_count': len(doc_ids),
                                'rag_document_count': stats.get('document_count', 0),
                            }
                            logger.info(f"RAG 并行索引完成 [{world_id}]: 新增 {len(doc_ids)} 块，总计 {stats.get('document_count', 0)} 文档"
                                        f" (来源: {uploaded_filenames or '直接输入'})")
                        except Exception as rag_err:
                            logger.warning(f"RAG 并行索引失败 [{world_id}]: {rag_err}", exc_info=True)
                            _rag_result[0] = {'rag_indexed': False, 'rag_error': str(rag_err)}
                    _rag_thread = threading.Thread(target=_do_rag, daemon=True)
                    _rag_thread.start()
                    progress_cb('indexing', 7, '正在并行执行 LLM 提取与小说章节向量索引...', {'rag_progress': {'stage': 'queued', 'progress': 0, 'message': 'RAG 索引已排队'}})
                elif not world_id:
                    logger.info("RAG 索引跳过: 未提供 world_id")
                elif not emb_config.get('api_key'):
                    logger.warning("RAG 索引跳过: 未配置 Embedding/LLM API Key")

                extractor = EnhancedWorldExtractor()

                text_len = len(text) if text else 0
                if text_len > extractor.LONG_TEXT_THRESHOLD:
                    progress_cb('chunking', 8, f'文本 {text_len} 字符，正在章节感知切分...')

                # LLM 提取（与 RAG 并行进行中）
                result = extractor.extract_from_text(text, progress_callback=progress_cb)

                # 合并直接导入的 JSON 数据
                if direct_json_data is not None:
                    if direct_json_data.get('entities'):
                        result.setdefault('entities', []).extend(direct_json_data['entities'])
                    if direct_json_data.get('events'):
                        result.setdefault('events', []).extend(direct_json_data['events'])
                    if direct_json_data.get('settings', {}).get('items'):
                        result.setdefault('settings', {}).setdefault('items', []).extend(
                            direct_json_data['settings']['items'])
                    if direct_json_data.get('settings', {}).get('calendars'):
                        result.setdefault('settings', {}).setdefault('calendars', []).extend(
                            direct_json_data['settings']['calendars'])

                # 等待 RAG 索引线程（通常已提前完成）
                if _rag_thread and _rag_thread.is_alive():
                    progress_cb('indexing', 93, '正在等待向量索引收尾...')
                    _rag_thread.join()
                    import time as _time
                    _time.sleep(0.3)  # 让前端看到收尾状态
                if _rag_result[0]:
                    result.update(_rag_result[0])

                with _tasks_lock:
                    _extraction_tasks[task_id].update({
                        'stage': 'done', 'progress': 100,
                        'message': f'提取完成: {len(result.get("entities", []))} 实体, {len(result.get("events", []))} 事件',
                        'done': True, 'result': result,
                    })
            except Exception as e:
                logger.error(f"后台提取失败 [{task_id}]: {e}")
                with _tasks_lock:
                    _extraction_tasks[task_id].update({
                        'stage': 'error', 'done': True,
                        'error': str(e),
                        'message': f'提取失败: {str(e)[:100]}',
                    })

        threading.Thread(target=run_extraction, daemon=True).start()

        resp = {
            'success': True,
            'task_id': task_id,
            'message': '提取任务已启动',
        }
        if uploaded_filenames:
            resp['source_files'] = uploaded_filenames
        return jsonify(resp)
    except Exception as e:
        logger.error(f"提取世界观失败: {str(e)}")
        error_text = str(e).lower()
        status_code = 400 if any(keyword in error_text for keyword in ['llm', 'api key', 'api_key', 'invalid_api_key']) else 500
        return jsonify({
            'success': False,
            'message': f'提取失败: {str(e)}'
        }), status_code


@world_build_bp.route('/extract/<task_id>/progress', methods=['GET'])
def extract_progress(task_id):
    """轮询提取任务进度"""
    with _tasks_lock:
        task = _extraction_tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'message': '任务不存在或已过期'}), 404
    resp = {
        'success': True,
        'task_id': task_id,
        'stage': task['stage'],
        'progress': task['progress'],
        'message': task['message'],
        'detail': task.get('detail') or {},
        'rag_progress': task.get('rag_progress'),
        'done': task['done'],
    }
    if task['done'] and task.get('result'):
        resp['extracted_data'] = task['result']
    if task.get('error'):
        resp['error'] = task['error']
    return jsonify(resp)


@world_build_bp.route('/llm-config', methods=['GET'])
def get_llm_config():
    """获取当前 LLM 配置状态。"""
    return jsonify({
        'success': True,
        'config': Config.get_llm_config_status()
    })


@world_build_bp.route('/llm-config', methods=['PUT'])
def update_llm_config():
    """保存 LLM 配置。"""
    try:
        data = request.json or {}
        config = Config.save_llm_config(
            api_key=data.get('api_key') if 'api_key' in data else None,
            base_url=data.get('base_url') if 'base_url' in data else None,
            model_name=data.get('model_name') if 'model_name' in data else None,
        )
        return jsonify({
            'success': True,
            'config': config,
            'message': 'LLM 配置已保存'
        })
    except Exception as e:
        logger.error(f"保存 LLM 配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'保存失败: {str(e)}'
        }), 400


@world_build_bp.route('/llm-config/test', methods=['POST'])
def test_llm_config():
    """测试当前或传入的 LLM 配置。"""
    try:
        data = request.json or {}

        resolved_llm = Config.get_llm_config('agent')
        api_key = data.get('api_key') or resolved_llm['api_key']
        base_url = data.get('base_url') or resolved_llm['base_url']
        model_name = data.get('model_name') or resolved_llm['model_name']

        if not api_key:
            return jsonify({
                'success': False,
                'message': '请先提供 LLM API Key'
            }), 400

        test_result = LLMClient.test_connection(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
        )

        return jsonify({
            'success': True,
            'message': 'LLM 连接测试成功',
            'config': {
                'api_key_configured': bool(api_key),
                'api_key_masked': Config.mask_secret(api_key),
                'base_url': base_url,
                'model_name': model_name,
            },
            'test_result': test_result,
        })
    except Exception as e:
        logger.error(f"测试 LLM 配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        }), 400


@world_build_bp.route('/<world_id>/entities', methods=['POST'])
def add_entity(world_id):
    """添加实体（人物、国家等）"""
    try:
        data = request.json or {}
        entity = WorldManager.add_entity(
            world_id=world_id,
            name=data.get('name'),
            type=data.get('type'),
            attributes=data.get('attributes', {}),
            stages=data.get('stages', []),
            setting_item_id=data.get('setting_item_id', '')
        )
        return jsonify({
            'success': True,
            'entity_id': entity.id,
            'entity': entity.to_dict(),
            'message': '实体添加成功'
        })
    except Exception as e:
        logger.error(f"添加实体失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'添加失败: {str(e)}'
        }), 500


@world_build_bp.route('/<world_id>/events', methods=['POST'])
def add_event(world_id):
    """添加事件"""
    try:
        data = request.json or {}
        event = WorldManager.add_event(
            world_id=world_id,
            name=data.get('name'),
            description=data.get('description'),
            date=data.get('date'),
            entities=data.get('entities', [])
        )
        return jsonify({
            'success': True,
            'event_id': event.id,
            'event': event.to_dict(),
            'message': '事件添加成功'
        })
    except Exception as e:
        logger.error(f"添加事件失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'添加失败: {str(e)}'
        }), 500


@world_build_bp.route('/<world_id>', methods=['PUT'])
def update_world(world_id):
    """更新世界观详情。"""
    try:
        data = request.json or {}
        world = WorldManager.update_world(world_id, data)
        if not world:
            return jsonify({
                'success': False,
                'message': '世界观不存在'
            }), 404

        return jsonify({
            'success': True,
            'world': world.to_dict(),
            'message': '世界观更新成功'
        })
    except Exception as e:
        logger.error(f"更新世界观失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@world_build_bp.route('/list', methods=['GET'])
def list_worlds():
    """列出所有世界观"""
    try:
        worlds = WorldManager.list_worlds()
        return jsonify({
            'success': True,
            'worlds': [
                {
                    'id': w.id,
                    'name': w.name,
                    'description': w.description,
                    'era': w.era,
                    'anchor_time': w.anchor_time,
                    'entities_count': len(w.entities),
                    'events_count': len(w.events),
                    'created_at': w.created_at,
                }
                for w in worlds
            ]
        })
    except Exception as e:
        logger.error(f"列出世界观失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500


@world_build_bp.route('/<world_id>', methods=['GET'])
def get_world(world_id):
    """获取世界观详情"""
    try:
        world = WorldManager.get_world(world_id)
        if not world:
            return jsonify({
                'success': False,
                'message': '世界观不存在'
            }), 404

        return jsonify({
            'success': True,
            'world': world.to_dict()
        })
    except Exception as e:
        logger.error(f"获取世界观失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500


@world_build_bp.route('/<world_id>', methods=['DELETE'])
def delete_world(world_id):
    """删除世界观"""
    try:
        deleted = WorldManager.delete_world(world_id)
        if not deleted:
            return jsonify({
                'success': False,
                'message': '世界观不存在'
            }), 404

        return jsonify({
            'success': True,
            'message': '世界观已删除'
        })
    except Exception as e:
        logger.error(f"删除世界观失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500
