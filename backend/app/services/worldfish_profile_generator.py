"""WorldFish Agent Profile 生成器。"""

import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger
from .knowledge_graph import EntityNode

logger = get_logger('worldfish.profile')


@dataclass
class WorldFishAgentProfile:
    agent_id: int
    agent_name: str
    display_name: str
    bio: str
    persona: str
    influence_weight: float = 1.0
    activity_level: float = 0.5
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "display_name": self.display_name,
            "name": self.display_name,
            "bio": self.bio,
            "persona": self.persona,
            "influence_weight": self.influence_weight,
            "activity_level": self.activity_level,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
            "runner": "worldfish_builtin",
        }


class WorldFishProfileGenerator:
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP",
    ]

    def __init__(self, graph_id: str = None):
        self.graph_id = graph_id

    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: str = None,
        parallel_count: int = 3,
        realtime_output_path: str = None,
    ) -> List[WorldFishAgentProfile]:
        profiles: List[WorldFishAgentProfile] = []
        total = len(entities)
        for idx, entity in enumerate(entities):
            profile = self._create_profile_from_entity(entity, idx)
            profiles.append(profile)
            if realtime_output_path:
                self.save_profiles(profiles, realtime_output_path)
            if progress_callback:
                progress_callback(idx + 1, total, profile.display_name)
        logger.info(f"生成 WorldFish profiles 完成: {len(profiles)}")
        return profiles

    def _create_profile_from_entity(self, entity: EntityNode, agent_id: int) -> WorldFishAgentProfile:
        entity_type = entity.get_entity_type() or "Entity"
        topics = self._extract_topics(entity)
        bio = self._build_bio(entity, entity_type)
        persona = self._build_persona(entity, entity_type, topics)
        return WorldFishAgentProfile(
            agent_id=agent_id,
            agent_name=self._safe_agent_name(entity.name, agent_id),
            display_name=entity.name or f"Agent {agent_id}",
            bio=bio,
            persona=persona,
            influence_weight=self._influence_weight(entity_type),
            activity_level=self._activity_level(entity_type),
            age=self._infer_age(entity_type),
            gender="other",
            mbti=random.choice(self.MBTI_TYPES),
            country="未指定",
            profession=entity_type,
            interested_topics=topics,
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )

    def _build_bio(self, entity: EntityNode, entity_type: str) -> str:
        summary = (entity.summary or "").strip()
        if summary:
            return summary[:500]
        return f"{entity.name} 是 WorldFish 图谱中的 {entity_type} 类型实体。"

    def _build_persona(self, entity: EntityNode, entity_type: str, topics: List[str]) -> str:
        topic_text = "、".join(topics[:5]) if topics else "当前局势"
        summary = (entity.summary or "").strip()
        base = f"你是 {entity.name}，实体类型为 {entity_type}。你关注 {topic_text}。"
        if summary:
            base += f"背景信息：{summary[:700]}"
        base += "在推演中，你会根据自身背景观察世界变化、表明位置、调整计划并扩散影响。"
        return base

    def _extract_topics(self, entity: EntityNode) -> List[str]:
        text = f"{entity.name} {entity.summary or ''}"
        for sep in "，。！？；：、,.!?;:()（）[]【】\n\t":
            text = text.replace(sep, " ")
        topics = []
        stopwords = {"一个", "以及", "进行", "相关", "包括", "the", "and", "for", "with"}
        for token in text.split():
            clean = token.strip("《》\"' ")
            if len(clean) < 2 or clean.lower() in stopwords:
                continue
            if clean not in topics:
                topics.append(clean)
            if len(topics) >= 8:
                break
        return topics or [entity.get_entity_type() or "世界局势"]

    def _safe_agent_name(self, name: str, agent_id: int) -> str:
        base = re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff-]+", "_", name or "")
        base = base.strip("_") or f"agent_{agent_id}"
        return base[:64]

    def _influence_weight(self, entity_type: str) -> float:
        normalized = entity_type.lower()
        if normalized in {"university", "governmentagency", "official", "institution"}:
            return 3.0
        if normalized in {"mediaoutlet", "journalist"}:
            return 2.4
        if normalized in {"professor", "expert", "faculty", "publicfigure"}:
            return 2.0
        return 1.0

    def _activity_level(self, entity_type: str) -> float:
        normalized = entity_type.lower()
        if normalized in {"student", "activist"}:
            return 0.8
        if normalized in {"alumni", "person", "community"}:
            return 0.65
        if normalized in {"university", "governmentagency", "official", "institution"}:
            return 0.2
        return 0.5

    def _infer_age(self, entity_type: str) -> int:
        normalized = entity_type.lower()
        if normalized == "student":
            return random.randint(18, 26)
        if normalized in {"professor", "expert", "faculty"}:
            return random.randint(35, 65)
        return random.randint(24, 55)

    def save_profiles(
        self,
        profiles: List[WorldFishAgentProfile],
        file_path: str,
    ):
        with open(file_path, 'w', encoding='utf-8') as handle:
            json.dump([profile.to_dict() for profile in profiles], handle, ensure_ascii=False, indent=2)

