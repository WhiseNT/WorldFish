"""世界观模型与持久化仓库。"""

import json
import os
import shutil
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config


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
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldSetting":
        payload = dict(data or {})
        extra_fields = {
            key: value
            for key, value in payload.items()
            if key not in cls._KNOWN_FIELDS
        }
        return cls(
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

        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
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
    _lock = threading.RLock()

    @classmethod
    def _ensure_base_dir(cls):
        os.makedirs(cls.WORLDS_DIR, exist_ok=True)

    @classmethod
    def _world_dir(cls, world_id: str) -> str:
        cls._ensure_base_dir()
        return os.path.join(cls.WORLDS_DIR, world_id)

    @classmethod
    def _world_file(cls, world_id: str) -> str:
        return os.path.join(cls._world_dir(world_id), "world.json")

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
            )
            cls.save_world(world)
            return world

    @classmethod
    def save_world(cls, world: WorldSetting) -> WorldSetting:
        with cls._lock:
            os.makedirs(cls._world_dir(world.id), exist_ok=True)
            world.updated_at = datetime.now().isoformat()
            with open(cls._world_file(world.id), "w", encoding="utf-8") as handle:
                json.dump(world.to_dict(), handle, ensure_ascii=False, indent=2)
            return world

    @classmethod
    def get_world(cls, world_id: str) -> Optional[WorldSetting]:
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
        """列出所有世界观"""
        cls._ensure_base_dir()
        worlds = []
        if os.path.isdir(cls.WORLDS_DIR):
            for dirname in os.listdir(cls.WORLDS_DIR):
                world = cls.get_world(dirname)
                if world:
                    worlds.append(world)
        worlds.sort(key=lambda w: w.updated_at, reverse=True)
        return worlds

    @classmethod
    def delete_world(cls, world_id: str) -> bool:
        with cls._lock:
            world_dir = cls._world_dir(world_id)
            if not os.path.exists(world_dir):
                return False
            shutil.rmtree(world_dir)
            return True
