"""
Agent Tool 定义 — 所有 Agent 可调用的工具
每个 Tool 都有明确的 name、description、parameters schema 和 execute 方法
符合 OpenAI function calling 格式，同时兼容 MCP tools/list 格式
"""

import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..config import Config
from ..models.world import WorldManager, Entity, Event, WorldSetting
from ..models.map import (
    add_change_record,
    apply_batch_update,
    apply_cell_update,
    cell_neighbors,
    find_cell,
    find_map,
    list_maps as list_structured_maps,
    save_maps,
    search_cells,
    stats_for_map,
    summarize_map,
)
from ..models.agent import AgentManager, Skill, MemoryEntry
from ..services.timeline_manager import TimelineManager
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger("worldfish.agent_tools")
TIMELINE_MANAGER = TimelineManager()

# ============================================================
# Base Tool
# ============================================================


@dataclass
class ToolCallResult:
    """工具调用结果"""
    success: bool
    content: str                     # 给 LLM 看的文本结果
    data: Any = None                 # 结构化数据
    needs_user_response: bool = False  # 是否需要用户响应
    user_options: Optional[List[Dict[str, Any]]] = None  # 提供给用户的选项


class BaseTool(ABC):
    """工具基类"""
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        ...

    def to_openai_schema(self) -> Dict[str, Any]:
        """转为 OpenAI function calling schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.parameters.keys())
                }
            }
        }

    def to_mcp_schema(self) -> Dict[str, Any]:
        """转为 MCP tools/list schema"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys())
            }
        }


# ============================================================
# World 读取/查询类 Tools
# ============================================================

class ReadWorldTool(BaseTool):
    name = "read_world"
    description = "读取当前世界观的整体摘要，包括基础信息、实体数量、事件数量、设定概况。用于快速了解世界观全貌。"
    parameters = {}

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID，请先让用户选择或创建世界观。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        # 瘦身：不再返回 entity_types 列表（可能很长）
        summary = {
            "name": world.name,
            "description": (world.description or "")[:300],
            "era": world.era,
            "anchor_time": world.anchor_time,
            "entity_count": len(world.entities),
            "event_count": len(world.events),
            "settings_count": len(world.settings.get("items", []) if world.settings else []),
        }
        return ToolCallResult(True, json.dumps(summary, ensure_ascii=False), data=summary)


