"""世界观模型与持久化仓库。"""

import json
import os
import re
import shutil
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger("worldfish.model.world")

ENTITY_TYPE_TO_SETTING_CATEGORY = {
    "人物": "character",
    "角色": "character",
    "种族": "character",
    "生物": "character",
    "person": "character",
    "character": "character",
    "国家": "organization",
    "政权": "organization",
    "组织": "organization",
    "势力": "organization",
    "团体": "organization",
    "教会": "organization",
    "公司": "organization",
    "公会": "organization",
    "organization": "organization",
    "nation": "organization",
    "faction": "organization",
    "地点": "geography",
    "位置": "geography",
    "城市": "geography",
    "区域": "geography",
    "location": "geography",
    "geography": "geography",
    "place": "geography",
    "物品": "item",
    "道具": "item",
    "装备": "item",
    "武器": "item",
    "item": "item",
    "能力": "ability",
    "魔法": "ability",
    "技能": "ability",
    "体系": "ability",
    "ability": "ability",
}
SETTING_CATEGORY_TO_ENTITY_TYPE = {
    "character": "人物",
    "organization": "组织",
    "geography": "地点",
    "item": "物品",
    "ability": "能力",
    "other": "其他",
}
ENTITY_BACKED_SETTING_CATEGORIES = {"character", "organization", "geography", "item", "ability"}


