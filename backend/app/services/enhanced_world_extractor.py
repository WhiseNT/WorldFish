"""
世界观提取服务
严格按照项目中已建立的世界观体系进行内容提取
支持并行 AI 调用，细粒度提取，确保不遗漏内容
章节感知切分，全文处理无遗漏
"""

from app.utils.llm_client import LLMClient
from app.utils.logger import get_logger
from app.prompts import load_prompt
import json
import re
import threading
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = get_logger('worldfish.service.enhanced_world_extractor')

# 每线程独立的 LLMClient，避免共享阻塞
_thread_local = threading.local()


class EnhancedWorldExtractor:
    """世界观提取器 — 章节感知 + 并行细粒度提取"""

    SETTING_CATEGORIES = {
        "character": ["character", "人物", "角色", "种族", "生物", "身份", "阵营成员"],
        "item": ["item", "物品", "道具", "装备", "资源", "科技", "技术", "建筑"],
        "organization": ["organization", "组织", "势力", "国家", "政权", "教会", "团体"],
        "geography": ["geography", "地理", "地点", "区域", "城市", "地貌", "环境"],
        "ability": ["ability", "能力", "魔法", "法术", "规则", "体系", "超凡"],
        "other": ["other", "其他", "文化", "历史", "社会", "经济", "设定"],
    }

    ALIAS_ATTRIBUTE_KEYS = (
        "别名", "别称", "曾用名", "旧名", "原名", "本名", "真名", "化名", "伪名", "代号",
        "称号", "外号", "昵称", "字", "号", "法号", "封号", "尊号",
        "former_name", "original_name", "real_name", "nickname", "codename",
    )

    GENERIC_IDENTITY_KEYS = {
        "他", "她", "它", "他们", "她们", "它们", "对方", "双方", "自己", "某人", "有人",
        "男人", "女人", "少年", "少女", "青年", "孩子", "老者", "老妇", "敌人", "敌军", "众人",
        "师父", "师尊", "老师", "师兄", "师姐", "师弟", "师妹", "父亲", "母亲", "哥哥", "姐姐", "弟弟", "妹妹",
        "掌门", "宗主", "门主", "教主", "教皇", "国王", "皇帝", "皇后", "王后", "王爷", "公主", "太子", "将军", "元帅", "大臣", "首领", "统领",
    }

    SETTING_CATEGORY_TO_ENTITY_TYPE = {
        "character": "人物",
        "item": "物品",
        "organization": "组织",
        "geography": "地点",
        "ability": "能力",
        "other": "其他",
    }

    # 分段阈值
    LONG_TEXT_THRESHOLD = 15000
    CHUNK_SIZE = 8000
    CHUNK_OVERLAP = 300
    CHAPTERS_PER_CHUNK = 4   # 每批最多合并 4 章，降低单次 LLM 负载
    CHAPTER_CHUNK_CHAR_BUDGET = 10000
    OUTER_WORKERS = 20       # 并行 LLM 调用数

    # 章节标记正则
    CHAPTER_RE = (
        r'(?:^|\n)\s*'
        r'(?:'
        r'第[零一二三四五六七八九十百千\d]+[部卷章节]'
        r'|Chapter\s+\d+'
        r'|Part\s+\d+'
        r'|VOLUME\s*\d+'
        r'|[第]?[零一二三四五六七八九十百千\d]+章[\s\n]'
        r')'
    )

    def __init__(self):
        self.errors: List[str] = []

    @staticmethod
    def _get_client():
        """每线程独立 LLMClient，8 线程x独立连接池 = 8 倍并发"""
        if not hasattr(_thread_local, 'client'):
            _thread_local.client = LLMClient()
        return _thread_local.client

    def _record_error(self, stage: str, error: Exception):
        message = str(error).strip()
        logger.error(f"{stage}失败: {message}")
        self.errors.append(f"{stage}: {message}")

    def _has_meaningful_content(self, data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        if data.get("entities") or data.get("events"):
            return True
        wi = data.get("world_info") or {}
        if isinstance(wi, dict) and any(str(v).strip() for v in wi.values() if v is not None):
            return True
        settings = data.get("settings") or {}
        if isinstance(settings, dict):
            for v in settings.values():
                if isinstance(v, (dict, list)) and v:
                    return True
                if isinstance(v, str) and v.strip():
                    return True
        return False

    # ==================== 规范化 ====================

    def _normalize_setting_category(self, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if not normalized:
            return "other"
        for category, keywords in self.SETTING_CATEGORIES.items():
            if normalized == category:
                return category
            if any(keyword.lower() in normalized for keyword in keywords):
                return category
        return "other"

    def _to_string_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(i).strip() for i in value if str(i).strip()]
        if isinstance(value, str):
            for sep in [",", "，", "、", "/", "|"]:
                if sep in value:
                    return [p.strip() for p in value.split(sep) if p.strip()]
            return [value.strip()] if value.strip() else []
        return []

    def _normalize_identity_key(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        return re.sub(r"[\s\-—_·•・()（）\[\]{}《》<>『』\"'`]+", "", text)

    def _is_generic_identity_value(self, value: Any) -> bool:
        key = self._normalize_identity_key(value)
        return not key or key in self.GENERIC_IDENTITY_KEYS

    def _is_strong_identity_value(self, value: Any) -> bool:
        key = self._normalize_identity_key(value)
        if not key or key in self.GENERIC_IDENTITY_KEYS:
            return False
        return len(key) > 1

    def _dedupe_strings(self, values: List[Any], exclude: Optional[List[str]] = None) -> List[str]:
        excluded = {self._normalize_identity_key(value) for value in (exclude or []) if str(value or '').strip()}
        results: List[str] = []
        seen = set()
        for value in values or []:
            text = str(value or "").strip()
            if not text:
                continue
            key = self._normalize_identity_key(text)
            if not key or key in seen or key in excluded:
                continue
            seen.add(key)
            results.append(text)
        return results

    def _collect_entity_aliases(self, entity: Dict[str, Any], attributes: Dict[str, Any], name: str) -> List[str]:
        alias_values = self._to_string_list(entity.get("aliases") or entity.get("alias"))
        alias_values.extend(self._to_string_list(attributes.get("aliases") or attributes.get("alias") or attributes.get("别名")))

        for key in self.ALIAS_ATTRIBUTE_KEYS:
            alias_values.extend(self._to_string_list(entity.get(key)))
            alias_values.extend(self._to_string_list(attributes.get(key)))

        return self._dedupe_strings(alias_values, exclude=[name])

    def _is_placeholder_text(self, value: Any) -> bool:
        text = str(value or "").strip().lower()
        return text in {"", "未知", "未命名", "未定义", "暂无", "待定", "无", "none", "null", "unknown"}

    def _merge_text(self, *values: Any) -> str:
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

    def _merge_list_values(self, current: Any, incoming: Any) -> List[Any]:
        merged: List[Any] = []
        seen = set()
        for item in (current or []) + (incoming or []):
            try:
                key = json.dumps(item, ensure_ascii=False, sort_keys=True)
            except TypeError:
                key = str(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return merged

    def _merge_generic_value(self, current: Any, incoming: Any) -> Any:
        if incoming is None or incoming == "":
            return current
        if current is None or current == "":
            return incoming
        if isinstance(current, dict) and isinstance(incoming, dict):
            merged = dict(current)
            for key, value in incoming.items():
                merged[key] = self._merge_generic_value(merged.get(key), value)
            return merged
        if isinstance(current, list) and isinstance(incoming, list):
            return self._merge_list_values(current, incoming)
        if isinstance(current, str) or isinstance(incoming, str):
            current_text = str(current or "").strip()
            incoming_text = str(incoming or "").strip()
            if self._is_placeholder_text(current_text):
                return incoming_text
            if self._is_placeholder_text(incoming_text):
                return current_text
            if incoming_text in current_text:
                return current_text
            if current_text in incoming_text:
                return incoming_text
            return self._merge_text(current_text, incoming_text)
        return incoming if self._is_placeholder_text(current) else current

    def _normalize_stage(self, stage: Any, entity_name: str = "", index: int = 0) -> Dict[str, Any]:
        if not isinstance(stage, dict):
            return {}
        raw_attributes = stage.get("attributes") or stage.get("属性") or {}
        attributes = dict(raw_attributes) if isinstance(raw_attributes, dict) else {}
        name = str(stage.get("name") or stage.get("名称") or stage.get("title") or f"{entity_name or '实体'}阶段{index + 1}").strip()
        if not name:
            return {}
        return {
            "id": stage.get("id") or f"stage_{entity_name or 'entity'}_{index}",
            "name": name,
            "era": str(stage.get("era") or stage.get("时期") or stage.get("time") or "").strip(),
            "description": str(stage.get("description") or stage.get("描述") or "").strip(),
            "attributes": attributes,
            "setting_item_id": str(stage.get("setting_item_id") or stage.get("settingId") or stage.get("linked_setting_id") or "").strip(),
            "source": dict(stage.get("source")) if isinstance(stage.get("source"), dict) else {},
        }

    def _normalize_relationship(self, relationship: Any) -> Dict[str, Any]:
        if isinstance(relationship, str):
            return {}
        if not isinstance(relationship, dict):
            return {}
        target = str(
            relationship.get("target")
            or relationship.get("entity")
            or relationship.get("name")
            or relationship.get("对象")
            or relationship.get("目标")
            or relationship.get("related_entity")
            or ""
        ).strip()
        relation_type = str(
            relationship.get("type")
            or relationship.get("relation")
            or relationship.get("kind")
            or relationship.get("关系类型")
            or relationship.get("关系")
            or "关联"
        ).strip()
        description = str(
            relationship.get("description")
            or relationship.get("detail")
            or relationship.get("summary")
            or relationship.get("说明")
            or ""
        ).strip()
        if not target:
            return {}
        return {
            "target": target,
            "type": relation_type or "关联",
            "description": description,
            "time_period": str(relationship.get("time_period") or relationship.get("period") or relationship.get("时期") or relationship.get("时间") or "").strip(),
            "source_event": str(relationship.get("source_event") or relationship.get("event") or relationship.get("触发事件") or "").strip(),
        }

    def _build_relationship_summary(self, relationships: List[Dict[str, Any]]) -> str:
        lines = []
        for relationship in relationships[:8]:
            target = relationship.get("target") or ""
            relation_type = relationship.get("type") or "关联"
            description = relationship.get("description") or ""
            summary = f"{target}（{relation_type}）"
            if description:
                summary = f"{summary}: {description}"
            if summary not in lines:
                lines.append(summary)
        return "；".join(lines)

    def _normalize_entity(self, entity: Any) -> Dict[str, Any]:
        if not isinstance(entity, dict):
            return {}
        name = str(entity.get("name") or entity.get("title") or entity.get("label") or "").strip()
        if not name:
            return {}
        raw_attributes = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
        attributes = dict(raw_attributes)
        raw_stages = entity.get("stages") or entity.get("阶段") or attributes.get("stages") or attributes.get("阶段") or []
        raw_relationships = (
            entity.get("relationships")
            or entity.get("relations")
            or entity.get("links")
            or attributes.get("relationships")
            or attributes.get("关系")
            or attributes.get("关系网络")
            or []
        )

        if isinstance(raw_relationships, dict):
            raw_relationships = [
                {"target": target, "description": value}
                for target, value in raw_relationships.items()
                if str(target or "").strip() and str(value or "").strip()
            ]

        stages = [
            normalized for index, stage in enumerate(raw_stages if isinstance(raw_stages, list) else [])
            for normalized in [self._normalize_stage(stage, entity_name=name, index=index)]
            if normalized
        ]
        relationships = [
            normalized for relationship in (raw_relationships if isinstance(raw_relationships, list) else [])
            for normalized in [self._normalize_relationship(relationship)]
            if normalized
        ]

        for field in ["stages", "阶段", "relationships", "关系", "关系网络"]:
            attributes.pop(field, None)

        aliases = self._collect_entity_aliases(entity, attributes, name)

        if relationships and not str(attributes.get("关系网络概述") or "").strip():
            attributes["关系网络概述"] = self._build_relationship_summary(relationships)

        if str(entity.get("type") or "").strip() == "人物":
            for key in ["实力变化", "性格变化", "关键转折"]:
                value = attributes.get(key)
                if value and not isinstance(value, list):
                    attributes[key] = [value]
                elif value is None:
                    attributes[key] = []

        return {
            **entity,
            "name": name,
            "type": str(entity.get("type") or "其他").strip() or "其他",
            "aliases": aliases,
            "attributes": attributes,
            "stages": stages,
            "relationships": relationships,
        }

    def _normalize_event(self, event: Any) -> Dict[str, Any]:
        if not isinstance(event, dict):
            return {}
        name = str(event.get("name") or event.get("title") or "").strip()
        if not name:
            return {}
        entities = self._dedupe_strings(self._to_string_list(event.get("entities") or event.get("participants") or []))
        time_type = str(event.get("time_type") or "unknown").strip().lower() or "unknown"
        if time_type not in self.VALID_TIME_TYPES:
            time_type = "unknown"
        return {
            **event,
            "name": name,
            "description": str(event.get("description") or "").strip(),
            "time_type": time_type,
            "estimated_date": str(event.get("estimated_date") or event.get("estimatedTime") or "未知").strip() or "未知",
            "date": str(event.get("date") or "").strip(),
            "entities": entities,
        }

    def _entity_identity_keys(self, entity: Dict[str, Any]) -> List[str]:
        keys: List[str] = []
        seen = set()

        name_key = self._normalize_identity_key(entity.get("name"))
        if name_key:
            keys.append(name_key)
            seen.add(name_key)

        for value in entity.get("aliases") or []:
            alias_key = self._normalize_identity_key(value)
            if not alias_key or alias_key in seen or not self._is_strong_identity_value(value):
                continue
            keys.append(alias_key)
            seen.add(alias_key)

        return keys

    def _merge_stage_lists(self, current: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged_by_key: Dict[str, Dict[str, Any]] = {}
        for index, stage in enumerate((current or []) + (incoming or [])):
            normalized = self._normalize_stage(stage, index=index)
            if not normalized:
                continue
            key = f"{self._normalize_identity_key(normalized.get('name'))}|{self._normalize_identity_key(normalized.get('era'))}"
            existing = merged_by_key.get(key)
            if not existing:
                merged_by_key[key] = normalized
                continue
            merged_by_key[key] = {
                **existing,
                **normalized,
                "description": self._merge_text(existing.get("description"), normalized.get("description")),
                "attributes": self._merge_generic_value(existing.get("attributes") or {}, normalized.get("attributes") or {}),
                "source": self._merge_generic_value(existing.get("source") or {}, normalized.get("source") or {}),
                "setting_item_id": str(existing.get("setting_item_id") or normalized.get("setting_item_id") or "").strip(),
            }
        return list(merged_by_key.values())

    def _merge_relationship_lists(self, current: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged_by_key: Dict[str, Dict[str, Any]] = {}
        for relationship in (current or []) + (incoming or []):
            normalized = self._normalize_relationship(relationship)
            if not normalized:
                continue
            key = f"{self._normalize_identity_key(normalized.get('target'))}|{self._normalize_identity_key(normalized.get('type'))}"
            existing = merged_by_key.get(key)
            if not existing:
                merged_by_key[key] = normalized
                continue
            merged_by_key[key] = {
                **existing,
                **normalized,
                "description": self._merge_text(existing.get("description"), normalized.get("description")),
                "time_period": self._merge_text(existing.get("time_period"), normalized.get("time_period")),
                "source_event": self._merge_text(existing.get("source_event"), normalized.get("source_event")),
            }
        return list(merged_by_key.values())

    def _merge_entity_attributes(self, current: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(current or {})
        for key, value in (incoming or {}).items():
            merged[key] = self._merge_generic_value(merged.get(key), value)
        return merged

    def _merge_entities(self, current: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        existing = self._normalize_entity(current)
        new_value = self._normalize_entity(incoming)
        if not existing:
            return new_value
        if not new_value:
            return existing

        preferred_type = existing.get("type")
        if preferred_type in {"", "其他"} and new_value.get("type") not in {"", "其他"}:
            preferred_type = new_value.get("type")

        preferred_name = existing.get("name")
        if self._is_placeholder_text(preferred_name) and not self._is_placeholder_text(new_value.get("name")):
            preferred_name = new_value.get("name")

        aliases = self._dedupe_strings(
            [existing.get("name"), new_value.get("name")] + list(existing.get("aliases") or []) + list(new_value.get("aliases") or []),
            exclude=[preferred_name],
        )
        relationships = self._merge_relationship_lists(existing.get("relationships") or [], new_value.get("relationships") or [])
        attributes = self._merge_entity_attributes(existing.get("attributes") or {}, new_value.get("attributes") or {})
        if relationships:
            attributes["关系网络概述"] = self._build_relationship_summary(relationships)

        return {
            **existing,
            **new_value,
            "name": preferred_name,
            "type": preferred_type or "其他",
            "aliases": aliases,
            "attributes": attributes,
            "stages": self._merge_stage_lists(existing.get("stages") or [], new_value.get("stages") or []),
            "relationships": relationships,
        }

    def _merge_events(self, current: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        existing = self._normalize_event(current)
        new_value = self._normalize_event(incoming)
        if not existing:
            return new_value
        if not new_value:
            return existing
        return {
            **existing,
            **new_value,
            "name": existing.get("name") or new_value.get("name"),
            "description": self._merge_text(existing.get("description"), new_value.get("description")),
            "time_type": new_value.get("time_type") if existing.get("time_type") == "unknown" and new_value.get("time_type") != "unknown" else existing.get("time_type"),
            "estimated_date": new_value.get("estimated_date") if self._is_placeholder_text(existing.get("estimated_date")) and not self._is_placeholder_text(new_value.get("estimated_date")) else existing.get("estimated_date"),
            "date": new_value.get("date") or existing.get("date") or "",
            "entities": self._dedupe_strings(list(existing.get("entities") or []) + list(new_value.get("entities") or [])),
        }

    def _canonicalize_entity_links(self, entities: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> None:
        alias_to_name: Dict[str, str] = {}
        for entity in entities or []:
            canonical_name = str(entity.get("name") or "").strip()
            if not canonical_name:
                continue
            for key in self._entity_identity_keys(entity):
                if key and key not in alias_to_name:
                    alias_to_name[key] = canonical_name

        for entity in entities or []:
            normalized_relationships = []
            for relationship in entity.get("relationships") or []:
                normalized = self._normalize_relationship(relationship)
                if not normalized:
                    continue
                canonical_target = alias_to_name.get(self._normalize_identity_key(normalized.get("target")), normalized.get("target"))
                normalized["target"] = canonical_target
                normalized_relationships.append(normalized)
            entity["relationships"] = self._merge_relationship_lists([], normalized_relationships)
            if entity.get("relationships"):
                entity.setdefault("attributes", {})["关系网络概述"] = self._build_relationship_summary(entity["relationships"])

        for event in events or []:
            canonical_entities = []
            for name in event.get("entities") or []:
                canonical_entities.append(alias_to_name.get(self._normalize_identity_key(name), str(name or "").strip()))
            event["entities"] = self._dedupe_strings(canonical_entities)

    def _setting_identity_keys(self, item: Dict[str, Any]) -> List[str]:
        keys: List[str] = []
        seen = set()
        for value in [item.get("name")] + list(item.get("aliases") or []):
            key = self._normalize_identity_key(value)
            if not key or key in seen:
                continue
            keys.append(key)
            seen.add(key)
        return keys

    def _setting_category_to_entity_type(self, category: Any) -> str:
        return self.SETTING_CATEGORY_TO_ENTITY_TYPE.get(
            self._normalize_setting_category(category),
            "其他",
        )

    def _ensure_referenced_entities_exist(
        self,
        entities: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        settings: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        normalized_entities = [
            normalized for entity in entities or []
            for normalized in [self._normalize_entity(entity)]
            if normalized
        ]

        entity_index: Dict[str, Dict[str, Any]] = {}
        for entity in normalized_entities:
            for key in self._entity_identity_keys(entity):
                entity_index.setdefault(key, entity)

        setting_index: Dict[str, Dict[str, Any]] = {}
        for item in settings.get("items") or []:
            normalized_item = self._normalize_setting_item(item)
            if not normalized_item:
                continue
            for key in self._setting_identity_keys(normalized_item):
                setting_index.setdefault(key, normalized_item)

        reference_names: Dict[str, str] = {}
        reference_notes: Dict[str, List[str]] = {}
        inferred_types: Dict[str, str] = {}
        personal_relationship_types = {"亲属", "敌对", "盟友", "上下级", "师徒"}

        def add_reference(raw_name: Any, note: str = "", inferred_type: str = "") -> None:
            name = str(raw_name or "").strip()
            key = self._normalize_identity_key(name)
            if not key or self._is_generic_identity_value(name):
                return
            reference_names.setdefault(key, name)
            if note:
                reference_notes.setdefault(key, [])
                if note not in reference_notes[key]:
                    reference_notes[key].append(note)
            if inferred_type and key not in inferred_types:
                inferred_types[key] = inferred_type

        for event in events or []:
            event_name = str(event.get("name") or "").strip()
            for name in event.get("entities") or []:
                add_reference(name, f"在事件《{event_name}》中被明确提及。")

        for entity in normalized_entities:
            entity_name = str(entity.get("name") or "").strip()
            entity_type = str(entity.get("type") or "").strip()
            for relationship in entity.get("relationships") or []:
                target = relationship.get("target")
                relation_type = str(relationship.get("type") or "关联").strip() or "关联"
                inferred_type = "人物" if entity_type == "人物" and relation_type in personal_relationship_types else ""
                add_reference(target, f"与{entity_name}存在{relation_type}关系。", inferred_type=inferred_type)

        for key, reference_name in reference_names.items():
            existing = entity_index.get(key)
            setting_item = setting_index.get(key)

            if existing:
                if setting_item:
                    if existing.get("type") in {"", "其他"}:
                        existing["type"] = self._setting_category_to_entity_type(setting_item.get("category"))
                    existing.setdefault("attributes", {})
                    existing["attributes"]["简介"] = self._merge_text(
                        existing["attributes"].get("简介"),
                        setting_item.get("description"),
                        setting_item.get("detailContent"),
                    )
                continue

            display_name = str(setting_item.get("name") if setting_item else reference_name).strip() or reference_name
            intro = self._merge_text(
                setting_item.get("description") if setting_item else "",
                setting_item.get("detailContent") if setting_item else "",
                "；".join(reference_notes.get(key) or []),
            ) or f"文本中明确提及了实体“{display_name}”。"

            aliases = [reference_name]
            if setting_item:
                aliases.extend(setting_item.get("aliases") or [])

            stub = self._normalize_entity({
                "name": display_name,
                "type": inferred_types.get(key) or (
                    self._setting_category_to_entity_type(setting_item.get("category")) if setting_item else "其他"
                ),
                "aliases": self._dedupe_strings(aliases, exclude=[display_name]),
                "attributes": {"简介": intro},
            })
            if not stub:
                continue

            normalized_entities.append(stub)
            for identity_key in self._entity_identity_keys(stub):
                entity_index.setdefault(identity_key, stub)

        return normalized_entities

    def _finalize_extraction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        normalized_entities = []
        for entity in data.get("entities") or []:
            normalized = self._normalize_entity(entity)
            if normalized:
                normalized_entities.append(normalized)

        normalized_events = []
        for event in data.get("events") or []:
            normalized = self._normalize_event(event)
            if normalized:
                normalized_events.append(normalized)

        finalized = self._merge_extractions([{
            "world_info": data.get("world_info") or {},
            "entities": normalized_entities,
            "events": normalized_events,
            "settings": self._normalize_settings(data.get("settings") or {}),
        }])
        finalized["entities"] = self._ensure_referenced_entities_exist(
            finalized.get("entities") or [],
            finalized.get("events") or [],
            finalized.get("settings") or {},
        )
        self._canonicalize_entity_links(finalized.get("entities") or [], finalized.get("events") or [])
        finalized["writing_style"] = str(data.get("writing_style") or "").strip()
        finalized["reference_text"] = str(data.get("reference_text") or "")
        return finalized

    def _normalize_setting_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        name = str(item.get("name") or item.get("title") or item.get("label") or "").strip()
        desc = str(item.get("description") or item.get("summary") or item.get("content") or "").strip()
        detail = str(item.get("detailContent") or item.get("detail") or desc).strip()
        if not name or not (desc or detail):
            return {}
        return {
            "name": name, "settingType": "setting",
            "category": self._normalize_setting_category(item.get("category") or item.get("type")),
            "description": desc or detail, "aliases": self._to_string_list(item.get("aliases") or item.get("alias")),
            "detailContent": detail or desc,
        }

    def _normalize_calendar(self, item: Dict[str, Any]) -> Dict[str, Any]:
        name = str(item.get("name") or item.get("title") or "").strip()
        if not name:
            return {}
        ct = str(item.get("type") or item.get("calendarKind") or "纪元").strip()
        if "纪年" not in ct:
            ct = "纪元"
        bt = str(item.get("baseTime") or item.get("startYear") or item.get("start") or "").strip()
        et = str(item.get("endYear") or item.get("end") or "").strip()
        tr = str(item.get("timeRange") or "").strip()
        if not tr and bt:
            tr = f"{bt} ~ {et or '无'}"
        ratio = str(item.get("ratio") or "×1").strip() or "×1"
        if not ratio.startswith("×"):
            ratio = f"×{ratio}"
        return {
            "name": name, "type": ct, "baseTime": bt, "timeRange": tr,
            "unit": str(item.get("unit") or "年").strip() or "年", "ratio": ratio,
            "calendarType": str(item.get("calendarType") or item.get("monthDaySystem") or "未开启").strip() or "未开启",
            "description": str(item.get("description") or item.get("detail") or "").strip(),
        }

    def _normalize_map_text(self, value: Any) -> str:
        if isinstance(value, list):
            return "\n".join(str(i).strip() for i in value if str(i).strip())
        if isinstance(value, dict):
            return "\n".join(f"{k}: {i}" for k, i in value.items() if str(i).strip())
        return str(value or "").strip()

    def _normalize_settings(self, settings: Any) -> Dict[str, Any]:
        normalized = {
            "items": [], "mapData": {"regionRelations": "", "countryRelations": "", "importantLocations": ""}, "calendars": [],
        }
        if not isinstance(settings, dict):
            return normalized
        raw_items = settings.get("items") if isinstance(settings.get("items"), list) else []
        raw_cals = settings.get("calendars") if isinstance(settings.get("calendars"), list) else []
        raw_map = settings.get("mapData") if isinstance(settings.get("mapData"), dict) else {}
        normalized["items"] = [
            ni for item in raw_items if isinstance(item, dict) for ni in [self._normalize_setting_item(item)] if ni
        ]
        normalized["calendars"] = [
            nc for item in raw_cals if isinstance(item, dict) for nc in [self._normalize_calendar(item)] if nc
        ]
        normalized["mapData"] = {
            "regionRelations": self._normalize_map_text(raw_map.get("regionRelations") or raw_map.get("区域关系")),
            "countryRelations": self._normalize_map_text(raw_map.get("countryRelations") or raw_map.get("国家关系")),
            "importantLocations": self._normalize_map_text(raw_map.get("importantLocations") or raw_map.get("重要地点")),
        }
        if not raw_items and not raw_cals and not raw_map:
            for key, value in settings.items():
                if key in {"items", "mapData", "calendars"}:
                    continue
                text = self._normalize_map_text(value)
                if not text:
                    continue
                normalized["items"].append({
                    "name": str(key).strip(), "settingType": "setting",
                    "category": self._normalize_setting_category(key),
                    "description": text, "aliases": [], "detailContent": text,
                })
        return normalized

    # ==================== 综合提取 ====================

    _EXTRACTION_SYSTEM_PROMPT = load_prompt("extraction_system")

    def _extract_from_chunk(self, chunk: str, chunk_index: int = 0) -> Dict[str, Any]:
        """单次 LLM 调用穷举提取一个文本块的所有世界观数据"""
        context_text = ("这是整个文本的开头部分（含多章），世界观基础设定通常在此。"
                        if chunk_index == 0
                        else f"这是文本的第{chunk_index + 1}个章节组（含多章）。请提取本段中出现的所有信息。")
        prompt = load_prompt("extraction_chunk", context=context_text, chunk=chunk)


        result = self._get_client().chat_json(
            messages=[
                {"role": "system", "content": self._EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=32768,
        )

        if not isinstance(result, dict):
            raise ValueError(f"章节组{chunk_index + 1}提取返回格式无效")

        entities = result.get("entities") or []
        if isinstance(entities, list):
            entities = [
                normalized for entity in entities
                for normalized in [self._normalize_entity(entity)]
                if normalized
            ]

        events = result.get("events") or []
        if isinstance(events, list):
            events = [
                normalized for event in events
                for normalized in [self._normalize_event(event)]
                if normalized
            ]

        settings = self._normalize_settings(result.get("settings") or {})
        world_info = result.get("world_info") or {}

        chunk_result = {
            "world_info": world_info if chunk_index == 0 else {},
            "entities": entities,
            "events": events,
            "settings": settings,
        }

        # 验证提取结果
        validation_errors = self._validate_chunk_result(chunk_result, chunk_index)
        if validation_errors:
            critical = [e for e in validation_errors if "name 缺失" in e]
            if critical:
                logger.error(f"章节组{chunk_index + 1}有 {len(critical)} 个致命验证错误")
                self._record_error(f"章节组{chunk_index + 1}验证", ValueError("; ".join(critical[:5])))

        logger.info(f"章节组{chunk_index + 1}: {len(entities)} 实体, {len(events)} 事件, {len(settings.get('items', []))} 设定条目, {len(validation_errors)} 验证问题")
        return chunk_result

    # ==================== 整体提取流程 ====================

    def extract_from_text(self, text: str, progress_callback=None) -> Dict[str, Any]:
        """从文本提取世界观信息（章节感知全文处理，无遗漏）"""
        text_len = len(text) if text else 0
        if text_len <= self.LONG_TEXT_THRESHOLD:
            return self._extract_short_text(text, progress_callback)
        logger.info(f"文本 {text_len} 字符 -> 章节感知全量提取")
        return self._extract_chapters(text, progress_callback)

    def _extract_short_text(self, text: str, progress_callback=None) -> Dict[str, Any]:
        """短文本提取：主提取与文风分析并行，节省一次 LLM 往返"""
        self.errors = []
        try:
            # 主提取和文风分析互不依赖，并行执行
            from concurrent.futures import ThreadPoolExecutor, as_completed

            if progress_callback:
                progress_callback('extracting', 10, '正在提取世界观信息 + 分析文风...')

            extraction_result = [None]
            style_result = [None]
            errors = []

            def do_extract():
                try:
                    return self._extract_from_chunk(text, chunk_index=0)
                except Exception as e:
                    errors.append(e)
                    return None

            def do_style():
                try:
                    return self.extract_writing_style(text)
                except Exception as e:
                    self._record_error("文风分析", e)
                    return {"writing_style": "", "reference_text": text[:2000] if text else ""}

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_extract = executor.submit(do_extract)
                future_style = executor.submit(do_style)

                for future in as_completed([future_extract, future_style]):
                    if future == future_extract:
                        extraction_result[0] = future.result()
                        if progress_callback:
                            progress_callback('extracting', 50, '世界观提取完成，等待文风分析...')
                    else:
                        style_result[0] = future.result()

            if errors or extraction_result[0] is None:
                raise ValueError("世界观提取失败，请检查 LLM 配置。详细错误：" + " | ".join(str(e) for e in errors))

            result = extraction_result[0]
            style_data = style_result[0] or {"writing_style": "", "reference_text": text[:2000] if text else ""}

            if progress_callback:
                progress_callback('finalizing', 85, '正在整理结果...')

            extracted_data = {
                "world_info": result["world_info"],
                "entities": result["entities"],
                "events": result["events"],
                "settings": self._normalize_settings(result.get("settings") or {}),
                "writing_style": style_data.get("writing_style", ""),
                "reference_text": style_data.get("reference_text", ""),
            }

            if progress_callback:
                progress_callback(
                    'consolidating',
                    90,
                    '正在执行规则整合，保留全部已提取实体与事件...' if not self.USE_LLM_CONSOLIDATION else '正在整合修正所有提取结果...'
                )
            extracted_data = self._consolidate_results(extracted_data)
            extracted_data = self._finalize_extraction(extracted_data)
            val_errors = self._validate_consolidated(extracted_data)
            if val_errors:
                logger.warning(f"整合后验证: {len(val_errors)} 个问题")

            if progress_callback:
                progress_callback('done', 95, f'提取完成: {len(extracted_data.get("entities", []))} 实体, {len(extracted_data.get("events", []))} 事件')

            logger.info(f"短文本提取完成: {len(extracted_data.get('entities', []))} 实体, {len(extracted_data.get('events', []))} 事件")
            return extracted_data
        except Exception as e:
            logger.error(f"提取世界观失败: {str(e)}")
            raise

    def _extract_chapters(self, text: str, progress_callback=None) -> Dict[str, Any]:
        """章节感知全量提取：文风分析+章节提取全部并行，不遗漏任何剧情"""
        self.errors = []
        chunks = self._chapter_aware_split(text)
        logger.info(f"章节切分: {len(text)} 字符 -> {len(chunks)} 个章节组（每 {self.CHAPTERS_PER_CHUNK} 章合并）")

        if len(chunks) == 1:
            return self._extract_short_text(chunks[0], progress_callback)

        max_workers = min(self.OUTER_WORKERS, len(chunks))
        all_results = [None] * len(chunks)
        style_result = [None]
        completed_count = [0]

        if progress_callback:
            progress_callback('extracting', 2,
                f'全量提取 {len(chunks)} 个章节组（{max_workers} 线程并行）+ 文风分析...')

        def process_chunk(idx, chunk):
            try:
                result = self._extract_from_chunk(chunk, chunk_index=idx)
                if self._has_meaningful_content(result):
                    return (idx, result)
            except Exception as e:
                self._record_error(f"章节组{idx + 1}", e)
            return (idx, None)

        def do_style():
            try:
                return self.extract_writing_style(chunks[0])
            except Exception as e:
                self._record_error("文风分析", e)
                return {"writing_style": "", "reference_text": chunks[0][:2000] if chunks[0] else ""}

        with ThreadPoolExecutor(max_workers=max_workers + 1) as executor:
            # 章节提取和文风分析全部并行
            future_style = executor.submit(do_style)
            futures = {executor.submit(process_chunk, i, c): i for i, c in enumerate(chunks)}

            for future in as_completed(futures):
                idx, result = future.result()
                if result:
                    all_results[idx] = result
                completed_count[0] += 1
                if progress_callback and len(chunks) > 0:
                    pct = 3 + int(completed_count[0] / len(chunks) * 85)
                    progress_callback('extracting', pct,
                        f'章节组 {completed_count[0]}/{len(chunks)} 完成...')

            # 等待文风分析完成
            style_result[0] = future_style.result()

        successful = [r for r in all_results if r is not None]
        if not successful:
            raise ValueError("所有章节提取均失败: " + " | ".join(self.errors))

        style_data = style_result[0] or {"writing_style": "", "reference_text": chunks[0][:2000] if chunks[0] else ""}

        if progress_callback:
            progress_callback('merging', 88, f'正在合并 {len(successful)} 个章节结果...')
        merged = self._merge_extractions(successful)
        merged["settings"] = self._normalize_settings(merged.get("settings") or {})
        merged["writing_style"] = style_data.get("writing_style", "")
        merged["reference_text"] = style_data.get("reference_text", "")

        if progress_callback:
            progress_callback(
                'consolidating',
                92,
                '正在执行规则整合，保留全部已提取实体与事件...' if not self.USE_LLM_CONSOLIDATION else '正在整合修正所有提取结果（合并身份、修正时间线、丰富生平）...'
            )
        merged = self._consolidate_results(merged)
        merged = self._finalize_extraction(merged)
        val_errors = self._validate_consolidated(merged)
        if val_errors:
            logger.warning(f"章节提取整合后验证: {len(val_errors)} 个问题")

        logger.info(f"章节提取完成: {len(merged.get('entities', []))} 实体, {len(merged.get('events', []))} 事件 ({len(successful)}/{len(chunks)})")
        return merged

    # ==================== 章节感知切分 ====================

    def _chapter_aware_split(self, text: str) -> List[str]:
        """按章节标记切分文本，每 CHAPTERS_PER_CHUNK 章合并为一次 LLM 调用"""
        chapter_starts = []
        for match in re.finditer(self.CHAPTER_RE, text, re.MULTILINE):
            pos = match.start()
            start = pos if text[pos] == '\n' else pos
            if text[start] == '\n':
                start = start + 1
            existing = {s for s, _ in chapter_starts}
            if start not in existing:
                chapter_starts.append((start, match.group().strip()))

        if not chapter_starts:
            logger.info("未检测到章节标记，使用等宽切分")
            return self._fallback_split(text)

        logger.info(
            f"检测到 {len(chapter_starts)} 个章节标记，每段最多 {self.CHAPTERS_PER_CHUNK} 章且不超过 {self.CHAPTER_CHUNK_CHAR_BUDGET} 字"
        )

        chapter_segments = []
        for idx, (start_pos, _) in enumerate(chapter_starts):
            end_pos = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(text)
            chapter_text = text[start_pos:end_pos].strip()
            if chapter_text:
                chapter_segments.append(chapter_text)

        chunks = []
        current_parts: List[str] = []
        current_len = 0
        for chapter_text in chapter_segments:
            chapter_len = len(chapter_text)
            exceeds_chapter_limit = len(current_parts) >= self.CHAPTERS_PER_CHUNK
            exceeds_char_budget = bool(current_parts) and current_len + chapter_len > self.CHAPTER_CHUNK_CHAR_BUDGET
            if exceeds_chapter_limit or exceeds_char_budget:
                chunk = "\n\n".join(current_parts).strip()
                if chunk:
                    chunks.append(chunk)
                current_parts = [chapter_text]
                current_len = chapter_len
                continue

            current_parts.append(chapter_text)
            current_len += chapter_len

        if current_parts:
            chunk = "\n\n".join(current_parts).strip()
            if chunk:
                chunks.append(chunk)

        avg_len = sum(len(c) for c in chunks) // max(len(chunks), 1)
        logger.info(f"切分结果: {len(chunks)} 段 (平均 {avg_len} 字符)")
        return chunks

    def _fallback_split(self, text: str) -> List[str]:
        """等宽切分（无章节标记时的回退方案）"""
        if len(text) <= self.CHUNK_SIZE:
            return [text] if text.strip() else []
        chunks = []
        pos = 0
        while pos < len(text):
            end = min(pos + self.CHUNK_SIZE, len(text))
            if end < len(text):
                search_start = max(pos + self.CHUNK_SIZE // 2, pos)
                chunk_text = text[search_start:end + 500]
                best_break = -1
                for sep in ['\n\n\n', '\n\n', '\n第', '。\n', '！\n', '？\n', '。', '！', '？']:
                    idx = chunk_text.rfind(sep)
                    if idx >= 0:
                        candidate = search_start + idx + len(sep)
                        if candidate > pos + self.CHUNK_SIZE // 2:
                            best_break = candidate
                            break
                if best_break > 0:
                    end = best_break
            chunk = text[pos:end].strip()
            if chunk:
                chunks.append(chunk)
            pos = max(end - self.CHUNK_OVERLAP, pos + 1)
        return chunks

    # ==================== 合并 ====================

    def _merge_extractions(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个分段的提取结果（按名称去重，合并属性，保留最详细版本，O(n) 合并）"""
        merged_world_info = {}
        seen_entity_names = {}  # key -> entity object
        merged_entities = []
        seen_event_idx = {}     # key -> index in merged_events (O(1) lookup)
        merged_events = []
        seen_item_names = {}    # key -> item object
        merged_items = []
        seen_calendar_names = set()
        merged_calendars = []
        merged_map_region = []
        merged_map_country = []
        merged_map_locations = []

        for result in results:
            wi = result.get("world_info") or {}
            if not merged_world_info.get("name") and wi.get("name"):
                merged_world_info = wi

            for ent in result.get("entities") or []:
                normalized_entity = self._normalize_entity(ent)
                name = str(normalized_entity.get("name", "")).strip()
                if not name:
                    continue
                identity_keys = self._entity_identity_keys(normalized_entity)
                matched_entity = next((seen_entity_names[key] for key in identity_keys if key in seen_entity_names), None)
                if matched_entity is None:
                    merged_entities.append(normalized_entity)
                    for key in identity_keys:
                        seen_entity_names[key] = normalized_entity
                    continue

                merged_entity = self._merge_entities(matched_entity, normalized_entity)
                merged_entities[merged_entities.index(matched_entity)] = merged_entity
                for key in self._entity_identity_keys(merged_entity):
                    seen_entity_names[key] = merged_entity

            for evt in result.get("events") or []:
                normalized_event = self._normalize_event(evt)
                name = str(normalized_event.get("name", "")).strip()
                if not name:
                    continue
                key = "|".join([
                    name.lower(),
                    str(normalized_event.get("date", "")).strip().lower(),
                    str(normalized_event.get("estimated_date", "")).strip().lower(),
                ])
                if key in seen_event_idx:
                    existing = merged_events[seen_event_idx[key]]
                    merged_events[seen_event_idx[key]] = self._merge_events(existing, normalized_event)
                else:
                    seen_event_idx[key] = len(merged_events)
                    merged_events.append(normalized_event)

            settings = result.get("settings") or {}
            for item in settings.get("items") or []:
                name = str(item.get("name", "")).strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen_item_names:
                    existing = seen_item_names[key]
                    nd = str(item.get("detailContent", ""))
                    od = str(existing.get("detailContent", ""))
                    if len(nd) > len(od):
                        existing["detailContent"] = nd
                else:
                    seen_item_names[key] = item
                    merged_items.append(item)

            for cal in settings.get("calendars") or []:
                name = str(cal.get("name", "")).strip().lower()
                if name and name not in seen_calendar_names:
                    seen_calendar_names.add(name)
                    merged_calendars.append(cal)

            map_data = settings.get("mapData") or {}
            for field, target in [
                ("regionRelations", merged_map_region),
                ("countryRelations", merged_map_country),
                ("importantLocations", merged_map_locations),
            ]:
                value = map_data.get(field)
                if isinstance(value, list):
                    for item in value:
                        s = str(item).strip()
                        if s and s not in target:
                            target.append(s)
                elif isinstance(value, str) and value.strip():
                    target.append(value.strip())

        return {
            "world_info": merged_world_info,
            "entities": merged_entities,
            "events": merged_events,
            "settings": {
                "items": merged_items,
                "mapData": {
                    "regionRelations": merged_map_region,
                    "countryRelations": merged_map_country,
                    "importantLocations": merged_map_locations,
                },
                "calendars": merged_calendars,
            },
        }

    # ==================== 验证 ====================

    VALID_ENTITY_TYPES = {"人物", "国家", "组织", "种族", "地点", "物品", "能力", "其他"}
    VALID_TIME_TYPES = {"past", "present", "future", "unknown"}

    def _validate_entity(self, entity: Dict[str, Any], idx: int) -> List[str]:
        """验证单个实体，返回错误列表"""
        errors = []
        name = str(entity.get("name", "")).strip()
        if not name:
            errors.append(f"实体#{idx}: name 缺失")
        etype = entity.get("type", "")
        if etype and etype not in self.VALID_ENTITY_TYPES:
            errors.append(f"实体'{name}': type='{etype}' 不在 {self.VALID_ENTITY_TYPES}")
        if not isinstance(entity.get("attributes"), dict):
            errors.append(f"实体'{name}': attributes 不是 dict")
        elif "简介" not in entity["attributes"]:
            errors.append(f"实体'{name}': attributes 缺少 '简介' 字段")
        if not isinstance(entity.get("aliases"), list):
            errors.append(f"实体'{name}': aliases 不是 list")
        if entity.get("stages") is not None and not isinstance(entity.get("stages"), list):
            errors.append(f"实体'{name}': stages 不是 list")
        if entity.get("relationships") is not None and not isinstance(entity.get("relationships"), list):
            errors.append(f"实体'{name}': relationships 不是 list")
        return errors

    def _validate_event(self, event: Dict[str, Any], idx: int) -> List[str]:
        """验证单个事件，返回错误列表"""
        errors = []
        name = str(event.get("name", "")).strip()
        if not name:
            errors.append(f"事件#{idx}: name 缺失")
        if not event.get("description", "").strip():
            errors.append(f"事件'{name}': description 为空")
        tt = event.get("time_type", "")
        if tt and tt not in self.VALID_TIME_TYPES:
            errors.append(f"事件'{name}': time_type='{tt}' 不在 {self.VALID_TIME_TYPES}")
        if not isinstance(event.get("entities"), list):
            errors.append(f"事件'{name}': entities 不是 list")
        return errors

    def _validate_chunk_result(self, result: Dict[str, Any], chunk_index: int) -> List[str]:
        """验证单个章节组的提取结果，返回错误列表"""
        all_errors = []
        entities = result.get("entities") or []
        for i, e in enumerate(entities):
            all_errors.extend(self._validate_entity(e, i))
        events = result.get("events") or []
        for i, e in enumerate(events):
            all_errors.extend(self._validate_event(e, i))
        if all_errors:
            logger.warning(f"章节组{chunk_index + 1}验证发现 {len(all_errors)} 个问题: {all_errors[:10]}...")
        return all_errors

    def _validate_consolidated(self, data: Dict[str, Any]) -> List[str]:
        """验证整合后的最终结果"""
        all_errors = []
        for i, e in enumerate(data.get("entities") or []):
            all_errors.extend(self._validate_entity(e, i))
        for i, e in enumerate(data.get("events") or []):
            all_errors.extend(self._validate_event(e, i))
        return all_errors

    # ==================== 最终整合 ====================

    CONSOLIDATE_BATCH = 24   # 每批整合的实体数，控制 prompt 大小
    CONSOLIDATE_EVENT_BATCH = 18
    MAX_RELATED_EVENTS_PER_ENTITY = 4
    CONSOLIDATE_WORKERS = 4
    CONSOLIDATE_MAX_TOKENS = 4096
    MAX_CONSOLIDATION_SUMMARY_CHARS = 45000
    USE_LLM_CONSOLIDATION = False

    def _merge_event_collection(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged_events: List[Dict[str, Any]] = []
        seen_event_idx: Dict[str, int] = {}
        for event in events or []:
            normalized_event = self._normalize_event(event)
            name = str(normalized_event.get("name", "")).strip()
            if not name:
                continue
            key = "|".join([
                name.lower(),
                str(normalized_event.get("date", "")).strip().lower(),
                str(normalized_event.get("estimated_date", "")).strip().lower(),
            ])
            if key in seen_event_idx:
                existing = merged_events[seen_event_idx[key]]
                merged_events[seen_event_idx[key]] = self._merge_events(existing, normalized_event)
            else:
                seen_event_idx[key] = len(merged_events)
                merged_events.append(normalized_event)
        return merged_events

    def _select_events_for_entities(self, entities: List[Dict[str, Any]], events: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        entity_keys = set()
        for entity in entities or []:
            entity_keys.update(self._entity_identity_keys(entity))

        if not entity_keys:
            return []

        selected = []
        seen = set()
        for event in events or []:
            normalized_event = self._normalize_event(event)
            if not normalized_event:
                continue
            participant_keys = {
                self._normalize_identity_key(name)
                for name in normalized_event.get("entities") or []
                if str(name or "").strip()
            }
            if not participant_keys.intersection(entity_keys):
                continue

            key = self._normalize_identity_key(normalized_event.get("name"))
            if key in seen:
                continue
            seen.add(key)
            selected.append(normalized_event)
            if len(selected) >= limit:
                break

        return selected

    def _summarize_entity_clues(self, attributes: Dict[str, Any], limit: int = 6) -> Dict[str, str]:
        clues: Dict[str, str] = {}
        for key, value in (attributes or {}).items():
            if key in {"简介", "实力变化", "性格变化", "关键转折", "关系网络概述"}:
                continue

            text = ""
            if isinstance(value, str):
                text = value.strip()
            elif isinstance(value, (int, float)):
                text = str(value)
            elif isinstance(value, list) and key in self.ALIAS_ATTRIBUTE_KEYS:
                text = " / ".join(self._to_string_list(value)[:6])

            if not text:
                continue

            clues[str(key)] = text[:160]
            if len(clues) >= limit:
                break

        return clues

    def _consolidate_results(self, merged: Dict[str, Any]) -> Dict[str, Any]:
        """最终 LLM 整合：合并同一人物的不同身份、修正时间线、丰富角色生平。超过批次上限时分批处理。"""
        entities = merged.get("entities", [])
        events = merged.get("events", [])
        if not entities and not events:
            return merged

        if not self.USE_LLM_CONSOLIDATION:
            logger.info(f"最终整合使用规则模式，跳过 LLM 合并: {len(entities)} 实体, {len(events)} 事件")
            return {
                **merged,
                "entities": [
                    normalized for entity in entities
                    for normalized in [self._normalize_entity(entity)]
                    if normalized
                ],
                "events": self._merge_event_collection(events),
                "settings": self._normalize_settings(merged.get("settings") or {}),
            }

        # 不超过一批的量直接整合
        if len(entities) <= self.CONSOLIDATE_BATCH and len(events) <= self.CONSOLIDATE_EVENT_BATCH:
            return self._consolidate_batch(merged, entities, events)

        # 超出上限：按实体批次整合，并为每批携带相关事件上下文
        logger.info(f"数据量大 ({len(entities)} 实体, {len(events)} 事件)，分批整合...")
        all_consolidated_entities = []
        consolidated_event_candidates: List[Dict[str, Any]] = []
        batch_specs = []

        for batch_start in range(0, len(entities), self.CONSOLIDATE_BATCH):
            batch_end = min(batch_start + self.CONSOLIDATE_BATCH, len(entities))
            batch_entities = entities[batch_start:batch_end]
            batch_events = self._select_events_for_entities(batch_entities, events, self.CONSOLIDATE_EVENT_BATCH)
            batch_merged = dict(merged)
            batch_merged["entities"] = batch_entities
            batch_merged["events"] = batch_events
            batch_specs.append((batch_start, batch_end, batch_merged, batch_entities, batch_events))

        if len(batch_specs) == 1:
            _, _, batch_merged, batch_entities, batch_events = batch_specs[0]
            result = self._consolidate_batch(batch_merged, batch_entities, batch_events)
            merged["entities"] = result.get("entities", [])
            merged["events"] = self._merge_event_collection(list(events) + list(result.get("events", [])))
            return merged

        max_workers = min(self.CONSOLIDATE_WORKERS, len(batch_specs))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._consolidate_batch, batch_merged, batch_entities, batch_events): (batch_start, batch_end, batch_merged)
                for batch_start, batch_end, batch_merged, batch_entities, batch_events in batch_specs
            }
            batch_results = {}
            for future in as_completed(futures):
                batch_start, batch_end, fallback_merged = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    self._record_error(f"整合批次 {batch_start // self.CONSOLIDATE_BATCH + 1}", e)
                    result = fallback_merged
                batch_results[batch_start] = result
                logger.info(
                    f"整合批次 {batch_start // self.CONSOLIDATE_BATCH + 1} 完成: {batch_end}/{len(entities)} 实体"
                )

        for batch_start, _, _, _, _ in sorted(batch_specs, key=lambda item: item[0]):
            result = batch_results.get(batch_start) or {}
            all_consolidated_entities.extend(result.get("entities", []))
            consolidated_event_candidates.extend(result.get("events", []))

        merged["entities"] = all_consolidated_entities
        merged["events"] = self._merge_event_collection(list(events) + consolidated_event_candidates)
        return merged

    def _consolidate_batch(self, merged: Dict[str, Any], entities: List, events: List) -> Dict[str, Any]:
        """整合一批实体和事件（单次 LLM 调用）"""
        # 压缩字段以控制 prompt 长度，但不丢失关键信息
        entity_payload = []
        for e in entities:
            attrs = e.get("attributes") or {}
            item = {
                "name": e.get("name"), "type": e.get("type"),
                "aliases": e.get("aliases", []),
                "relationships": e.get("relationships", [])[:8],
                "stages": e.get("stages", [])[:8],
                "简介": attrs.get("简介", "")[:280],
                "identity_clues": self._summarize_entity_clues(attrs),
                "related_events": [
                    {
                        "name": event.get("name"),
                        "time_type": event.get("time_type", "unknown"),
                        "estimated_date": event.get("estimated_date", "未知"),
                        "entities": (event.get("entities") or [])[:6],
                    }
                    for event in self._select_events_for_entities([e], events, self.MAX_RELATED_EVENTS_PER_ENTITY)
                ],
            }
            changes = attrs.get("实力变化")
            if changes:
                item["实力变化"] = changes[:10]
            changes = attrs.get("性格变化")
            if changes:
                item["性格变化"] = changes[:10]
            changes = attrs.get("关键转折")
            if changes:
                item["关键转折"] = changes[:10]
            entity_payload.append(item)

        event_payload = []
        for e in (events or []):
            event_payload.append({
                "name": e.get("name"),
                "description": (e.get("description", ""))[:80],
                "time_type": e.get("time_type", "unknown"),
                "estimated_date": e.get("estimated_date", "未知"),
                "date": e.get("date", ""),
                "entities": (e.get("entities") or [])[:6],
            })

        summary = {
            "world_info": merged.get("world_info", {}),
            "entities_count": len(entities),
            "events_count": len(events),
            "entities": entity_payload,
            "events": event_payload,
        }

        summary_json = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
        if len(summary_json) > self.MAX_CONSOLIDATION_SUMMARY_CHARS:
            logger.warning(
                f"整合批次跳过 LLM: payload 过大 ({len(summary_json)} 字符, {len(entities)} 实体, {len(events)} 事件)"
            )
            return merged

        logger.info(
            f"整合批次准备: {len(entities)} 实体, {len(events)} 事件, payload {len(summary_json)} 字符"
        )

        prompt = load_prompt("consolidation", entity_count=len(entities), event_count=len(events), summary_json=summary_json)


        try:
            result = self._get_client().chat_json(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.CONSOLIDATE_MAX_TOKENS,
            )
            if isinstance(result, dict):
                if result.get("entities"):
                    merged["entities"] = [
                        normalized for entity in result["entities"]
                        for normalized in [self._normalize_entity(entity)]
                        if normalized
                    ]
                if result.get("events"):
                    merged["events"] = [
                        normalized for event in result["events"]
                        for normalized in [self._normalize_event(event)]
                        if normalized
                    ]
                logger.info(f"整合批次完成: {len(result.get('entities', []))} 实体, {len(result.get('events', []))} 事件")
        except Exception as e:
            self._record_error("整合批次", e)
            logger.warning(f"整合批次失败，保留原始数据: {e}")

        return merged

    # ==================== 文风 & 验证 ====================

    def extract_writing_style(self, text: str) -> Dict[str, str]:
        """从文本中分析提取文风特征"""
        try:
            sample = text[:3000]
            if len(text) > 3000:
                sample += "\n...(文本过长，此处为开头片段)"
            prompt = load_prompt("writing_style", sample=sample)
            result = self._get_client().chat_json(messages=[{"role": "user", "content": prompt}])
            if not isinstance(result, dict):
                raise ValueError("文风提取返回格式无效")
            return {
                "writing_style": str(result.get("writing_style", "") or "").strip(),
                "reference_text": text[:2000],
            }
        except Exception as e:
            self._record_error("提取文风特征", e)
            return {"writing_style": "", "reference_text": text[:2000] if text else ""}

    def validate_extraction(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证提取数据质量"""
        try:
            summary = {
                "entities_count": len(extracted_data.get("entities", [])),
                "events_count": len(extracted_data.get("events", [])),
                "settings_items_count": len((extracted_data.get("settings") or {}).get("items", [])),
                "sample_entities": (extracted_data.get("entities") or [])[:30],
                "sample_events": (extracted_data.get("events") or [])[:20],
            }
            prompt = load_prompt("validation", summary=json.dumps(summary, ensure_ascii=False, indent=2))
            result = self._get_client().chat_json(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            if isinstance(result, dict) and result.get("supplement"):
                s = result["supplement"]
                if s.get("entities"):
                    extracted_data.setdefault("entities", []).extend(s["entities"])
                if s.get("events"):
                    extracted_data.setdefault("events", []).extend(s["events"])
            return extracted_data
        except Exception as e:
            self._record_error("验证提取数据", e)
            return extracted_data
