"""
实体读取与过滤服务
支持 Zep 云端图谱和本地 JSON 图谱两种后端
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Set, Callable, TypeVar
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('worldfish.entity_reader')

T = TypeVar('T')


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
            if label not in ["Entity", "Node"]:
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


class ZepEntityReader:
    """实体读取与过滤服务 — 自动检测 Zep / 本地图谱后端"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.ZEP_API_KEY
        self._client = None
        self._local_graphs_dir = os.path.join(Config.UPLOAD_FOLDER, "graphs")

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("ZEP_API_KEY 未配置")
            from zep_cloud.client import Zep
            self._client = Zep(api_key=self.api_key)
        return self._client

    @staticmethod
    def _is_local_graph(graph_id: str) -> bool:
        return bool(graph_id and graph_id.startswith("local_"))

    def _load_local_graph(self, graph_id: str) -> Dict[str, Any]:
        path = os.path.join(self._local_graphs_dir, f"{graph_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Local graph not found: {graph_id}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _call_with_retry(
        self, func: Callable[[], T], operation_name: str,
        max_retries: int = 3, initial_delay: float = 2.0
    ) -> T:
        last_exception = None
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(f"Zep {operation_name} attempt {attempt + 1} failed: {str(e)[:100]}, retry in {delay:.1f}s")
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"Zep {operation_name} failed after {max_retries} attempts: {str(e)}")
        raise last_exception

    # ---- Node / Edge getters (local + Zep) ----

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info(f"Getting all nodes for graph {graph_id}...")
        if self._is_local_graph(graph_id):
            graph = self._load_local_graph(graph_id)
            return graph.get("nodes", [])

        from ..utils.zep_paging import fetch_all_nodes
        nodes = fetch_all_nodes(self.client, graph_id)
        result = []
        for node in nodes:
            result.append({
                "uuid": getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                "name": node.name or "",
                "labels": node.labels or [],
                "summary": node.summary or "",
                "attributes": node.attributes or {},
            })
        logger.info(f"Got {len(result)} nodes")
        return result

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info(f"Getting all edges for graph {graph_id}...")
        if self._is_local_graph(graph_id):
            graph = self._load_local_graph(graph_id)
            return graph.get("edges", [])

        from ..utils.zep_paging import fetch_all_edges
        edges = fetch_all_edges(self.client, graph_id)
        result = []
        for edge in edges:
            result.append({
                "uuid": getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', ''),
                "name": edge.name or "",
                "fact": edge.fact or "",
                "source_node_uuid": edge.source_node_uuid,
                "target_node_uuid": edge.target_node_uuid,
                "attributes": edge.attributes or {},
            })
        logger.info(f"Got {len(result)} edges")
        return result

    def get_node_edges(self, node_uuid: str) -> List[Dict[str, Any]]:
        """获取指定节点的相关边（仅 Zep 支持，本地图谱通过 get_all_edges 处理）"""
        try:
            edges = self._call_with_retry(
                func=lambda: self.client.graph.node.get_entity_edges(node_uuid=node_uuid),
                operation_name=f"get_node_edges(node={node_uuid[:8]}...)"
            )
            result = []
            for edge in edges:
                result.append({
                    "uuid": getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', ''),
                    "name": edge.name or "",
                    "fact": edge.fact or "",
                    "source_node_uuid": edge.source_node_uuid,
                    "target_node_uuid": edge.target_node_uuid,
                    "attributes": edge.attributes or {},
                })
            return result
        except Exception as e:
            logger.warning(f"Failed to get edges for node {node_uuid}: {str(e)}")
            return []

    # ---- Filtering ----

    def filter_defined_entities(
        self, graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ) -> FilteredEntities:
        logger.info(f"Filtering entities for graph {graph_id}...")
        all_nodes = self.get_all_nodes(graph_id)
        total_count = len(all_nodes)
        all_edges = self.get_all_edges(graph_id) if enrich_with_edges else []
        node_map = {n["uuid"]: n for n in all_nodes}

        filtered_entities = []
        entity_types_found = set()

        for node in all_nodes:
            labels = node.get("labels", [])
            custom_labels = [l for l in labels if l not in ["Entity", "Node"]]
            if not custom_labels:
                continue
            if defined_entity_types:
                matching = [l for l in custom_labels if l in defined_entity_types]
                if not matching:
                    continue
                entity_type = matching[0]
            else:
                entity_type = custom_labels[0]

            entity_types_found.add(entity_type)
            entity = EntityNode(
                uuid=node["uuid"], name=node["name"],
                labels=labels, summary=node["summary"],
                attributes=node["attributes"],
            )

            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()
                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "outgoing", "edge_name": edge["name"],
                            "fact": edge["fact"], "target_node_uuid": edge["target_node_uuid"],
                        })
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "incoming", "edge_name": edge["name"],
                            "fact": edge["fact"], "source_node_uuid": edge["source_node_uuid"],
                        })
                        related_node_uuids.add(edge["source_node_uuid"])

                entity.related_edges = related_edges
                entity.related_nodes = [
                    {"uuid": node_map[uid]["uuid"], "name": node_map[uid]["name"],
                     "labels": node_map[uid]["labels"], "summary": node_map[uid].get("summary", "")}
                    for uid in related_node_uuids if uid in node_map
                ]

            filtered_entities.append(entity)

        logger.info(f"Filtered: {total_count} total -> {len(filtered_entities)} entities, types: {entity_types_found}")
        return FilteredEntities(
            entities=filtered_entities, entity_types=entity_types_found,
            total_count=total_count, filtered_count=len(filtered_entities),
        )

    def get_entity_with_context(self, graph_id: str, entity_uuid: str) -> Optional[EntityNode]:
        """获取单个实体及上下文（支持本地图谱）"""
        try:
            if self._is_local_graph(graph_id):
                graph = self._load_local_graph(graph_id)
                node = next((n for n in graph.get("nodes", []) if n["uuid"] == entity_uuid), None)
                if not node:
                    return None
                all_nodes = graph.get("nodes", [])
                all_edges = graph.get("edges", [])
            else:
                node_obj = self._call_with_retry(
                    func=lambda: self.client.graph.node.get(uuid_=entity_uuid),
                    operation_name=f"get_entity(uuid={entity_uuid[:8]}...)"
                )
                if not node_obj:
                    return None
                node = {
                    "uuid": getattr(node_obj, 'uuid_', None) or getattr(node_obj, 'uuid', ''),
                    "name": node_obj.name or "",
                    "labels": node_obj.labels or [],
                    "summary": node_obj.summary or "",
                    "attributes": node_obj.attributes or {},
                }
                all_nodes = self.get_all_nodes(graph_id)
                all_edges = self.get_node_edges(entity_uuid)

            node_map = {n["uuid"]: n for n in all_nodes}
            related_edges = []
            related_node_uuids = set()

            for edge in all_edges:
                if edge["source_node_uuid"] == entity_uuid:
                    related_edges.append({
                        "direction": "outgoing", "edge_name": edge["name"],
                        "fact": edge["fact"], "target_node_uuid": edge["target_node_uuid"],
                    })
                    related_node_uuids.add(edge["target_node_uuid"])
                elif edge["target_node_uuid"] == entity_uuid:
                    related_edges.append({
                        "direction": "incoming", "edge_name": edge["name"],
                        "fact": edge["fact"], "source_node_uuid": edge["source_node_uuid"],
                    })
                    related_node_uuids.add(edge["source_node_uuid"])

            return EntityNode(
                uuid=node["uuid"], name=node["name"], labels=node["labels"],
                summary=node["summary"], attributes=node["attributes"],
                related_edges=related_edges,
                related_nodes=[
                    {"uuid": node_map[uid]["uuid"], "name": node_map[uid]["name"],
                     "labels": node_map[uid]["labels"], "summary": node_map[uid].get("summary", "")}
                    for uid in related_node_uuids if uid in node_map
                ],
            )
        except Exception as e:
            logger.error(f"Failed to get entity {entity_uuid}: {str(e)}")
            return None

    def get_entities_by_type(
        self, graph_id: str, entity_type: str, enrich_with_edges: bool = True
    ) -> List[EntityNode]:
        result = self.filter_defined_entities(
            graph_id=graph_id, defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges
        )
        return result.entities