def _normalize_identity_key(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _normalize_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        for sep in (",", "，", "、", "/", "|"):
            if sep in value:
                return [part.strip() for part in value.split(sep) if part.strip()]
        return [value.strip()] if value.strip() else []
    return []


def _dedupe_strings(values: List[Any], exclude: Optional[List[Any]] = None) -> List[str]:
    excluded = {_normalize_identity_key(item) for item in (exclude or []) if str(item or "").strip()}
    seen = set()
    result: List[str] = []
    for value in values or []:
        text = str(value or "").strip()
        key = _normalize_identity_key(text)
        if not text or not key or key in seen or key in excluded:
            continue
        seen.add(key)
        result.append(text)
    return result


def _merge_text(*values: Any) -> str:
    parts: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        if any(text == existing or text in existing for existing in parts):
            continue
        parts = [existing for existing in parts if existing not in text]
        parts.append(text)
    return "\n".join(parts)


def _normalize_setting_category(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return "other"
    if normalized in SETTING_CATEGORY_TO_ENTITY_TYPE:
        return normalized
    keyword_map = {
        "character": ("人物", "角色", "种族", "生物", "身份", "character", "person"),
        "organization": ("组织", "势力", "国家", "政权", "团体", "organization", "faction", "nation"),
        "geography": ("地理", "地点", "区域", "城市", "位置", "geography", "location", "place"),
        "item": ("物品", "道具", "装备", "武器", "资源", "科技", "item"),
        "ability": ("能力", "魔法", "技能", "体系", "规则", "ability"),
    }
    for category, keywords in keyword_map.items():
        if any(keyword.lower() in normalized for keyword in keywords):
            return category
    return "other"


def _setting_category_to_entity_type(category: Any) -> str:
    return SETTING_CATEGORY_TO_ENTITY_TYPE.get(_normalize_setting_category(category), "其他")


def _entity_type_to_setting_category(entity_type: Any) -> str:
    text = str(entity_type or "").strip()
    if not text:
        return "other"
    return ENTITY_TYPE_TO_SETTING_CATEGORY.get(text, ENTITY_TYPE_TO_SETTING_CATEGORY.get(text.lower(), _normalize_setting_category(text)))


def _normalize_stage(stage: Dict[str, Any], entity_name: str = "", index: int = 0) -> Dict[str, Any]:
    """标准化实体阶段结构，兼容历史字段名。"""

    if not isinstance(stage, dict):
        return {}

    raw_attributes = stage.get("attributes", stage.get("属性", {}))
    attributes = dict(raw_attributes) if isinstance(raw_attributes, dict) else {}
    name = str(
        stage.get("name")
        or stage.get("名称")
        or stage.get("title")
        or f"{entity_name or '实体'}阶段{index + 1}"
    ).strip()

    return {
        "id": stage.get("id") or f"stage_{uuid.uuid4().hex[:12]}",
        "name": name,
        "era": str(stage.get("era") or stage.get("时期") or stage.get("time") or "").strip(),
        "description": str(stage.get("description") or stage.get("描述") or "").strip(),
        "attributes": attributes,
        "setting_item_id": str(
            stage.get("setting_item_id")
            or stage.get("settingId")
            or stage.get("linked_setting_id")
            or ""
        ).strip(),
        "source": dict(stage.get("source")) if isinstance(stage.get("source"), dict) else {},
    }


def _extract_entity_stages(data: Dict[str, Any], attributes: Dict[str, Any], entity_name: str = "") -> List[Dict[str, Any]]:
    """从新旧两种实体结构中提取阶段数据。"""

    raw_stages = data.get("stages") or data.get("阶段")
    if not isinstance(raw_stages, list):
        raw_stages = attributes.get("stages") or attributes.get("阶段") or []

    if not isinstance(raw_stages, list):
        return []

    stages: List[Dict[str, Any]] = []
    for index, stage in enumerate(raw_stages):
        normalized = _normalize_stage(stage, entity_name=entity_name, index=index)
        if normalized and normalized.get("name"):
            stages.append(normalized)
    return stages


class Entity:
    """实体（人物、国家等）。"""

    def __init__(
        self,
        id: str,
        world_id: str,
        name: str,
        type: str,
        aliases: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        stages: Optional[List[Dict[str, Any]]] = None,
        relationships: Optional[List[Dict[str, Any]]] = None,
        setting_item_id: str = "",
        evolution_refs: Optional[List[str]] = None,
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.world_id = world_id
        self.name = name
        self.type = type
        self.aliases = [str(alias).strip() for alias in (aliases or []) if str(alias).strip()]
        self.attributes = attributes or {}
        self.stages = stages or []
        self.relationships = [dict(item) for item in (relationships or []) if isinstance(item, dict)]
        self.setting_item_id = setting_item_id or ""
        self.evolution_refs = [str(ref).strip() for ref in (evolution_refs or []) if str(ref).strip()]
        self.created_at = created_at or datetime.now().isoformat()

    @classmethod
    def create(
        cls,
        world_id: str,
        name: str,
        type: str,
        aliases: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        stages: Optional[List[Dict[str, Any]]] = None,
        relationships: Optional[List[Dict[str, Any]]] = None,
        setting_item_id: str = "",
        evolution_refs: Optional[List[str]] = None,
    ) -> "Entity":
        return cls(
            id=f"ent_{uuid.uuid4().hex[:12]}",
            world_id=world_id,
            name=name,
            type=type,
            aliases=aliases,
            attributes=attributes,
            stages=stages,
            relationships=relationships,
            setting_item_id=setting_item_id,
            evolution_refs=evolution_refs,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any], world_id: Optional[str] = None) -> "Entity":
        raw_attributes = data.get("attributes") or {}
        attributes = dict(raw_attributes) if isinstance(raw_attributes, dict) else {}
        stages = _extract_entity_stages(data, attributes, data.get("name", ""))
        attributes.pop("阶段", None)
        attributes.pop("stages", None)
        aliases = [str(alias).strip() for alias in (data.get("aliases") or data.get("alias") or []) if str(alias).strip()]
        raw_relationships = data.get("relationships") or data.get("relations") or attributes.get("relationships") or attributes.get("关系") or []
        relationships = [dict(item) for item in raw_relationships if isinstance(item, dict)] if isinstance(raw_relationships, list) else []
        attributes.pop("relationships", None)
        attributes.pop("关系", None)

        return cls(
            id=data.get("id") or f"ent_{uuid.uuid4().hex[:12]}",
            world_id=data.get("world_id") or world_id or "",
            name=data.get("name", ""),
            type=data.get("type", ""),
            aliases=aliases,
            attributes=attributes,
            stages=stages,
            relationships=relationships,
            setting_item_id=str(
                data.get("setting_item_id")
                or data.get("settingId")
                or data.get("linked_setting_id")
                or ""
            ).strip(),
            evolution_refs=data.get("evolution_refs") or [],
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "world_id": self.world_id,
            "name": self.name,
            "type": self.type,
            "aliases": self.aliases,
            "attributes": self.attributes,
            "stages": self.stages,
            "relationships": self.relationships,
            "setting_item_id": self.setting_item_id,
            "evolution_refs": self.evolution_refs,
            "created_at": self.created_at,
        }


class Event:
    """事件。"""

    def __init__(
        self,
        id: str,
        world_id: str,
        name: str,
        description: str,
        date: str,
        time_type: str = "unknown",
        estimated_date: str = "未知",
        entities: Optional[List[str]] = None,
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.world_id = world_id
        self.name = name
        self.description = description
        self.date = date
        self.time_type = time_type or "unknown"
        self.estimated_date = estimated_date or "未知"
        self.entities = entities or []
        self.created_at = created_at or datetime.now().isoformat()

    @classmethod
    def create(
        cls,
        world_id: str,
        name: str,
        description: str,
        date: str,
        time_type: str = "unknown",
        estimated_date: str = "未知",
        entities: Optional[List[str]] = None,
    ) -> "Event":
        return cls(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            world_id=world_id,
            name=name,
            description=description,
            date=date,
            time_type=time_type,
            estimated_date=estimated_date,
            entities=entities,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any], world_id: Optional[str] = None) -> "Event":
        return cls(
            id=data.get("id") or f"evt_{uuid.uuid4().hex[:12]}",
            world_id=data.get("world_id") or world_id or "",
            name=data.get("name", ""),
            description=data.get("description", ""),
            date=data.get("date", ""),
            time_type=data.get("time_type", "unknown"),
            estimated_date=data.get("estimated_date", "未知"),
            entities=data.get("entities") or [],
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "world_id": self.world_id,
            "name": self.name,
            "description": self.description,
            "date": self.date,
            "time_type": self.time_type,
            "estimated_date": self.estimated_date,
            "entities": self.entities,
            "created_at": self.created_at,
        }


def _entity_identity_keys(entity: Entity) -> List[str]:
    keys = [_normalize_identity_key(entity.name)]
    keys.extend(_normalize_identity_key(alias) for alias in entity.aliases or [])
    return [key for key in dict.fromkeys(keys) if key]


def _setting_identity_keys(setting: Dict[str, Any]) -> List[str]:
    values = [setting.get("name")]
    values.extend(_normalize_string_list(setting.get("aliases") or setting.get("alias")))
    return [key for key in dict.fromkeys(_normalize_identity_key(value) for value in values) if key]


def _normalize_setting_item(item: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    setting_type = "collection" if item.get("settingType") == "collection" else "setting"
    name = str(item.get("name") or item.get("title") or item.get("label") or "").strip()
    if not name:
        return {}
    category = _normalize_setting_category(item.get("category") or item.get("type"))
    normalized = dict(item)
    normalized["id"] = str(item.get("id") or f"setting_{uuid.uuid4().hex[:12]}").strip()
    normalized["name"] = name
    normalized["settingType"] = setting_type
    normalized["category"] = category
    normalized["aliases"] = _dedupe_strings(_normalize_string_list(item.get("aliases") or item.get("alias")), exclude=[name])
    normalized["description"] = str(item.get("description") or item.get("summary") or item.get("content") or "").strip()
    normalized["detailContent"] = str(item.get("detailContent") or item.get("detail") or normalized["description"] or "").strip()
    normalized["linkedEntityId"] = str(item.get("linkedEntityId") or item.get("entityId") or "").strip()
    if setting_type == "setting":
        normalized["collectionId"] = str(item.get("collectionId") or item.get("collection_id") or item.get("parentCollection") or f"collection_{category}").strip()
    if not isinstance(normalized.get("structuredDetail"), dict):
        normalized["structuredDetail"] = {}
    return normalized


def _structured_detail_from_entity(entity: Entity, fallback_intro: str = "") -> Dict[str, Any]:
    detail = {
        "intro": _merge_text(fallback_intro, entity.attributes.get("简介") if isinstance(entity.attributes, dict) else ""),
        "facts": [],
        "relationships": [],
        "stages": [],
    }
    if isinstance(entity.attributes, dict):
        for key, value in entity.attributes.items():
            if key in {"简介", "关系网络概述"} or value in (None, ""):
                continue
            detail["facts"].append({"label": str(key), "value": value})
    for relationship in entity.relationships or []:
        if not isinstance(relationship, dict):
            continue
        detail["relationships"].append({
            "target": relationship.get("target") or "",
            "type": relationship.get("type") or relationship.get("relation") or "关联",
            "description": relationship.get("description") or "",
            "time_period": relationship.get("time_period") or "",
            "source_event": relationship.get("source_event") or "",
        })
    for stage in entity.stages or []:
        if not isinstance(stage, dict):
            continue
        attrs = stage.get("attributes") if isinstance(stage.get("attributes"), dict) else {}
        detail["stages"].append({
            "id": stage.get("id") or f"stage_{uuid.uuid4().hex[:12]}",
            "name": stage.get("name") or "未命名阶段",
            "era": stage.get("era") or "",
            "description": stage.get("description") or "",
            "fields": [{"label": str(key), "value": value} for key, value in attrs.items() if value not in (None, "")],
        })
    return detail


def _entity_to_setting_item(entity: Entity, existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    existing = _normalize_setting_item(existing or {}) if existing else {}
    category = _normalize_setting_category(existing.get("category") or _entity_type_to_setting_category(entity.type))
    setting_id = str(existing.get("id") or entity.setting_item_id or f"setting_{entity.id}").strip()
    intro = ""
    if isinstance(entity.attributes, dict):
        intro = str(entity.attributes.get("简介") or "").strip()
    description = _merge_text(existing.get("description"), intro, entity.type)
    detail_content = _merge_text(existing.get("detailContent"), intro)
    setting = {
        **existing,
        "id": setting_id,
        "name": str(existing.get("name") or entity.name or "未命名实体").strip(),
        "settingType": "setting",
        "category": category,
        "collectionId": str(existing.get("collectionId") or f"collection_{category}").strip(),
        "description": description,
        "aliases": _dedupe_strings(list(existing.get("aliases") or []) + list(entity.aliases or []), exclude=[entity.name]),
        "detailContent": detail_content or description,
        "structuredDetail": _structured_detail_from_entity(entity, existing.get("detailContent") or existing.get("description") or intro),
        "linkedEntityId": entity.id,
        "sourceType": existing.get("sourceType") or "entity",
        "autoGenerated": True if existing.get("autoGenerated") is None else bool(existing.get("autoGenerated")),
    }
    return setting


def _setting_to_entity(setting: Dict[str, Any], world_id: str, existing: Optional[Entity] = None) -> Optional[Entity]:
    setting = _normalize_setting_item(setting)
    if not setting or setting.get("settingType") != "setting":
        return existing
    category = _normalize_setting_category(setting.get("category"))
    if category not in ENTITY_BACKED_SETTING_CATEGORIES:
        return existing
    entity_id = str((existing.id if existing else "") or setting.get("linkedEntityId") or f"ent_{uuid.uuid4().hex[:12]}").strip()
    name = str(setting.get("name") or (existing.name if existing else "") or "").strip()
    if not name:
        return existing

    detail = setting.get("structuredDetail") if isinstance(setting.get("structuredDetail"), dict) else {}

    attributes: Dict[str, Any] = {}
    intro = _merge_text(setting.get("description"), detail.get("intro"), setting.get("detailContent"))
    if intro:
        attributes["简介"] = intro
    for fact in detail.get("facts") or []:
        if isinstance(fact, dict) and str(fact.get("label") or "").strip():
            attributes[str(fact.get("label")).strip()] = fact.get("value") or ""

    stages: List[Dict[str, Any]] = []
    for index, stage in enumerate(detail.get("stages") or []):
        if not isinstance(stage, dict):
            continue
        fields = stage.get("fields") if isinstance(stage.get("fields"), list) else []
        stage_attrs = {
            str(field.get("label") or "").strip(): field.get("value")
            for field in fields
            if isinstance(field, dict) and str(field.get("label") or "").strip()
        }
        normalized_stage = _normalize_stage({
            "id": stage.get("id"),
            "name": stage.get("name") or f"{name}阶段{index + 1}",
            "era": stage.get("era") or "",
            "description": stage.get("description") or "",
            "attributes": stage_attrs,
            "setting_item_id": setting.get("id") or "",
        }, entity_name=name, index=index)
        if normalized_stage:
            stages.append(normalized_stage)

    relationships: List[Dict[str, Any]] = []
    for relation in detail.get("relationships") or []:
        if isinstance(relation, dict) and str(relation.get("target") or "").strip():
            relationships.append({
                "target": str(relation.get("target") or "").strip(),
                "type": str(relation.get("type") or "关联").strip() or "关联",
                "description": str(relation.get("description") or "").strip(),
                "time_period": str(relation.get("time_period") or "").strip(),
                "source_event": str(relation.get("source_event") or "").strip(),
            })

    return Entity(
        id=entity_id,
        world_id=world_id,
        name=name,
        type=_setting_category_to_entity_type(category),
        aliases=_dedupe_strings(list(existing.aliases if existing else []) + list(setting.get("aliases") or []), exclude=[name]),
        attributes=attributes,
        stages=stages,
        relationships=relationships,
        setting_item_id=str(setting.get("id") or "").strip(),
        evolution_refs=existing.evolution_refs if existing else [],
        created_at=existing.created_at if existing else None,
    )


def _normalize_world_entity_setting_links(world: "WorldSetting") -> None:
    if not world:
        return
    settings = world.settings if isinstance(world.settings, dict) else {}
    raw_items = settings.get("items") if isinstance(settings.get("items"), list) else []
    normalized_items = [item for item in (_normalize_setting_item(item, index) for index, item in enumerate(raw_items)) if item]

    collections = [item for item in normalized_items if item.get("settingType") == "collection"]
    setting_items = [item for item in normalized_items if item.get("settingType") == "setting"]
    collection_keys = {str(item.get("id") or "").strip() for item in collections}
    for category in sorted({item.get("category") for item in setting_items if item.get("category")}):
        collection_id = f"collection_{category}"
        if collection_id not in collection_keys:
            collections.append({
                "id": collection_id,
                "name": _setting_category_to_entity_type(category) + "设定",
                "settingType": "collection",
                "category": category,
                "description": "自动归一化生成的设定集",
                "detailContent": "自动归一化生成的设定集",
                "aliases": [],
                "structuredDetail": {},
                "linkedEntityId": "",
                "sourceType": "normalized",
                "autoGenerated": True,
            })
            collection_keys.add(collection_id)

    entities = [entity if isinstance(entity, Entity) else Entity.from_dict(entity, world.id) for entity in (world.entities or [])]
    entity_by_id = {str(entity.id or "").strip(): entity for entity in entities if str(entity.id or "").strip()}
    entity_by_key: Dict[str, Entity] = {}
    for entity in entities:
        for key in _entity_identity_keys(entity):
            entity_by_key.setdefault(key, entity)

    setting_by_id = {str(item.get("id") or "").strip(): item for item in setting_items if str(item.get("id") or "").strip()}
    setting_by_entity_id = {str(item.get("linkedEntityId") or "").strip(): item for item in setting_items if str(item.get("linkedEntityId") or "").strip()}
    setting_by_key: Dict[str, Dict[str, Any]] = {}
    for item in setting_items:
        for key in _setting_identity_keys(item):
            setting_by_key.setdefault(key, item)

    for entity in entities:
        setting = None
        if entity.setting_item_id:
            setting = setting_by_id.get(entity.setting_item_id)
        if not setting:
            setting = setting_by_entity_id.get(entity.id)
        if not setting:
            for key in _entity_identity_keys(entity):
                setting = setting_by_key.get(key)
                if setting:
                    break
        if setting:
            setting = _normalize_setting_item(setting)
        else:
            setting = _entity_to_setting_item(entity)
        entity.setting_item_id = str(setting.get("id") or "").strip()
        setting["linkedEntityId"] = entity.id
        setting_by_id[setting["id"]] = setting
        setting_by_entity_id[entity.id] = setting
        for key in _setting_identity_keys(setting):
            setting_by_key[key] = setting

    for setting in list(setting_by_id.values()):
        if setting.get("settingType") != "setting":
            continue
        category = _normalize_setting_category(setting.get("category"))
        if category not in ENTITY_BACKED_SETTING_CATEGORIES:
            continue
        entity = entity_by_id.get(str(setting.get("linkedEntityId") or "").strip())
        if not entity:
            for key in _setting_identity_keys(setting):
                entity = entity_by_key.get(key)
                if entity:
                    break
        entity = _setting_to_entity(setting, world.id, entity)
        if not entity:
            continue
        entity.setting_item_id = str(setting.get("id") or "").strip()
        setting["linkedEntityId"] = entity.id

        existing_index = next(
            (index for index, item in enumerate(entities) if str(item.id or "").strip() == entity.id),
            -1,
        )
        if existing_index >= 0:
            entities[existing_index] = entity
        else:
            entities.append(entity)
        entity_by_id[entity.id] = entity
        for key in _entity_identity_keys(entity):
            entity_by_key[key] = entity

    seen_setting_ids = set()
    final_items = []
    for item in collections + list(setting_by_id.values()):
        item_id = str(item.get("id") or "").strip()
        if not item_id or item_id in seen_setting_ids:
            continue
        seen_setting_ids.add(item_id)
        final_items.append(item)

    seen_entity_ids = set()
    final_entities = []
    for entity in entities:
        entity_id = str(entity.id or entity.name or "").strip()
        if not entity_id or entity_id in seen_entity_ids:
            continue
        seen_entity_ids.add(entity_id)
        final_entities.append(entity)

    world.entities = final_entities
    world.settings = {
        **settings,
        "items": final_items,
        "mapData": settings.get("mapData") if isinstance(settings.get("mapData"), dict) else {},
        "calendars": settings.get("calendars") if isinstance(settings.get("calendars"), list) else [],
    }


class WorldSetting:
    """世界观设置。"""

    _KNOWN_FIELDS = {
        "id",
        "name",
        "description",
        "era",
        "anchor_time",
        "settings",
        "entities",
        "events",
        "writing_style",
        "reference_text",
        "created_at",
        "updated_at",
    }

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        era: str = "",
        anchor_time: str = "",
        settings: Optional[Dict[str, Any]] = None,
        entities: Optional[List[Entity]] = None,
        events: Optional[List[Event]] = None,
        writing_style: str = "",
        reference_text: str = "",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        **extra_fields: Any,
    ):
        now = datetime.now().isoformat()
        self.id = id
        self.name = name
        self.description = description or ""
        self.era = era or ""
        self.anchor_time = anchor_time or ""
        self.settings = settings or {}
        self.writing_style = writing_style or ""
        self.reference_text = reference_text or ""
        self.entities = entities or []
        self.events = events or []
        self.created_at = created_at or now
        self.updated_at = updated_at or now

        for key, value in extra_fields.items():
            setattr(self, key, value)

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        era: str = "",
        anchor_time: str = "",
        settings: Optional[Dict[str, Any]] = None,
        writing_style: str = "",
        reference_text: str = "",
        **extra_fields: Any,
    ) -> "WorldSetting":
        return cls(
            id=f"world_{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            era=era,
            anchor_time=anchor_time,
            settings=settings,
            writing_style=writing_style,
            reference_text=reference_text,
            **extra_fields,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldSetting":
        payload = dict(data or {})
        extra_fields = {
            key: value
            for key, value in payload.items()
            if key not in cls._KNOWN_FIELDS
        }
        world = cls(
            id=payload.get("id") or f"world_{uuid.uuid4().hex[:12]}",
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            era=payload.get("era", ""),
            anchor_time=payload.get("anchor_time", ""),
            settings=payload.get("settings") or {},
            entities=[Entity.from_dict(item, payload.get("id")) for item in payload.get("entities") or []],
            events=[Event.from_dict(item, payload.get("id")) for item in payload.get("events") or []],
            writing_style=payload.get("writing_style", ""),
            reference_text=payload.get("reference_text", ""),
            created_at=payload.get("created_at"),
            updated_at=payload.get("updated_at"),
            **extra_fields,
        )
        _normalize_world_entity_setting_links(world)
        return world

    @classmethod
    def get_by_id(cls, world_id: str) -> Optional["WorldSetting"]:
        return WorldManager.get_world(world_id)

    def update(self, data: Dict[str, Any]):
        payload = dict(data or {})
        world_info = payload.pop("world_info", None)
        if isinstance(world_info, dict):
            payload = {**world_info, **payload}

        for field_name in ("name", "description", "era", "anchor_time", "writing_style", "reference_text"):
            if field_name in payload:
                setattr(self, field_name, payload.get(field_name) or "")

        if "settings" in payload:
            self.settings = payload.get("settings") or {}
        if "entities" in payload:
            self.entities = [Entity.from_dict(item, self.id) for item in payload.get("entities") or []]
        if "events" in payload:
            self.events = [Event.from_dict(item, self.id) for item in payload.get("events") or []]

        for key, value in payload.items():
            if key in self._KNOWN_FIELDS or key == "world_info":
                continue
            setattr(self, key, value)

        _normalize_world_entity_setting_links(self)
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        _normalize_world_entity_setting_links(self)
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "era": self.era,
            "anchor_time": self.anchor_time,
            "settings": self.settings,
            "entities": [entity.to_dict() for entity in self.entities],
            "events": [event.to_dict() for event in self.events],
            "writing_style": self.writing_style,
            "reference_text": self.reference_text,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        for key, value in self.__dict__.items():
            if key in data:
                continue
            data[key] = value
        return data

    def to_text(self) -> str:
        sections: List[str] = []

        world_info_lines = []
        if self.name:
            world_info_lines.append(f"世界观名称: {self.name}")
        if self.description:
            world_info_lines.append(f"世界观描述: {self.description}")
        if self.era:
            world_info_lines.append(f"时代背景: {self.era}")
        if self.anchor_time:
            world_info_lines.append(f"锚定时间: {self.anchor_time}")
        if world_info_lines:
            sections.append("世界观基础信息:\n" + "\n".join(world_info_lines))

        settings = self.settings if isinstance(self.settings, dict) else {}

        item_lines = []
        for item in settings.get("items") or []:
            if not isinstance(item, dict):
                continue

            detail_parts = [f"- {item.get('name') or '未命名设定'}"]
            if item.get("category"):
                detail_parts.append(f"分类: {item['category']}")
            if item.get("settingType"):
                detail_parts.append(f"类型: {item['settingType']}")
            if item.get("description"):
                detail_parts.append(f"描述: {item['description']}")

            aliases = [str(alias) for alias in item.get("aliases") or [] if alias]
            if aliases:
                detail_parts.append(f"别名: {', '.join(aliases)}")

            item_lines.append("；".join(detail_parts))

        if item_lines:
            sections.append("世界观设定条目:\n" + "\n".join(item_lines))

        map_data = settings.get("mapData") if isinstance(settings.get("mapData"), dict) else {}
        map_lines = []
        if map_data.get("regionRelations"):
            map_lines.append(f"区域关系: {map_data['regionRelations']}")
        if map_data.get("countryRelations"):
            map_lines.append(f"国家关系: {map_data['countryRelations']}")
        if map_data.get("importantLocations"):
            map_lines.append(f"重要地点: {map_data['importantLocations']}")
        structured_maps = map_data.get("structuredMaps") if isinstance(map_data.get("structuredMaps"), list) else []
        for map_item in structured_maps[:5]:
            if not isinstance(map_item, dict):
                continue
            cells = map_item.get("cells") if isinstance(map_item.get("cells"), list) else []
            map_lines.append(
                f"结构化地图《{map_item.get('name') or '未命名地图'}》: "
                f"类型={map_item.get('type') or 'world'}，尺寸={map_item.get('width')}x{map_item.get('height')}，区域数={len(cells)}"
            )
            notable_cells = []
            for cell in cells:
                if not isinstance(cell, dict):
                    continue
                if cell.get("name") or cell.get("faction") or cell.get("resources") or cell.get("status") not in ("normal", ""):
                    parts = [cell.get("name") or cell.get("id") or "未命名区域"]
                    if cell.get("terrain"):
                        parts.append(f"地形={cell.get('terrain')}")
                    if cell.get("faction"):
                        parts.append(f"势力={cell.get('faction')}")
                    if cell.get("resources"):
                        parts.append(f"资源={', '.join(str(item) for item in cell.get('resources') or [])}")
                    if cell.get("status") and cell.get("status") != "normal":
                        parts.append(f"状态={cell.get('status')}")
                    notable_cells.append("；".join(parts))
                if len(notable_cells) >= 12:
                    break
            if notable_cells:
                map_lines.append("重要地图区域: " + " | ".join(notable_cells))
        if map_lines:
            sections.append("地图与地点:\n" + "\n".join(f"- {line}" for line in map_lines))

        calendar_lines = []
        for calendar in settings.get("calendars") or []:
            if not isinstance(calendar, dict):
                continue

            detail_parts = [f"- {calendar.get('name') or '未命名历法'}"]
            if calendar.get("type"):
                detail_parts.append(f"类型: {calendar['type']}")
            if calendar.get("timeRange"):
                detail_parts.append(f"时间范围: {calendar['timeRange']}")
            if calendar.get("description"):
                detail_parts.append(f"描述: {calendar['description']}")
            calendar_lines.append("；".join(detail_parts))

        if calendar_lines:
            sections.append("历法系统:\n" + "\n".join(calendar_lines))

        entity_lines = []
        for entity in self.entities:
            detail_parts = [f"- {entity.name or '未命名实体'}"]
            if entity.type:
                detail_parts.append(f"类型: {entity.type}")
            if entity.attributes:
                attributes_text = "；".join(
                    f"{key}={value}" for key, value in entity.attributes.items() if value is not None
                )
                if attributes_text:
                    detail_parts.append(f"属性: {attributes_text}")
            if entity.stages:
                stage_lines = []
                for stage in entity.stages:
                    if not isinstance(stage, dict):
                        continue
                    stage_parts = [str(stage.get("name") or "未命名阶段").strip()]
                    if stage.get("era"):
                        stage_parts.append(f"时期: {stage['era']}")
                    if stage.get("description"):
                        stage_parts.append(f"描述: {stage['description']}")
                    stage_lines.append("（" + "；".join(part for part in stage_parts if part) + "）")
                if stage_lines:
                    detail_parts.append(f"阶段: {' '.join(stage_lines)}")
            entity_lines.append("；".join(detail_parts))

        if entity_lines:
            sections.append("核心实体:\n" + "\n".join(entity_lines))

        event_lines = []
        for event in self.events:
            detail_parts = [f"- {event.name or '未命名事件'}"]
            if event.date:
                detail_parts.append(f"时间: {event.date}")
            if event.description:
                detail_parts.append(f"描述: {event.description}")
            if event.entities:
                detail_parts.append(f"关联实体: {', '.join(str(item) for item in event.entities if item)}")
            event_lines.append("；".join(detail_parts))

        if event_lines:
            sections.append("关键事件:\n" + "\n".join(event_lines))

        return "\n\n".join(section for section in sections if section).strip()


class WorldManager:
    """文件持久化世界观仓库。"""

    WORLDS_DIR = os.path.join(Config.UPLOAD_FOLDER, "worlds")
    WORLD_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,120}$")
    _lock = threading.RLock()

    @classmethod
    def _ensure_base_dir(cls):
        os.makedirs(cls.WORLDS_DIR, exist_ok=True)

    @classmethod
    def is_valid_world_id(cls, world_id: str) -> bool:
        world_id = str(world_id or "").strip()
        return bool(world_id and cls.WORLD_ID_RE.fullmatch(world_id))

    @classmethod
    def _safe_world_id(cls, world_id: str) -> str:
        world_id = str(world_id or "").strip()
        if not cls.is_valid_world_id(world_id):
            raise ValueError(f"非法世界观 ID: {world_id}")
        return world_id

    @classmethod
    def _safe_join_world_path(cls, world_id: str, *parts: str) -> str:
        cls._ensure_base_dir()
        base_dir = os.path.abspath(cls.WORLDS_DIR)
        target = os.path.abspath(os.path.join(base_dir, cls._safe_world_id(world_id), *parts))
        if os.path.commonpath([base_dir, target]) != base_dir:
            raise ValueError(f"非法世界观路径: {world_id}")
        return target

    @classmethod
    def _world_dir(cls, world_id: str) -> str:
        return cls._safe_join_world_path(world_id)

    @classmethod
    def _world_file(cls, world_id: str) -> str:
        return cls._safe_join_world_path(world_id, "world.json")

    @classmethod
    def _write_json_atomic(cls, path: str, payload: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @classmethod
    def create_world(
        cls,
        name: str,
        description: str = "",
        era: str = "",
        anchor_time: str = "",
        settings: Optional[Dict[str, Any]] = None,
        writing_style: str = "",
        reference_text: str = "",
        **extra_fields: Any,
    ) -> WorldSetting:
        with cls._lock:
            world = WorldSetting.create(
                name=name,
                description=description,
                era=era,
                anchor_time=anchor_time,
                settings=settings,
                writing_style=writing_style,
                reference_text=reference_text,
                **extra_fields,
            )
            cls.save_world(world)
            return world

    @classmethod
    def save_world(cls, world: WorldSetting) -> WorldSetting:
        with cls._lock:
            os.makedirs(cls._world_dir(world.id), exist_ok=True)
            _normalize_world_entity_setting_links(world)
            world.updated_at = datetime.now().isoformat()
            cls._write_json_atomic(cls._world_file(world.id), world.to_dict())
            return world

    @classmethod
    def get_world(cls, world_id: str) -> Optional[WorldSetting]:
        if not cls.is_valid_world_id(world_id):
            return None
        path = cls._world_file(world_id)
        if not os.path.exists(path):
            return None
        with cls._lock:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return WorldSetting.from_dict(payload)

    @classmethod
    def update_world(cls, world_id: str, data: Dict[str, Any]) -> Optional[WorldSetting]:
        with cls._lock:
            world = cls.get_world(world_id)
            if not world:
                return None
            world.update(data)
            return cls.save_world(world)

    @classmethod
    def add_entity(
        cls,
        world_id: str,
        name: str,
        type: str,
        attributes: Optional[Dict[str, Any]] = None,
        stages: Optional[List[Dict[str, Any]]] = None,
        setting_item_id: str = "",
    ) -> Entity:
        with cls._lock:
            world = cls.get_world(world_id)
            if not world:
                raise ValueError(f"世界观不存在: {world_id}")
            entity = Entity.create(
                world_id=world_id,
                name=name,
                type=type,
                attributes=attributes,
                stages=stages,
                setting_item_id=setting_item_id,
            )
            world.entities.append(entity)
            cls.save_world(world)
            return entity

    @classmethod
    def add_event(
        cls,
        world_id: str,
        name: str,
        description: str,
        date: str,
        entities: Optional[List[str]] = None,
    ) -> Event:
        with cls._lock:
            world = cls.get_world(world_id)
            if not world:
                raise ValueError(f"世界观不存在: {world_id}")
            event = Event.create(
                world_id=world_id,
                name=name,
                description=description,
                date=date,
                entities=entities,
            )
            world.events.append(event)
            cls.save_world(world)
            return event

    @classmethod
    def list_worlds(cls) -> List[WorldSetting]:
        """列出所有世界观。单个坏文件不影响整个列表。"""
        cls._ensure_base_dir()
        worlds = []
        if os.path.isdir(cls.WORLDS_DIR):
            for dirname in os.listdir(cls.WORLDS_DIR):
                if not cls.is_valid_world_id(dirname):
                    continue
                try:
                    world = cls.get_world(dirname)
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    logger.warning(f"读取世界观失败，已跳过 [{dirname}]: {exc}")
                    continue
                if world:
                    worlds.append(world)
        worlds.sort(key=lambda w: w.updated_at, reverse=True)
        return worlds

    @classmethod
    def delete_world(cls, world_id: str) -> bool:
        with cls._lock:
            if not cls.is_valid_world_id(world_id):
                return False
            world_dir = cls._world_dir(world_id)
            if not os.path.exists(world_dir):
                return False
            shutil.rmtree(world_dir)
            return True
