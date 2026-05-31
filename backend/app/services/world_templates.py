"""世界模板注册表。

当前仅保留通用模板，但保留统一接口，方便后续继续扩展。
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from app.prompts import load_prompt

DEFAULT_WORLD_TEMPLATE_ID = "generic"


def _detail_section(section_id: str, name: str, target: str, description: str) -> Dict[str, str]:
    return {
        "id": str(section_id).strip(),
        "name": str(name).strip(),
        "target": str(target).strip(),
        "description": str(description).strip(),
    }


WORLD_TEMPLATE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "id": DEFAULT_WORLD_TEMPLATE_ID,
        "name": "通用模板",
        "description": "默认解析结构，按核心简介、关键事实、关系网络、阶段/演变和设定补充说明组织世界观内容。",
        "conflict_warning": "不同模板的结构栏目可能不一致。",
        "focus_tags": ["核心简介", "关键事实", "关系网络", "阶段/演变", "设定补充说明"],
        "focus_points": [
            "所有实体和设定都按模板栏目拆分，避免把简介、事实、关系和演变混在同一段长文本里。",
            "模板栏目可以增删；当前通用模板保留五个基础栏目。",
        ],
        "detail_sections": [
            _detail_section(
                "core_intro",
                "核心简介",
                "entities[].attributes.简介 / settings.items[].structuredDetail.intro",
                "对象的高密度概览，说明本质、身份、定位、用途或叙事作用。",
            ),
            _detail_section(
                "key_facts",
                "关键事实",
                "entities[].attributes / settings.items[].structuredDetail.facts",
                "可被反复引用的稳定事实，使用短字段承载身份、归属、能力、资源、规则边界等信息。",
            ),
            _detail_section(
                "relationships",
                "关系网络",
                "entities[].relationships / settings.items[].structuredDetail.relationships",
                "对象与人物、组织、地点、事件、规则之间的关联，保留关系类型、说明、时期和来源事件。",
            ),
            _detail_section(
                "stages",
                "阶段/演变",
                "entities[].stages / settings.items[].structuredDetail.stages",
                "对象在不同时间、版本、势力阶段或剧情阶段中的变化。",
            ),
            _detail_section(
                "supplement",
                "设定补充说明",
                "entities[].attributes.设定补充说明 / settings.items[].detailContent",
                "不适合放入短字段但仍有价值的背景、限制、解释、争议和人工补充说明。",
            ),
        ],
        "setting_collections": [],
        "world_info_guide": [
            "优先提取作品/世界名称、时代背景、主线时间锚点与整体世界描述。",
            "若文本同时包含多个时期，anchor_time 应优先落在主线剧情最常活动的时期。",
        ],
        "settings_guide": [
            "settings.items 仅沉淀文本明确支撑的长期设定。",
            "mapData 聚焦区域关系、国家关系、重要地点；calendars 聚焦纪年或历法系统。",
        ],
    }
]


def _template_index() -> Dict[str, Dict[str, Any]]:
    return {
        str(template.get("id") or "").strip(): template
        for template in WORLD_TEMPLATE_DEFINITIONS
        if str(template.get("id") or "").strip()
    }


def resolve_world_template_id(template_id: str | None) -> str:
    normalized = str(template_id or "").strip()
    if normalized and normalized in _template_index():
        return normalized
    return DEFAULT_WORLD_TEMPLATE_ID


def get_world_template(template_id: str | None = None) -> Dict[str, Any]:
    resolved_id = resolve_world_template_id(template_id)
    template = _template_index().get(resolved_id) or _template_index()[DEFAULT_WORLD_TEMPLATE_ID]
    return copy.deepcopy(template)


def serialize_world_template(template: Dict[str, Any]) -> Dict[str, Any]:
    normalized = get_world_template(template.get("id"))
    return {
        "id": normalized.get("id"),
        "name": normalized.get("name"),
        "description": normalized.get("description"),
        "conflict_warning": normalized.get("conflict_warning"),
        "focus_tags": list(normalized.get("focus_tags") or []),
        "focus_points": list(normalized.get("focus_points") or []),
        "detail_sections": copy.deepcopy(normalized.get("detail_sections") or []),
        "setting_collections": copy.deepcopy(normalized.get("setting_collections") or []),
        "world_info_guide": list(normalized.get("world_info_guide") or []),
        "settings_guide": list(normalized.get("settings_guide") or []),
    }


def list_world_templates() -> List[Dict[str, Any]]:
    return [serialize_world_template(template) for template in WORLD_TEMPLATE_DEFINITIONS]


def get_world_template_summary(template_id: str | None = None) -> Dict[str, Any]:
    return serialize_world_template(get_world_template(template_id))


def build_world_template_default_data(template_id: str | None = None) -> Dict[str, Any]:
    """构建模板创建新世界时默认携带的数据。"""
    resolve_world_template_id(template_id)
    return {
        "world_info": {
            "name": "",
            "description": "",
            "era": "",
            "anchor_time": "",
            "writing_style": "",
            "reference_text": "",
        },
        "entities": [],
        "events": [],
        "settings": {
            "items": [],
            "mapData": {
                "regionRelations": "",
                "countryRelations": "",
                "importantLocations": "",
                "structuredMaps": [],
            },
            "calendars": [],
        },
    }


def get_world_template_detail(template_id: str | None = None) -> Dict[str, Any]:
    """获取单个模板的完整定义与默认数据。"""
    resolved_id = resolve_world_template_id(template_id)
    detail = serialize_world_template(get_world_template(resolved_id))
    detail["default_data"] = build_world_template_default_data(resolved_id)
    return detail


def build_world_template_prompt_context(template_id: str | None = None) -> Dict[str, str]:
    template = get_world_template(template_id)

    focus_guide = "\n".join(
        f"- {item}" for item in (template.get("focus_points") or [])
    ) or "- 无额外模板重点，按通用规则提取。"

    section_lines = []
    for section in template.get("detail_sections") or []:
        section_lines.append(
            f"- {section.get('name')}：写入 {section.get('target')}。{str(section.get('description') or '').strip()}"
        )
    section_guide = "\n".join(section_lines) or "- 按核心简介、关键事实、关系网络、阶段/演变和设定补充说明提取。"

    collection_lines = []
    for collection in template.get("setting_collections") or []:
        routes = "、".join(collection.get("routes") or [])
        collection_lines.append(
            f"- {collection.get('name')}：category={collection.get('category')}，collectionId={collection.get('id')}，适用对象={routes or '通用'}。{str(collection.get('description') or '').strip()}"
        )
    setting_collection_guide = "\n".join(collection_lines)

    settings_guide = "\n".join(
        f"- {item}" for item in (template.get("settings_guide") or [])
    ) or "- settings.items 保留长期设定；mapData/calendars 仅在文本有证据时填写。"

    world_info_guide = "\n".join(
        f"- {item}" for item in (template.get("world_info_guide") or [])
    ) or "- world_info 仅填写文本直接支撑的信息。"

    chunk_hint_items = []
    section_names = [str(section.get("name") or "").strip() for section in template.get("detail_sections") or [] if str(section.get("name") or "").strip()]
    collection_names = [str(collection.get("name") or "").strip() for collection in template.get("setting_collections") or [] if str(collection.get("name") or "").strip()]
    if section_names:
        chunk_hint_items.append(f"按栏目提取：{'、'.join(section_names)}")
    if collection_names:
        chunk_hint_items.append(f"详细资料归入：{'、'.join(collection_names[:6])}")
    chunk_hint = "；".join(chunk_hint_items) or "优先提取实体、事件、关系和长期设定"

    return {
        "template_name": str(template.get("name") or "通用模板").strip(),
        "template_description": str(template.get("description") or "").strip(),
        "template_focus_guide": focus_guide,
        "template_section_guide": section_guide,
        "template_setting_collection_guide": setting_collection_guide,
        "template_setting_guide": settings_guide,
        "template_world_info_guide": world_info_guide,
        "template_chunk_hint": chunk_hint,
    }


def build_extraction_system_prompt(template_id: str | None = None) -> str:
    return load_prompt("extraction_system", **build_world_template_prompt_context(template_id))
