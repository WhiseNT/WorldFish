"""WorldFish 模拟管理器。"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.locale import t
from ..utils.logger import get_logger
from .worldfish_profile_generator import WorldFishProfileGenerator
from .simulation_config_generator import SimulationConfigGenerator
from .zep_entity_reader import ZepEntityReader

logger = get_logger('worldfish.simulation')


class SimulationStatus(str, Enum):
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SimulationState:
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_mode: str = "unknown"
    time_range: Optional[str] = None
    status: SimulationStatus = SimulationStatus.CREATED
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    config_generated: bool = False
    config_reasoning: str = ""
    current_round: int = 0
    runner_status: str = "not_started"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_mode": self.simulation_mode,
            "time_range": self.time_range,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "runner_status": self.runner_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    def to_simple_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_mode": self.simulation_mode,
            "time_range": self.time_range,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "error": self.error,
        }


class SimulationManager:
    SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/simulations')

    def __init__(self):
        os.makedirs(self.SIMULATION_DATA_DIR, exist_ok=True)
        self._simulations: Dict[str, SimulationState] = {}

    def _get_simulation_dir(self, simulation_id: str) -> str:
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir

    def _save_simulation_state(self, state: SimulationState):
        sim_dir = self._get_simulation_dir(state.simulation_id)
        state.updated_at = datetime.now().isoformat()
        with open(os.path.join(sim_dir, "state.json"), 'w', encoding='utf-8') as handle:
            json.dump(state.to_dict(), handle, ensure_ascii=False, indent=2)
        self._simulations[state.simulation_id] = state

    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]

        state_file = os.path.join(self._get_simulation_dir(simulation_id), "state.json")
        if not os.path.exists(state_file):
            return None

        with open(state_file, 'r', encoding='utf-8') as handle:
            data = json.load(handle)

        state = SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            simulation_mode=data.get("simulation_mode", "unknown"),
            time_range=data.get("time_range"),
            status=SimulationStatus(data.get("status", "created")),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            current_round=data.get("current_round", 0),
            runner_status=data.get("runner_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
        )
        self._simulations[simulation_id] = state
        return state

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        simulation_mode: str = "unknown",
        time_range: Optional[str] = None,
    ) -> SimulationState:
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_mode=simulation_mode,
            time_range=time_range,
            status=SimulationStatus.CREATED,
        )
        self._save_simulation_state(state)
        logger.info(f"创建模拟: {simulation_id}, project={project_id}, graph={graph_id}")
        return state

    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3,
    ) -> SimulationState:
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"模拟不存在: {simulation_id}")

        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)
            sim_dir = self._get_simulation_dir(simulation_id)

            if progress_callback:
                progress_callback("reading", 0, t('progress.connectingZepGraph'))

            reader = ZepEntityReader()
            if progress_callback:
                progress_callback("reading", 30, t('progress.readingNodeData'))

            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True,
            )
            state.entities_count = filtered.filtered_count
            state.entity_types = list(filtered.entity_types)

            if progress_callback:
                progress_callback(
                    "reading", 100,
                    t('progress.readingComplete', count=filtered.filtered_count),
                    current=filtered.filtered_count,
                    total=filtered.filtered_count,
                )

            if filtered.filtered_count == 0:
                state.status = SimulationStatus.FAILED
                state.error = "没有找到符合条件的实体，请检查图谱是否正确构建"
                self._save_simulation_state(state)
                return state

            total_entities = len(filtered.entities)
            if progress_callback:
                progress_callback(
                    "generating_profiles", 0,
                    t('progress.startGenerating'),
                    current=0,
                    total=total_entities,
                )

            generator = WorldFishProfileGenerator(graph_id=state.graph_id)

            def profile_progress(current, total, msg):
                if progress_callback:
                    progress_callback(
                        "generating_profiles",
                        int(current / max(total, 1) * 100),
                        msg,
                        current=current,
                        total=total,
                        item_name=msg,
                    )

            profiles = generator.generate_profiles_from_entities(
                entities=filtered.entities,
                use_llm=use_llm_for_profiles,
                progress_callback=profile_progress,
                graph_id=state.graph_id,
                parallel_count=parallel_profile_count,
                realtime_output_path=os.path.join(sim_dir, "worldfish_profiles.json"),
            )
            state.profiles_count = len(profiles)

            if progress_callback:
                progress_callback(
                    "generating_profiles", 95,
                    t('progress.savingProfiles'),
                    current=total_entities,
                    total=total_entities,
                )

            generator.save_profiles(
                profiles=profiles,
                file_path=os.path.join(sim_dir, "worldfish_profiles.json"),
            )

            if progress_callback:
                progress_callback(
                    "generating_profiles", 100,
                    t('progress.profilesComplete', count=len(profiles)),
                    current=len(profiles),
                    total=len(profiles),
                )

            if progress_callback:
                progress_callback("generating_config", 0, t('progress.analyzingRequirements'), current=0, total=3)

            config_generator = SimulationConfigGenerator()
            if progress_callback:
                progress_callback("generating_config", 30, t('progress.callingLLMConfig'), current=1, total=3)

            sim_params = config_generator.generate_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                entities=filtered.entities,
                simulation_mode=state.simulation_mode,
                time_range=state.time_range,
            )

            if progress_callback:
                progress_callback("generating_config", 70, t('progress.savingConfigFiles'), current=2, total=3)

            with open(os.path.join(sim_dir, "simulation_config.json"), 'w', encoding='utf-8') as handle:
                handle.write(sim_params.to_json())

            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning

            if progress_callback:
                progress_callback("generating_config", 100, t('progress.configComplete'), current=3, total=3)

            state.status = SimulationStatus.READY
            self._save_simulation_state(state)
            logger.info(f"模拟准备完成: {simulation_id}, entities={state.entities_count}, profiles={state.profiles_count}")
            return state
        except Exception as exc:
            logger.error(f"模拟准备失败: {simulation_id}, error={exc}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(exc)
            self._save_simulation_state(state)
            raise

    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        return self._load_simulation_state(simulation_id)

    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        simulations = []
        if os.path.exists(self.SIMULATION_DATA_DIR):
            for sim_id in os.listdir(self.SIMULATION_DATA_DIR):
                sim_path = os.path.join(self.SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith('.') or not os.path.isdir(sim_path):
                    continue
                state = self._load_simulation_state(sim_id)
                if state and (project_id is None or state.project_id == project_id):
                    simulations.append(state)
        return simulations

    def get_profiles(self, simulation_id: str) -> List[Dict[str, Any]]:
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"模拟不存在: {simulation_id}")
        profile_path = os.path.join(self._get_simulation_dir(simulation_id), "worldfish_profiles.json")
        if not os.path.exists(profile_path):
            return []
        with open(profile_path, 'r', encoding='utf-8') as handle:
            return json.load(handle)

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        config_path = os.path.join(self._get_simulation_dir(simulation_id), "simulation_config.json")
        if not os.path.exists(config_path):
            return None
        with open(config_path, 'r', encoding='utf-8') as handle:
            return json.load(handle)

    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        return {
            "simulation_dir": sim_dir,
            "config_file": config_path,
            "runner": "worldfish_builtin",
            "commands": {
                "api": f"POST /api/simulation/{simulation_id}/start",
            },
            "instructions": (
                "当前版本使用 WorldFish 内置运行器。\n"
                f"配置文件: {config_path}\n"
                f"通过后端接口 POST /api/simulation/{simulation_id}/start 启动模拟。"
            ),
        }

