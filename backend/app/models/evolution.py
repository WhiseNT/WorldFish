"""进化推演数据模型与持久化"""

import json
import os
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config


class EvolutionRound:
    def __init__(
        self,
        round_number: int,
        narrative: str = "",
        year_advanced_to: str = "",
        affected_entities: Optional[List[Dict]] = None,
        new_events: Optional[List[Dict]] = None,
    ):
        self.round_number = round_number
        self.narrative = narrative
        self.year_advanced_to = year_advanced_to
        self.affected_entities = affected_entities or []
        self.new_events = new_events or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_number": self.round_number,
            "narrative": self.narrative,
            "year_advanced_to": self.year_advanced_to,
            "affected_entities": self.affected_entities,
            "new_events": self.new_events,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionRound":
        return cls(
            round_number=data.get("round_number", 0),
            narrative=data.get("narrative", ""),
            year_advanced_to=data.get("year_advanced_to", ""),
            affected_entities=data.get("affected_entities") or [],
            new_events=data.get("new_events") or [],
        )


class Evolution:
    def __init__(
        self,
        id: str,
        world_id: str,
        scenario: str,
        config: Optional[Dict[str, Any]] = None,
        rounds: Optional[List[EvolutionRound]] = None,
        status: str = "created",
        parent_evolution_id: str = "",
        parent_round: int = -1,
        evolution_type: str = "forward",  # "forward" | "branch"
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        now = datetime.now().isoformat()
        self.id = id
        self.world_id = world_id
        self.scenario = scenario
        self.config = config or {}
        self.rounds = rounds or []
        self.status = status
        self.parent_evolution_id = parent_evolution_id
        self.parent_round = parent_round
        self.evolution_type = evolution_type
        self.consolidation = None  # 推演后整合结果
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    @classmethod
    def create(cls, world_id: str, scenario: str, config: Dict[str, Any] = None,
               parent_evolution_id: str = "", parent_round: int = -1,
               evolution_type: str = "forward") -> "Evolution":
        return cls(
            id=f"evol_{uuid.uuid4().hex[:12]}",
            world_id=world_id,
            scenario=scenario,
            config=config or {},
            status="running",
            parent_evolution_id=parent_evolution_id,
            parent_round=parent_round,
            evolution_type=evolution_type,
        )

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "world_id": self.world_id,
            "scenario": self.scenario,
            "config": self.config,
            "rounds": [r.to_dict() for r in self.rounds],
            "status": self.status,
            "parent_evolution_id": self.parent_evolution_id,
            "parent_round": self.parent_round,
            "evolution_type": self.evolution_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.consolidation:
            d["consolidation"] = self.consolidation
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evolution":
        evo = cls(
            id=data.get("id", ""),
            world_id=data.get("world_id", ""),
            scenario=data.get("scenario", ""),
            config=data.get("config") or {},
            rounds=[EvolutionRound.from_dict(r) for r in data.get("rounds") or []],
            status=data.get("status", "created"),
            parent_evolution_id=data.get("parent_evolution_id", ""),
            parent_round=data.get("parent_round", -1),
            evolution_type=data.get("evolution_type", "forward"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
        if data.get("consolidation"):
            evo.consolidation = data["consolidation"]
        return evo


class EvolutionManager:
    _EVOLUTIONS_DIR = os.path.join(Config.UPLOAD_FOLDER, "evolutions")
    _lock = threading.RLock()

    @classmethod
    def _ensure_dir(cls):
        os.makedirs(cls._EVOLUTIONS_DIR, exist_ok=True)

    @classmethod
    def _file(cls, evolution_id: str) -> str:
        cls._ensure_dir()
        return os.path.join(cls._EVOLUTIONS_DIR, f"{evolution_id}.json")

    @classmethod
    def save(cls, evolution: Evolution) -> Evolution:
        with cls._lock:
            evolution.updated_at = datetime.now().isoformat()
            with open(cls._file(evolution.id), "w", encoding="utf-8") as f:
                json.dump(evolution.to_dict(), f, ensure_ascii=False, indent=2)
            return evolution

    @classmethod
    def get(cls, evolution_id: str) -> Optional[Evolution]:
        path = cls._file(evolution_id)
        if not os.path.exists(path):
            return None
        with cls._lock:
            with open(path, "r", encoding="utf-8") as f:
                return Evolution.from_dict(json.load(f))

    @classmethod
    def add_round(cls, evolution_id: str, round_data: EvolutionRound) -> Optional[Evolution]:
        with cls._lock:
            evolution = cls.get(evolution_id)
            if not evolution:
                return None
            evolution.rounds.append(round_data)
            return cls.save(evolution)

    @classmethod
    def update_status(cls, evolution_id: str, status: str) -> Optional[Evolution]:
        with cls._lock:
            evolution = cls.get(evolution_id)
            if not evolution:
                return None
            evolution.status = status
            return cls.save(evolution)

    @classmethod
    def list_by_world(cls, world_id: str) -> List[Evolution]:
        cls._ensure_dir()
        results = []
        for filename in os.listdir(cls._EVOLUTIONS_DIR):
            path = os.path.join(cls._EVOLUTIONS_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("world_id") == world_id:
                    results.append(Evolution.from_dict(data))
            except Exception:
                pass
        results.sort(key=lambda e: e.updated_at, reverse=True)
        return results
