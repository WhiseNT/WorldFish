"""
WorldFish 模拟配置生成器。

只生成 WorldFish 内置 runner 需要的配置。
"""

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..utils.logger import get_logger
from .knowledge_graph import EntityNode

logger = get_logger('worldfish.simulation_config')


@dataclass
class AgentActivityConfig:
    """单个 Agent 的活动配置。"""

    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str
    activity_level: float = 0.5
    actions_per_hour: float = 1.0
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))
    response_delay_min: int = 5
    response_delay_max: int = 60
    stance: str = "neutral"
    influence_weight: float = 1.0


@dataclass
class TimeSimulationConfig:
    """时间模拟配置。"""

    total_simulation_hours: int = 72
    minutes_per_round: int = 60
    agents_per_hour_min: int = 1
    agents_per_hour_max: int = 10
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    work_hours: List[int] = field(default_factory=lambda: list(range(9, 19)))


@dataclass
class EventConfig:
    """事件配置。"""

    initial_events: List[Dict[str, Any]] = field(default_factory=list)
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    hot_topics: List[str] = field(default_factory=list)
    narrative_direction: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorldFishConfig:
    """WorldFish 内置 runner 的运行配置。"""

    runner: str = "worldfish_builtin"
    event_store: str = "worldfish/actions.jsonl"
    event_types: List[str] = field(default_factory=lambda: [
        "observe_world",
        "state_position",
        "adjust_plan",
        "spread_influence",
    ])
    action_stream: str = "worldfish"
    memory_update_source: str = "worldfish_actions"


