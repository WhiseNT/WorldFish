"""
知识图谱服务
基于邻接表 + 倒排索引的高性能图模型，零外部依赖。

数据模型：
  节点 (Node)   — 一个可行动/可发声的实体（人物、组织、地点等）
  边   (Edge)   — 两个节点之间的关系，携带 fact 语义描述

存储格式 (.graph.json)：
  {
    "meta":      {graph_id, name, created_at},
    "ontology":  {},
    "node_index": {uuid → node_dict},
    "type_index": {type_name → [uuid, ...]},
    "name_index": {name_lower → [uuid, ...]},
    "adj_out":   {uuid → [{target, edge_data}, ...]},
    "adj_in":    {uuid → [{source, edge_data}, ...]},
    "edge_index": {uuid → edge_dict}
  }

对外兼容旧格式：get_graph_data() 展开索引为 {nodes[], edges[]}。
"""

import json
import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('worldfish.knowledge_graph')


# ════════════════════════════════════════════════════════
#  数据结构（对外不变）
# ════════════════════════════════════════════════════════

@dataclass
class EntityNode:
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> Optional[str]:
        for label in self.labels:
            if label not in ("Entity", "Node"):
                return label
        return None


@dataclass
class FilteredEntities:
    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


# ════════════════════════════════════════════════════════
#  索引核心函数
# ════════════════════════════════════════════════════════

def _build_indexes(graph: Dict[str, Any]) -> None:
    """从 raw nodes/edges 批量构建全套哈希索引。"""
    nodes: List[Dict[str, Any]] = graph.get("nodes", [])
    edges: List[Dict[str, Any]] = graph.get("edges", [])

    node_index: Dict[str, Dict[str, Any]] = {}
    type_index: Dict[str, List[str]] = {}
    name_index: Dict[str, List[str]] = {}
    adj_out: Dict[str, List[Dict[str, Any]]] = {}
    adj_in: Dict[str, List[Dict[str, Any]]] = {}
    edge_index: Dict[str, Dict[str, Any]] = {}

    for node in nodes:
        uid = node["uuid"]
        node_index[uid] = node
        for label in (node.get("labels") or []):
            type_index.setdefault(label, []).append(uid)
        name = (node.get("name") or "").strip().lower()
        if name:
            name_index.setdefault(name, []).append(uid)

    for edge in edges:
        eid = edge["uuid"]
        edge_index[eid] = edge
        src = edge.get("source_node_uuid", "")
        tgt = edge.get("target_node_uuid", "")
        if src:
            adj_out.setdefault(src, []).append({"target": tgt, "edge_data": edge})
        if tgt:
            adj_in.setdefault(tgt, []).append({"source": src, "edge_data": edge})

    graph["node_index"] = node_index
    graph["type_index"] = type_index
    graph["name_index"] = name_index
    graph["adj_out"] = adj_out
    graph["adj_in"] = adj_in
    graph["edge_index"] = edge_index


def _node_dict_to_entity(node: Dict[str, Any]) -> EntityNode:
    return EntityNode(
        uuid=node["uuid"],
        name=node.get("name", ""),
        labels=node.get("labels", []),
        summary=node.get("summary", ""),
        attributes=node.get("attributes", {}),
    )


# ════════════════════════════════════════════════════════
#  KnowledgeGraph — 图谱构建与持久化
# ════════════════════════════════════════════════════════

