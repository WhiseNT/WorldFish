"""世界观 schema / context 只读 API。"""

from __future__ import annotations

from flask import jsonify, request

from . import world_build_bp
from app.domain.canonical_world import build_canonical_world
from app.models.world import WorldManager
from app.services.world_context import VALID_CONTEXT_PURPOSES, build_world_context
from app.utils.logger import get_logger

logger = get_logger("worldfish.api.world_schema")


def _get_world_or_404(world_id: str):
    world = WorldManager.get_world(world_id)
    if not world:
        return None, (jsonify({
            "success": False,
            "message": f"世界观不存在: {world_id}",
        }), 404)
    return world, None


@world_build_bp.route("/<world_id>/canonical", methods=["GET"])
def get_canonical_world(world_id: str):
    """读取 Canonical World Model v1。"""

    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        canonical = build_canonical_world(world)
        return jsonify({
            "success": True,
            "world_id": world.id,
            "canonical": canonical,
            "schema_id": canonical.get("schema_id"),
            "schema_version": canonical.get("schema_version"),
            "warnings": canonical.get("warnings") or [],
        })
    except Exception as exc:
        logger.error(f"读取 canonical world 失败 [{world_id}]: {exc}")
        return jsonify({
            "success": False,
            "message": f"读取 canonical world 失败: {exc}",
        }), 500


@world_build_bp.route("/<world_id>/context", methods=["GET"])
def get_world_context(world_id: str):
    """读取用途化世界观上下文。"""

    try:
        world, error = _get_world_or_404(world_id)
        if error:
            return error
        purpose = str(request.args.get("purpose") or "general").strip().lower()
        if purpose not in VALID_CONTEXT_PURPOSES:
            purpose = "general"
        include_sections = request.args.get("sections")
        sections = [item.strip() for item in include_sections.split(",") if item.strip()] if include_sections else None
        context = build_world_context(world, purpose=purpose, include_sections=sections)
        return jsonify({
            "success": True,
            "world_id": world.id,
            "context": context,
            "schema_id": context.get("schema_id"),
            "schema_version": context.get("schema_version"),
            "purpose": context.get("purpose"),
            "warnings": context.get("warnings") or [],
        })
    except Exception as exc:
        logger.error(f"读取 world context 失败 [{world_id}]: {exc}")
        return jsonify({
            "success": False,
            "message": f"读取 world context 失败: {exc}",
        }), 500
