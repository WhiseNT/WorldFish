"""
Agent REST API
提供 Agent 对话、Session 管理、MCP、文件上传、Skill/Memory 管理等接口
"""

import json
import os
import uuid
import time
import threading

from flask import request, jsonify, Response, stream_with_context

from . import agent_bp
from ..config import Config
from ..models.world import WorldManager
from ..models.agent import (
    AgentManager, AgentSession, AgentMessage,
    Skill,
)
from ..services.agent_service import AgentService
from ..utils.logger import get_logger

logger = get_logger("mirofish.api.agent")

# 全局 Agent 服务实例
agent_service = AgentService()

# SSE 活动连接管理
_active_sse = {}  # session_id -> bool (是否还在活跃)
_sse_lock = threading.Lock()


# ============================================================
# 全局 SSE 消息广播 —— 用于跨页面同步
# ============================================================

# 全局 SSE 监听器列表（用于聊天窗口实时获取后端消息）
_global_sse_listeners = []  # List[queue.Queue]
_global_sse_lock = threading.Lock()


def _broadcast_agent_event(event_type: str, data: dict):
    """向所有全局监听器广播 Agent 事件"""
    with _global_sse_lock:
        dead = []
        for q in _global_sse_listeners:
            try:
                q.put({"event": event_type, "data": data})
            except Exception:
                dead.append(q)
        for q in dead:
            _global_sse_listeners.remove(q)


# ============================================================
# Session CRUD
# ============================================================