class ListEntitiesTool(BaseTool):
    name = "list_entities"
    description = "列出世界观中的实体（支持类型过滤和数量限制）。默认返回前 20 条，可按需传入更大的 limit。"
    parameters = {
        "entity_type": {"type": "string", "description": "可选：按类型过滤（如 人物、国家、组织）"},
        "limit": {"type": "integer", "description": "返回条数（默认 20，按需可传更大值）"},
    }

    def execute(self, world_id: str = "", entity_type: str = "", limit: int = 20, **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        entities = world.entities
        if entity_type:
            entities = [e for e in entities if e.type == entity_type]
        limit = max(1, int(limit if limit is not None else 20))
        # 紧凑输出：仅返回 id/name/type，去掉 aliases/stage_count
        data = [{"id": e.id, "name": e.name, "type": e.type} for e in entities[:limit]]
        total = len(entities)
        meta = f"共 {total} 个实体" + (f"（类型: {entity_type}）" if entity_type else "")
        if total > limit:
            meta += f"，已返回前 {limit} 条"
        return ToolCallResult(True, meta + "\n" + json.dumps(data, ensure_ascii=False), data=data)


class GetEntityDetailTool(BaseTool):
    name = "get_entity_detail"
    description = "获取指定实体的完整详情，包括属性、阶段、关系等。"
    parameters = {
        "entity_id": {"type": "string", "description": "实体 ID"}
    }

    def execute(self, world_id: str = "", entity_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        for e in world.entities:
            if e.id == entity_id:
                d = e.to_dict()
                # 截断过长的 description/attributes 文本
                if d.get("attributes"):
                    for k in list(d["attributes"].keys()):
                        v = d["attributes"][k]
                        if isinstance(v, str) and len(v) > 300:
                            d["attributes"][k] = v[:300] + "..."
                return ToolCallResult(True, json.dumps(d, ensure_ascii=False, indent=2), data=d)
        return ToolCallResult(False, f"实体 {entity_id} 未找到。")


class ListEventsTool(BaseTool):
    name = "list_events"
    description = "列出世界观中的事件。默认返回前 20 条，可按需传入更大的 limit。"
    parameters = {
        "limit": {"type": "integer", "description": "返回条数（默认 20，按需可传更大值）"},
    }

    def execute(self, world_id: str = "", limit: int = 20, **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        limit = max(1, int(limit if limit is not None else 20))
        events = world.events[:limit]
        data = [{"id": ev.id, "name": ev.name, "date": ev.date,
                 "desc": (ev.description or "")[:120]} for ev in events]
        total = len(world.events)
        meta = f"共 {total} 个事件"
        if total > limit:
            meta += f"，已返回前 {limit} 条"
        return ToolCallResult(True, meta + "\n" + json.dumps(data, ensure_ascii=False), data=data)


class GetEventDetailTool(BaseTool):
    name = "get_event_detail"
    description = "获取指定事件的完整详情。"
    parameters = {
        "event_id": {"type": "string", "description": "事件 ID"}
    }

    def execute(self, world_id: str = "", event_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        for ev in world.events:
            if ev.id == event_id:
                return ToolCallResult(True, json.dumps(ev.to_dict(), ensure_ascii=False, indent=2), data=ev.to_dict())
        return ToolCallResult(False, f"事件 {event_id} 未找到。")


class ReadSettingsTool(BaseTool):
    name = "read_settings"
    description = "读取世界观设定项、时间线历法（日历/纪元/纪年）和地图数据。"
    parameters = {}

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        settings = world.settings or {}
        data = {
            "items": settings.get("items", [])[:50],
            "calendars": settings.get("calendars", []),
            "mapData": settings.get("mapData", {}),
        }
        return ToolCallResult(True, json.dumps(data, ensure_ascii=False, indent=2), data=data)


class SearchKnowledgeTool(BaseTool):
    name = "search_knowledge"
    description = """从 RAG 向量知识库语义检索。只返回相关度 >= 25% 的结果。
**重要：如果返回空或无相关内容，你必须诚实告知用户"知识库中暂无相关信息"，绝不能编造！**"""
    parameters = {
        "query": {"type": "string", "description": "自然语言查询"},
        "top_k": {"type": "integer", "description": "返回条数（默认 5，最大 10）"},
    }

    def execute(self, world_id: str = "", query: str = "", top_k: int = 5, **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        if not query.strip():
            return ToolCallResult(False, "请提供查询内容。")
        try:
            from ..services.rag_service import RagService
            rag = RagService(world_id)
            if rag.count() == 0:
                return ToolCallResult(True,
                    "⚠️ 知识库为空，无法检索。请告诉用户：当前世界观还没有建立 RAG 知识库，建议先在 RAG 页面添加文档或通过世界观提取功能自动索引。")
            top_k = min(max(1, int(top_k or 5)), 10)
            results = rag.search(query=query.strip(), top_k=top_k)
            if not results:
                return ToolCallResult(True,
                    "知识库中未找到任何匹配内容。请诚实告知用户：当前知识库中暂无与此查询相关的信息，不要编造。")
            # 过滤低分结果（<0.25 基本无关）
            MIN_SCORE = 0.25
            relevant = [r for r in results if r.score >= MIN_SCORE]
            if not relevant:
                top_score = max(r.score for r in results)
                return ToolCallResult(True,
                    f"所有结果相关度均低于阈值（最高 {top_score:.2f}）。"
                    "请诚实告知用户：知识库中暂无强相关的信息，不要猜测或编造。")
            items = []
            for r in relevant:
                items.append({
                    "text": (r.text or "")[:400],
                    "score": round(r.score, 3),
                    "source": r.metadata.get("source", "?") if r.metadata else "?",
                })
            return ToolCallResult(True,
                f"检索到 {len(items)} 条相关结果（相关度 ≥{MIN_SCORE}）:\n" + json.dumps(items, ensure_ascii=False),
                data=items)
        except ValueError as e:
            return ToolCallResult(False, str(e))
        except Exception as e:
            return ToolCallResult(False, f"检索失败: {e}")


class ListMapsTool(BaseTool):
    name = "list_maps"
    description = "列出当前世界观中的结构化地图。用于了解有哪些世界地图、大陆地图、国家地图或区域地图。"
    parameters = {}

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        maps = list_structured_maps(world)
        save_maps(world, maps)
        WorldManager.save_world(world)
        data = [summarize_map(item) for item in maps]
        if not data:
            return ToolCallResult(True, "当前世界观还没有结构化地图。", data=[])
        return ToolCallResult(True, json.dumps(data, ensure_ascii=False, indent=2), data=data)


class ReadMapTool(BaseTool):
    name = "read_map"
    description = "读取指定地图的摘要、尺寸、图层统计和部分重要区域。不会返回全部格子，适合先了解地图全貌。"
    parameters = {
        "map_id": {"type": "string", "description": "地图 ID"}
    }

    def execute(self, world_id: str = "", map_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id or not map_id:
            return ToolCallResult(False, "缺少世界观 ID 或地图 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        target = find_map(list_structured_maps(world), map_id)
        if not target:
            return ToolCallResult(False, f"地图 {map_id} 不存在。")
        notable = []
        for cell in target.get("cells", []):
            if cell.get("name") or cell.get("faction") or cell.get("resources") or cell.get("event_relations") or cell.get("status") not in ("normal", ""):
                notable.append({
                    "id": cell.get("id"), "name": cell.get("name"), "coord": [cell.get("q"), cell.get("r")],
                    "terrain": cell.get("terrain"), "status": cell.get("status"), "faction": cell.get("faction"),
                    "resources": cell.get("resources", []),
                })
        data = {"summary": summarize_map(target), "stats": stats_for_map(target), "notable_cells": notable[:30]}
        return ToolCallResult(True, json.dumps(data, ensure_ascii=False, indent=2), data=data)


class SearchMapCellsTool(BaseTool):
    name = "search_map_cells"
    description = "在指定地图中搜索区域名称、地形、势力、资源、状态、地点、实体或事件。"
    parameters = {
        "map_id": {"type": "string", "description": "地图 ID"},
        "query": {"type": "string", "description": "搜索关键词，如 北方王国、铁矿、战争中、森林"},
        "limit": {"type": "integer", "description": "返回数量上限，默认 20"},
    }

    def execute(self, world_id: str = "", map_id: str = "", query: str = "", limit: int = 20, **kwargs) -> ToolCallResult:
        if not world_id or not map_id:
            return ToolCallResult(False, "缺少世界观 ID 或地图 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        target = find_map(list_structured_maps(world), map_id)
        if not target:
            return ToolCallResult(False, f"地图 {map_id} 不存在。")
        limit = max(1, min(int(limit or 20), 100))
        cells = search_cells(target, query)[:limit]
        data = [{
            "id": cell.get("id"), "name": cell.get("name"), "coord": [cell.get("q"), cell.get("r")],
            "terrain": cell.get("terrain"), "status": cell.get("status"), "faction": cell.get("faction"),
            "resources": cell.get("resources", []), "locations": cell.get("locations", []),
        } for cell in cells]
        return ToolCallResult(True, f"找到 {len(data)} 个地图单元\n" + json.dumps(data, ensure_ascii=False), data=data)


class GetMapCellDetailTool(BaseTool):
    name = "get_map_cell_detail"
    description = "读取指定地图单元完整详情，并返回相邻单元摘要。"
    parameters = {
        "map_id": {"type": "string", "description": "地图 ID"},
        "cell_id": {"type": "string", "description": "地图单元 ID"},
    }

    def execute(self, world_id: str = "", map_id: str = "", cell_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id or not map_id or not cell_id:
            return ToolCallResult(False, "缺少 world_id、map_id 或 cell_id。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        target = find_map(list_structured_maps(world), map_id)
        if not target:
            return ToolCallResult(False, f"地图 {map_id} 不存在。")
        cell = find_cell(target, cell_id)
        if not cell:
            return ToolCallResult(False, f"地图单元 {cell_id} 不存在。")
        neighbors = [{"id": item.get("id"), "name": item.get("name"), "coord": [item.get("q"), item.get("r")], "terrain": item.get("terrain"), "faction": item.get("faction")} for item in cell_neighbors(target, cell)]
        data = {"cell": cell, "neighbors": neighbors}
        return ToolCallResult(True, json.dumps(data, ensure_ascii=False, indent=2), data=data)


class UpdateMapCellTool(BaseTool):
    name = "update_map_cell"
    description = "修改一个明确指定的地图单元。必须已经知道 map_id 和 cell_id；目标不明确时不要调用，先搜索或询问用户。"
    parameters = {
        "map_id": {"type": "string", "description": "地图 ID"},
        "cell_id": {"type": "string", "description": "地图单元 ID"},
        "updates": {"type": "object", "description": "要更新的字段，如 name、description、terrain、status、faction、resources、locations、entity_relations、event_relations、notes"},
    }

    def execute(self, world_id: str = "", map_id: str = "", cell_id: str = "", updates: dict = None, **kwargs) -> ToolCallResult:
        if not world_id or not map_id or not cell_id:
            return ToolCallResult(False, "缺少 world_id、map_id 或 cell_id。")
        updates = updates or {}
        if not updates:
            return ToolCallResult(False, "没有提供要修改的地图字段。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        maps = list_structured_maps(world)
        target = find_map(maps, map_id)
        if not target:
            return ToolCallResult(False, f"地图 {map_id} 不存在。")
        cell = find_cell(target, cell_id)
        if not cell:
            return ToolCallResult(False, f"地图单元 {cell_id} 不存在。")
        before = copy.deepcopy(cell)
        updated = apply_cell_update(cell, updates)
        target["cells"] = [updated if item.get("id") == cell_id else item for item in target.get("cells", [])]
        target["updated_at"] = updated.get("updated_at")
        add_change_record(target, "cell", cell_id, before, updated, source="agent", agent=True)
        save_maps(world, maps)
        WorldManager.save_world(world)
        return ToolCallResult(True, f"✅ 地图单元 {cell_id} 已更新。", data=updated)


class BatchUpdateMapCellsTool(BaseTool):
    name = "batch_update_map_cells"
    description = "批量修改一组明确指定的地图单元。必须提供明确 cell_ids；不要对模糊目标直接调用。"
    parameters = {
        "map_id": {"type": "string", "description": "地图 ID"},
        "cell_ids": {"type": "array", "description": "地图单元 ID 列表"},
        "updates": {"type": "object", "description": "批量更新字段，如 terrain、status、faction、resources、tags、clear_faction、clear_resources"},
    }

    def execute(self, world_id: str = "", map_id: str = "", cell_ids: list = None, updates: dict = None, **kwargs) -> ToolCallResult:
        if not world_id or not map_id:
            return ToolCallResult(False, "缺少 world_id 或 map_id。")
        cell_ids = [str(item) for item in (cell_ids or []) if str(item).strip()]
        if not cell_ids:
            return ToolCallResult(False, "没有提供明确的 cell_ids。目标区域不明确时，请先搜索或询问用户确认。")
        updates = updates or {}
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        maps = list_structured_maps(world)
        target = find_map(maps, map_id)
        if not target:
            return ToolCallResult(False, f"地图 {map_id} 不存在。")
        id_set = set(cell_ids)
        changed = []
        new_cells = []
        for cell in target.get("cells", []):
            if cell.get("id") in id_set:
                before = copy.deepcopy(cell)
                updated = apply_batch_update(cell, updates)
                changed.append(updated)
                add_change_record(target, "cell", cell.get("id"), before, updated, source="agent", agent=True)
                new_cells.append(updated)
            else:
                new_cells.append(cell)
        target["cells"] = new_cells
        save_maps(world, maps)
        WorldManager.save_world(world)
        return ToolCallResult(True, f"✅ 已批量更新 {len(changed)} 个地图单元。", data=changed)


class GetRagStatsTool(BaseTool):
    name = "get_rag_stats"
    description = "查看 RAG 知识库统计信息（文档总数、集合名称）。用于判断知识库是否有内容可检索。"
    parameters = {}

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        try:
            from ..services.rag_service import RagService
            rag = RagService(world_id)
            stats = rag.get_stats()
            return ToolCallResult(True, json.dumps(stats, ensure_ascii=False), data=stats)
        except ValueError as e:
            return ToolCallResult(False, str(e))
        except Exception as e:
            return ToolCallResult(False, f"获取失败: {e}")


class ListRagDocsTool(BaseTool):
    name = "list_rag_docs"
    description = "列出 RAG 知识库中的文档摘要（按来源分组统计）。不返回全文，只返回数量分布。"
    parameters = {}

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        try:
            from ..services.rag_service import RagService
            rag = RagService(world_id)
            total = rag.count()
            if total == 0:
                return ToolCallResult(True, "知识库为空。")
            docs = rag.list_documents(limit=200, offset=0)
            # 按来源分组统计
            by_source = {}
            for d in docs:
                src = (d.metadata or {}).get("source", "未知")
                by_source[src] = by_source.get(src, 0) + 1
            return ToolCallResult(True,
                f"知识库共 {total} 条文档\n按来源分布: " + json.dumps(by_source, ensure_ascii=False),
                data={"total": total, "by_source": by_source})
        except ValueError as e:
            return ToolCallResult(False, str(e))
        except Exception as e:
            return ToolCallResult(False, f"获取失败: {e}")


# ============================================================
# World 修改类 Tools
# ============================================================

ENTITY_TYPE_TO_SETTING_CATEGORY = {
    "人物": "character", "角色": "character", "person": "character", "character": "character",
    "种族": "character", "生物": "character",
    "国家": "organization", "政权": "organization", "组织": "organization", "势力": "organization",
    "nation": "organization", "organization": "organization", "faction": "organization",
    "团体": "organization", "教会": "organization", "公司": "organization", "公会": "organization",
    "地点": "geography", "位置": "geography", "城市": "geography", "location": "geography",
    "geography": "geography", "place": "geography", "区域": "geography",
    "物品": "item", "道具": "item", "装备": "item", "武器": "item", "item": "item",
    "能力": "ability", "魔法": "ability", "技能": "ability", "体系": "ability", "ability": "ability",
}


def _normalize_entity_key(value: Any) -> str:
    return re.sub(r"[\s\-_·•/\\()（）\[\]{}<>《》“”\"'`]+", "", str(value or "").strip().lower())


def _resolve_entity_setting_category(entity_type: str) -> str:
    normalized_type = str(entity_type or "").strip()
    if normalized_type in ENTITY_TYPE_TO_SETTING_CATEGORY:
        return ENTITY_TYPE_TO_SETTING_CATEGORY[normalized_type]
    return ENTITY_TYPE_TO_SETTING_CATEGORY.get(normalized_type.lower(), "other")


def _ensure_settings_items(world) -> List[Dict[str, Any]]:
    if not isinstance(world.settings, dict):
        world.settings = {"items": [], "mapData": {}, "calendars": []}
    items = world.settings.setdefault("items", [])
    if not isinstance(items, list):
        world.settings["items"] = []
        items = world.settings["items"]
    return items


def _find_entity_setting_item(items: List[Dict[str, Any]], entity: Entity) -> Optional[Dict[str, Any]]:
    entity_id = str(getattr(entity, "id", "") or "").strip()
    setting_item_id = str(getattr(entity, "setting_item_id", "") or "").strip()
    entity_name_key = _normalize_entity_key(getattr(entity, "name", ""))
    fallback = None

    for item in items:
        if not isinstance(item, dict) or item.get("settingType") == "collection":
            continue
        if setting_item_id and str(item.get("id") or "").strip() == setting_item_id:
            return item
        if entity_id and str(item.get("linkedEntityId") or item.get("entityId") or "").strip() == entity_id:
            return item
        if entity_name_key and _normalize_entity_key(item.get("name")) == entity_name_key:
            fallback = item
    return fallback


def _stringify_setting_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _build_entity_setting_summary(entity: Entity) -> Dict[str, str]:
    attributes = entity.attributes if isinstance(entity.attributes, dict) else {}
    description = ""
    for key in ["简介", "描述", "description", "summary", "背景"]:
        value = attributes.get(key)
        if value:
            description = _stringify_setting_value(value).strip()
            break
    if not description:
        description = str(getattr(entity, "type", "") or "实体设定").strip()

    lines = [
        f"名称：{entity.name}",
        f"类型：{entity.type or '未分类'}",
    ]
    if getattr(entity, "aliases", None):
        lines.append("别名：" + "、".join(entity.aliases))

    for key, value in attributes.items():
        text = _stringify_setting_value(value).strip()
        if text:
            lines.append(f"{key}：{text}")

    stages = entity.stages if isinstance(entity.stages, list) else []
    if stages:
        lines.append("阶段：")
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            label = str(stage.get("name") or stage.get("era") or "未命名阶段").strip()
            detail = str(stage.get("description") or "").strip()
            lines.append(f"- {label}" + (f"：{detail}" if detail else ""))

    return {
        "description": description[:300],
        "detailContent": "\n".join(lines).strip(),
    }


def _upsert_entity_setting(world, entity: Entity) -> Dict[str, Any]:
    items = _ensure_settings_items(world)
    setting_item = _find_entity_setting_item(items, entity)
    summary = _build_entity_setting_summary(entity)

    if setting_item is None:
        setting_item = {
            "id": entity.setting_item_id or f"setting_{entity.id}",
            "settingType": "setting",
            "sourceType": "entity",
            "autoGenerated": True,
            "showInList": True,
        }
        items.append(setting_item)

    setting_item.update({
        "name": entity.name,
        "category": _resolve_entity_setting_category(entity.type),
        "description": summary["description"],
        "aliases": list(getattr(entity, "aliases", []) or []),
        "detailContent": summary["detailContent"] or summary["description"],
        "linkedEntityId": entity.id,
        "sourceType": setting_item.get("sourceType") or "entity",
        "autoGenerated": bool(setting_item.get("autoGenerated", True)),
        "showInList": setting_item.get("showInList", True),
    })
    entity.setting_item_id = str(setting_item.get("id") or "")

    for stage in getattr(entity, "stages", []) or []:
        if isinstance(stage, dict):
            stage["setting_item_id"] = entity.setting_item_id

    return setting_item


def _delete_entity_setting(world, entity: Entity) -> Optional[Dict[str, Any]]:
    items = _ensure_settings_items(world)
    target = _find_entity_setting_item(items, entity)
    if not target:
        return None
    world.settings["items"] = [item for item in items if item is not target]
    return target


class AddEntityTool(BaseTool):
    name = "add_entity"
    description = "向世界观添加一个新实体（人物、国家、组织、地点、物品、能力等）。"
    parameters = {
        "name": {"type": "string", "description": "实体名称"},
        "entity_type": {"type": "string", "description": "实体类型：人物/国家/组织/地点/物品/能力/其他"},
        "attributes": {"type": "object", "description": "实体属性（可选，key-value 对象）"},
        "stages": {"type": "array", "description": "实体阶段列表（可选）"},
        "setting_item_id": {"type": "string", "description": "关联的设定项 ID（可选）"},
    }

    def execute(self, world_id: str = "", name: str = "", entity_type: str = "",
                attributes: dict = None, stages: list = None,
                setting_item_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        if not name:
            return ToolCallResult(False, "实体名称不能为空。")
        if not entity_type:
            return ToolCallResult(False, "实体类型不能为空。")
        try:
            entity = WorldManager.add_entity(
                world_id=world_id, name=name, type=entity_type,
                attributes=attributes or {},
                stages=stages or [],
                setting_item_id=setting_item_id,
            )
            world = WorldManager.get_world(world_id)
            synced_setting = None
            if world:
                for saved_entity in world.entities:
                    if saved_entity.id == entity.id:
                        synced_setting = _upsert_entity_setting(world, saved_entity)
                        entity = saved_entity
                        break
                WorldManager.save_world(world)
            return ToolCallResult(True,
                f"✅ 实体 '{name}'（类型: {entity_type}）已成功添加，ID: {entity.id}，并已同步对应设定项。",
                data={"entity": entity.to_dict(), "setting": synced_setting})
        except Exception as e:
            return ToolCallResult(False, f"添加实体失败: {str(e)}")


class UpdateEntityTool(BaseTool):
    name = "update_entity"
    description = "更新指定实体的信息。只需提供要修改的字段，未提供的字段保持不变。"
    parameters = {
        "entity_id": {"type": "string", "description": "实体 ID"},
        "name": {"type": "string", "description": "新名称（可选）"},
        "entity_type": {"type": "string", "description": "新类型（可选）"},
        "attributes": {"type": "object", "description": "新属性（可选，会替换整个 attributes 对象）"},
        "stages": {"type": "array", "description": "新阶段列表（可选，会替换整个 stages）"},
    }

    def execute(self, world_id: str = "", entity_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id or not entity_id:
            return ToolCallResult(False, "缺少世界观 ID 或实体 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        target = None
        for i, e in enumerate(world.entities):
            if e.id == entity_id:
                target = (i, e)
                break
        if not target:
            return ToolCallResult(False, f"实体 {entity_id} 未找到。")
        idx, entity = target
        if "name" in kwargs and kwargs["name"] is not None:
            entity.name = kwargs["name"]
        if "entity_type" in kwargs and kwargs["entity_type"] is not None:
            entity.type = kwargs["entity_type"]
        if "attributes" in kwargs and kwargs["attributes"] is not None:
            entity.attributes = kwargs["attributes"]
        if "stages" in kwargs and kwargs["stages"] is not None:
            entity.stages = kwargs["stages"]
        synced_setting = _upsert_entity_setting(world, entity)
        WorldManager.save_world(world)
        return ToolCallResult(True,
            f"✅ 实体 '{entity.name}' 已更新，并已同步对应设定项。", data={"entity": entity.to_dict(), "setting": synced_setting})


class DeleteEntityTool(BaseTool):
    name = "delete_entity"
    description = "从世界观中删除指定实体。此操作不可撤销。"
    parameters = {
        "entity_id": {"type": "string", "description": "要删除的实体 ID"}
    }

    def execute(self, world_id: str = "", entity_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id or not entity_id:
            return ToolCallResult(False, "缺少世界观 ID 或实体 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        removed_entity = None
        removed_name = None
        new_entities = []
        for e in world.entities:
            if e.id == entity_id:
                removed_entity = e
                removed_name = e.name
            else:
                new_entities.append(e)
        if removed_name is None:
            return ToolCallResult(False, f"实体 {entity_id} 未找到。")
        removed_setting = _delete_entity_setting(world, removed_entity)
        world.entities = new_entities
        WorldManager.save_world(world)
        setting_text = "并已同步删除对应设定项" if removed_setting else "未找到对应设定项，无需删除"
        return ToolCallResult(True, f"✅ 实体 '{removed_name}' 已删除，{setting_text}。", data={"entity_id": entity_id, "removed_setting": removed_setting})


class AddEventTool(BaseTool):
    name = "add_event"
    description = "向世界观添加一个新事件。"
    parameters = {
        "name": {"type": "string", "description": "事件名称"},
        "description": {"type": "string", "description": "事件描述"},
        "date": {"type": "string", "description": "事件日期/时间"},
        "time_type": {"type": "string", "description": "时间类型: point/period/unknown（默认 unknown）"},
        "related_entity_ids": {"type": "array", "description": "关联的实体 ID 列表（可选）"},
    }

    def execute(self, world_id: str = "", name: str = "", description: str = "",
                date: str = "", time_type: str = "unknown",
                related_entity_ids: list = None, **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        if not name:
            return ToolCallResult(False, "事件名称不能为空。")
        try:
            event = WorldManager.add_event(
                world_id=world_id, name=name, description=description,
                date=date, entities=related_entity_ids or [],
            )
            # 尝试更新 time_type
            world = WorldManager.get_world(world_id)
            if world:
                for ev in world.events:
                    if ev.id == event.id:
                        ev.time_type = time_type
                        WorldManager.save_world(world)
                        break
            return ToolCallResult(True,
                f"✅ 事件 '{name}' 已成功添加，ID: {event.id}", data=event.to_dict())
        except Exception as e:
            return ToolCallResult(False, f"添加事件失败: {str(e)}")


class UpdateEventTool(BaseTool):
    name = "update_event"
    description = "更新指定事件的信息。"
    parameters = {
        "event_id": {"type": "string", "description": "事件 ID"},
        "name": {"type": "string", "description": "新名称（可选）"},
        "description": {"type": "string", "description": "新描述（可选）"},
        "date": {"type": "string", "description": "新日期（可选）"},
    }

    def execute(self, world_id: str = "", event_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id or not event_id:
            return ToolCallResult(False, "缺少世界观 ID 或事件 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        for ev in world.events:
            if ev.id == event_id:
                if "name" in kwargs and kwargs["name"] is not None:
                    ev.name = kwargs["name"]
                if "description" in kwargs and kwargs["description"] is not None:
                    ev.description = kwargs["description"]
                if "date" in kwargs and kwargs["date"] is not None:
                    ev.date = kwargs["date"]
                WorldManager.save_world(world)
                return ToolCallResult(True, f"✅ 事件 '{ev.name}' 已更新。", data=ev.to_dict())
        return ToolCallResult(False, f"事件 {event_id} 未找到。")


class DeleteEventTool(BaseTool):
    name = "delete_event"
    description = "从世界观中删除指定事件。此操作不可撤销。"
    parameters = {
        "event_id": {"type": "string", "description": "要删除的事件 ID"}
    }

    def execute(self, world_id: str = "", event_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id or not event_id:
            return ToolCallResult(False, "缺少世界观 ID 或事件 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        removed_name = None
        new_events = []
        for ev in world.events:
            if ev.id == event_id:
                removed_name = ev.name
            else:
                new_events.append(ev)
        if removed_name is None:
            return ToolCallResult(False, f"事件 {event_id} 未找到。")
        world.events = new_events
        WorldManager.save_world(world)
        return ToolCallResult(True, f"✅ 事件 '{removed_name}' 已被删除。")


class UpdateWorldMetaTool(BaseTool):
    name = "update_world_meta"
    description = "更新世界观的基础信息（名称、描述、时代背景、锚定时间等）。"
    parameters = {
        "name": {"type": "string", "description": "世界观名称（可选）"},
        "description": {"type": "string", "description": "世界观描述（可选）"},
        "era": {"type": "string", "description": "时代背景（可选）"},
        "anchor_time": {"type": "string", "description": "锚定时间（可选）"},
    }

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        update_data = {k: v for k, v in kwargs.items() if v is not None and k in
                       ("name", "description", "era", "anchor_time")}
        if not update_data:
            return ToolCallResult(False, "没有提供要更新的字段。")
        world = WorldManager.update_world(world_id, update_data)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")
        return ToolCallResult(True,
            f"✅ 世界观已更新，修改的字段: {', '.join(update_data.keys())}",
            data=world.to_dict())


class ListCalendarsTool(BaseTool):
    name = "list_calendars"
    description = "列出世界观时间线栏目中的历法条目，可按纪元/纪年类型或关键字过滤。"
    parameters = {
        "timeline_type": {"type": "string", "description": "可选：按类型过滤，如 纪元/纪年"},
        "keyword": {"type": "string", "description": "可选：按名称、时间范围或描述关键字过滤"},
        "limit": {"type": "integer", "description": "返回条数上限（默认 50，最大 100）"},
    }

    def execute(self, world_id: str = "", timeline_type: str = "", keyword: str = "", limit: int = 50, **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")

        calendars = TIMELINE_MANAGER.list_calendars(
            world,
            calendar_type=timeline_type,
            keyword=keyword,
            limit=limit,
        )
        data = [
            {
                "id": calendar.get("id"),
                "name": calendar.get("name"),
                "type": calendar.get("type"),
                "baseTime": calendar.get("baseTime"),
                "timeRange": calendar.get("timeRange"),
                "unit": calendar.get("unit"),
                "ratio": calendar.get("ratio"),
                "calendarType": calendar.get("calendarType"),
                "description": calendar.get("description"),
            }
            for calendar in calendars
        ]
        meta = f"共 {len(data)} 条历法条目"
        if timeline_type:
            meta += f"（类型: {timeline_type}）"
        if keyword:
            meta += f"，关键字: {keyword}"
        return ToolCallResult(True, meta + "\n" + json.dumps(data, ensure_ascii=False, indent=2), data=data)


class GetCalendarDetailTool(BaseTool):
    name = "get_calendar_detail"
    description = "获取指定历法的完整详情。优先按 ID 查找，也可按名称查找。"
    parameters = {
        "calendar_id": {"type": "string", "description": "历法 ID（优先）"},
        "calendar_name": {"type": "string", "description": "历法名称（可选）"},
    }

    def execute(self, world_id: str = "", calendar_id: str = "", calendar_name: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")

        matches = TIMELINE_MANAGER.find_calendar_matches(world, calendar_id=calendar_id, calendar_name=calendar_name)
        if not matches:
            return ToolCallResult(False, f"历法 {calendar_id or calendar_name} 未找到。")
        if len(matches) > 1:
            options = [{"id": calendar.get("id"), "name": calendar.get("name"), "type": calendar.get("type")} for _, calendar in matches]
            return ToolCallResult(
                False,
                "匹配到多个同名历法，请使用 calendar_id 精确指定。",
                data=options,
            )

        _, calendar = matches[0]
        normalized = TIMELINE_MANAGER._normalize_calendar(calendar)
        return ToolCallResult(True, json.dumps(normalized, ensure_ascii=False, indent=2), data=normalized)


class CreateCalendarTool(BaseTool):
    name = "create_calendar"
    description = "向世界观时间线栏目新增一个历法条目（纪元/纪年）。"
    parameters = {
        "name": {"type": "string", "description": "历法名称"},
        "timeline_type": {"type": "string", "description": "历法类型：纪元/纪年"},
        "base_time": {"type": "string", "description": "基准时间/开始时间（可选）"},
        "end_time": {"type": "string", "description": "结束时间（可选）"},
        "time_range": {"type": "string", "description": "完整时间范围（可选）"},
        "unit": {"type": "string", "description": "时间单位（默认 年）"},
        "ratio": {"type": "string", "description": "时间比例，如 ×1、×12"},
        "calendar_system": {"type": "string", "description": "自定义历法系统/规则名称（对应 calendarType）"},
        "no_end_time": {"type": "boolean", "description": "是否没有结束时间"},
        "description": {"type": "string", "description": "历法描述"},
    }

    def execute(self, world_id: str = "", name: str = "", timeline_type: str = "纪元",
                base_time: str = "", end_time: str = "", time_range: str = "",
                unit: str = "年", ratio: str = "×1", calendar_system: str = "未开启",
                no_end_time: bool = False, description: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        if not name:
            return ToolCallResult(False, "历法名称不能为空。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")

        calendar_data = {
            "name": name,
            "type": timeline_type or "纪元",
            "baseTime": base_time,
            "timeRange": time_range,
            "endYear": end_time,
            "noEndTime": no_end_time,
            "unit": unit or "年",
            "ratio": ratio or "×1",
            "calendarType": calendar_system or "未开启",
            "description": description or "",
        }
        created = TIMELINE_MANAGER.create_calendar(world, calendar_data)
        WorldManager.save_world(world)
        return ToolCallResult(True, f"✅ 历法 '{created.get('name')}' 已创建，ID: {created.get('id')}", data=created)


class UpdateCalendarTool(BaseTool):
    name = "update_calendar"
    description = "更新指定历法的字段。修改、纠错、重命名都应优先使用此工具，不要通过 delete_calendar + create_calendar 代替更新。updates 里只放要修改的字段即可。"
    parameters = {
        "calendar_id": {"type": "string", "description": "历法 ID（优先）"},
        "calendar_name": {"type": "string", "description": "历法名称（可选）"},
        "updates": {"type": "object", "description": "要修改的字段对象，可包含 name、timeline_type、base_time、end_time、time_range、unit、ratio、calendar_system、description、no_end_time。"},
    }

    def execute(self, world_id: str = "", calendar_id: str = "", calendar_name: str = "", updates: dict = None, **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")

        if not isinstance(updates, dict) or not updates:
            return ToolCallResult(False, "请提供要修改的字段对象 updates。")

        try:
            updated = TIMELINE_MANAGER.update_calendar(
                world,
                calendar_id=calendar_id,
                calendar_name=calendar_name,
                updates=updates,
            )
        except ValueError as e:
            return ToolCallResult(False, str(e))

        if not updated:
            return ToolCallResult(False, f"历法 {calendar_id or calendar_name} 未找到。")

        WorldManager.save_world(world)
        return ToolCallResult(True, f"✅ 历法 '{updated.get('name')}' 已更新。", data=updated)


class DeleteCalendarTool(BaseTool):
    name = "delete_calendar"
    description = "仅当用户明确要求删除历法时才可使用。修改、纠错、重命名、去重优先使用 update_calendar，不要用删旧建新代替更新。此操作不可撤销。"
    parameters = {
        "calendar_id": {"type": "string", "description": "历法 ID（优先）"},
        "calendar_name": {"type": "string", "description": "历法名称（可选）"},
    }

    def execute(self, world_id: str = "", calendar_id: str = "", calendar_name: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")

        try:
            removed = TIMELINE_MANAGER.delete_calendar(world, calendar_id=calendar_id, calendar_name=calendar_name)
        except ValueError as e:
            return ToolCallResult(False, str(e))

        if not removed:
            return ToolCallResult(False, f"历法 {calendar_id or calendar_name} 未找到。")

        WorldManager.save_world(world)
        return ToolCallResult(True, f"✅ 历法 '{removed.get('name')}' 已删除。", data=removed)


# ============================================================
# Agent 自身管理类 Tools
# ============================================================

class ReadAgentMdTool(BaseTool):
    name = "read_agent_md"
    description = "读取当前世界观的 Agent.md 文件内容。Agent.md 包含用户对 Agent 行为的自定义指令。"
    parameters = {}

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        content = AgentManager.get_agent_md(world_id)
        if not content:
            return ToolCallResult(True, "当前没有 Agent.md 内容（空白）。")
        return ToolCallResult(True, content)


class WriteAgentMdTool(BaseTool):
    name = "write_agent_md"
    description = "写入/更新当前世界观的 Agent.md 文件。用于保存用户对 Agent 行为的自定义指令。"
    parameters = {
        "content": {"type": "string", "description": "Agent.md 文件内容"}
    }

    def execute(self, world_id: str = "", content: str = "", **kwargs) -> ToolCallResult:
        if not content:
            return ToolCallResult(False, "内容不能为空。")
        AgentManager.save_agent_md(content, world_id)
        return ToolCallResult(True, f"✅ Agent.md 已保存（{len(content)} 字符）。")


class ListSkillsTool(BaseTool):
    name = "list_skills"
    description = "列出所有可用的 Agent Skills。"
    parameters = {}

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        skills = AgentManager.list_skills(world_id)
        data = [{
            "skill_id": s.skill_id, "name": s.name,
            "description": s.description, "world_id": s.world_id
        } for s in skills]
        return ToolCallResult(True, json.dumps(data, ensure_ascii=False, indent=2), data=data)


class ActivateSkillTool(BaseTool):
    name = "activate_skill"
    description = "激活指定的 Skill，获取其详细指令。"
    parameters = {
        "skill_id_or_name": {"type": "string", "description": "Skill ID 或名称"}
    }

    def execute(self, world_id: str = "", skill_id_or_name: str = "", **kwargs) -> ToolCallResult:
        skills = AgentManager.list_skills(world_id)
        target = None
        for s in skills:
            if s.skill_id == skill_id_or_name or s.name == skill_id_or_name:
                target = s
                break
        if not target:
            return ToolCallResult(False, f"Skill '{skill_id_or_name}' 未找到。")
        return ToolCallResult(True,
            f"# Skill: {target.name}\n\n{target.description}\n\n## 指令\n\n{target.instructions}")


class SetMemoryTool(BaseTool):
    name = "set_memory"
    description = "保存一条记忆（key-value 对），用于后续对话中参考。"
    parameters = {
        "key": {"type": "string", "description": "记忆键名"},
        "value": {"type": "string", "description": "记忆内容"}
    }

    def execute(self, world_id: str = "", key: str = "", value: str = "", **kwargs) -> ToolCallResult:
        if not key:
            return ToolCallResult(False, "记忆 key 不能为空。")
        AgentManager.set_memory(key, value, world_id)
        return ToolCallResult(True, f"✅ 记忆 '{key}' 已保存。")


class GetMemoryTool(BaseTool):
    name = "get_memory"
    description = "读取指定记忆内容。"
    parameters = {
        "key": {"type": "string", "description": "记忆键名"}
    }

    def execute(self, world_id: str = "", key: str = "", **kwargs) -> ToolCallResult:
        value = AgentManager.get_memory(key, world_id)
        if value is None:
            return ToolCallResult(True, f"记忆 '{key}' 不存在。")
        return ToolCallResult(True, str(value), data=value)


class ListMemoriesTool(BaseTool):
    name = "list_memories"
    description = "列出所有已保存的记忆键值。"
    parameters = {}

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        memories = AgentManager.get_memories(world_id)
        return ToolCallResult(True, json.dumps(memories, ensure_ascii=False, indent=2), data=memories)


# ============================================================
# 用户交互类 Tools
# ============================================================

class AskUserTool(BaseTool):
    name = "ask_user"
    description = "向用户提问，获取更多信息后再继续。用于需要用户输入明确信息的场景。"
    parameters = {
        "question": {"type": "string", "description": "向用户提出的问题"}
    }

    def execute(self, world_id: str = "", question: str = "", **kwargs) -> ToolCallResult:
        return ToolCallResult(True,
            f"🔔 需要用户回答: {question}",
            needs_user_response=True)


class PlanOptionsTool(BaseTool):
    name = "plan_options"
    description = """提供多个选项让用户选择来决定下一步行动。
选项可以是单选（multi_select=false）或多选（multi_select=true）。
当你有多个可选方案时，使用此工具让用户做出决定。"""
    parameters = {
        "question": {"type": "string", "description": "问题描述"},
        "options": {"type": "array", "description": "选项列表，每项包含 label 和 description"},
        "multi_select": {"type": "boolean", "description": "是否允许多选（默认 false）"}
    }

    def execute(self, world_id: str = "", question: str = "", options: list = None,
                multi_select: bool = False, **kwargs) -> ToolCallResult:
        options = options or []
        user_options = [{
            "label": str(o.get("label", o if isinstance(o, str) else "")),
            "description": str(o.get("description", "")),
        } for o in options]
        return ToolCallResult(True,
            f"🔔 请用户选择: {question}",
            needs_user_response=True,
            user_options={"question": question, "options": user_options, "multiSelect": multi_select})


class ListWorldsTool(BaseTool):
    name = "list_worlds"
    description = "列出所有可用的世界观，供用户选择。"
    parameters = {}

    def execute(self, world_id: str = "", **kwargs) -> ToolCallResult:
        worlds = WorldManager.list_worlds()
        data = [{
            "id": w.id, "name": w.name, "era": w.era,
            "entity_count": len(w.entities), "event_count": len(w.events)
        } for w in worlds]
        if not data:
            return ToolCallResult(True, "当前没有创建任何世界观。是否需要我帮你创建一个？")
        return ToolCallResult(True, json.dumps(data, ensure_ascii=False, indent=2), data=data)


class CreateWorldTool(BaseTool):
    name = "create_world"
    description = "创建一个新的世界观。"
    parameters = {
        "name": {"type": "string", "description": "世界观名称"},
        "description": {"type": "string", "description": "世界观描述（可选）"},
        "era": {"type": "string", "description": "时代背景（可选）"},
        "anchor_time": {"type": "string", "description": "锚定时间（可选）"},
    }

    def execute(self, world_id: str = "", name: str = "", description: str = "",
                era: str = "", anchor_time: str = "", **kwargs) -> ToolCallResult:
        if not name:
            return ToolCallResult(False, "世界观名称不能为空。")
        world = WorldManager.create_world(
            name=name, description=description, era=era, anchor_time=anchor_time)
        return ToolCallResult(True,
            f"✅ 世界观 '{name}' 已创建，ID: {world.id}", data=world.to_dict())


# ============================================================
# 设定管理类 Tools
# ============================================================

SETTING_CATEGORY_MAP = {
    "character": "角色", "item": "物品", "organization": "组织",
    "geography": "地理", "ability": "能力", "other": "其他",
    "角色": "character", "物品": "item", "组织": "organization",
    "地理": "geography", "能力": "ability", "其他": "other",
}


class CreateSettingCollectionTool(BaseTool):
    name = "create_setting_collection"
    description = """创建一个新的设定集（Setting Collection）。设定集是分类下的容器，可以包含多个具体的设定项。
例如：在"角色"分类下创建"主角团设定集"、"A组织角色设定集"等。
设定集本身也可以作为子设定集挂在另一个设定集下。"""
    parameters = {
        "name": {"type": "string", "description": "设定集名称，如：'主角团设定集'、'A组织角色'、'西大陆地理设定集'"},
        "category": {"type": "string", "description": "所属分类：character(角色)/item(物品)/organization(组织)/geography(地理)/ability(能力)/other(其他)，支持中英文"},
        "description": {"type": "string", "description": "设定集描述（可选）"},
        "parent_collection_id": {"type": "string", "description": "上级设定集 ID（可选，用于创建嵌套设定集）"},
        "aliases": {"type": "array", "description": "别名列表（可选），如 ['主角', '主角阵营']"},
    }

    def execute(self, world_id: str = "", name: str = "", category: str = "",
                description: str = "", parent_collection_id: str = "",
                aliases: list = None, **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID，请先选择世界观。")
        if not name:
            return ToolCallResult(False, "设定集名称不能为空。")
        if not category:
            return ToolCallResult(False, "请指定分类（如 角色/character、组织/organization 等）。")

        # 标准化分类名
        category = category.strip()
        if category in SETTING_CATEGORY_MAP:
            category = SETTING_CATEGORY_MAP[category]

        valid = {"character", "item", "organization", "geography", "ability", "other"}
        if category not in valid:
            return ToolCallResult(False,
                f"无效分类 '{category}'。有效值: character(角色), item(物品), organization(组织), geography(地理), ability(能力), other(其他)")

        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")

        # 验证 parent_collection_id 如果提供
        if parent_collection_id:
            items = world.settings.get("items", []) if isinstance(world.settings, dict) else []
            parent = next((it for it in items if isinstance(it, dict) and it.get("id") == parent_collection_id), None)
            if not parent:
                return ToolCallResult(False, f"上级设定集 {parent_collection_id} 不存在，请先创建或使用正确的 ID。")
            if parent.get("settingType") != "collection":
                return ToolCallResult(False, f"{parent_collection_id} 不是设定集（是'设定'），不能作为父容器。")

        try:
            # 初始化 settings
            if not isinstance(world.settings, dict):
                world.settings = {}
            items = world.settings.setdefault("items", [])

            new_collection = {
                "id": f"collection_{uuid.uuid4().hex[:12]}",
                "name": name,
                "settingType": "collection",
                "category": category,
                "collectionId": parent_collection_id or "",
                "description": description or "",
                "aliases": aliases or [],
                "detailContent": description or "",
                "showInList": True,
                "sourceType": "agent",
                "autoGenerated": True,
            }
            items.append(new_collection)

            WorldManager.save_world(world)

            return ToolCallResult(True,
                f"✅ 设定集 '{name}'（分类: {category}）创建成功！\nID: {new_collection['id']}" +
                (f"\n上级设定集: {parent_collection_id}" if parent_collection_id else ""),
                data=new_collection)
        except Exception as e:
            return ToolCallResult(False, f"创建设定集失败: {str(e)}")


class CreateSettingItemTool(BaseTool):
    name = "create_setting_item"
    description = """在某个设定集下创建一个具体的设定项（Setting Item）。设定项是世界观的最小设定单位。
例如：在"主角团设定集"下创建"张起灵"、"吴邪"等人物设定。"""
    parameters = {
        "name": {"type": "string", "description": "设定项名称"},
        "collection_id": {"type": "string", "description": "所属设定集 ID（必需，设定项必须属于某个设定集）"},
        "description": {"type": "string", "description": "设定描述（可选）"},
        "detail_content": {"type": "string", "description": "详细内容（可选）"},
        "aliases": {"type": "array", "description": "别名列表（可选）"},
        "category": {"type": "string", "description": "分类（可选，默认从设定集继承）"},
    }

    def execute(self, world_id: str = "", name: str = "", collection_id: str = "",
                description: str = "", detail_content: str = "",
                aliases: list = None, category: str = "", **kwargs) -> ToolCallResult:
        if not world_id:
            return ToolCallResult(False, "未指定世界观 ID。")
        if not name:
            return ToolCallResult(False, "设定项名称不能为空。")
        if not collection_id:
            return ToolCallResult(False, "请指定所属设定集 ID（collection_id）。设定项必须属于某个设定集。")

        world = WorldManager.get_world(world_id)
        if not world:
            return ToolCallResult(False, f"世界观 {world_id} 不存在。")

        items = world.settings.get("items", []) if isinstance(world.settings, dict) else []
        collection = next((it for it in items if isinstance(it, dict) and it.get("id") == collection_id), None)
        if not collection:
            return ToolCallResult(False, f"设定集 {collection_id} 不存在。请先使用 create_setting_collection 创建设定集。")
        if collection.get("settingType") != "collection":
            return ToolCallResult(False, f"{collection_id} 不是设定集（是设定项），不能添加子设定。")

        if not category:
            category = collection.get("category", "other")

        try:
            if not isinstance(world.settings, dict):
                world.settings = {}
            items = world.settings.setdefault("items", [])

            new_item = {
                "id": f"setting_{uuid.uuid4().hex[:12]}",
                "name": name,
                "settingType": "setting",
                "category": category,
                "collectionId": collection_id,
                "description": description or "",
                "aliases": aliases or [],
                "detailContent": detail_content or description or "",
                "showInList": True,
                "sourceType": "agent",
                "autoGenerated": True,
            }
            items.append(new_item)

            WorldManager.save_world(world)

            return ToolCallResult(True,
                f"✅ 设定项 '{name}' 创建成功！\nID: {new_item['id']}\n所属设定集: {collection.get('name', collection_id)}",
                data=new_item)
        except Exception as e:
            return ToolCallResult(False, f"创建设定项失败: {str(e)}")


class SubAgentTool(BaseTool):
    name = "sub_agent"
    description = """委派一个子 Agent 处理复杂任务。子 Agent 独立运行并返回结果。
适用场景：需要并行处理多个实体生成、批量数据分析等。"""
    parameters = {
        "task": {"type": "string", "description": "委派给子 Agent 的任务描述"},
        "sub_agent_type": {"type": "string", "description": "子 Agent 类型: researcher/writer/analyzer"},
        "max_steps": {"type": "integer", "description": "子 Agent 最大执行步数（默认 5）"}
    }

    def execute(self, world_id: str = "", task: str = "", sub_agent_type: str = "researcher",
                max_steps: int = 5, **kwargs) -> ToolCallResult:
        if not task:
            return ToolCallResult(False, "委派任务描述不能为空。")
        # 子 Agent 使用独立的 LLM 调用执行任务
        try:
            llm = LLMClient()
            system_prompt = f"""你是一个子 Agent，类型为 {sub_agent_type}。
当前世界观 ID: {world_id}
你的任务是: {task}
请独立完成此任务并返回结果。最多执行 {max_steps} 步。"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请完成以下任务并直接返回结果:\n{task}"}
            ]
            result = llm.chat(messages, temperature=0.5, max_tokens=2048)
            return ToolCallResult(True,
                f"🤖 子 Agent [{sub_agent_type}] 返回结果:\n\n{result}")
        except Exception as e:
            return ToolCallResult(False, f"子 Agent 执行失败: {str(e)}")


# ============================================================
# 工具注册表
# ============================================================

ALL_TOOLS: List[BaseTool] = [
    # 读取类
    ReadWorldTool(),
    ListEntitiesTool(),
    GetEntityDetailTool(),
    ListEventsTool(),
    GetEventDetailTool(),
    ReadSettingsTool(),
    ListMapsTool(),
    ReadMapTool(),
    SearchMapCellsTool(),
    GetMapCellDetailTool(),
    SearchKnowledgeTool(),
    GetRagStatsTool(),
    ListRagDocsTool(),
    # 修改类
    AddEntityTool(),
    UpdateEntityTool(),
    DeleteEntityTool(),
    AddEventTool(),
    UpdateEventTool(),
    DeleteEventTool(),
    UpdateWorldMetaTool(),
    UpdateMapCellTool(),
    BatchUpdateMapCellsTool(),
    ListCalendarsTool(),
    GetCalendarDetailTool(),
    CreateCalendarTool(),
    UpdateCalendarTool(),
    DeleteCalendarTool(),
    # 设定管理
    CreateSettingCollectionTool(),
    CreateSettingItemTool(),
    # Agent 自身
    ReadAgentMdTool(),
    WriteAgentMdTool(),
    ListSkillsTool(),
    ActivateSkillTool(),
    SetMemoryTool(),
    GetMemoryTool(),
    ListMemoriesTool(),
    # 用户交互
    AskUserTool(),
    PlanOptionsTool(),
    ListWorldsTool(),
    CreateWorldTool(),
    # 子 Agent
    SubAgentTool(),
]


def get_tool_by_name(name: str) -> Optional[BaseTool]:
    for t in ALL_TOOLS:
        if t.name == name:
            return t
    return None


def get_all_tool_schemas_openai() -> List[Dict[str, Any]]:
    return [t.to_openai_schema() for t in ALL_TOOLS]


def get_all_tool_schemas_mcp() -> List[Dict[str, Any]]:
    return [t.to_mcp_schema() for t in ALL_TOOLS]
