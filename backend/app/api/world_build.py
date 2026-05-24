"""世界观构建 API。"""

import copy
import hashlib
import json
import os
import uuid
import threading
from datetime import datetime

from flask import request, jsonify

from . import world_build_bp
from app.config import Config
from app.models.world import WorldManager
from app.models.map import (
    add_change_record,
    apply_batch_update,
    apply_cell_update,
    cell_neighbors,
    find_cell,
    find_map,
    list_maps as list_structured_maps,
    map_id as create_map_id,
    normalize_map,
    save_maps,
    search_cells,
    stats_for_map,
    summarize_map,
)
from app.services.enhanced_world_extractor import EnhancedWorldExtractor
from app.utils.file_parser import FileParser
from app.utils.llm_client import LLMClient
from app.utils.logger import get_logger
logger = get_logger('mirofish.api.world_build')

# 提取任务进度存储
_extraction_tasks = {}
_tasks_lock = threading.Lock()
_tasks_loaded = False
_running_threads = set()


def _now_iso():
    return datetime.now().isoformat()


def _task_dir():
    path = os.path.join(Config.UPLOAD_FOLDER, 'extraction_tasks')
    os.makedirs(path, exist_ok=True)
    return path


def _safe_task_id(task_id):
    return ''.join(ch for ch in str(task_id or '') if ch.isalnum() or ch in {'_', '-'})[:120]


def _task_path(task_id):
    safe_id = _safe_task_id(task_id)
    return os.path.join(_task_dir(), f'{safe_id}.json')


def _task_result_path(task_id):
    safe_id = _safe_task_id(task_id)
    return os.path.join(_task_dir(), f'{safe_id}.result.json')


def _persist_task_result(task_id, result):
    if result is None:
        return None
    path = _task_result_path(task_id)
    tmp_path = f'{path}.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    return os.path.basename(path)


def _load_task_result(task_id, task=None):
    task = task or {}
    result = task.get('result')
    if result:
        return result
    path = _task_result_path(task_id)
    if not os.path.exists(path) and task.get('result_file'):
        result_file = os.path.basename(str(task.get('result_file') or ''))
        path = os.path.join(_task_dir(), result_file)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception as exc:
        logger.warning(f'读取提取任务结果失败 [{task_id}]: {exc}')
        return None


