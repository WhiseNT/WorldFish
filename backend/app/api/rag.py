"""RAG API — 世界观向量知识库 CRUD + 检索。"""

import threading
import traceback
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

from ..config import Config
from ..services.rag_service import RagService
from ..models.world import WorldManager
from ..utils.logger import get_logger

rag_bp = Blueprint("rag", __name__)
logger = get_logger("worldfish.api.rag")

_index_tasks = {}
_index_tasks_lock = threading.Lock()


def _update_index_task(task_id: str, **updates):
    with _index_tasks_lock:
        if task_id in _index_tasks:
            _index_tasks[task_id].update(updates)
            _index_tasks[task_id]["updated_at"] = datetime.now().isoformat()


def _get_rag_service(world_id: str) -> RagService:
    """获取 RAG 服务实例（校验世界观存在）。"""
    world = WorldManager.get_world(world_id)
    if not world:
        raise ValueError(f"世界观不存在: {world_id}")
    return RagService(world_id)


# ============== 文档管理 ==============


@rag_bp.route("/rag/chunk-presets", methods=["GET"])
def get_chunk_presets():
    """获取 RAG 切分预设。"""
    return jsonify({"success": True, "data": {"presets": RagService.get_chunk_presets()}})


@rag_bp.route("/<world_id>/rag/documents", methods=["POST"])
def add_documents(world_id: str):
    """添加文档到 RAG。

    请求（JSON）：
        {
            "texts": ["文本1", "文本2"],          // 或
            "text": "长文本",                      // 单个长文本（按文本量自动切块）
            "chunk_size": 800,                     // 兼容旧参数，会被自动策略忽略
            "chunk_overlap": 100,                  // 兼容旧参数，会被自动策略忽略
            "source": "manual",                    // 可选
            "metadata": {}                         // 可选
        }

    返回：
        {
            "success": true,
            "data": {
                "added_count": 3,
                "total_count": 3,
                "doc_ids": ["rag_xxx", ...]
            }
        }
    """
    try:
        rag = _get_rag_service(world_id)
        data = request.get_json() or {}

        texts = data.get("texts")
        single_text = data.get("text")
        source = data.get("source", "manual")
        metadata = data.get("metadata")

        if texts and isinstance(texts, list):
            doc_ids = rag.add_documents(
                texts=[str(t).strip() for t in texts if str(t).strip()],
                source=source,
                metadatas=[dict(metadata or {}) for _ in texts] if metadata else None,
            )
        elif single_text and str(single_text).strip():
            chunk_preset = data.get("chunk_preset")
            doc_ids = rag.add_text_chunks(
                text=str(single_text).strip(),
                source=source,
                metadata=metadata,
                chunk_preset=chunk_preset,
            )
        else:
            return jsonify({"success": False, "error": "请提供 texts 或 text 参数"}), 400

        return jsonify({
            "success": True,
            "data": {
                "added_count": len(doc_ids),
                "total_count": rag.count(),
                "doc_ids": doc_ids,
            },
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"添加 RAG 文档失败: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/<world_id>/rag/documents", methods=["GET"])
def list_documents(world_id: str):
    """列出 RAG 中的文档（分页）。

    Query 参数：limit (默认 100), offset (默认 0)
    """
    try:
        rag = _get_rag_service(world_id)
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        docs = rag.list_documents(limit=limit, offset=offset)
        return jsonify({
            "success": True,
            "data": {
                "documents": [d.to_dict() for d in docs],
                "total_count": rag.count(),
                "limit": limit,
                "offset": offset,
            },
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"列出 RAG 文档失败: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/<world_id>/rag/documents/<doc_id>", methods=["DELETE"])
def delete_document(world_id: str, doc_id: str):
    """删除 RAG 中的单个文档。"""
    try:
        rag = _get_rag_service(world_id)
        ok = rag.delete_document(doc_id)
        return jsonify({
            "success": ok,
            "data": {"deleted": ok, "total_count": rag.count()},
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"删除 RAG 文档失败: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============== 检索 ==============


@rag_bp.route("/<world_id>/rag/search", methods=["POST"])
def search_rag(world_id: str):
    """语义检索 RAG。

    请求（JSON）：
        {
            "query": "这个世界的魔法体系是怎样的？",
            "top_k": 5,                // 可选
            "source": "manual"         // 可选，按来源过滤
        }

    返回：
        {
            "success": true,
            "data": {
                "query": "...",
                "results": [
                    {"doc_id": "rag_xxx", "text": "...", "score": 0.95, "metadata": {...}},
                    ...
                ]
            }
        }
    """
    try:
        rag = _get_rag_service(world_id)
        data = request.get_json() or {}
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"success": False, "error": "请提供 query 参数"}), 400

        top_k = data.get("top_k")
        where = None
        if data.get("source"):
            where = {"source": data["source"]}

        results = rag.search(query=query, top_k=top_k, where=where)

        return jsonify({
            "success": True,
            "data": {
                "query": query,
                "results": [r.to_dict() for r in results],
            },
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"RAG 检索失败: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============== 管理 ==============


@rag_bp.route("/<world_id>/rag/stats", methods=["GET"])
def get_rag_stats(world_id: str):
    """获取 RAG 统计信息。"""
    try:
        rag = _get_rag_service(world_id)
        return jsonify({
            "success": True,
            "data": rag.get_stats(),
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"获取 RAG 统计失败: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/<world_id>/rag/clear", methods=["DELETE"])
def clear_rag(world_id: str):
    """清空 RAG Collection。"""
    try:
        rag = _get_rag_service(world_id)
        ok = rag.delete_all()
        return jsonify({
            "success": ok,
            "data": {"cleared": ok},
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"清空 RAG 失败: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============== 文件上传 ==============


@rag_bp.route("/<world_id>/rag/index-task", methods=["POST"])
def create_index_task(world_id: str):
    """异步添加文本到 RAG，提供真实 Embedding 进度。"""
    try:
        _get_rag_service(world_id)
        data = request.get_json() or {}
        text = str(data.get("text") or "").strip()
        if not text:
            return jsonify({"success": False, "error": "请提供 text 参数"}), 400

        task_id = f"ragidx_{uuid.uuid4().hex[:12]}"
        with _index_tasks_lock:
            _index_tasks[task_id] = {
                "task_id": task_id,
                "world_id": world_id,
                "stage": "queued",
                "progress": 0,
                "message": "索引任务已创建",
                "detail": {},
                "done": False,
                "error": None,
                "result": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

        def run_task():
            try:
                rag = _get_rag_service(world_id)

                def progress_cb(stage, progress, message, detail=None):
                    _update_index_task(task_id, stage=stage, progress=progress, message=message, detail=detail or {})

                doc_ids = rag.add_text_chunks(
                    text=text,
                    source=data.get("source", "manual"),
                    metadata=data.get("metadata") or {},
                    chunk_preset=data.get("chunk_preset"),
                    progress_callback=progress_cb,
                )
                result = {"added_count": len(doc_ids), "total_count": rag.count(), "doc_ids": doc_ids}
                _update_index_task(task_id, stage="done", progress=100, message=f"索引完成：新增 {len(doc_ids)} 个文本块", detail=result, done=True, result=result)
            except Exception as e:
                logger.error(f"RAG 索引任务失败: {traceback.format_exc()}")
                _update_index_task(task_id, stage="error", progress=100, message=f"索引失败: {str(e)[:120]}", error=str(e), done=True)

        threading.Thread(target=run_task, daemon=True).start()
        return jsonify({"success": True, "data": {"task_id": task_id}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"创建 RAG 索引任务失败: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/<world_id>/rag/index-task/<task_id>", methods=["GET"])
def get_index_task(world_id: str, task_id: str):
    with _index_tasks_lock:
        task = dict(_index_tasks.get(task_id) or {})
    if not task or task.get("world_id") != world_id:
        return jsonify({"success": False, "error": "任务不存在或已过期"}), 404
    return jsonify({"success": True, "data": task})


@rag_bp.route("/<world_id>/rag/upload", methods=["POST"])
def upload_rag_file(world_id: str):
    """上传文件到 RAG 知识库。

    支持 PDF、Markdown、TXT 文件。
    文件提取文本后自动切块并插入向量库。
    """
    import os
    import uuid
    import time
    from ..utils.file_parser import FileParser

    try:
        rag = _get_rag_service(world_id)

        if "files" not in request.files:
            return jsonify({"success": False, "error": "请上传文件"}), 400

        files = request.files.getlist("files")
        chunk_preset = request.form.get("chunk_preset") or None

        results = []
        total_added = 0

        for file in files:
            if not file or not file.filename:
                continue

            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in FileParser.SUPPORTED_EXTENSIONS:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "message": f"不支持的文件格式: {ext}",
                })
                continue

            safe_name = f"rag_{int(time.time())}_{uuid.uuid4().hex[:8]}_{file.filename}"
            file_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            try:
                file.save(file_path)

                # 与世界观构建相同的提取 + 切块流程
                text = FileParser.extract_text(file_path)
                if not text.strip():
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "message": "文件内容为空",
                    })
                    continue

                # 预处理文本（标准化换行、去除多余空白）
                from ..services.text_processor import TextProcessor
                text = TextProcessor.preprocess_text(text)

                doc_ids = rag.add_text_chunks(
                    text=text,
                    source="file",
                    metadata={"filename": file.filename},
                    chunk_preset=chunk_preset,
                )
                if not doc_ids:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "message": "文本切块后无有效内容",
                    })
                    continue

                total_added += len(doc_ids)
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "message": f"已添加 {len(doc_ids)} 个文档块（{len(text)} 字符 → {len(doc_ids)} 块）",
                    "chunks": len(doc_ids),
                    "chars": len(text),
                })
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "message": f"处理失败: {str(e)}",
                })
            finally:
                try:
                    os.remove(file_path)
                except OSError:
                    pass

        return jsonify({
            "success": True,
            "data": {
                "total_added": total_added,
                "total_count": rag.count(),
                "results": results,
            },
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"上传 RAG 文件失败: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
