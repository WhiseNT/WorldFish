"""World Event Schema v1 纯函数。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

WORLD_EVENT_SCHEMA_ID = "worldfish.world_event.v1"
WORLD_EVENT_SCHEMA_VERSION = "1.0.0"

WORLD_EVENT_TYPES = {
    "world.created",
    "world.updated",
    "entity.created",
    "entity.updated",
    "setting.updated",
    "map.cell.updated",
    "simulation.branch.created",
    "simulation.event.recorded",
    "trpg.session.event",
    "report.generated",
}


def now_iso() -> str:
    return datetime.now().isoformat()


def _string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _event_id() -> str:
    return f"wevt_{uuid.uuid4().hex[:12]}"


def normalize_event_type(event_type: Any) -> str:
    text = _string(event_type, "world.updated")
    return text if text in WORLD_EVENT_TYPES else text


def build_world_event(
    event_type: str,
    world_id: str,
    payload: Dict[str, Any] | None = None,
    source: str = "system",
    actor_id: str = "local_user",
    event_id: str | None = None,
    created_at: str | None = None,
    schema_version: str = WORLD_EVENT_SCHEMA_VERSION,
) -> Dict[str, Any]:
    """构造 append-only 世界事件。"""

    normalized_payload = dict(payload or {})
    normalized_world_id = _string(world_id or normalized_payload.get("world_id"))
    if normalized_world_id:
        normalized_payload.setdefault("world_id", normalized_world_id)

    return {
        "schema_id": WORLD_EVENT_SCHEMA_ID,
        "schema_version": schema_version or WORLD_EVENT_SCHEMA_VERSION,
        "event_id": _string(event_id) or _event_id(),
        "world_id": normalized_world_id,
        "event_type": normalize_event_type(event_type),
        "source": _string(source, "system"),
        "actor_id": _string(actor_id, "local_user"),
        "payload": normalized_payload,
        "created_at": _string(created_at) or now_iso(),
    }


def normalize_world_event(raw: Dict[str, Any] | None) -> Dict[str, Any]:
    """归一化世界事件，兼容协作事件或旧事件 dict。"""

    data = _dict(raw)
    payload = _dict(data.get("payload"))
    event_type = data.get("event_type") or data.get("type") or payload.get("event_type") or "world.updated"
    world_id = data.get("world_id") or payload.get("world_id") or data.get("linked_world_id") or ""
    return build_world_event(
        event_type=event_type,
        world_id=world_id,
        payload=payload,
        source=data.get("source") or payload.get("source") or "imported",
        actor_id=data.get("actor_id") or data.get("user_id") or payload.get("actor_id") or "local_user",
        event_id=data.get("event_id") or data.get("id"),
        created_at=data.get("created_at") or data.get("timestamp"),
        schema_version=data.get("schema_version") or WORLD_EVENT_SCHEMA_VERSION,
    )


def event_to_context_line(event: Dict[str, Any]) -> str:
    """将世界事件转换成可读上下文行，供回放、报告与调试使用。"""

    normalized = normalize_world_event(event)
    payload = normalized.get("payload") or {}
    event_type = normalized.get("event_type") or "world.updated"
    created_at = normalized.get("created_at") or "未知时间"
    actor_id = normalized.get("actor_id") or "local_user"
    summary = payload.get("summary") or payload.get("message") or payload.get("name") or payload.get("title") or ""
    target = payload.get("target_id") or payload.get("entity_id") or payload.get("setting_id") or payload.get("map_id") or ""

    parts = [created_at, event_type, f"actor={actor_id}"]
    if target:
        parts.append(f"target={target}")
    if summary:
        parts.append(str(summary))
    return " | ".join(str(part) for part in parts if str(part).strip())
