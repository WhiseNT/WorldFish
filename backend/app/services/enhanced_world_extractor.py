"""
世界观提取服务
严格按照项目中已建立的世界观体系进行内容提取
支持并行 AI 调用，细粒度提取，确保不遗漏内容
章节感知切分，全文处理无遗漏
"""

from app.config import Config
from app.utils.llm_client import LLMClient
from app.utils.logger import get_logger
from app.prompts import load_prompt
from app.services.world_templates import (
    build_extraction_system_prompt,
    build_world_template_prompt_context,
    get_world_template,
    resolve_world_template_id,
)
import copy
from datetime import datetime
import hashlib
import json
import os
import re
import threading
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

logger = get_logger('worldfish.service.enhanced_world_extractor')

# 每线程独立的 LLMClient，避免共享阻塞
_thread_local = threading.local()
_cache_file_locks: Dict[str, threading.Lock] = {}
_cache_file_locks_guard = threading.Lock()


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

    FRAGMENT_ENTITY_KEYS = {
        "的", "地", "得", "了", "着", "过", "和", "与", "及", "或", "在", "从", "向", "把", "被", "对", "为", "以", "于",
        "心地", "冷酷", "残酷", "尊敬", "尊敬的", "可敬", "可敬的", "敌人", "敌人的", "人类", "人类是", "人类应该",
        "这", "那", "这个", "那个", "一种", "某种", "东西", "事情", "方面", "时候", "地方", "问题",
    }
    FRAGMENT_NAME_PATTERNS = (
        r"^[的地得了着过和与及或在从向把被对于以之其]$",
        r"^[，。！？、；：,.!?;:'\"“”‘’（）()\[\]{}<>《》\s]+$",
        r"^[一二三四五六七八九十百千万\d]+$",
        r".*[。！？；;]$",
        r"^(说|说道|写道|认为|觉得|表示|指出|开始|继续|突然|然后)$",
    )

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
    OUTER_WORKERS = 6        # 并行 LLM 调用数；过高容易触发中转站连接/编码异常
    CHUNK_RETRY_TIMES = 3

    # 章节标记正则
    CHAPTER_TITLE_SUFFIX = r'(?:\s*[：:、.．\-—]\s*[^\n]{0,80}|\s+[^\n]{1,80})?'
    CHAPTER_RE = (
        r'(?:^|\n)\s*'
        r'(?:#{1,6}\s*)?'
        r'(?:'
        r'(?:第\s*[零〇一二三四五六七八九十百千万\d]+\s*[部卷章节篇集]' + CHAPTER_TITLE_SUFFIX + r')'
        r'|(?:[零〇一二三四五六七八九十百千万\d]+\s*[部卷章节篇集]' + CHAPTER_TITLE_SUFFIX + r')'
        r'|(?:卷\s*[零〇一二三四五六七八九十百千万\d]+' + CHAPTER_TITLE_SUFFIX + r')'
        r'|(?:Chapter\s+\d+' + CHAPTER_TITLE_SUFFIX + r')'
        r'|(?:Part\s+\d+' + CHAPTER_TITLE_SUFFIX + r')'
        r'|(?:VOLUME\s*\d+' + CHAPTER_TITLE_SUFFIX + r')'
        r'|(?:三体\s*[ⅠⅡⅢIVXivx123一二三]+' + CHAPTER_TITLE_SUFFIX + r')'
        r'|(?:(?:序章|楔子|引子|尾声|终章|后记)' + CHAPTER_TITLE_SUFFIX + r')'
        r')\s*(?=\n|$)'
    )

    def __init__(self, template_id: Optional[str] = None):
        self.errors: List[str] = []
        self.template_id = resolve_world_template_id(template_id)
        self.template = get_world_template(self.template_id)
        self.template_name = str(self.template.get("name") or "通用模板").strip() or "通用模板"
        self.template_setting_collections = [
            collection for collection in (self.template.get("setting_collections") or [])
            if isinstance(collection, dict)
        ]
        self.template_collection_by_category = {
            str(collection.get("category") or "").strip(): collection
            for collection in self.template_setting_collections
            if str(collection.get("category") or "").strip()
        }
        self.template_prompt_context = build_world_template_prompt_context(self.template_id)
        self._extraction_system_prompt = build_extraction_system_prompt(self.template_id)

    def _template_collection_id_for_category(self, category: str) -> str:
        collection = self.template_collection_by_category.get(category)
        return str(collection.get("id") or "").strip() if collection else ""

    def _template_collection_items(self) -> List[Dict[str, Any]]:
        items = []
        for collection in self.template_setting_collections:
            collection_id = str(collection.get("id") or "").strip()
            name = str(collection.get("name") or "").strip()
            category = self._normalize_setting_category(collection.get("category"))
            if not collection_id or not name:
                continue
            description = str(collection.get("description") or name).strip()
            items.append({
                "id": collection_id,
                "name": name,
                "settingType": "collection",
                "category": category,
                "description": description,
                "detailContent": description,
                "sourceType": "world_template",
                "autoGenerated": True,
            })
        return items

    @staticmethod
    def _get_client():
        """每线程独立 LLMClient，8 线程x独立连接池 = 8 倍并发"""
        if not hasattr(_thread_local, 'client'):
            _thread_local.client = LLMClient(role="parser")
        return _thread_local.client

    def _format_error_message(self, error: Exception) -> str:
        message = str(error).strip()
        if isinstance(error, UnicodeDecodeError):
            return (
                f"响应编码解码失败：尝试用 {error.encoding or '未知编码'} 解码时，"
                f"在字节位置 {error.start} 遇到非法字节 0x{error.object[error.start]:02x}。"
                "通常是模型中转站返回了非 UTF-8/压缩异常响应，请稍后重试或降低并发。"
            )
        return message

    def _record_error(self, stage: str, error: Exception):
        message = self._format_error_message(error)
        logger.error(f"{stage}失败: {message}")
        self.errors.append(f"{stage}: {message}")

    @classmethod
    def get_text_volume_profile(cls, text_len: int) -> Dict[str, Any]:
        """根据解析模型上下文窗口生成统一大块切分策略。"""
        text_len = max(0, int(text_len or 0))
        max_workers = max(1, int(getattr(Config, "EXTRACTION_MAX_WORKERS", cls.OUTER_WORKERS)))
        context_window = int(getattr(Config, "LLM_DEFAULT_CONTEXT_WINDOW", 128 * 1024) or 128 * 1024)
        parser_model = ""
        try:
            client = LLMClient(role="parser")
            context_window = max(8192, int(getattr(client, "context_window", context_window) or context_window))
            parser_model = getattr(client, "model", "") or ""
        except Exception:
            llm_config = Config.get_llm_config("parser")
            parser_model = llm_config.get("model_name", "") or ""
            if getattr(Config, "LLM_CONTEXT_WINDOW", 0) > 0:
                context_window = int(Config.LLM_CONTEXT_WINDOW)

        tokenizer_estimate = max(0.1, float(getattr(Config, "EXTRACTION_TOKENIZER_ESTIMATE", 1.2)))
        target_ratio = max(0.05, float(getattr(Config, "EXTRACTION_TARGET_CONTEXT_RATIO", 0.45)))
        output_reserve_ratio = max(0.0, float(getattr(Config, "EXTRACTION_OUTPUT_RESERVE_RATIO", 0.18)))
        # 深度/快速提取都应尽量吃满模型上下文，而不是按 RAG 小块策略切成大量碎片。
        usable_tokens = max(2048, int(context_window * max(0.08, target_ratio - output_reserve_ratio)))
        target_chunk_chars = int(usable_tokens / tokenizer_estimate)
        dynamic_min_chars = 60_000 if context_window >= 128_000 else int(getattr(Config, "EXTRACTION_MIN_CHUNK_CHARS", 8000))
        dynamic_max_chars = max(int(getattr(Config, "EXTRACTION_MAX_CHUNK_CHARS", 220000)), 180_000 if context_window >= 128_000 else 80_000)
        target_chunk_chars = max(dynamic_min_chars, min(dynamic_max_chars, target_chunk_chars))
        chunk_overlap = max(500, min(4000, int(target_chunk_chars * 0.01)))

        profile_name = "short" if text_len <= target_chunk_chars else "novel"
        if text_len > target_chunk_chars * 8:
            profile_name = "huge"
        if text_len > target_chunk_chars * 20:
            profile_name = "massive"

        profile = {
            "profile": profile_name,
            "chunk_size": target_chunk_chars,
            "chunk_overlap": chunk_overlap,
            "chapter_chunk_char_budget": target_chunk_chars,
            "chapters_per_chunk": 9999,
            "outer_workers": max_workers,
            "rag_chunk_size": max(Config.RAG_HUGE_CHUNK_SIZE, 1800),
            "rag_chunk_overlap": 180,
            "rag_chunk_preset": "novel",
            "rag_profile": "novel",
            "text_length": text_len,
            "context_window": context_window,
            "target_chunk_chars": target_chunk_chars,
            "parser_model": parser_model,
            "chunk_profile_version": int(getattr(Config, "EXTRACTION_CHUNK_PROFILE_VERSION", 3)),
        }
        profile["outer_workers"] = max(1, min(int(profile["outer_workers"]), max_workers))
        return profile

    @staticmethod
    def _safe_text(value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        text = str(value or '')
        return text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')

    def _is_high_confidence_noise_line(self, line: str) -> bool:
        stripped = str(line or '').strip()
        if not stripped:
            return False
        normalized = stripped.lower()
        if re.fullmatch(r'[=\-_*#~·•—─]{4,}', stripped):
            return True
        if normalized in {'目录', '目录：', 'contents', 'table of contents'}:
            return True
        if re.match(r'^\s*(?:第\s*[零〇一二三四五六七八九十百千万\d]+\s*[章节卷部篇回]|chapter\s*\d+|part\s*\d+).{0,80}(?:\.{2,}|…{2,}|\s{2,})\d+\s*$', stripped, re.IGNORECASE):
            return True

        high_confidence_noise = (
            '版权所有', '版权归', '侵权必究', '免责声明', '未经授权', '仅供学习交流', '严禁用于商业用途',
            '请于下载后', '免费电子书', '广告合作', '扫码', '公众号', '微信读书', '本书来自', '最新章节请访问',
            'app下载', '下载地址', '支持正版', '手机访问', '书友群',
        )
        if len(stripped) <= 180 and any(token in stripped for token in high_confidence_noise):
            return True
        if re.search(r'(https?://|www\.)\S+', stripped) and any(token in stripped for token in ('下载', '阅读', '版权', '公众号')):
            return True
        return False

    def _preclean_extraction_text(self, text: str) -> str:
        raw_text = self._safe_text(text)
        if not raw_text:
            return ''

        normalized = raw_text.replace('\r\n', '\n').replace('\r', '\n')
        cleaned_lines: List[str] = []
        removed_noise = 0

        for raw_line in normalized.split('\n'):
            line = raw_line.rstrip()
            stripped = line.strip()
            if self._is_high_confidence_noise_line(stripped):
                removed_noise += 1
                continue
            if not stripped:
                if cleaned_lines and cleaned_lines[-1] == '':
                    continue
                cleaned_lines.append('')
                continue
            cleaned_lines.append(stripped)

        cleaned_text = re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned_lines).strip())
        if removed_noise:
            logger.info(f'预清理移除 {removed_noise} 行高置信噪声')
        return cleaned_text or normalized.strip()

    @staticmethod
    def _empty_style_payload() -> Dict[str, str]:
        return {'writing_style': '', 'reference_text': ''}

    @staticmethod
    def _truncate_preserving_boundaries(text: Any, max_chars: int) -> str:
        normalized = str(text or '').strip()
        max_chars = int(max_chars or 0)
        if max_chars <= 0 or len(normalized) <= max_chars:
            return normalized

        search_start = max(1, int(max_chars * 0.7))
        boundary = -1
        for marker in ('\n\n', '\n', '。', '！', '？', '；'):
            marker_index = normalized.rfind(marker, search_start, max_chars + 1)
            if marker_index >= 0:
                marker_end = marker_index if marker.startswith('\n') else marker_index + len(marker)
                boundary = max(boundary, marker_end)
        if boundary <= 0:
            boundary = max_chars
        return normalized[:boundary].rstrip() + '……'

    def _limit_entity_intro(self, entity: Dict[str, Any]) -> None:
        if not isinstance(entity, dict):
            return
        if str(entity.get('type') or '').strip() != '人物':
            return
        attributes = entity.get('attributes') if isinstance(entity.get('attributes'), dict) else None
        if not attributes:
            return
        intro = str(attributes.get('简介') or '').strip()
        if not intro:
            return
        max_chars = int(getattr(Config, 'EXTRACTION_ENTITY_INTRO_MAX_CHARS', 1200) or 1200)
        attributes['简介'] = self._truncate_preserving_boundaries(intro, max_chars)

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

    def _is_fragment_entity_name(self, name: Any, entity_type: Any = "", attributes: Optional[Dict[str, Any]] = None) -> bool:
        """过滤 LLM 把语气词、单字、形容词、引语残片误当实体的情况。"""
        text = str(name or "").strip()
        key = self._normalize_identity_key(text)
        etype = str(entity_type or "").strip()
        attributes = attributes or {}
        if not key:
            return True
        if key in self.FRAGMENT_ENTITY_KEYS:
            return True
        if any(re.match(pattern, text) for pattern in self.FRAGMENT_NAME_PATTERNS):
            return True
        if len(key) == 1 and etype in {"", "其他", "地点", "人物", "物品", "能力"}:
            return True

        intro = str(attributes.get("简介") or attributes.get("description") or "").strip()
        if len(key) <= 2 and intro:
            # 典型坏例：name=地 / 心地，简介=地说：'人类应该...'。这种不是实体，而是句子碎片。
            if re.search(r"[说道认为表示指出]\s*[：:]|[，。！？；]", intro) and etype in {"", "其他", "地点"}:
                return True
        return False

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
        entity_type = str(entity.get("type") or "其他").strip() or "其他"
        if self._is_fragment_entity_name(name, entity_type, attributes):
            logger.debug(f"过滤疑似碎片实体: {name} ({entity_type})")
            return {}
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
            "type": entity_type,
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
            if not key or self._is_generic_identity_value(name) or self._is_fragment_entity_name(name, inferred_type or "其他"):
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
        for entity in finalized.get("entities") or []:
            self._limit_entity_intro(entity)
        finalized["writing_style"] = str(data.get("writing_style") or "").strip()
        finalized["reference_text"] = str(data.get("reference_text") or "")
        finalized["template_id"] = self.template_id
        finalized["template_name"] = self.template_name
        if isinstance(data.get("extraction_diagnostics"), dict):
            finalized["extraction_diagnostics"] = data["extraction_diagnostics"]
        return finalized

    def _normalize_setting_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        name = str(item.get("name") or item.get("title") or item.get("label") or "").strip()
        desc = str(item.get("description") or item.get("summary") or item.get("content") or "").strip()
        detail = str(item.get("detailContent") or item.get("detail") or desc).strip()
        category = self._normalize_setting_category(item.get("category") or item.get("type"))
        setting_type = str(item.get("settingType") or item.get("setting_type") or "setting").strip()
        setting_type = "collection" if setting_type == "collection" else "setting"
        structured_detail = item.get("structuredDetail") or item.get("structured_detail")
        if not isinstance(structured_detail, dict):
            structured_detail = {}
        has_structured_detail = any(
            bool(value) for value in structured_detail.values()
        )
        collection_id = str(
            item.get("collectionId")
            or item.get("collection_id")
            or item.get("parentCollection")
            or ""
        ).strip()
        if setting_type == "setting" and not collection_id:
            collection_id = self._template_collection_id_for_category(category)
        pseudo_type = self._setting_category_to_entity_type(category)
        if not name:
            return {}
        if setting_type == "setting":
            if not (desc or detail or has_structured_detail):
                return {}
            if self._is_fragment_entity_name(name, pseudo_type, {"简介": desc or detail}):
                return {}

        normalized = {
            "name": name,
            "settingType": setting_type,
            "category": category,
            "description": desc or detail,
            "aliases": self._to_string_list(item.get("aliases") or item.get("alias")),
            "detailContent": detail or desc,
        }
        item_id = str(item.get("id") or "").strip()
        if item_id:
            normalized["id"] = item_id
        if setting_type == "setting" and collection_id:
            normalized["collectionId"] = collection_id
        if structured_detail:
            normalized["structuredDetail"] = copy.deepcopy(structured_detail)
        source_type = str(item.get("sourceType") or item.get("source_type") or "").strip()
        if source_type:
            normalized["sourceType"] = source_type
        if "autoGenerated" in item or "auto_generated" in item:
            normalized["autoGenerated"] = bool(item.get("autoGenerated", item.get("auto_generated")))
        return normalized

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
        normalized_items = [
            ni for item in raw_items if isinstance(item, dict) for ni in [self._normalize_setting_item(item)] if ni
        ]
        collection_items = self._template_collection_items()
        merged_items_by_key: Dict[str, Dict[str, Any]] = {}
        for item in [*collection_items, *normalized_items]:
            item_id = str(item.get("id") or "").strip()
            key = item_id or "|".join([
                str(item.get("settingType") or "").strip(),
                str(item.get("category") or "").strip(),
                str(item.get("name") or "").strip().lower(),
            ])
            if key and key not in merged_items_by_key:
                merged_items_by_key[key] = item
        normalized["items"] = list(merged_items_by_key.values())
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

    def _extract_from_chunk(self, chunk: str, chunk_index: int = 0, context_prefix: str = "") -> Dict[str, Any]:
        """单次 LLM 调用穷举提取一个文本块的所有世界观数据"""
        context_text = ("这是整个文本的开头部分（含多章），世界观基础设定通常在此。"
                        if chunk_index == 0
                        else f"这是文本的第{chunk_index + 1}个章节组（含多章）。请提取本段中出现的所有信息。")
        if context_prefix:
            context_text = f"{context_text}\n\n{context_prefix}"
        context_text = f"{context_text}\n\n重要要求：本次为{'深度连续扫描' if context_prefix else '全量扫描'}，必须穷举当前文本块中的人物、组织/国家/种族、地点、物品/能力、事件、关系与设定条目；不要因为已有摘要中出现过就跳过当前块中的新证据、新别名、新关系或新阶段。"
        safe_chunk = self._safe_text(chunk)
        prompt = load_prompt(
            "extraction_chunk",
            context=context_text,
            chunk=safe_chunk,
            template_name=self.template_name,
            template_chunk_hint=self.template_prompt_context.get("template_chunk_hint", ""),
        )


        last_error = None
        for attempt in range(1, self.CHUNK_RETRY_TIMES + 1):
            try:
                result = self._get_client().chat_json(
                    messages=[
                        {"role": "system", "content": self._extraction_system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=32768,
                )
                break
            except UnicodeDecodeError as exc:
                last_error = exc
                if hasattr(_thread_local, 'client'):
                    delattr(_thread_local, 'client')
                logger.warning(
                    f"章节组{chunk_index + 1}响应解码失败，第 {attempt}/{self.CHUNK_RETRY_TIMES} 次：{self._format_error_message(exc)}"
                )
                if attempt < self.CHUNK_RETRY_TIMES:
                    time.sleep(0.8 * attempt)
                    continue
                raise
            except Exception as exc:
                last_error = exc
                if attempt < self.CHUNK_RETRY_TIMES and any(keyword in str(exc).lower() for keyword in ['connection', 'timeout', 'temporarily', 'rate limit', '502', '503', '504']):
                    if hasattr(_thread_local, 'client'):
                        delattr(_thread_local, 'client')
                    logger.warning(f"章节组{chunk_index + 1}请求失败，第 {attempt}/{self.CHUNK_RETRY_TIMES} 次：{exc}")
                    time.sleep(0.8 * attempt)
                    continue
                raise
        else:
            raise last_error or RuntimeError(f"章节组{chunk_index + 1}提取失败")

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
            "world_info": world_info if isinstance(world_info, dict) else {},
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

    def _source_hash(self, text: str) -> str:
        return hashlib.sha256(self._safe_text(text).encode("utf-8", errors="replace")).hexdigest()

    def build_cache_key(self, text: str, extraction_mode: str, volume_profile: Optional[Dict[str, Any]] = None) -> str:
        volume_profile = volume_profile or self.get_text_volume_profile(len(text or ""))
        raw = "|".join([
            self._source_hash(text),
            str(extraction_mode or "fast"),
            self.template_id,
            str(volume_profile.get("parser_model") or ""),
            str(volume_profile.get("context_window") or ""),
            str(volume_profile.get("chunk_profile_version") or ""),
        ])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cache_dir(self) -> str:
        path = os.path.join(Config.UPLOAD_FOLDER, getattr(Config, "EXTRACTION_CHECKPOINT_DIR", "extraction_cache"))
        os.makedirs(path, exist_ok=True)
        return path

    def _cache_path(self, cache_key: str) -> str:
        safe_key = re.sub(r"[^a-fA-F0-9_-]", "", cache_key)[:96]
        return os.path.join(self._cache_dir(), f"{safe_key}.json")

    def _cache_file_lock(self, cache_key: str) -> threading.Lock:
        key = re.sub(r"[^a-fA-F0-9_-]", "", str(cache_key or ""))[:96] or "default"
        with _cache_file_locks_guard:
            lock = _cache_file_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                _cache_file_locks[key] = lock
            return lock

    def _load_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        path = self._cache_path(cache_key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            logger.warning(f"读取提取缓存失败 [{cache_key}]: {exc}")
            return None

    def _save_cache(self, cache: Dict[str, Any]) -> None:
        cache_key = cache.get("cache_key") or ""
        cache["updated_at"] = datetime.now().isoformat()
        payload = copy.deepcopy(cache)
        path = self._cache_path(cache_key)
        lock = self._cache_file_lock(cache_key)
        with lock:
            tmp_path = f"{path}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
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

    def _build_chunk_records(self, text: str, chunks: List[Any]) -> List[Dict[str, Any]]:
        records = []
        cursor = 0
        total = len(chunks)
        text_len = len(text or "")
        for index, item in enumerate(chunks):
            if isinstance(item, dict):
                chunk_text = item.get("text") or ""
                start, end = item.get("char_range") or (None, None)
                if start is None:
                    start = cursor
                if end is None:
                    end = start + len(chunk_text)
                titles = item.get("chapter_titles") or []
            else:
                chunk_text = str(item or "")
                found = text.find(chunk_text[: min(len(chunk_text), 200)], cursor)
                start = found if found >= 0 else cursor
                end = start + len(chunk_text)
                titles = [m.group().strip() for m in re.finditer(self.CHAPTER_RE, chunk_text, re.MULTILINE | re.IGNORECASE)][:8]
            start = max(0, min(int(start or 0), text_len))
            end = max(start, min(int(end or start + len(chunk_text)), text_len))
            cursor = max(end, cursor)
            records.append({
                "index": index,
                "char_range": [start, end],
                "chapter_titles": titles,
                "status": "pending",
                "attempts": 0,
                "error": "",
                "result": {},
                "text": chunk_text,
                "chunk_count": total,
            })
        return records

    def _new_cache(self, cache_key: str, source_hash: str, mode: str, volume_profile: Dict[str, Any], chunks: List[Any]) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        return {
            "cache_key": cache_key,
            "source_hash": source_hash,
            "mode": mode,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "status": "running",
            "created_at": now,
            "updated_at": now,
            "parser_model": volume_profile.get("parser_model"),
            "context_window": volume_profile.get("context_window"),
            "profile": volume_profile,
            "chunks": self._build_chunk_records(getattr(self, "_current_source_text", ""), chunks),
            "partial_results": [],
            "diagnostics": {"merge_conflicts": [], "failed_chunks": [], "duplicate_candidates": [], "overlap_aligned_entities": []},
            "final_result": None,
            "rolling_summary": "",
            "confirmed_entities": [],
            "last_completed_chunk": -1,
            "snapshot_stats": {},
        }

    def extract_from_text(self, text: str, progress_callback=None, extraction_mode: str = None, force_rebuild: bool = False, should_cancel=None, should_pause=None) -> Dict[str, Any]:
        """从文本提取世界观信息（统一大块切分 + Fast/Deep 缓存续传）。"""
        text = self._preclean_extraction_text(text)
        mode = str(extraction_mode or getattr(Config, "EXTRACTION_DEFAULT_MODE", "fast") or "fast").lower()
        if mode not in {"fast", "deep"}:
            mode = "fast"
        text_len = len(text) if text else 0
        volume_profile = self.get_text_volume_profile(text_len)
        logger.info(
            f"文本 {text_len} 字符 -> {mode}/{volume_profile['profile']} 策略 "
            f"(target={volume_profile['target_chunk_chars']}, context={volume_profile['context_window']}, workers={volume_profile['outer_workers']})"
        )
        if text_len <= self.LONG_TEXT_THRESHOLD:
            result = self._extract_short_text(text, progress_callback)
            result.setdefault("extraction_diagnostics", {})["volume_profile"] = volume_profile
            result["cache_key"] = self.build_cache_key(text, mode, volume_profile)
            result["cache_status"] = "skipped_short_text"
            result["resumed_from_cache"] = False
            return result
        return self._extract_chapters(text, progress_callback, volume_profile=volume_profile, extraction_mode=mode, force_rebuild=force_rebuild, should_cancel=should_cancel, should_pause=should_pause)

    def _extract_short_text(self, text: str, progress_callback=None) -> Dict[str, Any]:
        """短文本提取：仅执行结构化提取，暂停文风分析。"""
        self.errors = []
        try:
            if progress_callback:
                progress_callback('extracting', 10, '正在提取世界观信息...')

            result = self._extract_from_chunk(text, chunk_index=0)
            if result is None:
                raise ValueError('世界观提取失败，请检查 LLM 配置。')

            if progress_callback:
                progress_callback('finalizing', 85, '正在整理结果...')

            extracted_data = {
                "world_info": result["world_info"],
                "entities": result["entities"],
                "events": result["events"],
                "settings": self._normalize_settings(result.get("settings") or {}),
                "writing_style": "",
                "reference_text": "",
            }

            if progress_callback:
                progress_callback(
                    'consolidating',
                    90,
                    '正在执行规则整合，保留全部已提取实体与事件...' if not self.USE_LLM_CONSOLIDATION else '正在整合修正所有提取结果...'
                )
            extracted_data = self._consolidate_results(extracted_data)
            extracted_data = self._finalize_extraction(extracted_data)
            if progress_callback:
                progress_callback('validating', 94, '正在质量验证并补充明显遗漏...')
            extracted_data = self.validate_extraction(extracted_data)
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

    def _extract_chapters(
        self,
        text: str,
        progress_callback=None,
        volume_profile: Optional[Dict[str, Any]] = None,
        extraction_mode: str = "fast",
        force_rebuild: bool = False,
        should_cancel=None,
        should_pause=None,
    ) -> Dict[str, Any]:
        """统一大块提取：Fast 并行 / Deep 线性，共用缓存结构。"""
        self.errors = []
        self._current_source_text = text
        mode = extraction_mode if extraction_mode in {"fast", "deep"} else "fast"
        volume_profile = volume_profile or self.get_text_volume_profile(len(text or ""))
        chunks = self._chapter_aware_split(text, volume_profile=volume_profile)
        source_hash = self._source_hash(text)
        cache_key = self.build_cache_key(text, mode, volume_profile)
        cache = None if force_rebuild else self._load_cache(cache_key)
        resumed_from_cache = bool(cache and cache.get("chunks"))
        if not cache:
            cache = self._new_cache(cache_key, source_hash, mode, volume_profile, chunks)
            self._save_cache(cache)

        chunk_records = cache.get("chunks") or []
        for record in chunk_records:
            if record.get("status") in {"running", "failed"}:
                record["status"] = "pending"
        all_results = [record.get("result") if record.get("status") == "completed" else None for record in chunk_records]
        completed_initial = sum(1 for item in all_results if item)
        logger.info(f"提取切分: {len(text)} 字符 -> {len(chunk_records)} 个大块，mode={mode}, cache={cache_key[:12]}, resumed={resumed_from_cache}")

        if progress_callback:
            progress_callback('extracting', 2,
                f'{mode.upper()} 扫描 {len(chunk_records)} 个大块，已缓存 {completed_initial}/{len(chunk_records)} 块...',
                self._progress_detail(cache, volume_profile, resumed_from_cache))

        if cache.get("status") == "completed" and cache.get("final_result") and not force_rebuild:
            final = cache["final_result"]
            final.update(self._cache_result_fields(cache, volume_profile, resumed_from_cache))
            return final

        def process_record(record: Dict[str, Any], context_prefix: str = "") -> Tuple[int, Optional[Dict[str, Any]], str]:
            idx = int(record.get("index") or 0)
            chunk = record.get("text") or ""
            record["status"] = "running"
            record["attempts"] = int(record.get("attempts") or 0) + 1
            self._save_cache(cache)
            try:
                result = self._extract_from_chunk(chunk, chunk_index=idx, context_prefix=context_prefix)
                if self._has_meaningful_content(result):
                    return idx, result, ""
                return idx, None, "块结果为空"
            except Exception as e:
                self._record_error(f"大块{idx + 1}", e)
                retry_chunks = self._fallback_split(chunk, chunk_size=max(self.CHUNK_SIZE, int(volume_profile.get("chunk_size", self.CHUNK_SIZE) // 2)), overlap=self.CHUNK_OVERLAP) if len(chunk) > self.CHUNK_SIZE else []
                if len(retry_chunks) > 1:
                    sub_results = []
                    for sub_idx, sub_chunk in enumerate(retry_chunks):
                        try:
                            sub_result = self._extract_from_chunk(sub_chunk, chunk_index=idx, context_prefix=context_prefix)
                            if self._has_meaningful_content(sub_result):
                                sub_results.append(sub_result)
                        except Exception as sub_error:
                            self._record_error(f"大块{idx + 1}子段{sub_idx + 1}", sub_error)
                    if sub_results:
                        return idx, self._merge_extractions(sub_results), ""
                return idx, None, self._format_error_message(e)

        pending_records = [record for record in chunk_records if record.get("status") != "completed"]
        completed_count = completed_initial

        with ThreadPoolExecutor(max_workers=(1 if mode == "deep" else min(int(volume_profile.get("outer_workers") or self.OUTER_WORKERS), max(1, len(pending_records))))) as executor:
            if mode == "deep":
                for record in pending_records:
                    if should_cancel and should_cancel():
                        cache["status"] = "cancelled"
                        self._save_cache(cache)
                        break
                    if should_pause and should_pause():
                        cache["status"] = "paused"
                        self._save_cache(cache)
                        break
                    snapshot, snapshot_stats = self._build_entity_snapshot(cache)
                    context_prefix = self._build_deep_context(cache.get("rolling_summary") or "", snapshot)
                    cache["current_chunk_index"] = int(record.get("index") or 0)
                    cache["current_chunk_started_at"] = datetime.now().isoformat()
                    cache["current_chunk_title"] = self._current_chunk_title(record)
                    cache["current_chunk_char_range"] = record.get("char_range") or [0, 0]
                    cache["current_chunk_text_length"] = len(record.get("text") or "")
                    self._save_cache(cache)
                    if progress_callback:
                        progress_callback('extracting', 3 + int(completed_count / max(len(chunk_records), 1) * 85),
                            f'DEEP 正在阅读 {cache["current_chunk_title"]}...',
                            self._progress_detail(cache, volume_profile, resumed_from_cache))
                    idx, result, error = process_record(record, context_prefix=context_prefix)
                    self._checkpoint_chunk(cache, idx, result, error, deep_mode=True, snapshot_stats=snapshot_stats)
                    all_results[idx] = result if result else None
                    completed_count = sum(1 for item in all_results if item)
                    if progress_callback:
                        progress_callback('extracting', 3 + int(completed_count / max(len(chunk_records), 1) * 85),
                            f'DEEP 大块 {completed_count}/{len(chunk_records)} 完成...',
                            self._progress_detail(cache, volume_profile, resumed_from_cache))
            else:
                max_fast_workers = min(int(volume_profile.get("outer_workers") or self.OUTER_WORKERS), max(1, len(pending_records)))
                record_iter = iter(pending_records)
                futures = {}
                stop_requested = False

                def submit_next_records():
                    while not stop_requested and len(futures) < max_fast_workers:
                        if should_cancel and should_cancel():
                            cache["status"] = "cancelled"
                            self._save_cache(cache)
                            return
                        if should_pause and should_pause():
                            cache["status"] = "paused"
                            self._save_cache(cache)
                            return
                        try:
                            next_record = next(record_iter)
                        except StopIteration:
                            return
                        futures[executor.submit(process_record, next_record)] = int(next_record.get("index") or 0)

                submit_next_records()
                while futures:
                    done_futures, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                    for future in done_futures:
                        futures.pop(future, None)
                        idx, result, error = future.result()
                        self._checkpoint_chunk(cache, idx, result, error)
                        all_results[idx] = result if result else None
                        completed_count = sum(1 for item in all_results if item)
                        if progress_callback:
                            progress_callback('extracting', 3 + int(completed_count / max(len(chunk_records), 1) * 85),
                                f'FAST 大块 {completed_count}/{len(chunk_records)} 完成...',
                                self._progress_detail(cache, volume_profile, resumed_from_cache))

                    if should_cancel and should_cancel():
                        cache["status"] = "cancelled"
                        self._save_cache(cache)
                        stop_requested = True
                    elif should_pause and should_pause():
                        cache["status"] = "paused"
                        self._save_cache(cache)
                        stop_requested = True

                    if not stop_requested:
                        submit_next_records()

        successful = [r for r in all_results if r is not None]
        failed_chunks = [
            {"index": idx + 1, "preview": (chunk_records[idx].get("text") or "")[:120], "error": chunk_records[idx].get("error", "")}
            for idx, result in enumerate(all_results)
            if result is None
        ]
        cache.setdefault("diagnostics", {})["failed_chunks"] = failed_chunks
        cancelled = bool(cache.get("status") == "cancelled" or (should_cancel and should_cancel()))
        paused = bool(cache.get("status") == "paused" or (should_pause and should_pause()))
        if cancelled:
            cache["status"] = "cancelled"
            self._save_cache(cache)
            return self._build_force_cancel_result(cache, volume_profile, resumed_from_cache)
        if not successful:
            cache["status"] = "failed"
            self._save_cache(cache)
            raise ValueError("所有大块提取均失败: " + " | ".join(self.errors))

        if progress_callback:
            progress_callback('merging', 88, f'正在保存已提取的 {len(successful)}/{len(chunk_records)} 个大块结果...' if (cancelled or paused) else f'正在合并 {len(successful)}/{len(chunk_records)} 个大块结果...', self._progress_detail(cache, volume_profile, resumed_from_cache))
        style_data = self._empty_style_payload()
        merged = self._merge_extractions(successful)
        merged["settings"] = self._normalize_settings(merged.get("settings") or {})
        merged["writing_style"] = style_data.get("writing_style", "")
        merged["reference_text"] = style_data.get("reference_text", "")
        merged["extraction_diagnostics"] = {
            "volume_profile": volume_profile,
            "total_chunks": len(chunk_records),
            "successful_chunks": len(successful),
            "failed_chunks": failed_chunks,
            "errors": list(self.errors),
            **cache.get("diagnostics", {}),
        }

        if progress_callback:
            progress_callback('consolidating', 92, '正在执行规则整合，保留全部已提取实体与事件...', self._progress_detail(cache, volume_profile, resumed_from_cache))
        merged = self._consolidate_results(merged)
        merged = self._finalize_extraction(merged)
        merged["extraction_diagnostics"] = {**merged.get("extraction_diagnostics", {}), **cache.get("diagnostics", {})}
        merged.update(self._cache_result_fields(cache, volume_profile, resumed_from_cache))
        if not (cancelled or paused):
            if progress_callback:
                progress_callback('validating', 94, '正在质量验证并补充明显遗漏...', self._progress_detail(cache, volume_profile, resumed_from_cache))
            merged = self.validate_extraction(merged)
            merged = self._finalize_extraction(merged)
            merged["extraction_diagnostics"] = {**merged.get("extraction_diagnostics", {}), **cache.get("diagnostics", {})}
            merged.update(self._cache_result_fields(cache, volume_profile, resumed_from_cache))
        if cancelled:
            merged.setdefault("extraction_diagnostics", {})["cancelled"] = True
            merged["cancelled"] = True
            merged["cache_status"] = "cancelled"
        if paused:
            merged.setdefault("extraction_diagnostics", {})["paused"] = True
            merged["paused"] = True
            merged["cache_status"] = "paused"
        cache["final_result"] = merged
        cache["status"] = "cancelled" if cancelled else ("paused" if paused else ("completed" if not failed_chunks else "partial"))
        self._save_cache(cache)
        logger.info(f"提取{'中断保存' if cancelled else ('暂停保存' if paused else '完成')}: {len(merged.get('entities', []))} 实体, {len(merged.get('events', []))} 事件 ({len(successful)}/{len(chunk_records)})")
        return merged

    def resume_from_cache(self, cache_key: str, progress_callback=None, should_cancel=None, should_pause=None) -> Dict[str, Any]:
        """从已保存的提取缓存继续未完成块。"""
        cache = self._load_cache(cache_key)
        if not cache or not cache.get("chunks"):
            raise ValueError("提取缓存不存在，无法继续任务")
        chunks = cache.get("chunks") or []
        text = "\n\n".join(record.get("text") or "" for record in chunks)
        mode = str(cache.get("mode") or "fast").lower()
        volume_profile = cache.get("profile") or self.get_text_volume_profile(len(text))
        cache["status"] = "running"
        for record in chunks:
            if record.get("status") == "running":
                record["status"] = "pending"
        self._save_cache(cache)
        return self._extract_chapters(
            text,
            progress_callback=progress_callback,
            volume_profile=volume_profile,
            extraction_mode=mode,
            force_rebuild=False,
            should_cancel=should_cancel,
            should_pause=should_pause,
        )

    def _progress_detail(self, cache: Dict[str, Any], volume_profile: Dict[str, Any], resumed_from_cache: bool) -> Dict[str, Any]:
        chunks = cache.get("chunks") or []
        completed = sum(1 for item in chunks if item.get("status") == "completed")
        failed = sum(1 for item in chunks if item.get("status") == "failed")
        total_chars = max(1, int((volume_profile or {}).get("text_length") or 0))
        completed_ranges = []
        for item in chunks:
            if item.get("status") == "completed":
                char_range = item.get("char_range") or [0, 0]
                completed_ranges.append([max(0, int(char_range[0] or 0)), max(0, int(char_range[-1] or 0))])
        processed_chars = self._merged_range_length(completed_ranges)
        current_index = cache.get("current_chunk_index")
        current_record = chunks[current_index] if isinstance(current_index, int) and 0 <= current_index < len(chunks) else None
        current_range = cache.get("current_chunk_char_range") or (current_record or {}).get("char_range") or [processed_chars, processed_chars]
        if current_record and current_record.get("status") == "running":
            processed_chars = max(processed_chars, int(current_range[0] or 0))
        deep_discoveries = self._build_deep_discoveries(cache)
        knowledge_stats = self._build_knowledge_stats(cache)
        return {
            "cache_key": cache.get("cache_key"),
            "cache_status": cache.get("status"),
            "resumed_from_cache": resumed_from_cache,
            "completed_chunks": completed,
            "failed_chunks": failed,
            "total_chunks": len(chunks),
            "processed_chars": processed_chars,
            "total_chars": total_chars,
            "processed_chars_label": self._format_char_count(processed_chars),
            "total_chars_label": self._format_char_count(total_chars),
            "context_window": volume_profile.get("context_window"),
            "target_chunk_chars": volume_profile.get("target_chunk_chars"),
            "volume_profile": volume_profile,
            "deep_state": {
                "current_chunk_index": current_index,
                "current_chunk_title": cache.get("current_chunk_title") or self._current_chunk_title(current_record or {}),
                "current_chunk_char_range": current_range,
                "current_chunk_progress": 100 if current_record and current_record.get("status") == "completed" else (80 if current_record and current_record.get("status") == "running" else 0),
                "rolling_summary_preview": (cache.get("rolling_summary") or "")[-500:],
                "confirmed_entity_count": len(cache.get("confirmed_entities") or []),
                "snapshot_stats": cache.get("snapshot_stats") or {},
                "discoveries": deep_discoveries,
                "knowledge_stats": knowledge_stats,
            },
        }

    def _cache_result_fields(self, cache: Dict[str, Any], volume_profile: Dict[str, Any], resumed_from_cache: bool) -> Dict[str, Any]:
        detail = self._progress_detail(cache, volume_profile, resumed_from_cache)
        return {
            "cache_key": cache.get("cache_key"),
            "cache_status": cache.get("status"),
            "resumed_from_cache": resumed_from_cache,
            "template_id": cache.get("template_id") or self.template_id,
            "template_name": cache.get("template_name") or self.template_name,
            "completed_chunks": detail["completed_chunks"],
            "failed_chunks": detail["failed_chunks"],
            "processed_chars": detail["processed_chars"],
            "total_chars": detail["total_chars"],
            "context_window": volume_profile.get("context_window"),
            "target_chunk_chars": volume_profile.get("target_chunk_chars"),
            "deep_state": detail["deep_state"],
        }

    def _build_force_cancel_result(self, cache: Dict[str, Any], volume_profile: Dict[str, Any], resumed_from_cache: bool) -> Dict[str, Any]:
        chunks = cache.get("chunks") or []
        diagnostics = cache.get("diagnostics", {})
        result = {
            "cancelled": True,
            "force_cancelled": True,
            "cache_status": "cancelled",
            "extraction_diagnostics": {
                "cancelled": True,
                "force_cancelled": True,
                "volume_profile": volume_profile,
                "total_chunks": len(chunks),
                "successful_chunks": sum(1 for item in chunks if item.get("status") == "completed"),
                "failed_chunks": diagnostics.get("failed_chunks") or [],
                "errors": list(self.errors),
                **diagnostics,
            },
        }
        result.update(self._cache_result_fields(cache, volume_profile, resumed_from_cache))
        return result

    def _checkpoint_chunk(self, cache: Dict[str, Any], idx: int, result: Optional[Dict[str, Any]], error: str = "", deep_mode: bool = False, snapshot_stats: Optional[Dict[str, Any]] = None) -> None:
        chunks = cache.get("chunks") or []
        if idx < 0 or idx >= len(chunks):
            return
        record = chunks[idx]
        if result:
            record["status"] = "completed"
            record["result"] = result
            record["error"] = ""
            cache.setdefault("partial_results", [])
            existing_indexes = {item.get("index") for item in cache["partial_results"] if isinstance(item, dict)}
            if idx not in existing_indexes:
                cache["partial_results"].append({"index": idx, "result": result})
            if deep_mode:
                cache["last_completed_chunk"] = idx
                cache["rolling_summary"] = self._update_rolling_summary(cache.get("rolling_summary") or "", result)
                cache["confirmed_entities"] = self._update_confirmed_entities(cache.get("confirmed_entities") or [], result)
                cache["snapshot_stats"] = snapshot_stats or {}
                if result.get("entities"):
                    cache.setdefault("diagnostics", {}).setdefault("entity_yield_by_chunk", []).append({"index": idx + 1, "entities": len(result.get("entities") or []), "events": len(result.get("events") or [])})
        else:
            record["status"] = "failed"
            record["error"] = error or "提取失败"
            cache.setdefault("diagnostics", {}).setdefault("failed_chunks", []).append({"index": idx + 1, "error": record["error"]})
        completed = sum(1 for item in chunks if item.get("status") == "completed")
        failed = sum(1 for item in chunks if item.get("status") == "failed")
        cache["status"] = "completed" if completed == len(chunks) else ("partial" if completed or failed else "running")
        self._save_cache(cache)

    def _merged_range_length(self, ranges: List[List[int]]) -> int:
        normalized = sorted((max(0, int(a)), max(0, int(b))) for a, b in ranges if int(b) > int(a))
        if not normalized:
            return 0
        merged = []
        for start, end in normalized:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        return sum(end - start for start, end in merged)

    def _format_char_count(self, value: int) -> str:
        value = max(0, int(value or 0))
        if value >= 10_000:
            return f"{value / 10_000:.1f}万字"
        return f"{value}字"

    def _current_chunk_title(self, record: Dict[str, Any]) -> str:
        if not record:
            return "准备中"
        titles = record.get("chapter_titles") or []
        if titles:
            return str(titles[-1]).strip() or f"文本块 {int(record.get('index') or 0) + 1}"
        return f"文本块 {int(record.get('index') or 0) + 1}"

    def _build_deep_discoveries(self, cache: Dict[str, Any]) -> List[str]:
        partials = cache.get("partial_results") or []
        latest = next((item.get("result") for item in reversed(partials) if isinstance(item, dict) and item.get("result")), None)
        discoveries: List[str] = []
        if isinstance(latest, dict):
            for entity in (latest.get("entities") or [])[:3]:
                if isinstance(entity, dict) and entity.get("name"):
                    discoveries.append(f"新实体: {entity.get('name')} ({entity.get('type') or '其他'})")
            for event in (latest.get("events") or [])[:2]:
                if isinstance(event, dict) and event.get("name"):
                    discoveries.append(f"事件更新: {event.get('name')}")
            for item in ((latest.get("settings") or {}).get("items") or [])[:2]:
                if isinstance(item, dict) and item.get("name"):
                    discoveries.append(f"设定补充: {item.get('name')}")
        return discoveries[:5]

    def _build_knowledge_stats(self, cache: Dict[str, Any]) -> Dict[str, int]:
        stats = {"人物": 0, "物品": 0, "势力": 0, "地点": 0, "事件": 0}
        seen_entities = set()
        seen_events = set()
        for item in cache.get("partial_results") or []:
            result = item.get("result") if isinstance(item, dict) else None
            if not isinstance(result, dict):
                continue
            for entity in result.get("entities") or []:
                if not isinstance(entity, dict):
                    continue
                name = str(entity.get("name") or "").strip()
                if not name or name in seen_entities:
                    continue
                seen_entities.add(name)
                entity_type = str(entity.get("type") or "其他")
                if entity_type == "人物":
                    stats["人物"] += 1
                elif entity_type in {"物品", "能力"}:
                    stats["物品"] += 1
                elif entity_type in {"组织", "国家", "种族"}:
                    stats["势力"] += 1
                elif entity_type == "地点":
                    stats["地点"] += 1
            for event in result.get("events") or []:
                if not isinstance(event, dict):
                    continue
                name = str(event.get("name") or "").strip()
                if name and name not in seen_events:
                    seen_events.add(name)
                    stats["事件"] += 1
        return stats

    def _update_rolling_summary(self, previous: str, result: Dict[str, Any]) -> str:
        names = [str(e.get("name") or "").strip() for e in result.get("entities") or [] if isinstance(e, dict)][:20]
        events = [str(e.get("name") or "").strip() for e in result.get("events") or [] if isinstance(e, dict)][:12]
        line = f"新增实体：{'、'.join([n for n in names if n])}；新增事件：{'、'.join([n for n in events if n])}。"
        summary = (previous + "\n" + line).strip()
        return summary[-int(getattr(Config, "DEEP_EXTRACTION_SUMMARY_MAX_CHARS", 4000)):]

    def _update_confirmed_entities(self, current: List[Dict[str, Any]], result: Dict[str, Any]) -> List[Dict[str, Any]]:
        by_key = {self._normalize_identity_key(item.get("name")): item for item in current if isinstance(item, dict)}
        for entity in result.get("entities") or []:
            if not isinstance(entity, dict):
                continue
            key = self._normalize_identity_key(entity.get("name"))
            if key:
                by_key[key] = {"name": entity.get("name"), "type": entity.get("type"), "aliases": entity.get("aliases") or []}
        return list(by_key.values())[-int(getattr(Config, "DEEP_EXTRACTION_ACTIVE_ENTITY_LIMIT", 80)):]

    def _build_entity_snapshot(self, cache: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        entities = cache.get("confirmed_entities") or []
        limit = int(getattr(Config, "DEEP_EXTRACTION_ACTIVE_ENTITY_LIMIT", 80))
        selected = entities[-limit:]
        omitted = max(0, len(entities) - len(selected))
        lines = [f"- {item.get('name')}（{item.get('type') or '其他'}）" for item in selected if isinstance(item, dict)]
        text = "\n".join(lines)
        max_chars = int(getattr(Config, "DEEP_EXTRACTION_ENTITY_SNAPSHOT_MAX_CHARS", 10000))
        if len(text) > max_chars:
            text = text[-max_chars:]
        return text, {"entity_count": len(selected), "snapshot_omitted_count": omitted}

    def _build_deep_context(self, rolling_summary: str, snapshot: str) -> str:
        parts = []
        if rolling_summary:
            parts.append(f"【滚动摘要】\n{rolling_summary}")
        if snapshot:
            parts.append(f"【已确认实体快照】\n{snapshot}")
        return "\n\n".join(parts)

    # ==================== 章节感知切分 ====================

    def _chapter_aware_split(self, text: str, volume_profile: Optional[Dict[str, Any]] = None) -> List[str]:
        """按章节标记切分文本，每 CHAPTERS_PER_CHUNK 章合并为一次 LLM 调用。"""
        text = self._safe_text(text)
        volume_profile = volume_profile or self.get_text_volume_profile(len(text))
        chapters_per_chunk = int(volume_profile.get("chapters_per_chunk") or self.CHAPTERS_PER_CHUNK)
        char_budget = int(volume_profile.get("chapter_chunk_char_budget") or self.CHAPTER_CHUNK_CHAR_BUDGET)
        chapter_starts = []
        seen_starts = set()
        for match in re.finditer(self.CHAPTER_RE, text, re.MULTILINE | re.IGNORECASE):
            start = match.start()
            if start < len(text) and text[start] == '\n':
                start += 1
            if start in seen_starts:
                continue
            seen_starts.add(start)
            chapter_starts.append((start, match.group().strip()))

        if not chapter_starts:
            logger.info("未检测到章节标记，使用等宽切分")
            return self._fallback_split(text)

        logger.info(
            f"检测到 {len(chapter_starts)} 个章节标记，每段最多 {chapters_per_chunk} 章且不超过 {char_budget} 字"
        )

        chapter_segments: List[Dict[str, Any]] = []
        preface = text[:chapter_starts[0][0]].strip()
        if preface:
            chapter_segments.extend(self._split_oversized_record(preface, 0, len(preface), ["序言/前置信息"], volume_profile=volume_profile))

        for idx, (start_pos, title) in enumerate(chapter_starts):
            end_pos = chapter_starts[idx + 1][0] if idx + 1 < len(chapter_starts) else len(text)
            chapter_text = text[start_pos:end_pos].strip()
            if not chapter_text:
                continue
            chapter_segments.extend(self._split_oversized_record(chapter_text, start_pos, end_pos, [title], volume_profile=volume_profile))

        chunks = self._pack_segments_into_chunks(chapter_segments, volume_profile=volume_profile)
        avg_len = sum(len(c) for c in chunks) // max(len(chunks), 1)
        max_len = max((len(c) for c in chunks), default=0)
        logger.info(f"切分结果: {len(chunks)} 段 (平均 {avg_len} 字符, 最大 {max_len} 字符)")
        return chunks

    def _split_oversized_record(self, segment: str, start_pos: int, end_pos: int, titles: List[str], volume_profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """将单个超长章节/分部继续拆小，并保留精确字符范围。"""
        volume_profile = volume_profile or self.get_text_volume_profile(len(segment or ""))
        char_budget = int(volume_profile.get("chapter_chunk_char_budget") or self.CHAPTER_CHUNK_CHAR_BUDGET)
        chunk_size = int(volume_profile.get("chunk_size") or self.CHUNK_SIZE)
        chunk_overlap = int(volume_profile.get("chunk_overlap") or self.CHUNK_OVERLAP)
        segment = self._safe_text(segment).strip()
        if not segment:
            return []
        if len(segment) <= char_budget:
            return [{"text": segment, "char_range": [start_pos, end_pos], "chapter_titles": titles}]

        logger.info(
            f"章节/分部过长 ({len(segment)} 字符)，按 {volume_profile.get('profile')} 策略继续以 {chunk_size} 字符切分"
        )
        chunks = self._fallback_split(segment, chunk_size=chunk_size, overlap=chunk_overlap)
        records = []
        cursor = 0
        for sub_chunk in chunks:
            found = segment.find(sub_chunk[: min(len(sub_chunk), 200)], cursor)
            local_start = found if found >= 0 else cursor
            local_end = local_start + len(sub_chunk)
            cursor = max(local_end - chunk_overlap, local_start + 1)
            records.append({
                "text": sub_chunk,
                "char_range": [start_pos + local_start, min(start_pos + local_end, end_pos)],
                "chapter_titles": titles,
            })
        return records

    def _pack_segments_into_chunks(self, segments: List[Any], volume_profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """将已安全切分的章节段合并为 prompt chunk，尽量生成少量上下文友好的大块。"""
        total_len = sum(len((s.get("text") if isinstance(s, dict) else s) or "") for s in segments)
        volume_profile = volume_profile or self.get_text_volume_profile(total_len)
        chapters_per_chunk = int(volume_profile.get("chapters_per_chunk") or self.CHAPTERS_PER_CHUNK)
        char_budget = int(volume_profile.get("chapter_chunk_char_budget") or self.CHAPTER_CHUNK_CHAR_BUDGET)
        chunks: List[Dict[str, Any]] = []
        current_parts: List[str] = []
        current_titles: List[str] = []
        current_start: Optional[int] = None
        current_end: Optional[int] = None
        current_len = 0

        def flush_current():
            nonlocal current_parts, current_titles, current_start, current_end, current_len
            chunk = "\n\n".join(current_parts).strip()
            if chunk:
                chunks.append({
                    "text": chunk,
                    "char_range": [int(current_start or 0), int(current_end or current_start or 0)],
                    "chapter_titles": current_titles[-8:],
                })
            current_parts = []
            current_titles = []
            current_start = None
            current_end = None
            current_len = 0

        for raw_segment in segments:
            if isinstance(raw_segment, dict):
                segment = self._safe_text(raw_segment.get("text") or "").strip()
                char_range = raw_segment.get("char_range") or [0, 0]
                titles = [str(t).strip() for t in raw_segment.get("chapter_titles") or [] if str(t).strip()]
            else:
                segment = self._safe_text(raw_segment).strip()
                char_range = [0, len(segment)]
                titles = []
            if not segment:
                continue

            segment_len = len(segment)
            join_extra = 2 if current_parts else 0
            exceeds_chapter_limit = len(current_titles) >= chapters_per_chunk
            exceeds_char_budget = bool(current_parts) and current_len + join_extra + segment_len > char_budget
            if exceeds_chapter_limit or exceeds_char_budget:
                flush_current()
                join_extra = 0

            current_parts.append(segment)
            current_titles.extend(t for t in titles if t not in current_titles)
            current_start = int(char_range[0] or 0) if current_start is None else min(current_start, int(char_range[0] or 0))
            current_end = int(char_range[-1] or 0) if current_end is None else max(current_end, int(char_range[-1] or 0))
            current_len += join_extra + segment_len

        if current_parts:
            flush_current()

        return chunks

    def _fallback_split(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
        """等宽切分（无章节标记时的回退方案）"""
        chunk_size = int(chunk_size or self.CHUNK_SIZE)
        overlap = int(overlap if overlap is not None else self.CHUNK_OVERLAP)
        text = self._safe_text(text)
        if len(text) <= chunk_size:
            return [text] if text.strip() else []
        chunks = []
        pos = 0
        while pos < len(text):
            end = min(pos + chunk_size, len(text))
            if end < len(text):
                search_start = max(pos + chunk_size // 2, pos)
                chunk_text = text[search_start:end + 500]
                best_break = -1
                for sep in ['\n\n\n', '\n\n', '\n第', '。\n', '！\n', '？\n', '。', '！', '？']:
                    idx = chunk_text.rfind(sep)
                    if idx >= 0:
                        candidate = search_start + idx + len(sep)
                        if candidate > pos + chunk_size // 2:
                            best_break = candidate
                            break
                if best_break > 0:
                    end = best_break
            chunk = text[pos:end].strip()
            if chunk:
                chunks.append(chunk)
            pos = max(end - overlap, pos + 1)
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
            if isinstance(wi, dict) and wi:
                if not merged_world_info:
                    merged_world_info = {}
                for key in ("name", "era", "anchor_time"):
                    if not merged_world_info.get(key) and wi.get(key):
                        merged_world_info[key] = wi.get(key)
                if wi.get("description"):
                    merged_world_info["description"] = self._merge_text(
                        merged_world_info.get("description"),
                        wi.get("description"),
                    )

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
            text = self._safe_text(text)
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
                extracted_data.setdefault("extraction_diagnostics", {})["quality_validation"] = {
                    "quality": result.get("quality", ""),
                    "suggestions": result.get("suggestions", ""),
                    "supplement_entities": len((result.get("supplement") or {}).get("entities") or []),
                    "supplement_events": len((result.get("supplement") or {}).get("events") or []),
                }
                s = result["supplement"]
                if s.get("entities"):
                    extracted_data.setdefault("entities", []).extend(s["entities"])
                if s.get("events"):
                    extracted_data.setdefault("events", []).extend(s["events"])
            elif isinstance(result, dict):
                extracted_data.setdefault("extraction_diagnostics", {})["quality_validation"] = {
                    "quality": result.get("quality", ""),
                    "suggestions": result.get("suggestions", ""),
                    "supplement_entities": 0,
                    "supplement_events": 0,
                }
            return extracted_data
        except Exception as e:
            self._record_error("验证提取数据", e)
            return extracted_data