@agent_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """列出所有 Session"""
    world_id = request.args.get("world_id", "")
    sessions = AgentManager.list_sessions(world_id=world_id if world_id else None)
    return jsonify({
        "success": True,
        "sessions": [
            {
                "session_id": s.session_id,
                "world_id": s.world_id,
                "title": s.title,
                "message_count": len(s.messages),
                "usage": s.usage,
                "context_stats": s.context_stats,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in sessions
        ]
    })


@agent_bp.route("/sessions", methods=["POST"])
def create_session():
    """创建新 Session"""
    data = request.json or {}
    world_id = data.get("world_id", "")
    title = data.get("title", "")
    session = AgentManager.create_session(world_id=world_id, title=title)
    return jsonify({
        "success": True,
        "session": session.to_dict(),
    })


@agent_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """获取 Session 详情"""
    session = AgentManager.get_session(session_id)
    if not session:
        return jsonify({"success": False, "message": "会话不存在"}), 404
    return jsonify({"success": True, "session": session.to_dict()})


@agent_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """删除 Session"""
    deleted = AgentManager.delete_session(session_id)
    return jsonify({"success": deleted, "message": "已删除" if deleted else "会话不存在"})


@agent_bp.route("/sessions/<session_id>/title", methods=["PUT"])
def update_session_title(session_id):
    """更新 Session 标题"""
    session = AgentManager.get_session(session_id)
    if not session:
        return jsonify({"success": False, "message": "会话不存在"}), 404
    data = request.json or {}
    session.title = data.get("title", session.title)
    AgentManager.save_session(session)
    return jsonify({"success": True, "session": session.to_dict()})


# ============================================================
# Agent Runtime Settings
# ============================================================

@agent_bp.route("/settings", methods=["GET"])
def get_agent_settings():
    """获取 Agent 运行设置。"""
    return jsonify({
        "success": True,
        "settings": Config.get_agent_settings_status(),
    })


@agent_bp.route("/settings", methods=["PUT"])
def update_agent_settings():
    """保存 Agent 运行设置。"""
    try:
        data = request.json or {}
        settings = Config.save_agent_settings(
            thinking_enabled=data.get("thinking_enabled") if "thinking_enabled" in data else None,
            reasoning_effort=data.get("reasoning_effort") if "reasoning_effort" in data else None,
            context_window=data.get("context_window") if "context_window" in data else None,
            compression_threshold=data.get("compression_threshold") if "compression_threshold" in data else None,
        )
        return jsonify({
            "success": True,
            "settings": settings,
            "message": "Agent 设置已保存",
        })
    except Exception as e:
        logger.error(f"保存 Agent 设置失败: {e}")
        return jsonify({
            "success": False,
            "message": f"保存失败: {str(e)}",
        }), 400


# ============================================================
# Chat (SSE Stream)
# ============================================================

@agent_bp.route("/chat", methods=["POST"])
def chat():
    """
    Agent 对话接口 — SSE 流式返回
    请求体: { session_id, message, world_id? }
    如果 session_id 为空，自动创建新 Session
    """
    data = request.json or {}
    session_id = data.get("session_id", "")
    user_message = data.get("message", "").strip()
    world_id = data.get("world_id", "")

    if not user_message:
        return jsonify({"success": False, "message": "消息不能为空"}), 400

    # 获取或创建 Session
    session = None
    if session_id:
        session = AgentManager.get_session(session_id)
    if not session:
        session = AgentManager.create_session(world_id=world_id)
        session_id = session.session_id

    # 如果指定了 world_id，更新 session
    if world_id and session.world_id != world_id:
        session.world_id = world_id
        AgentManager.save_session(session)

    def generate():
        """SSE 流生成器"""
        try:
            for chunk in agent_service.chat_stream(session, user_message, world_id):
                sse_data = json.dumps({
                    "type": chunk.type,
                    "content": chunk.content,
                    "data": chunk.data,
                    "session_id": session.session_id,
                }, ensure_ascii=False)
                yield f"data: {sse_data}\n\n"
        except Exception as e:
            logger.error(f"SSE error: {e}")
            error_data = json.dumps({
                "type": "error",
                "content": str(e),
                "session_id": session.session_id,
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@agent_bp.route("/chat/respond", methods=["POST"])
def chat_respond():
    """
    用户响应选项后继续对话
    请求体: { session_id, selected_options: string[], world_id? }
    """
    data = request.json or {}
    session_id = data.get("session_id", "")
    selected_options = data.get("selected_options", [])
    world_id = data.get("world_id", "")

    if not session_id:
        return jsonify({"success": False, "message": "缺少 session_id"}), 400

    session = AgentManager.get_session(session_id)
    if not session:
        return jsonify({"success": False, "message": "会话不存在"}), 404

    def generate():
        try:
            for chunk in agent_service.respond_to_options(session, selected_options, world_id):
                sse_data = json.dumps({
                    "type": chunk.type,
                    "content": chunk.content,
                    "data": chunk.data,
                    "session_id": session.session_id,
                }, ensure_ascii=False)
                yield f"data: {sse_data}\n\n"
        except Exception as e:
            logger.error(f"SSE error: {e}")
            error_data = json.dumps({
                "type": "error",
                "content": str(e),
                "session_id": session.session_id,
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============================================================
# 文件上传
# ============================================================

@agent_bp.route("/upload", methods=["POST"])
def upload_file():
    """上传文件到 Agent（在对话中使用）"""
    session_id = request.form.get("session_id", "")
    world_id = request.form.get("world_id", "")

    uploaded_files = request.files.getlist("files") if request.files else []
    if not uploaded_files:
        return jsonify({"success": False, "message": "没有上传文件"}), 400

    session = None
    if session_id:
        session = AgentManager.get_session(session_id)
    if not session:
        session = AgentManager.create_session(world_id=world_id)
        session_id = session.session_id

    results = []
    for file in uploaded_files:
        if not file or not file.filename:
            continue
        ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
        if ext not in Config.ALLOWED_EXTENSIONS:
            results.append({"filename": file.filename, "success": False, "message": f"不支持的文件格式: {ext}"})
            continue

        safe_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{file.filename}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
        file.save(file_path)

        try:
            summary = agent_service.process_uploaded_file(session, file_path, file.filename, world_id)
            results.append({"filename": file.filename, "success": True, "message": summary})
        except Exception as e:
            results.append({"filename": file.filename, "success": False, "message": str(e)})
        finally:
            try:
                os.remove(file_path)
            except OSError:
                pass

    return jsonify({
        "success": True,
        "session_id": session.session_id,
        "results": results,
        "message": f"已处理 {len(results)} 个文件",
    })


# ============================================================
# MCP 协议接口
# ============================================================

@agent_bp.route("/mcp", methods=["POST"])
def mcp_handler():
    """
    MCP (Model Context Protocol) JSON-RPC 接口
    支持: tools/list, tools/call, resources/list, resources/read
    """
    data = request.json or {}
    method = data.get("method", "")
    params = data.get("params", {})
    req_id = data.get("id")

    try:
        result = agent_service.mcp_handle(method, params)
        response = {"jsonrpc": "2.0", "id": req_id, "result": result}
        if "error" in result:
            response["error"] = {"code": -32602, "message": result["error"]}
            del response["result"]
        return jsonify(response)
    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": str(e)}
        }), 500


# ============================================================
# Agent.md 管理
# ============================================================

@agent_bp.route("/agent-md/<world_id>", methods=["GET"])
@agent_bp.route("/agent-md", methods=["GET"])
def get_agent_md(world_id=None):
    """获取 Agent.md 内容"""
    content = AgentManager.get_agent_md(world_id or "")
    return jsonify({
        "success": True,
        "content": content,
        "world_id": world_id or "",
    })


@agent_bp.route("/agent-md/<world_id>", methods=["PUT"])
@agent_bp.route("/agent-md", methods=["PUT"])
def save_agent_md(world_id=None):
    """保存 Agent.md 内容"""
    data = request.json or {}
    content = data.get("content", "")
    world_id = world_id or data.get("world_id", "")
    AgentManager.save_agent_md(content, world_id)
    return jsonify({
        "success": True,
        "message": f"Agent.md 已保存 ({len(content)} 字符)",
    })


# ============================================================
# Skill 管理
# ============================================================

# 注意: /skills/discover 必须在 /skills/<world_id> 之前，否则 "discover" 会被当作 world_id 捕获

@agent_bp.route("/skills/discover", methods=["GET"])
def discover_skills():
    """
    扫描本地 .agents/skills、.claude/skills、.openclaw/skills 目录，
    返回所有发现的 Skill 及其启用状态。
    """
    try:
        discovered = AgentManager.scan_discovered_skills()
        enabled_cfg = AgentManager.get_enabled_discovered()
        for ds in discovered:
            ds["enabled"] = enabled_cfg.get(ds["name"], False)
        return jsonify({
            "success": True,
            "skills": discovered,
            "count": len(discovered),
        })
    except Exception as e:
        logger.error(f"Skill discovery error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@agent_bp.route("/skills/discover/toggle", methods=["POST"])
def toggle_discovered_skill():
    """
    启用 / 禁用一个发现的 Skill。
    请求体: { name: string, enabled: bool }
    """
    data = request.json or {}
    name = data.get("name", "").strip()
    enabled = data.get("enabled", False)
    if not name:
        return jsonify({"success": False, "message": "缺少 name 参数"}), 400
    AgentManager.set_discovered_enabled(name, enabled)
    return jsonify({
        "success": True,
        "name": name,
        "enabled": enabled,
        "message": f"Skill '{name}' 已{'启用' if enabled else '禁用'}",
    })


@agent_bp.route("/skills/<world_id>", methods=["GET"])
@agent_bp.route("/skills", methods=["GET"])
def list_skills(world_id=None):
    """列出所有 Skills"""
    skills = AgentManager.list_skills(world_id or "")
    return jsonify({
        "success": True,
        "skills": [s.to_dict() for s in skills],
    })


@agent_bp.route("/skills", methods=["POST"])
def create_skill():
    """创建 / 更新 Skill"""
    data = request.json or {}
    world_id = data.get("world_id", "")
    skill = Skill(
        skill_id=data.get("skill_id") or f"skill_{uuid.uuid4().hex[:8]}",
        name=data.get("name", ""),
        description=data.get("description", ""),
        instructions=data.get("instructions", ""),
        world_id=world_id,
    )
    AgentManager.save_skill(skill)
    return jsonify({
        "success": True,
        "skill": skill.to_dict(),
        "message": "Skill 已保存",
    })


@agent_bp.route("/skills/<skill_id>", methods=["DELETE"])
def delete_skill(skill_id):
    """删除 Skill"""
    world_id = request.args.get("world_id", "")
    deleted = AgentManager.delete_skill(skill_id, world_id)
    return jsonify({
        "success": deleted,
        "message": "已删除" if deleted else "Skill 不存在",
    })


# ============================================================
# Memory 管理
# ============================================================

@agent_bp.route("/memory/<world_id>", methods=["GET"])
@agent_bp.route("/memory", methods=["GET"])
def list_memories(world_id=None):
    """列出所有记忆"""
    memories = AgentManager.get_memories(world_id or "")
    return jsonify({
        "success": True,
        "memories": memories,
    })


@agent_bp.route("/memory", methods=["POST"])
def set_memory():
    """设置记忆"""
    data = request.json or {}
    key = data.get("key", "")
    value = data.get("value", "")
    world_id = data.get("world_id", "")
    if not key:
        return jsonify({"success": False, "message": "key 不能为空"}), 400
    AgentManager.set_memory(key, value, world_id)
    return jsonify({"success": True, "message": f"记忆 '{key}' 已保存"})


@agent_bp.route("/memory/<key>", methods=["DELETE"])
def delete_memory(key):
    """删除记忆"""
    world_id = request.args.get("world_id", "")
    deleted = AgentManager.delete_memory(key, world_id)
    return jsonify({
        "success": deleted,
        "message": "已删除" if deleted else "记忆不存在",
    })