def _persist_task(task_id):
    task = _extraction_tasks.get(task_id)
    if not task:
        return
    result_file = None
    if task.get('result') is not None:
        result_file = _persist_task_result(task_id, task.get('result'))
    serializable = {key: value for key, value in task.items() if key not in {'thread', 'result'}}
    if result_file:
        serializable['result_file'] = result_file
    serializable['task_id'] = task_id
    serializable['updated_at'] = _now_iso()
    task['updated_at'] = serializable['updated_at']
    path = _task_path(task_id)
    tmp_path = f'{path}.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as handle:
        json.dump(serializable, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _ensure_tasks_loaded():
    global _tasks_loaded
    with _tasks_lock:
        if _tasks_loaded:
            return
        _tasks_loaded = True
        for filename in os.listdir(_task_dir()):
            if not filename.endswith('.json') or filename.endswith('.result.json'):
                continue
            path = os.path.join(_task_dir(), filename)
            try:
                with open(path, 'r', encoding='utf-8') as handle:
                    task = json.load(handle)
                task_id = task.get('task_id') or os.path.splitext(filename)[0]
                if not task.get('done') and (task.get('status') in {'running', 'pause_requested', 'cancel_requested'} or task.get('stage') in {'starting', 'preparing', 'extracting', 'indexing', 'chunking'}):
                    task['status'] = 'stale'
                    task['stage'] = 'stale'
                    task['done'] = False
                    task['message'] = '上次解析进程已中断，可从缓存继续'
                _extraction_tasks[task_id] = task
                _repair_finished_task_status(task_id, task)
                _persist_task(task_id)
            except Exception as exc:
                logger.warning(f'读取提取任务记录失败 {filename}: {exc}')


def _task_result_summary(result):
    result = result or {}
    settings = result.get('settings') or {}
    return {
        'entities': len(result.get('entities') or []),
        'events': len(result.get('events') or []),
        'settings': len(settings.get('items') or []) if isinstance(settings, dict) else 0,
    }


def _update_task(task_id, **updates):
    with _tasks_lock:
        task = _extraction_tasks.get(task_id)
        if not task:
            return None
        task.update(updates)
        _persist_task(task_id)
        return dict(task)


def _normalize_finished_task_status(task):
    status = task.get('status') or task.get('stage') or ''
    if not task.get('done'):
        return status
    if status == 'cancel_requested' or task.get('cancel_requested'):
        return 'cancelled'
    if status == 'pause_requested' or task.get('pause_requested'):
        return 'paused'
    if status == 'error':
        return 'failed'
    if status == 'done':
        return 'completed'
    return status


def _repair_finished_task_status(task_id, task):
    status = task.get('status') or task.get('stage') or ''
    normalized = _normalize_finished_task_status(task)
    if task.get('done') and normalized and normalized != status:
        task['status'] = normalized
        task['stage'] = 'done' if normalized == 'completed' else normalized
        task['updated_at'] = _now_iso()
        _persist_task(task_id)
    return normalized or status


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
        _ensure_tasks_loaded()
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

        extraction_mode = str(request_data.get('extraction_mode') or Config.EXTRACTION_DEFAULT_MODE or 'fast').strip().lower()
        if extraction_mode not in {'fast', 'deep'}:
            extraction_mode = 'fast'
        force_rebuild_raw = request_data.get('force_rebuild', False)
        force_rebuild = str(force_rebuild_raw).strip().lower() in {'1', 'true', 'yes', 'on'}

        # 启动后台提取任务，立即返回 task_id
        task_id = f"extract_{uuid.uuid4().hex[:12]}"
        with _tasks_lock:
            _extraction_tasks[task_id] = {
                'task_id': task_id,
                'world_id': request_data.get('world_id', '').strip(),
                'status': 'running',
                'stage': 'starting',
                'progress': 0,
                'message': '正在启动提取...',
                'done': False,
                'result': None,
                'error': None,
                'extraction_mode': extraction_mode,
                'force_rebuild': force_rebuild,
                'cancel_requested': False,
                'pause_requested': False,
                'source_files': uploaded_filenames,
                'text_length': len(text or ''),
                'created_at': _now_iso(),
                'updated_at': _now_iso(),
                'started_at': _now_iso(),
                'finished_at': None,
            }
            _persist_task(task_id)

        def run_extraction():
            _rag_result = [None]
            _rag_thread = None

            try:
                def progress_cb(stage, progress, message, detail=None):
                    detail = detail or {}
                    total_chunks = int(detail.get('total_chunks') or 0)
                    completed_chunks = int(detail.get('completed_chunks') or 0)
                    if extraction_mode == 'deep' and stage == 'extracting' and total_chunks > 0:
                        progress = 8 + int(completed_chunks / max(total_chunks, 1) * 80)
                    with _tasks_lock:
                        if task_id in _extraction_tasks:
                            status = _extraction_tasks[task_id].get('status') or 'running'
                            if status not in {'pause_requested', 'cancel_requested', 'paused', 'cancelled'}:
                                status = 'running'
                            _extraction_tasks[task_id].update({
                                'status': status,
                                'stage': stage,
                                'progress': max(0, min(int(progress), 100)),
                                'message': message,
                                'detail': detail,
                                'cache_key': detail.get('cache_key') or _extraction_tasks[task_id].get('cache_key'),
                                'cache_status': detail.get('cache_status') or _extraction_tasks[task_id].get('cache_status'),
                                'updated_at': _now_iso(),
                            })
                            _persist_task(task_id)

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
                            task['updated_at'] = _now_iso()
                            # RAG 是与 LLM 提取并行的子任务，只更新子进度。
                            # 不再把 RAG 完成映射到主进度 95%，否则会误导用户以为整体解析即将完成。
                            existing_detail = task.get('detail') or {}
                            existing_detail['rag_progress'] = rag_payload
                            task['detail'] = existing_detail
                            _persist_task(task_id)

                progress_cb('preparing', 5, '正在初始化...')

                extractor = EnhancedWorldExtractor()
                text_len = len(text) if text else 0
                volume_profile = extractor.get_text_volume_profile(text_len)
                cache_key = extractor.build_cache_key(text or '', extraction_mode, volume_profile)
                source_hash = hashlib.sha256((text or '').encode('utf-8', errors='replace')).hexdigest()
                progress_cb(
                    'preparing',
                    6,
                    f"文本 {text_len} 字符，采用 {extraction_mode.upper()} 扫描：上下文 {volume_profile['context_window']}，目标 {volume_profile['target_chunk_chars']} 字/块",
                    {'volume_profile': volume_profile, 'cache_key': cache_key, 'context_window': volume_profile.get('context_window'), 'target_chunk_chars': volume_profile.get('target_chunk_chars')},
                )

                def should_cancel():
                    with _tasks_lock:
                        return bool(_extraction_tasks.get(task_id, {}).get('cancel_requested'))

                def should_pause():
                    with _tasks_lock:
                        return bool(_extraction_tasks.get(task_id, {}).get('pause_requested'))

                # ── 启动 RAG 索引（与 LLM 提取并行）──
                world_id = request_data.get('world_id', '').strip()
                emb_config = Config.get_embedding_config()
                if world_id and text and emb_config.get('api_key'):
                    def _do_rag():
                        try:
                            if should_cancel() or should_pause():
                                _rag_result[0] = {'rag_indexed': False, 'rag_skipped': True, 'rag_skip_reason': '扫描已暂停或中断'}
                                rag_progress_cb('skipped', 100, '扫描已暂停/中断，跳过 RAG 索引')
                                return
                            from ..services.rag_service import RagService
                            rag = RagService(world_id)
                            doc_ids = rag.add_text_chunks(
                                text=text,
                                chunk_size=volume_profile['rag_chunk_size'],
                                chunk_overlap=volume_profile['rag_chunk_overlap'],
                                source="extraction",
                                metadata={
                                    "filename": ", ".join(uploaded_filenames) if uploaded_filenames else "direct_text",
                                    "volume_profile": volume_profile['profile'],
                                    "source_text_length": text_len,
                                    "source_hash": source_hash,
                                    "cache_key": cache_key,
                                    "rag_profile": volume_profile.get('rag_profile', 'novel'),
                                    "extraction_mode": extraction_mode,
                                },
                                chunk_preset=volume_profile['rag_chunk_preset'],
                                progress_callback=rag_progress_cb,
                                should_stop=lambda: should_cancel() or should_pause(),
                            )
                            if should_cancel() or should_pause():
                                _rag_result[0] = {'rag_indexed': False, 'rag_skipped': True, 'rag_skip_reason': '扫描已暂停或中断'}
                                return
                            stats = rag.get_stats()
                            _rag_result[0] = {
                                'rag_indexed': True,
                                'rag_added_count': len(doc_ids),
                                'rag_document_count': stats.get('document_count', 0),
                                'rag_volume_profile': volume_profile,
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

                if text_len > extractor.LONG_TEXT_THRESHOLD:
                    progress_cb('chunking', 8, f"文本 {text_len} 字符，正在按 {volume_profile['profile']} 策略章节感知切分...", {'volume_profile': volume_profile})

                # LLM 提取（与 RAG 并行进行中）
                result = extractor.extract_from_text(
                    text,
                    progress_callback=progress_cb,
                    extraction_mode=extraction_mode,
                    force_rebuild=force_rebuild,
                    should_cancel=should_cancel,
                    should_pause=should_pause,
                )
                result.setdefault('extraction_diagnostics', {})['volume_profile'] = volume_profile
                result['extraction_mode'] = extraction_mode

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
                    progress_cb('extracting', max(88, int(_extraction_tasks.get(task_id, {}).get('progress', 88))), '世界观提取已完成，正在等待向量索引收尾...')
                    _rag_thread.join()
                    import time as _time
                    _time.sleep(0.3)  # 让前端看到收尾状态
                if _rag_result[0]:
                    result.update(_rag_result[0])

                with _tasks_lock:
                    cancelled = bool(result.get('cancelled') or _extraction_tasks.get(task_id, {}).get('cancel_requested'))
                    paused = bool(result.get('paused') or _extraction_tasks.get(task_id, {}).get('pause_requested'))
                    final_status = 'cancelled' if cancelled else ('paused' if paused else 'completed')
                    _extraction_tasks[task_id].update({
                        'status': final_status,
                        'stage': final_status if final_status != 'completed' else 'done',
                        'progress': int(_extraction_tasks[task_id].get('progress', 100)) if (cancelled or paused) else 100,
                        'message': f'已中断并保存当前成果: {len(result.get("entities", []))} 实体, {len(result.get("events", []))} 事件' if cancelled else (f'已暂停并保存当前成果: {len(result.get("entities", []))} 实体, {len(result.get("events", []))} 事件' if paused else f'提取完成: {len(result.get("entities", []))} 实体, {len(result.get("events", []))} 事件'),
                        'done': True,
                        'result': result,
                        'result_summary': _task_result_summary(result),
                        'finished_at': _now_iso(),
                    })
                    _persist_task(task_id)
                _running_threads.discard(task_id)
            except Exception as e:
                logger.error(f"后台提取失败 [{task_id}]: {e}")
                with _tasks_lock:
                    _extraction_tasks[task_id].update({
                        'status': 'failed',
                        'stage': 'error', 'done': True,
                        'error': str(e),
                        'message': f'提取失败: {str(e)[:100]}',
                        'finished_at': _now_iso(),
                    })
                    _persist_task(task_id)
                _running_threads.discard(task_id)

        _running_threads.add(task_id)
        threading.Thread(target=run_extraction, daemon=True).start()

        resp = {
            'success': True,
            'task_id': task_id,
            'message': '提取任务已启动',
            'extraction_mode': extraction_mode,
            'force_rebuild': force_rebuild,
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


@world_build_bp.route('/extract/tasks', methods=['GET'])
def list_extract_tasks():
    """列出最近的世界观解析任务。"""
    _ensure_tasks_loaded()
    active_only = str(request.args.get('active', '')).lower() in {'1', 'true', 'yes'}
    limit = max(1, min(int(request.args.get('limit', 10) or 10), 50))
    active_statuses = {'running', 'pause_requested', 'paused', 'cancel_requested', 'stale'}
    with _tasks_lock:
        tasks = []
        for task_id, task in _extraction_tasks.items():
            status = _repair_finished_task_status(task_id, task)
            if active_only and status not in active_statuses:
                continue
            item = {key: value for key, value in task.items() if key != 'result'}
            item['task_id'] = task_id
            tasks.append(item)
    tasks.sort(key=lambda item: item.get('updated_at') or item.get('created_at') or '', reverse=True)
    return jsonify({'success': True, 'tasks': tasks[:limit]})


@world_build_bp.route('/extract/<task_id>', methods=['DELETE'])
def delete_extract_task(task_id):
    """删除已结束/已暂停的解析任务记录。"""
    _ensure_tasks_loaded()
    with _tasks_lock:
        task = _extraction_tasks.get(task_id)
        if not task:
            return jsonify({'success': True, 'message': '任务记录已不存在'})
        status = _repair_finished_task_status(task_id, task)
        if not task.get('done') and (task_id in _running_threads or status in {'running', 'pause_requested', 'cancel_requested'}):
            return jsonify({'success': False, 'message': '任务仍在运行，不能删除'}), 400
        _extraction_tasks.pop(task_id, None)
    try:
        path = _task_path(task_id)
        if os.path.exists(path):
            os.remove(path)
        result_path = _task_result_path(task_id)
        if os.path.exists(result_path):
            os.remove(result_path)
    except Exception as exc:
        logger.warning(f'删除提取任务文件失败 [{task_id}]: {exc}')
        return jsonify({'success': False, 'message': f'任务文件删除失败: {exc}'}), 500
    return jsonify({'success': True, 'message': '扫描任务已删除'})


@world_build_bp.route('/extract/<task_id>/cancel', methods=['POST'])
def cancel_extract(task_id):
    """请求中断提取任务；已完成的块会由后台线程保存为部分成果。"""
    _ensure_tasks_loaded()
    with _tasks_lock:
        task = _extraction_tasks.get(task_id)
        if not task:
            return jsonify({'success': False, 'message': '任务不存在或已过期'}), 404
        status = _repair_finished_task_status(task_id, task)
        if status in {'paused', 'stale'} and task_id not in _running_threads:
            task['cancel_requested'] = True
            task['status'] = 'cancelled'
            task['stage'] = 'cancelled'
            task['done'] = True
            task['message'] = '浠诲姟宸蹭腑鏂紝鍙互瀹夊叏鍒犻櫎'
            task['finished_at'] = task.get('finished_at') or _now_iso()
            _persist_task(task_id)
            return jsonify({'success': True, 'message': '浠诲姟宸蹭腑鏂紝鍙互瀹夊叏鍒犻櫎', 'done': True, 'stage': task.get('stage'), 'status': task.get('status')})
        if task.get('done') and status not in {'paused', 'stale'}:
            return jsonify({'success': True, 'message': '任务已结束', 'done': True, 'stage': task.get('stage'), 'status': task.get('status')})
        task['cancel_requested'] = True
        task['status'] = 'cancel_requested'
        task['stage'] = 'cancel_requested'
        task['message'] = '正在中断提取并保存当前成果...'
        _persist_task(task_id)
    return jsonify({'success': True, 'message': '已请求中断，当前块完成后将保存部分成果'})


@world_build_bp.route('/extract/<task_id>/pause', methods=['POST'])
def pause_extract(task_id):
    """请求暂停解析任务；当前块完成后停在 checkpoint。"""
    _ensure_tasks_loaded()
    with _tasks_lock:
        task = _extraction_tasks.get(task_id)
        if not task:
            return jsonify({'success': False, 'message': '任务不存在或已过期'}), 404
        status = task.get('status')
        if status in {'paused', 'stale'}:
            return jsonify({'success': True, 'message': '任务已暂停', 'status': status})
        if task.get('done') and status not in {'running', 'pause_requested'}:
            return jsonify({'success': False, 'message': '任务已结束，无法暂停', 'status': status}), 400
        task['pause_requested'] = True
        task['status'] = 'pause_requested'
        task['stage'] = 'pause_requested'
        task['message'] = '正在暂停解析，当前块完成后保存 checkpoint...'
        _persist_task(task_id)
    return jsonify({'success': True, 'message': '已请求暂停，当前块完成后将保存进度'})


def _run_resume_task(task_id):
    try:
        extractor = EnhancedWorldExtractor()

        def progress_cb(stage, progress, message, detail=None):
            detail = detail or {}
            total_chunks = int(detail.get('total_chunks') or 0)
            completed_chunks = int(detail.get('completed_chunks') or 0)
            if total_chunks > 0:
                progress = 8 + int(completed_chunks / max(total_chunks, 1) * 80)
            _update_task(
                task_id,
                status='running',
                stage=stage,
                progress=max(0, min(int(progress), 100)),
                message=message,
                detail=detail,
                cache_key=detail.get('cache_key') or _extraction_tasks.get(task_id, {}).get('cache_key'),
                cache_status=detail.get('cache_status') or _extraction_tasks.get(task_id, {}).get('cache_status'),
            )

        def should_cancel():
            with _tasks_lock:
                return bool(_extraction_tasks.get(task_id, {}).get('cancel_requested'))

        def should_pause():
            with _tasks_lock:
                return bool(_extraction_tasks.get(task_id, {}).get('pause_requested'))

        with _tasks_lock:
            cache_key = _extraction_tasks.get(task_id, {}).get('cache_key')
        if not cache_key:
            raise ValueError('任务缺少 cache_key，无法继续')
        result = extractor.resume_from_cache(cache_key, progress_callback=progress_cb, should_cancel=should_cancel, should_pause=should_pause)
        with _tasks_lock:
            task = _extraction_tasks.get(task_id, {})
            cancelled = bool(result.get('cancelled') or task.get('cancel_requested'))
            paused = bool(result.get('paused') or task.get('pause_requested'))
            final_status = 'cancelled' if cancelled else ('paused' if paused else 'completed')
        _update_task(
            task_id,
            status=final_status,
            stage=final_status if final_status != 'completed' else 'done',
            progress=int(_extraction_tasks.get(task_id, {}).get('progress', 100)) if (cancelled or paused) else 100,
            message=f'已中断并保存当前成果: {len(result.get("entities", []))} 实体, {len(result.get("events", []))} 事件' if cancelled else (f'已暂停并保存当前成果: {len(result.get("entities", []))} 实体, {len(result.get("events", []))} 事件' if paused else f'提取完成: {len(result.get("entities", []))} 实体, {len(result.get("events", []))} 事件'),
            done=True,
            result=result,
            result_summary=_task_result_summary(result),
            finished_at=_now_iso(),
        )
    except Exception as exc:
        logger.error(f"继续提取失败 [{task_id}]: {exc}")
        _update_task(task_id, status='failed', stage='error', done=True, error=str(exc), message=f'继续失败: {str(exc)[:100]}', finished_at=_now_iso())
    finally:
        _running_threads.discard(task_id)


@world_build_bp.route('/extract/<task_id>/resume', methods=['POST'])
def resume_extract(task_id):
    """从缓存继续暂停或意外中断的解析任务。"""
    _ensure_tasks_loaded()
    with _tasks_lock:
        task = _extraction_tasks.get(task_id)
        if not task:
            return jsonify({'success': False, 'message': '任务不存在或已过期'}), 404
        if task_id in _running_threads or task.get('status') in {'running', 'pause_requested', 'cancel_requested'}:
            return jsonify({'success': True, 'message': '任务已在运行', 'task_id': task_id})
        if not task.get('cache_key'):
            return jsonify({'success': False, 'message': '任务缺少缓存信息，无法继续'}), 400
        task.update({
            'status': 'running',
            'stage': 'starting',
            'done': False,
            'error': None,
            'cancel_requested': False,
            'pause_requested': False,
            'message': '正在从上次 checkpoint 继续解析...',
            'started_at': _now_iso(),
            'finished_at': None,
        })
        _persist_task(task_id)
        _running_threads.add(task_id)
    threading.Thread(target=_run_resume_task, args=(task_id,), daemon=True).start()
    return jsonify({'success': True, 'task_id': task_id, 'message': '已继续解析任务'})


@world_build_bp.route('/extract/<task_id>/progress', methods=['GET'])
def extract_progress(task_id):
    """轮询提取任务进度"""
    _ensure_tasks_loaded()
    with _tasks_lock:
        task_ref = _extraction_tasks.get(task_id)
        if task_ref:
            _repair_finished_task_status(task_id, task_ref)
        task = dict(task_ref or {})
    if not task:
        return jsonify({'success': False, 'message': '任务不存在或已过期'}), 404
    resp = {
        'success': True,
        'task_id': task_id,
        'status': task.get('status') or task.get('stage'),
        'stage': task['stage'],
        'progress': task['progress'],
        'message': task['message'],
        'detail': task.get('detail') or {},
        'rag_progress': task.get('rag_progress'),
        'done': task['done'],
        'extraction_mode': task.get('extraction_mode'),
        'force_rebuild': task.get('force_rebuild'),
    }
    detail = task.get('detail') or {}
    for key in ['cache_key', 'cache_status', 'resumed_from_cache', 'completed_chunks', 'failed_chunks', 'total_chunks', 'processed_chars', 'total_chars', 'processed_chars_label', 'total_chars_label', 'context_window', 'target_chunk_chars']:
        if key in detail:
            resp[key] = detail[key]
    if task['done']:
        result = _load_task_result(task_id, task)
        if result:
            resp['extracted_data'] = result
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
        if data.get('settings') and isinstance(data.get('settings'), dict):
            settings = data['settings']
            config = Config.save_agent_settings(
                thinking_enabled=settings.get('thinking_enabled') if 'thinking_enabled' in settings else None,
                reasoning_effort=settings.get('reasoning_effort') if 'reasoning_effort' in settings else None,
                context_window=settings.get('context_window') if 'context_window' in settings else None,
                compression_threshold=settings.get('compression_threshold') if 'compression_threshold' in settings else None,
            )
            config = Config.get_llm_config_status()
        elif data.get('role') == 'embedding':
            config = Config.save_embedding_config(
                api_key=data.get('api_key') if 'api_key' in data else None,
                base_url=data.get('base_url') if 'base_url' in data else None,
                model_name=data.get('model_name') if 'model_name' in data else None,
                api_type=data.get('api_type') if 'api_type' in data else None,
                url_mode=data.get('url_mode') if 'url_mode' in data else None,
            )
        else:
            config = Config.save_llm_config(
                role=data.get('role') or 'agent',
                api_key=data.get('api_key') if 'api_key' in data else None,
                base_url=data.get('base_url') if 'base_url' in data else None,
                model_name=data.get('model_name') if 'model_name' in data else None,
                api_type=data.get('api_type') if 'api_type' in data else None,
                url_mode=data.get('url_mode') if 'url_mode' in data else None,
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


@world_build_bp.route('/llm-config/models', methods=['POST'])
def list_llm_models():
    """按当前或传入配置获取模型列表。"""
    try:
        data = request.json or {}
        role = data.get('role') or 'agent'
        resolved_llm = Config.get_embedding_config() if role == 'embedding' else Config.get_llm_config(role)
        api_key = data.get('api_key') or resolved_llm['api_key']
        base_url = data.get('base_url') or resolved_llm['base_url']
        api_type = data.get('api_type') or resolved_llm.get('api_type') or 'openai_compatible'
        url_mode = data.get('url_mode') or resolved_llm.get('url_mode') or 'base_url'
        if not api_key:
            return jsonify({'success': False, 'message': '请先提供 API Key'}), 400
        models = LLMClient.list_models(api_key=api_key, base_url=base_url, api_type=api_type, url_mode=url_mode)
        return jsonify({'success': True, 'models': models})
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取模型列表失败: {str(e)}'}), 400


@world_build_bp.route('/llm-config/test', methods=['POST'])
def test_llm_config():
    """测试当前或传入的 LLM 配置。"""
    try:
        data = request.json or {}

        role = data.get('role') or 'agent'
        if role == 'embedding':
            resolved_llm = Config.get_embedding_config()
        else:
            resolved_llm = Config.get_llm_config(role)
        api_key = data.get('api_key') or resolved_llm['api_key']
        base_url = data.get('base_url') or resolved_llm['base_url']
        model_name = data.get('model_name') or resolved_llm['model_name']
        api_type = data.get('api_type') or resolved_llm.get('api_type') or 'openai_compatible'
        url_mode = data.get('url_mode') or resolved_llm.get('url_mode') or 'base_url'

        if not api_key:
            return jsonify({
                'success': False,
                'message': '请先提供 LLM API Key'
            }), 400

        test_result = LLMClient.test_connection(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            api_type=api_type,
            url_mode=url_mode,
        )

        return jsonify({
            'success': True,
            'message': 'LLM 连接测试成功',
            'config': {
                'api_key_configured': bool(api_key),
                'api_key_masked': Config.mask_secret(api_key),
                'base_url': base_url,
                'model_name': model_name,
                'api_type': api_type,
                'url_mode': url_mode,
            },
            'test_result': test_result,
        })
    except Exception as e:
        logger.error(f"测试 LLM 配置失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        }), 400


def _get_world_or_404(world_id):
    world = WorldManager.get_world(world_id)
    if not world:
        return None, (jsonify({'success': False, 'message': '世界观不存在'}), 404)
    return world, None


@world_build_bp.route('/<world_id>/maps', methods=['GET'])
def list_world_maps(world_id):
    """列出世界观下的结构化地图。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        maps = list_structured_maps(world)
        save_maps(world, maps)
        WorldManager.save_world(world)
        return jsonify({'success': True, 'maps': [summarize_map(item) for item in maps]})
    except Exception as e:
        logger.error(f"列出地图失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps', methods=['POST'])
def create_world_map(world_id):
    """创建结构化六边形地图。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        data = request.json or {}
        maps = list_structured_maps(world)
        new_id = create_map_id()
        raw_map = {
            'id': new_id,
            'world_id': world_id,
            'name': data.get('name') or '未命名地图',
            'description': data.get('description') or '',
            'type': data.get('type') or 'world',
            'width': data.get('width') or 12,
            'height': data.get('height') or 8,
            'is_default': bool(data.get('is_default') or not maps),
        }
        created = normalize_map(raw_map, world_id)
        if created.get('is_default'):
            for item in maps:
                item['is_default'] = False
        maps.append(created)
        save_maps(world, maps)
        WorldManager.save_world(world)
        return jsonify({'success': True, 'map': created, 'message': '地图创建成功'})
    except Exception as e:
        logger.error(f"创建地图失败: {str(e)}")
        return jsonify({'success': False, 'message': f'创建失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps/<map_id>', methods=['GET'])
def get_world_map(world_id, map_id):
    """获取完整地图。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        maps = list_structured_maps(world)
        target = find_map(maps, map_id)
        if not target:
            return jsonify({'success': False, 'message': '地图不存在'}), 404
        return jsonify({'success': True, 'map': target, 'stats': stats_for_map(target)})
    except Exception as e:
        logger.error(f"获取地图失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps/<map_id>', methods=['PUT'])
def update_world_map(world_id, map_id):
    """更新地图基础信息。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        data = request.json or {}
        maps = list_structured_maps(world)
        target = find_map(maps, map_id)
        if not target:
            return jsonify({'success': False, 'message': '地图不存在'}), 404
        before = copy.deepcopy(summarize_map(target))
        for field in ['name', 'description', 'type']:
            if field in data:
                target[field] = str(data.get(field) or '').strip()
        if 'view' in data and isinstance(data.get('view'), dict):
            target['view'] = {**target.get('view', {}), **data['view']}
        from app.models.map import now_iso
        target['updated_at'] = now_iso()
        add_change_record(target, 'map', map_id, before, summarize_map(target), source=data.get('source') or 'user')
        save_maps(world, maps)
        WorldManager.save_world(world)
        return jsonify({'success': True, 'map': target, 'message': '地图已更新'})
    except Exception as e:
        logger.error(f"更新地图失败: {str(e)}")
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps/<map_id>', methods=['DELETE'])
def delete_world_map(world_id, map_id):
    """删除结构化地图。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        maps = list_structured_maps(world)
        remaining = [item for item in maps if item.get('id') != map_id]
        if len(remaining) == len(maps):
            return jsonify({'success': False, 'message': '地图不存在'}), 404
        save_maps(world, remaining)
        WorldManager.save_world(world)
        return jsonify({'success': True, 'message': '地图已删除'})
    except Exception as e:
        logger.error(f"删除地图失败: {str(e)}")
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps/<map_id>/duplicate', methods=['POST'])
def duplicate_world_map(world_id, map_id):
    """复制地图。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        maps = list_structured_maps(world)
        target = find_map(maps, map_id)
        if not target:
            return jsonify({'success': False, 'message': '地图不存在'}), 404
        copied = copy.deepcopy(target)
        new_id = create_map_id()
        copied['id'] = new_id
        copied['name'] = f"{target.get('name') or '地图'} 副本"
        copied['is_default'] = False
        for cell in copied.get('cells', []):
            cell['map_id'] = new_id
        copied = normalize_map(copied, world_id)
        maps.append(copied)
        save_maps(world, maps)
        WorldManager.save_world(world)
        return jsonify({'success': True, 'map': copied, 'message': '地图已复制'})
    except Exception as e:
        logger.error(f"复制地图失败: {str(e)}")
        return jsonify({'success': False, 'message': f'复制失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps/<map_id>/default', methods=['PUT'])
def set_default_world_map(world_id, map_id):
    """设置默认地图。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        maps = list_structured_maps(world)
        target = find_map(maps, map_id)
        if not target:
            return jsonify({'success': False, 'message': '地图不存在'}), 404
        for item in maps:
            item['is_default'] = item.get('id') == map_id
        save_maps(world, maps)
        WorldManager.save_world(world)
        return jsonify({'success': True, 'maps': [summarize_map(item) for item in maps], 'message': '默认地图已更新'})
    except Exception as e:
        logger.error(f"设置默认地图失败: {str(e)}")
        return jsonify({'success': False, 'message': f'设置失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps/<map_id>/cells/<cell_id>', methods=['PUT'])
def update_world_map_cell(world_id, map_id, cell_id):
    """更新地图单元。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        data = request.json or {}
        maps = list_structured_maps(world)
        target_map = find_map(maps, map_id)
        if not target_map:
            return jsonify({'success': False, 'message': '地图不存在'}), 404
        target_cell = find_cell(target_map, cell_id)
        if not target_cell:
            return jsonify({'success': False, 'message': '地图单元不存在'}), 404
        before = copy.deepcopy(target_cell)
        updated = apply_cell_update(target_cell, data)
        target_map['cells'] = [updated if cell.get('id') == cell_id else cell for cell in target_map.get('cells', [])]
        target_map['updated_at'] = updated.get('updated_at')
        add_change_record(target_map, 'cell', cell_id, before, updated, source=data.get('source') or 'user', agent=bool(data.get('is_agent')))
        save_maps(world, maps)
        WorldManager.save_world(world)
        return jsonify({'success': True, 'cell': updated, 'message': '地图单元已更新'})
    except Exception as e:
        logger.error(f"更新地图单元失败: {str(e)}")
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps/<map_id>/cells/batch', methods=['POST'])
def batch_update_world_map_cells(world_id, map_id):
    """批量更新地图单元。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        data = request.json or {}
        cell_ids = set(data.get('cell_ids') or [])
        if not cell_ids:
            return jsonify({'success': False, 'message': '请提供要修改的地图单元'}), 400
        updates = data.get('updates') if isinstance(data.get('updates'), dict) else {}
        maps = list_structured_maps(world)
        target_map = find_map(maps, map_id)
        if not target_map:
            return jsonify({'success': False, 'message': '地图不存在'}), 404
        changed = []
        new_cells = []
        for cell in target_map.get('cells', []):
            if cell.get('id') in cell_ids:
                before = copy.deepcopy(cell)
                updated = apply_batch_update(cell, updates)
                changed.append(updated)
                add_change_record(target_map, 'cell', cell.get('id'), before, updated, source=data.get('source') or 'user', agent=bool(data.get('is_agent')))
                new_cells.append(updated)
            else:
                new_cells.append(cell)
        target_map['cells'] = new_cells
        from app.models.map import now_iso
        target_map['updated_at'] = now_iso()
        save_maps(world, maps)
        WorldManager.save_world(world)
        return jsonify({'success': True, 'updated_count': len(changed), 'cells': changed, 'message': f'已更新 {len(changed)} 个地图单元'})
    except Exception as e:
        logger.error(f"批量更新地图单元失败: {str(e)}")
        return jsonify({'success': False, 'message': f'批量更新失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps/<map_id>/search', methods=['GET'])
def search_world_map(world_id, map_id):
    """搜索地图单元。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        query = request.args.get('q', '')
        maps = list_structured_maps(world)
        target_map = find_map(maps, map_id)
        if not target_map:
            return jsonify({'success': False, 'message': '地图不存在'}), 404
        results = search_cells(target_map, query)[:100]
        compact = [{
            'id': cell.get('id'),
            'q': cell.get('q'),
            'r': cell.get('r'),
            'name': cell.get('name'),
            'terrain': cell.get('terrain'),
            'status': cell.get('status'),
            'faction': cell.get('faction'),
            'resources': cell.get('resources') or [],
        } for cell in results]
        return jsonify({'success': True, 'results': compact, 'total': len(results)})
    except Exception as e:
        logger.error(f"搜索地图失败: {str(e)}")
        return jsonify({'success': False, 'message': f'搜索失败: {str(e)}'}), 500


@world_build_bp.route('/<world_id>/maps/<map_id>/cells/<cell_id>/neighbors', methods=['GET'])
def get_world_map_cell_neighbors(world_id, map_id, cell_id):
    """获取地图单元邻接关系。"""
    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        maps = list_structured_maps(world)
        target_map = find_map(maps, map_id)
        if not target_map:
            return jsonify({'success': False, 'message': '地图不存在'}), 404
        target_cell = find_cell(target_map, cell_id)
        if not target_cell:
            return jsonify({'success': False, 'message': '地图单元不存在'}), 404
        return jsonify({'success': True, 'neighbors': cell_neighbors(target_map, target_cell)})
    except Exception as e:
        logger.error(f"获取邻接单元失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


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
        try:
            from ..services.rag_service import RagService
            RagService.delete_world_rag(world_id)
        except Exception as rag_exc:
            logger.warning(f"删除世界观 RAG 失败 [{world_id}]: {rag_exc}")

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