@dataclass
class SimulationParameters:
    """完整模拟参数配置。"""

    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)
    event_config: EventConfig = field(default_factory=EventConfig)
    worldfish_config: WorldFishConfig = field(default_factory=WorldFishConfig)
    llm_model: str = "worldfish_rule_engine"
    llm_base_url: str = "local"
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": asdict(self.time_config),
            "agent_configs": [asdict(agent) for agent in self.agent_configs],
            "event_config": self.event_config.to_dict(),
            "worldfish_config": asdict(self.worldfish_config),
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
            "runner": "worldfish_builtin",
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """WorldFish 本地规则配置生成器。"""

    MAX_CONTEXT_LENGTH = 50000
    AGENTS_PER_BATCH = 15
    ENTITIES_PER_TYPE_DISPLAY = 20
    ENTITY_SUMMARY_LENGTH = 300

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url or "local"
        self.model_name = model_name or "worldfish_rule_engine"
        self.client = None

    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        simulation_mode: str = "unknown",
        time_range: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        logger.info(f"开始生成 WorldFish 模拟配置: simulation_id={simulation_id}, entities={len(entities)}")

        batches = max(1, math.ceil(len(entities) / self.AGENTS_PER_BATCH))
        total_steps = 3 + batches

        def report(step: int, message: str):
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")

        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities,
            simulation_mode=simulation_mode,
            time_range=time_range,
        )

        report(1, "生成时间配置")
        time_config = self._parse_time_config(self._generate_time_config(len(entities)), len(entities))

        report(2, "生成事件配置")
        event_config = self._parse_event_config(self._generate_event_config(context, simulation_requirement, entities))

        agent_configs: List[AgentActivityConfig] = []
        for batch_idx in range(batches):
            start = batch_idx * self.AGENTS_PER_BATCH
            end = min(start + self.AGENTS_PER_BATCH, len(entities))
            report(3 + batch_idx, f"生成 Agent 配置 {start + 1}-{end}/{len(entities)}")
            agent_configs.extend(self._generate_agent_configs_batch(entities[start:end], start))

        event_config = self._assign_initial_event_agents(event_config, agent_configs)
        report(total_steps, "生成 WorldFish 运行配置")

        return SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=agent_configs,
            event_config=event_config,
            worldfish_config=WorldFishConfig(),
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning="由 WorldFish 本地规则生成：根据实体类型估算活跃度、影响力、响应速度和初始事件。",
        )

    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        simulation_mode: str = "unknown",
        time_range: Optional[str] = None,
    ) -> str:
        parts = [
            f"## 模拟需求\n{simulation_requirement}",
            f"\n## 推演模式\n{simulation_mode}",
            f"\n## 时间范围\n{time_range or '未指定'}",
            f"\n## 实体信息 ({len(entities)}个)\n{self._summarize_entities(entities)}",
        ]
        remaining = self.MAX_CONTEXT_LENGTH - sum(len(part) for part in parts) - 500
        if document_text and remaining > 0:
            tail = "\n...(文档已截断)" if len(document_text) > remaining else ""
            parts.append(f"\n## 原始文档内容\n{document_text[:remaining]}{tail}")
        return "\n".join(parts)

    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        grouped: Dict[str, List[EntityNode]] = {}
        for entity in entities:
            grouped.setdefault(entity.get_entity_type() or "Unknown", []).append(entity)

        lines: List[str] = []
        for entity_type, items in grouped.items():
            lines.append(f"\n### {entity_type} ({len(items)}个)")
            for entity in items[:self.ENTITIES_PER_TYPE_DISPLAY]:
                summary = (entity.summary or "").strip()
                if len(summary) > self.ENTITY_SUMMARY_LENGTH:
                    summary = summary[:self.ENTITY_SUMMARY_LENGTH] + "..."
                lines.append(f"- {entity.name}: {summary}")
            if len(items) > self.ENTITIES_PER_TYPE_DISPLAY:
                lines.append(f"  ... 还有 {len(items) - self.ENTITIES_PER_TYPE_DISPLAY} 个")
        return "\n".join(lines)

    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        raise RuntimeError("WorldFish 配置生成器不再调用外部 LLM")

    def _fix_truncated_json(self, content: str) -> str:
        content = content.strip()
        if content and content[-1] not in '",}]':
            content += '"'
        content += ']' * (content.count('[') - content.count(']'))
        content += '}' * (content.count('{') - content.count('}'))
        return content

    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(self._fix_truncated_json(content))
        except Exception:
            return None

    def _generate_time_config(self, num_entities: int) -> Dict[str, Any]:
        max_agents = max(1, num_entities)
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,
            "agents_per_hour_min": min(max(1, num_entities // 15), max_agents),
            "agents_per_hour_max": min(max(3, num_entities // 4), max_agents),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": list(range(9, 19)),
        }

    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        return self._generate_time_config(num_entities)

    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        max_agents = max(1, num_entities)
        min_agents = max(1, min(int(result.get("agents_per_hour_min", 1) or 1), max_agents))
        max_active = max(min_agents, min(int(result.get("agents_per_hour_max", min_agents) or min_agents), max_agents))
        return TimeSimulationConfig(
            total_simulation_hours=int(result.get("total_simulation_hours", 72) or 72),
            minutes_per_round=int(result.get("minutes_per_round", 60) or 60),
            agents_per_hour_min=min_agents,
            agents_per_hour_max=max_active,
            peak_hours=list(result.get("peak_hours", [19, 20, 21, 22])),
            off_peak_hours=list(result.get("off_peak_hours", [0, 1, 2, 3, 4, 5])),
            morning_hours=list(result.get("morning_hours", [6, 7, 8])),
            work_hours=list(result.get("work_hours", list(range(9, 19)))),
        )

    def _generate_event_config(
        self,
        context: str,
        simulation_requirement: str,
        entities: List[EntityNode],
    ) -> Dict[str, Any]:
        topics = self._extract_hot_topics(simulation_requirement, context)
        initial_events = []
        representatives = sorted(
            entities,
            key=lambda entity: self._entity_influence(entity.get_entity_type() or "Unknown"),
            reverse=True,
        )[:3]

        for entity in representatives:
            entity_type = entity.get_entity_type() or "Unknown"
            focus = topics[0] if topics else "当前局势"
            initial_events.append({
                "content": f"{entity.name} 开始关注「{focus}」相关变化，并准备评估后续影响。",
                "actor_type": entity_type,
            })

        if not initial_events and simulation_requirement:
            initial_events.append({
                "content": f"围绕「{simulation_requirement[:80]}」的初始观察已经形成。",
                "actor_type": "Observer",
            })

        return {
            "hot_topics": topics,
            "narrative_direction": self._build_narrative_direction(simulation_requirement, topics),
            "initial_events": initial_events,
        }

    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        return EventConfig(
            initial_events=list(result.get("initial_events") or []),
            scheduled_events=list(result.get("scheduled_events", [])),
            hot_topics=list(result.get("hot_topics", [])),
            narrative_direction=str(result.get("narrative_direction", "")),
        )

    def _assign_initial_event_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig],
    ) -> EventConfig:
        if not event_config.initial_events or not agent_configs:
            return event_config

        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            agents_by_type.setdefault(agent.entity_type.lower(), []).append(agent)

        fallback = max(agent_configs, key=lambda item: item.influence_weight)
        used: Dict[str, int] = {}
        updated_events = []

        for event in event_config.initial_events:
            actor_type = str(event.get("actor_type") or "").lower()
            agents = agents_by_type.get(actor_type) or self._find_alias_agents(actor_type, agents_by_type) or [fallback]
            idx = used.get(actor_type, 0) % len(agents)
            used[actor_type] = idx + 1

            updated = dict(event)
            updated["actor_agent_id"] = agents[idx].agent_id
            updated_events.append(updated)

        event_config.initial_events = updated_events
        return event_config

    def _generate_agent_configs_batch(
        self,
        entities: List[EntityNode],
        start_idx: int,
    ) -> List[AgentActivityConfig]:
        configs: List[AgentActivityConfig] = []
        for index, entity in enumerate(entities):
            agent_id = start_idx + index
            rule = self._generate_agent_config_by_rule(entity)
            configs.append(AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=rule["activity_level"],
                actions_per_hour=rule["actions_per_hour"],
                active_hours=rule["active_hours"],
                response_delay_min=rule["response_delay_min"],
                response_delay_max=rule["response_delay_max"],
                stance=rule["stance"],
                influence_weight=rule["influence_weight"],
            ))
        return configs

    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        entity_type = (entity.get_entity_type() or "Unknown").lower()
        if entity_type in {"university", "governmentagency", "official", "institution"}:
            return self._activity(0.2, 0.2, list(range(9, 18)), 60, 240, "neutral", 3.0)
        if entity_type in {"mediaoutlet", "journalist"}:
            return self._activity(0.55, 0.8, list(range(7, 24)), 5, 30, "observer", 2.4)
        if entity_type in {"professor", "expert", "faculty", "publicfigure"}:
            return self._activity(0.45, 0.5, list(range(8, 22)), 15, 90, "neutral", 2.0)
        if entity_type in {"student", "activist"}:
            return self._activity(0.8, 1.2, [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23], 1, 15, "neutral", 0.9)
        if entity_type in {"alumni", "person", "community"}:
            return self._activity(0.65, 0.8, [12, 13, 18, 19, 20, 21, 22, 23], 5, 30, "neutral", 1.0)
        return self._activity(0.5, 0.6, list(range(9, 23)), 10, 60, "neutral", 1.0)

    def _activity(
        self,
        activity_level: float,
        actions_per_hour: float,
        active_hours: List[int],
        response_delay_min: int,
        response_delay_max: int,
        stance: str,
        influence_weight: float,
    ) -> Dict[str, Any]:
        return {
            "activity_level": activity_level,
            "actions_per_hour": actions_per_hour,
            "active_hours": active_hours,
            "response_delay_min": response_delay_min,
            "response_delay_max": response_delay_max,
            "stance": stance,
            "influence_weight": influence_weight,
        }

    def _extract_hot_topics(self, requirement: str, context: str) -> List[str]:
        source = f"{requirement} {context[:1000]}"
        for sep in "，。！？；：、,.!?;:()（）[]【】\n\t":
            source = source.replace(sep, " ")
        stopwords = {"如果", "一个", "以及", "进行", "模拟", "推演", "事件", "影响", "the", "and", "for", "with"}
        topics = []
        for token in source.split():
            clean = token.strip("《》\"' ")
            if len(clean) < 2 or clean.lower() in stopwords:
                continue
            if clean not in topics:
                topics.append(clean)
            if len(topics) >= 8:
                break
        return topics or ["世界演化", "关键实体", "连锁反应"]

    def _build_narrative_direction(self, requirement: str, topics: List[str]) -> str:
        if requirement:
            return f"围绕「{requirement[:120]}」观察各实体的认知、行动和影响扩散。"
        return f"围绕 {', '.join(topics[:3])} 观察各实体的状态变化和互动。"

    def _entity_influence(self, entity_type: str) -> float:
        fake_entity = type("EntityStub", (), {"get_entity_type": lambda _: entity_type})()
        return self._generate_agent_config_by_rule(fake_entity).get("influence_weight", 1.0)

    def _find_alias_agents(
        self,
        actor_type: str,
        agents_by_type: Dict[str, List[AgentActivityConfig]],
    ) -> List[AgentActivityConfig]:
        aliases = {
            "official": ["official", "university", "governmentagency", "institution"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "journalist", "media"],
            "student": ["student", "person"],
            "person": ["person", "student", "alumni"],
            "organization": ["organization", "ngo", "company", "community"],
            "observer": ["expert", "person"],
        }
        for key, values in aliases.items():
            if actor_type == key or actor_type in values:
                for value in values:
                    if value in agents_by_type:
                        return agents_by_type[value]
        return []
