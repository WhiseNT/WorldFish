"""世界模板注册表。

当前仅保留通用模板，但保留统一接口，方便后续继续扩展。
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from app.prompts import load_prompt

DEFAULT_WORLD_TEMPLATE_ID = "generic"
DND_WORLD_TEMPLATE_ID = "dnd-campaign"


def _detail_section(section_id: str, name: str, target: str, description: str) -> Dict[str, str]:
    return {
        "id": str(section_id).strip(),
        "name": str(name).strip(),
        "target": str(target).strip(),
        "description": str(description).strip(),
    }


def _setting_collection(collection_id: str, name: str, category: str, description: str, routes: List[str] | None = None) -> Dict[str, Any]:
    return {
        "id": str(collection_id).strip(),
        "name": str(name).strip(),
        "category": str(category).strip(),
        "description": str(description).strip(),
        "routes": list(routes or []),
    }


def _square_cell(map_id_value: str, q: int, r: int) -> Dict[str, Any]:
    return {
        "id": f"cell_{q}_{r}",
        "map_id": map_id_value,
        "q": q,
        "r": r,
        "name": "",
        "description": "",
        "terrain": "unset",
        "status": "normal",
        "faction": "",
        "resources": [],
        "population": "",
        "settlement": "",
        "locations": [],
        "linked_map_id": "",
        "color": "",
        "tags": [],
        "notes": "",
        "custom": {},
    }


def _create_square_cells(map_id_value: str, width: int, height: int) -> List[Dict[str, Any]]:
    return [_square_cell(map_id_value, q, r) for r in range(height) for q in range(width)]


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
    },
    {
        "id": DND_WORLD_TEMPLATE_ID,
        "name": "DND 跑团世界模板",
        "description": "面向 DND 跑团的世界模板，覆盖战役前提、桌面规则、方格地图、势力、神祇位面、NPC、反派威胁、冒险遭遇、宝物和玩家角色接入。",
        "conflict_warning": "该模板会把资料优先拆分为战役运营、规则资源和跑团地图字段；不适合仅需小说式资料整理的世界。",
        "focus_tags": ["战役总览", "桌面规则", "方格地图", "势力与神祇", "冒险遭遇", "宝物据点", "玩家接入"],
        "focus_points": [
            "优先提取战役前提、起始等级、预期终局、主要威胁、玩家角色钩子和跑团类型。",
            "地图必须区分世界/区域地图与 DND 方格战斗地图；战斗地图需记录背景图、每格距离、网格大小和对齐参数。",
            "NPC、势力、反派、怪物、宝物、任务和遭遇都要能关联地图、地点、等级范围或玩家角色。",
            "桌面规则、允许资料书、升级方式、休息规则、死亡复活、暗骰和安全工具应作为长期设定保留。",
        ],
        "detail_sections": [
            _detail_section("campaign_overview", "战役总览", "world_info.dnd_campaign / settings.items[collectionId=dnd_campaign_overview]", "记录战役一句话前提、起始等级、目标等级、主题风格、主冲突、结束条件和玩家目标。"),
            _detail_section("table_rules", "桌面规则", "settings.items[collectionId=dnd_table_rules]", "记录版本、允许资料书、属性生成、升级、休息、死亡、复活、暗骰、PVP、安全工具和房规。"),
            _detail_section("maps", "地图与地点", "settings.mapData.structuredMaps / settings.items[collectionId=dnd_maps_locations]", "维护世界地图、区域地图、城市地图、地牢地图和方格战斗地图；跑团地图应带背景图与网格对齐参数。"),
            _detail_section("factions", "势力与政治", "settings.items[collectionId=dnd_factions] / entities[type=组织]", "记录王国、教会、公会、邪教、军团和怪物阵营的目标、资源、敌友、声望和任务来源。"),
            _detail_section("gods_planes", "神祇与位面", "settings.items[collectionId=dnd_gods_planes]", "记录神祇、领域、教会、圣地、位面结构、位面入口和神术/圣武士相关限制。"),
            _detail_section("npcs", "NPC 与重要角色", "entities[type=人物] / settings.items[collectionId=dnd_npcs]", "NPC 需要保留身份、阵营、目标、秘密、态度、任务、情报、战斗数据引用和出场场景。"),
            _detail_section("threats", "反派与威胁", "settings.items[collectionId=dnd_threats]", "记录主要威胁、阶段推进、爪牙、据点、仪式、线索、若玩家不行动会发生什么。"),
            _detail_section("adventures", "冒险与任务", "events / settings.items[collectionId=dnd_adventures]", "记录推荐等级、任务钩子、目标、关键地点、关键 NPC、遭遇、奖励、失败后果和后续任务。"),
            _detail_section("encounters", "遭遇与怪物", "settings.items[collectionId=dnd_encounters]", "记录战斗/社交/陷阱/环境危险遭遇，包含地图、怪物、战术、站位、胜败条件和奖励。"),
            _detail_section("treasure", "宝物与魔法物品", "settings.items[collectionId=dnd_treasure]", "记录魔法物品稀有度、同调、效果、持有者、获得地点、价格、传说背景和关联任务。"),
            _detail_section("bastions", "地牢与据点", "settings.items[collectionId=dnd_dungeons_bastions]", "记录地牢层级、房间、陷阱、宝物、秘密门、据点设施、雇员、服务、维护成本和据点事件。"),
            _detail_section("player_hooks", "玩家角色接入", "settings.items[collectionId=dnd_player_hooks]", "记录玩家角色出身、背景、所属势力、个人目标、秘密、宿敌、专属任务和主线关联。"),
        ],
        "setting_collections": [
            _setting_collection("dnd_campaign_overview", "战役总览", "other", "战役前提、等级范围、主题风格、主线冲突和结束条件。", ["world_info", "campaign"]),
            _setting_collection("dnd_table_rules", "桌面规则", "other", "版本、资料书、升级、休息、死亡、复活、暗骰和安全工具。", ["rules", "table"]),
            _setting_collection("dnd_maps_locations", "地图与地点", "geography", "世界/区域/城市/地牢/方格战斗地图与关键地点。", ["maps", "locations"]),
            _setting_collection("dnd_factions", "势力与政治", "organization", "王国、教会、公会、邪教、军团、怪物阵营及声望关系。", ["factions", "politics"]),
            _setting_collection("dnd_gods_planes", "神祇与位面", "ability", "神祇、领域、教会、位面结构、入口和神术相关限制。", ["gods", "planes"]),
            _setting_collection("dnd_npcs", "NPC 与重要角色", "character", "任务发布者、盟友、反派、导师、商人、可战斗 NPC。", ["npcs"]),
            _setting_collection("dnd_threats", "反派与威胁", "organization", "主威胁、爪牙、阶段推进、据点、仪式、线索和后果。", ["villains", "threats"]),
            _setting_collection("dnd_adventures", "冒险与任务", "other", "任务钩子、推荐等级、目标、地点、奖励、失败后果和后续任务。", ["quests", "adventures"]),
            _setting_collection("dnd_encounters", "遭遇与怪物", "other", "战斗、社交、陷阱、环境危险、怪物战术和胜败条件。", ["encounters", "monsters"]),
            _setting_collection("dnd_treasure", "宝物与魔法物品", "item", "魔法物品、宝藏、价格、同调、持有者和获得地点。", ["treasure", "magic_items"]),
            _setting_collection("dnd_dungeons_bastions", "地牢与据点", "geography", "地牢房间、陷阱、秘密门、据点设施、雇员和据点事件。", ["dungeons", "bastions"]),
            _setting_collection("dnd_player_hooks", "玩家角色接入", "character", "玩家角色背景、个人目标、秘密、宿敌和专属任务。", ["player_characters", "hooks"]),
        ],
        "world_info_guide": [
            "world_info 需保留世界名称、当前时代、战役起点、整体冲突和跑团风格。",
            "dnd_campaign 字段用于记录起始等级、目标等级、版本、资料书、升级方式和战役结束条件。",
            "若文本包含地图或战斗场景，应优先提取可转化为方格战斗地图的信息。",
        ],
        "settings_guide": [
            "长期规则和跑团运营信息写入 dnd_table_rules，不要混入普通简介。",
            "地图写入 settings.mapData.structuredMaps；DND 战斗地图应使用 grid_type=square，cell_distance=5 ft。",
            "遭遇、怪物、宝物、任务、反派和玩家钩子都应尽量记录推荐等级、关联地图、关联 NPC 与失败后果。",
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
    resolved_id = resolve_world_template_id(template_id)
    base = {
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
    if resolved_id != DND_WORLD_TEMPLATE_ID:
        return base

    template = get_world_template(DND_WORLD_TEMPLATE_ID)
    collection_items = [
        {
            "id": collection.get("id"),
            "name": collection.get("name"),
            "settingType": "collection",
            "category": collection.get("category") or "other",
            "description": collection.get("description") or "",
            "aliases": collection.get("routes") or [],
            "showInList": True,
            "expanded": False,
            "detailContent": collection.get("description") or "",
            "structuredDetail": {
                "intro": collection.get("description") or "",
                "facts": [],
                "relationships": [],
                "stages": [],
            },
        }
        for collection in template.get("setting_collections") or []
    ]

    battle_map_id = "dnd_default_battle_map"
    base["world_info"].update({
        "dnd_campaign": {
            "ruleset": "DND 5e / 2024 兼容",
            "campaign_premise": "",
            "starting_level": "1",
            "target_level": "10",
            "advancement": "milestone",
            "play_style": "战斗 / 探索 / 社交平衡",
            "table_rules": {
                "allowed_sources": [],
                "ability_generation": "标准数组 / 点购 / 掷骰",
                "resting": "标准短休与长休",
                "death_and_resurrection": "按桌面约定填写",
                "safety_tools": [],
            },
        }
    })
    base["settings"]["items"] = collection_items
    base["settings"]["mapData"]["structuredMaps"] = [
        {
            "id": battle_map_id,
            "world_id": "",
            "name": "DND 默认战斗地图",
            "description": "用于 DND 跑团的默认方格战斗地图。可上传背景图并调节网格对齐。",
            "type": "battlefield",
            "grid_type": "square",
            "width": 24,
            "height": 18,
            "radius": 0,
            "trpg_system": "dnd",
            "trpg_role": "battle",
            "cell_distance": "5 ft",
            "background_image": "",
            "custom": {
                "grid_type": "square",
                "trpg_system": "dnd",
                "trpg_role": "battle",
                "cell_distance": "5 ft",
            },
            "view": {
                "grid_size": 48,
                "image_scale": 1,
                "image_offset_x": 0,
                "image_offset_y": 0,
                "grid_opacity": 0.55,
                "image_opacity": 1,
            },
            "layers": [
                {"type": "terrain", "visible": True, "rules": {}, "field": "terrain"},
                {"type": "faction", "visible": False, "rules": {}, "field": "faction"},
                {"type": "resource", "visible": False, "rules": {}, "field": "resource"},
                {"type": "event", "visible": False, "rules": {}, "field": "event"},
                {"type": "status", "visible": False, "rules": {}, "field": "status"},
            ],
            "cells": _create_square_cells(battle_map_id, 24, 18),
            "change_records": [],
        }
    ]
    return base


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
