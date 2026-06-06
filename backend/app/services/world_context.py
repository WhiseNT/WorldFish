"""统一世界观上下文服务。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from app.domain.canonical_world import (
    CANONICAL_WORLD_MODEL_ID,
    CANONICAL_WORLD_MODEL_VERSION,
    build_canonical_world,
    summarize_canonical_world,
)

VALID_CONTEXT_PURPOSES = {"general", "rag", "simulation", "report", "trpg"}

DEFAULT_PURPOSE_SECTIONS = {
    "general": ["world_info", "settings", "entities", "events", "timelines", "maps", "rules", "references"],
    "rag": ["world_info", "settings", "entities", "events", "maps", "rules", "references"],
    "simulation": ["world_info", "entities", "events", "timelines", "maps", "rules"],
    "report": ["world_info", "settings", "entities", "events", "timelines", "maps", "rules", "references"],
    "trpg": ["world_info", "entities", "events", "maps", "rules"],
}


def _normalize_purpose(purpose: str) -> str:
    value = str(purpose or "general").strip().lower()
    return value if value in VALID_CONTEXT_PURPOSES else "general"


def _normalize_sections(sections: Optional[Iterable[str]], purpose: str) -> List[str]:
    if not sections:
        return list(DEFAULT_PURPOSE_SECTIONS[purpose])
    result: List[str] = []
    for section in sections:
        value = str(section or "").strip()
        if value and value not in result:
            result.append(value)
    return result or list(DEFAULT_PURPOSE_SECTIONS[purpose])


def _section_value(canonical: Dict[str, Any], section: str) -> Any:
    if section == "maps":
        maps = canonical.get("maps") or {}
        return maps.get("items") if isinstance(maps, dict) else maps
    if section == "settings":
        settings = canonical.get("settings") or {}
        return settings.get("items") if isinstance(settings, dict) else settings
    return canonical.get(section)


def _build_section_text(section: str, value: Any) -> str:
    if section == "world_info" and isinstance(value, dict):
        parts = [value.get("name"), value.get("description"), value.get("era"), value.get("anchor_time")]
        return "\n".join(str(part) for part in parts if str(part or "").strip())
    if isinstance(value, list):
        lines = []
        for item in value[:30]:
            if isinstance(item, dict):
                name = item.get("name") or item.get("title") or item.get("id")
                description = item.get("description") or item.get("detail") or item.get("date") or ""
                line = str(name or "").strip()
                if description:
                    line = f"{line}: {description}" if line else str(description)
                if line:
                    lines.append(line)
            elif str(item or "").strip():
                lines.append(str(item).strip())
        return "\n".join(lines)
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if item in (None, "", [], {}):
                continue
            lines.append(f"{key}: {item}")
        return "\n".join(lines)
    return str(value or "").strip()


def build_world_context(
    world: Any,
    purpose: str = "general",
    include_sections: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """构建统一世界上下文，不依赖 LLM / Embedding / 云服务。"""

    normalized_purpose = _normalize_purpose(purpose)
    canonical = build_canonical_world(world)
    summary = summarize_canonical_world(canonical)
    section_names = _normalize_sections(include_sections, normalized_purpose)

    sections: Dict[str, Dict[str, Any]] = {}
    for section in section_names:
        value = _section_value(canonical, section)
        if value in (None, [], {}):
            continue
        sections[section] = {
            "name": section,
            "data": value,
            "text": _build_section_text(section, value),
        }

    context_text_parts = [summary.get("text") or ""]
    for section in sections.values():
        text = section.get("text") or ""
        if text and text not in context_text_parts:
            context_text_parts.append(text)

    return {
        "schema_id": CANONICAL_WORLD_MODEL_ID,
        "schema_version": CANONICAL_WORLD_MODEL_VERSION,
        "purpose": normalized_purpose,
        "canonical": canonical,
        "summary": summary,
        "sections": sections,
        "context_text": "\n\n".join(part for part in context_text_parts if str(part or "").strip()),
        "warnings": canonical.get("warnings") or [],
    }


def build_world_context_for_rag(world: Any) -> Dict[str, Any]:
    return build_world_context(world, purpose="rag")


def build_world_context_for_simulation(world: Any) -> Dict[str, Any]:
    return build_world_context(world, purpose="simulation")


def build_world_context_for_report(world: Any) -> Dict[str, Any]:
    return build_world_context(world, purpose="report")


def build_world_context_for_trpg(world: Any) -> Dict[str, Any]:
    return build_world_context(world, purpose="trpg")