class KnowledgeGraph:
    """本地图谱构建器 — 邻接表 + 倒排索引模型。"""

    def __init__(self):
        self.graphs_dir = os.path.join(Config.UPLOAD_FOLDER, "graphs")
        os.makedirs(self.graphs_dir, exist_ok=True)

    # ── 公开 API ──

    def create_graph(self, name: str) -> str:
        gid = f"local_{uuid.uuid4().hex[:16]}"
        graph = {
            "meta": {"graph_id": gid, "name": name, "created_at": time.time()},
            "ontology": {},
            "nodes": [],
            "edges": [],
            "node_index": {},
            "type_index": {},
            "name_index": {},
            "adj_out": {},
            "adj_in": {},
            "edge_index": {},
        }
        self._save(gid, graph)
        return gid

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        graph = self._load(graph_id)
        graph["ontology"] = ontology
        self._save(graph_id, graph)

    def add_text_batches(
        self,
        graph_id: str,
        world_data: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> List[str]:
        graph = self._load(graph_id)
        nodes: List[Dict[str, Any]] = list(graph["nodes"])
        edges: List[Dict[str, Any]] = list(graph["edges"])
        uid_set: Set[str] = {n["uuid"] for n in nodes}
        edge_counter = max(
            (int((e.get("uuid") or "edge_0").split("_")[-1]) for e in edges if e.get("uuid", "").startswith("edge_")),
            default=-1,
        ) + 1

        if progress_callback:
            progress_callback("收集实体节点...", 0.1)

        # 1. entities → 节点
        for entity in (world_data.get("entities") or []):
            nid = entity.get("id") or f"ent_{uuid.uuid4().hex[:12]}"
            if nid in uid_set:
                continue
            uid_set.add(nid)
            nodes.append(_entity_to_node(entity))

        if progress_callback:
            progress_callback(f"{len(nodes)} 个实体节点", 0.3)

        # 2. settings → 节点
        for item in (world_data.get("settings") or {}).get("items") or []:
            if not isinstance(item, dict):
                continue
            nid = item.get("id") or f"set_{uuid.uuid4().hex[:12]}"
            if nid in uid_set:
                continue
            uid_set.add(nid)
            nodes.append(_setting_to_node(item))

        if progress_callback:
            progress_callback(f"{len(nodes)} 个节点（含设定）", 0.5)

        # 3. events → 边
        name_to_id = {n["name"]: n["uuid"] for n in nodes if n.get("name")}
        for event in (world_data.get("events") or []):
            event_entities = event.get("entities") or []
            if len(event_entities) < 2:
                continue
            for i, name_a in enumerate(event_entities):
                id_a = name_to_id.get(name_a)
                if not id_a:
                    continue
                for name_b in event_entities[i + 1:]:
                    id_b = name_to_id.get(name_b)
                    if not id_b:
                        continue
                    eid = f"edge_{edge_counter}"
                    edge_counter += 1
                    edges.append(_event_to_edge(eid, id_a, id_b, event))

        if progress_callback:
            progress_callback(f"{len(edges)} 条关系边", 0.7)

        # 4. mapData → 地点节点 + 边
        _add_location_nodes(nodes, edges, world_data, name_to_id, edge_counter)

        if progress_callback:
            progress_callback(f"重建索引...", 0.85)

        graph["nodes"] = nodes
        graph["edges"] = edges
        _build_indexes(graph)

        if progress_callback:
            progress_callback(f"图谱完成: {len(nodes)} 节点, {len(edges)} 边", 0.95)

        self._save(graph_id, graph)
        return []

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        graph = self._load(graph_id)
        return {
            "graph_id": graph_id,
            "nodes": graph.get("nodes", []),
            "edges": graph.get("edges", []),
            "node_count": len(graph.get("nodes", [])),
            "edge_count": len(graph.get("edges", [])),
        }

    def delete_graph(self, graph_id: str):
        path = self._path(graph_id)
        if os.path.exists(path):
            os.remove(path)

    # ── 内部 ──

    def _path(self, graph_id: str) -> str:
        return os.path.join(self.graphs_dir, f"{graph_id}.graph.json")

    def _load(self, graph_id: str) -> Dict[str, Any]:
        path = self._path(graph_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                graph = json.load(f)
            # 自动补充缺失的索引（兼容旧格式或无索引图）
            if "node_index" not in graph:
                _build_indexes(graph)
            return graph
        return {
            "meta": {"graph_id": graph_id},
            "nodes": [],
            "edges": [],
            "ontology": {},
            "node_index": {},
            "type_index": {},
            "name_index": {},
            "adj_out": {},
            "adj_in": {},
            "edge_index": {},
        }

    def _save(self, graph_id: str, graph: Dict[str, Any]):
        with open(self._path(graph_id), "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════
#  KnowledgeGraphReader — 索引化实体查询
# ════════════════════════════════════════════════════════

class KnowledgeGraphReader:
    """基于倒排索引的图谱实体查询服务。"""

    def __init__(self):
        self._graphs_dir = os.path.join(Config.UPLOAD_FOLDER, "graphs")

    def _load(self, graph_id: str) -> Dict[str, Any]:
        # 尝试 .graph.json 优先，回退 .json
        for suffix in (".graph.json", ".json"):
            path = os.path.join(self._graphs_dir, f"{graph_id}{suffix}")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    graph = json.load(f)
                if "node_index" not in graph:
                    _build_indexes(graph)
                return graph
        raise FileNotFoundError(f"Graph not found: {graph_id}")

    # ── 批量读取 ──

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        graph = self._load(graph_id)
        return list(graph.get("node_index", {}).values())

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        graph = self._load(graph_id)
        return list(graph.get("edge_index", {}).values())

    # ── 索引化过滤 ──

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> FilteredEntities:
        graph = self._load(graph_id)
        node_index: Dict[str, Any] = graph["node_index"]
        type_index: Dict[str, List[str]] = graph.get("type_index", {})
        adj_out: Dict[str, List[Dict[str, Any]]] = graph.get("adj_out", {})
        adj_in: Dict[str, List[Dict[str, Any]]] = graph.get("adj_in", {})

        total_count = len(node_index)
        entity_types_found: Set[str] = set()

        # 用 type_index 直接定位候选节点，不再扫描全部
        candidate_uuids: Set[str] = set()
        if defined_entity_types:
            for t in defined_entity_types:
                candidate_uuids.update(type_index.get(t, []))
        else:
            candidate_uuids = set(node_index.keys())

        filtered: List[EntityNode] = []
        for uid in candidate_uuids:
            node = node_index.get(uid)
            if not node:
                continue
            labels = node.get("labels", [])
            custom = [l for l in labels if l not in ("Entity", "Node")]
            if not custom:
                continue
            entity_type = custom[0]
            entity_types_found.add(entity_type)

            entity = _node_dict_to_entity(node)
            if enrich_with_edges:
                entity.related_edges = _build_related_edges(uid, adj_out, adj_in)
                entity.related_nodes = _build_related_nodes(
                    uid, adj_out, adj_in, node_index
                )
            filtered.append(entity)

        logger.info(
            f"Filtered: {total_count} total → {len(filtered)} entities, "
            f"types: {entity_types_found}"
        )
        return FilteredEntities(
            entities=filtered,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered),
        )

    def get_entity_with_context(self, graph_id: str, entity_uuid: str) -> Optional[EntityNode]:
        try:
            graph = self._load(graph_id)
            node = graph.get("node_index", {}).get(entity_uuid)
            if not node:
                return None
            adj_out: Dict[str, List[Dict]] = graph.get("adj_out", {})
            adj_in: Dict[str, List[Dict]] = graph.get("adj_in", {})
            node_index: Dict[str, Any] = graph["node_index"]

            entity = _node_dict_to_entity(node)
            entity.related_edges = _build_related_edges(entity_uuid, adj_out, adj_in)
            entity.related_nodes = _build_related_nodes(
                entity_uuid, adj_out, adj_in, node_index
            )
            return entity
        except Exception as e:
            logger.error(f"Failed to get entity {entity_uuid}: {e}")
            return None

    def get_entities_by_type(
        self, graph_id: str, entity_type: str, enrich_with_edges: bool = True
    ) -> List[EntityNode]:
        return self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges,
        ).entities


# ════════════════════════════════════════════════════════
#  辅助函数
# ════════════════════════════════════════════════════════

def _build_related_edges(
    uid: str,
    adj_out: Dict[str, List[Dict[str, Any]]],
    adj_in: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    related: List[Dict[str, Any]] = []
    for entry in adj_out.get(uid, []):
        related.append({
            "direction": "outgoing",
            "edge_name": entry["edge_data"].get("name", ""),
            "fact": entry["edge_data"].get("fact", ""),
            "target_node_uuid": entry["target"],
        })
    for entry in adj_in.get(uid, []):
        related.append({
            "direction": "incoming",
            "edge_name": entry["edge_data"].get("name", ""),
            "fact": entry["edge_data"].get("fact", ""),
            "source_node_uuid": entry["source"],
        })
    return related


def _build_related_nodes(
    uid: str,
    adj_out: Dict[str, List[Dict[str, Any]]],
    adj_in: Dict[str, List[Dict[str, Any]]],
    node_index: Dict[str, Any],
) -> List[Dict[str, Any]]:
    linked: Set[str] = set()
    for entry in adj_out.get(uid, []):
        linked.add(entry["target"])
    for entry in adj_in.get(uid, []):
        linked.add(entry["source"])
    result: List[Dict[str, Any]] = []
    for linked_uid in linked:
        neighbor = node_index.get(linked_uid)
        if neighbor:
            result.append({
                "uuid": linked_uid,
                "name": neighbor.get("name", ""),
                "labels": neighbor.get("labels", []),
                "summary": neighbor.get("summary", ""),
            })
    return result


def _entity_to_node(entity: Dict[str, Any]) -> Dict[str, Any]:
    attr_parts = [
        f"{k}: {v}"
        for k, v in (entity.get("attributes") or {}).items()
        if v is not None
    ]
    return {
        "uuid": entity.get("id") or f"ent_{uuid.uuid4().hex[:12]}",
        "name": entity.get("name", ""),
        "labels": [entity.get("type", "Entity")],
        "summary": "; ".join(attr_parts) if attr_parts else entity.get("name", ""),
        "attributes": entity.get("attributes") or {},
        "created_at": entity.get("created_at") or time.time(),
    }


def _setting_to_node(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "uuid": item.get("id") or f"set_{uuid.uuid4().hex[:12]}",
        "name": item.get("name", ""),
        "labels": [item.get("category", "Setting"), "Setting"],
        "summary": item.get("description") or item.get("detailContent") or "",
        "attributes": {
            "category": item.get("category", ""),
            "aliases": item.get("aliases") or [],
        },
        "created_at": time.time(),
    }


def _event_to_edge(
    eid: str, id_a: str, id_b: str, event: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "uuid": eid,
        "name": "RELATED_TO",
        "fact": f"共同参与事件「{event.get('name', '')}」: {event.get('description', '')[:200]}",
        "fact_type": "RELATED_TO",
        "source_node_uuid": id_a,
        "target_node_uuid": id_b,
        "attributes": {
            "event": event.get("name", ""),
            "date": event.get("date", ""),
        },
        "created_at": time.time(),
        "valid_at": event.get("date", ""),
    }


def _add_location_nodes(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    world_data: Dict[str, Any],
    name_to_id: Dict[str, str],
    edge_counter: int,
) -> None:
    map_data = (world_data.get("settings") or {}).get("mapData") or {}
    for field, relation_type in [
        ("regionRelations", "REGION_RELATION"),
        ("countryRelations", "COUNTRY_RELATION"),
        ("importantLocations", "LOCATED_AT"),
    ]:
        text = map_data.get(field, "")
        if not text:
            continue
        lines = text.split("\n") if isinstance(text, str) else text
        for line in lines:
            line = str(line).strip()
            if not line or len(line) < 5:
                continue
            loc_id = f"loc_{uuid.uuid4().hex[:8]}"
            nodes.append({
                "uuid": loc_id,
                "name": line[:100],
                "labels": ["Location"],
                "summary": line,
                "attributes": {},
                "created_at": time.time(),
            })
            # 绑定到名称匹配的已有节点
            for node in nodes:
                node_name = node.get("name", "")
                if node_name and len(node_name) > 1 and node_name in line:
                    edges.append({
                        "uuid": f"edge_{edge_counter}",
                        "name": relation_type,
                        "fact": line[:200],
                        "fact_type": relation_type,
                        "source_node_uuid": node["uuid"],
                        "target_node_uuid": loc_id,
                        "attributes": {},
                        "created_at": time.time(),
                    })
                    edge_counter += 1
                    break


# ════════════════════════════════════════════════════════
#  兼容别名 — 外部调用方无需改动
# ════════════════════════════════════════════════════════

LocalGraphBuilder = KnowledgeGraph
GraphEntityReader = KnowledgeGraphReader
ZepEntityReader = KnowledgeGraphReader
