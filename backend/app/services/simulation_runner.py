"""WorldFish 内置模拟运行器。"""

import atexit
import json
import os
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger('worldfish.simulation_runner')

_cleanup_registered = False


class RunnerStatus(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentAction:
    round_num: int
    timestamp: str
    stream: str
    agent_id: int
    agent_name: str
    action_type: str
    action_args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "timestamp": self.timestamp,
            "stream": self.stream,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "action_type": self.action_type,
            "action_args": self.action_args,
            "result": self.result,
            "success": self.success,
        }


@dataclass
class RoundSummary:
    round_num: int
    start_time: str
    end_time: Optional[str] = None
    simulated_hour: int = 0
    actions_count: int = 0
    active_agents: List[int] = field(default_factory=list)
    action_types: Dict[str, int] = field(default_factory=dict)
    actions: List[AgentAction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "simulated_hour": self.simulated_hour,
            "actions_count": self.actions_count,
            "active_agents": self.active_agents,
            "action_types": self.action_types,
            "actions": [action.to_dict() for action in self.actions],
        }


@dataclass
class SimulationRunState:
    simulation_id: str
    runner_status: RunnerStatus = RunnerStatus.IDLE
    current_round: int = 0
    total_rounds: int = 0
    simulated_hours: int = 0
    total_simulation_hours: int = 0
    actions_count: int = 0
    stream: str = "worldfish"
    stream_running: bool = False
    stream_completed: bool = False
    rounds: List[RoundSummary] = field(default_factory=list)
    recent_actions: List[AgentAction] = field(default_factory=list)
    max_recent_actions: int = 50
    started_at: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None
    process_pid: Optional[int] = None

    def add_action(self, action: AgentAction):
        self.recent_actions.insert(0, action)
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions = self.recent_actions[:self.max_recent_actions]
        self.actions_count += 1
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "runner_status": self.runner_status.value,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "simulated_hours": self.simulated_hours,
            "total_simulation_hours": self.total_simulation_hours,
            "progress_percent": round(self.current_round / max(self.total_rounds, 1) * 100, 1),
            "stream": self.stream,
            "stream_running": self.stream_running,
            "stream_completed": self.stream_completed,
            "actions_count": self.actions_count,
            "total_actions_count": self.actions_count,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "process_pid": self.process_pid,
        }

    def to_detail_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["recent_actions"] = [action.to_dict() for action in self.recent_actions]
        result["rounds_count"] = len(self.rounds)
        result["rounds"] = [round_summary.to_dict() for round_summary in self.rounds]
        return result


@dataclass
class WorldFishAgent:
    agent_id: int
    name: str
    persona: str = ""
    faction: str = ""
    focus: str = ""


class SimulationRunner:
    RUN_STATE_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/simulations')
    STREAM = "worldfish"

    _run_states: Dict[str, SimulationRunState] = {}
    _runner_threads: Dict[str, threading.Thread] = {}
    _stop_flags: Dict[str, threading.Event] = {}
    _graph_memory_enabled: Dict[str, bool] = {}
    _cleanup_done = False

    @classmethod
    def get_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        if simulation_id in cls._run_states:
            return cls._run_states[simulation_id]
        state = cls._load_run_state(simulation_id)
        if state:
            cls._run_states[simulation_id] = state
        return state

    @classmethod
    def _load_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        state_file = os.path.join(cls.RUN_STATE_DIR, simulation_id, "run_state.json")
        if not os.path.exists(state_file):
            return None

        try:
            with open(state_file, 'r', encoding='utf-8') as handle:
                data = json.load(handle)

            state = SimulationRunState(
                simulation_id=simulation_id,
                runner_status=RunnerStatus(data.get("runner_status", "idle")),
                current_round=data.get("current_round", 0),
                total_rounds=data.get("total_rounds", 0),
                simulated_hours=data.get("simulated_hours", 0),
                total_simulation_hours=data.get("total_simulation_hours", 0),
                actions_count=data.get("actions_count", data.get("total_actions_count", 0)),
                stream=data.get("stream", cls.STREAM),
                stream_running=data.get("stream_running", False),
                stream_completed=data.get("stream_completed", False),
                started_at=data.get("started_at"),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                completed_at=data.get("completed_at"),
                error=data.get("error"),
                process_pid=data.get("process_pid"),
            )

            for round_item in data.get("rounds", []):
                actions = [cls._action_from_dict(item) for item in round_item.get("actions", [])]
                state.rounds.append(RoundSummary(
                    round_num=round_item.get("round_num", 0),
                    start_time=round_item.get("start_time", ""),
                    end_time=round_item.get("end_time"),
                    simulated_hour=round_item.get("simulated_hour", 0),
                    actions_count=round_item.get("actions_count", len(actions)),
                    active_agents=round_item.get("active_agents", []),
                    action_types=round_item.get("action_types", {}),
                    actions=actions,
                ))

            state.recent_actions = [cls._action_from_dict(item) for item in data.get("recent_actions", [])]
            return state
        except Exception as exc:
            logger.error(f"加载运行状态失败: {exc}")
            return None

    @classmethod
    def _action_from_dict(cls, item: Dict[str, Any]) -> AgentAction:
        return AgentAction(
            round_num=item.get("round_num", item.get("round", 0)),
            timestamp=item.get("timestamp", ""),
            stream=item.get("stream") or item.get("platform") or cls.STREAM,
            agent_id=item.get("agent_id", 0),
            agent_name=item.get("agent_name", ""),
            action_type=item.get("action_type", ""),
            action_args=item.get("action_args", {}),
            result=item.get("result"),
            success=item.get("success", True),
        )

    @classmethod
    def _save_run_state(cls, state: SimulationRunState):
        sim_dir = os.path.join(cls.RUN_STATE_DIR, state.simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        state.updated_at = datetime.now().isoformat()
        with open(os.path.join(sim_dir, "run_state.json"), 'w', encoding='utf-8') as handle:
            json.dump(state.to_detail_dict(), handle, ensure_ascii=False, indent=2)
        cls._run_states[state.simulation_id] = state

    @classmethod
    def start_simulation(
        cls,
        simulation_id: str,
        max_rounds: int = None,
        enable_graph_memory_update: bool = False,
        graph_id: str = None,
    ) -> SimulationRunState:
        existing = cls.get_run_state(simulation_id)
        if existing and existing.runner_status in [RunnerStatus.RUNNING, RunnerStatus.STARTING]:
            raise ValueError(f"模拟已在运行中: {simulation_id}")

        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        if not os.path.exists(config_path):
            raise ValueError("模拟配置不存在，请先调用 /prepare 接口")

        with open(config_path, 'r', encoding='utf-8') as handle:
            config = json.load(handle)

        total_rounds = cls._calc_total_rounds(config, max_rounds)
        state = SimulationRunState(
            simulation_id=simulation_id,
            runner_status=RunnerStatus.RUNNING,
            total_rounds=total_rounds,
            total_simulation_hours=config.get("time_config", {}).get("total_simulation_hours", 0),
            stream=cls.STREAM,
            stream_running=True,
            started_at=datetime.now().isoformat(),
            process_pid=os.getpid(),
        )
        cls._save_run_state(state)

        if enable_graph_memory_update:
            # 图谱记忆更新功能需要 Zep API，当前已移除。
            logger.info(f"Simulation {simulation_id}: graph memory update requested but Zep is not available, skipping")
        else:
            cls._graph_memory_enabled[simulation_id] = False

        stop_flag = threading.Event()
        cls._stop_flags[simulation_id] = stop_flag
        thread = threading.Thread(
            target=cls._run_worldfish_loop,
            args=(simulation_id, config, stop_flag),
            daemon=True,
        )
        cls._runner_threads[simulation_id] = thread
        thread.start()
        logger.info(f"WorldFish 内置模拟已启动: {simulation_id}")
        return state

    @classmethod
    def _calc_total_rounds(cls, config: Dict[str, Any], max_rounds: Optional[int]) -> int:
        time_config = config.get("time_config", {})
        total_hours = max(float(time_config.get("total_simulation_hours", 24) or 24), 1.0)
        minutes_per_round = max(int(time_config.get("minutes_per_round", 60) or 60), 1)
        total_rounds = max(int(total_hours * 60 / minutes_per_round), 1)
        if max_rounds is not None and max_rounds > 0:
            total_rounds = min(total_rounds, max_rounds)
        return total_rounds

    @classmethod
    def _run_worldfish_loop(cls, simulation_id: str, config: Dict[str, Any], stop_flag: threading.Event):
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        main_log_path = os.path.join(sim_dir, "simulation.log")
        state = cls.get_run_state(simulation_id)
        if not state:
            return

        agents = cls._load_agents(sim_dir, config)
        if not agents:
            state.runner_status = RunnerStatus.FAILED
            state.stream_running = False
            state.error = "没有可运行的 Agent Profile"
            cls._save_run_state(state)
            return

        try:
            state.runner_status = RunnerStatus.RUNNING
            state.stream_running = True
            cls._save_run_state(state)

            with open(main_log_path, 'w', encoding='utf-8') as log_file:
                cls._write_log(log_file, f"WorldFish simulation started: {simulation_id}")
                cls._write_env_status(sim_dir, "running")

                for round_num in range(1, state.total_rounds + 1):
                    if stop_flag.is_set():
                        state.runner_status = RunnerStatus.STOPPED
                        state.completed_at = datetime.now().isoformat()
                        cls._write_log(log_file, f"simulation stopped at round {round_num}")
                        break

                    round_start = datetime.now().isoformat()
                    simulated_hour = cls._calc_simulated_hour(config, round_num)
                    active_agents = cls._pick_round_agents(agents, round_num)
                    round_actions: List[AgentAction] = []
                    action_types: Dict[str, int] = {}

                    cls._append_event(sim_dir, {
                        "event_type": "round_start",
                        "round": round_num,
                        "timestamp": round_start,
                        "simulated_hour": simulated_hour,
                    })

                    for agent in active_agents:
                        action_data = cls._build_worldfish_action(config, agent, round_num, simulated_hour)
                        cls._append_event(sim_dir, action_data)
                        action = cls._action_from_dict(action_data)
                        state.add_action(action)
                        round_actions.append(action)
                        action_types[action.action_type] = action_types.get(action.action_type, 0) + 1
                        cls._queue_graph_memory_update(simulation_id, action)

                    cls._append_event(sim_dir, {
                        "event_type": "round_end",
                        "round": round_num,
                        "timestamp": datetime.now().isoformat(),
                        "simulated_hours": simulated_hour,
                        "total_actions": len(round_actions),
                    })

                    state.current_round = round_num
                    state.simulated_hours = simulated_hour
                    state.rounds.append(RoundSummary(
                        round_num=round_num,
                        start_time=round_start,
                        end_time=datetime.now().isoformat(),
                        simulated_hour=simulated_hour,
                        actions_count=len(round_actions),
                        active_agents=sorted({action.agent_id for action in round_actions}),
                        action_types=action_types,
                        actions=round_actions,
                    ))
                    cls._save_run_state(state)
                    cls._write_log(log_file, f"round {round_num}/{state.total_rounds}, actions={len(round_actions)}")
                    time.sleep(0.05)

                if state.runner_status != RunnerStatus.STOPPED:
                    state.runner_status = RunnerStatus.COMPLETED
                    state.completed_at = datetime.now().isoformat()

                cls._append_event(sim_dir, {
                    "event_type": "simulation_end",
                    "timestamp": datetime.now().isoformat(),
                    "total_rounds": state.current_round,
                    "total_actions": state.actions_count,
                })

                state.stream_running = False
                state.stream_completed = state.runner_status == RunnerStatus.COMPLETED
                cls._write_env_status(sim_dir, "stopped")
                cls._save_run_state(state)
                cls._write_log(log_file, f"WorldFish simulation finished: {state.runner_status.value}")

        except Exception as exc:
            logger.error(f"WorldFish 模拟线程失败: {simulation_id}, error={exc}")
            state.runner_status = RunnerStatus.FAILED
            state.error = str(exc)
            state.stream_running = False
            state.completed_at = datetime.now().isoformat()
            cls._write_env_status(sim_dir, "stopped")
            cls._save_run_state(state)
        finally:
            if cls._graph_memory_enabled.get(simulation_id, False):
                cls._graph_memory_enabled.pop(simulation_id, None)
            cls._runner_threads.pop(simulation_id, None)
            cls._stop_flags.pop(simulation_id, None)

    @classmethod
    def _load_agents(cls, sim_dir: str, config: Dict[str, Any]) -> List[WorldFishAgent]:
        agents: List[WorldFishAgent] = []
        profile_path = os.path.join(sim_dir, "worldfish_profiles.json")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r', encoding='utf-8') as handle:
                    data = json.load(handle)
                for index, item in enumerate(data if isinstance(data, list) else []):
                    agents.append(WorldFishAgent(
                        agent_id=int(item.get("agent_id", index)),
                        name=str(item.get("agent_name") or item.get("name") or f"agent_{index}"),
                        persona=str(item.get("persona") or item.get("bio") or ""),
                        faction=str(item.get("profession") or item.get("source_entity_type") or ""),
                        focus=cls._pick_focus(item),
                    ))
            except Exception as exc:
                logger.warning(f"读取 WorldFish profile 失败: {exc}")

        if not agents:
            for index, item in enumerate(config.get("agent_configs", [])):
                agents.append(WorldFishAgent(
                    agent_id=int(item.get("agent_id", index)),
                    name=str(item.get("entity_name") or item.get("name") or f"agent_{index}"),
                    persona=str(item.get("persona") or ""),
                    faction=str(item.get("entity_type") or item.get("faction") or item.get("profession") or ""),
                    focus=cls._pick_focus(item),
                ))
        return agents

    @classmethod
    def _pick_focus(cls, item: Dict[str, Any]) -> str:
        topics = item.get("interested_topics") or item.get("topics") or []
        if isinstance(topics, str):
            return topics
        if isinstance(topics, list) and topics:
            return str(topics[0])
        return "世界局势"

    @classmethod
    def _calc_simulated_hour(cls, config: Dict[str, Any], round_num: int) -> int:
        minutes = int(config.get("time_config", {}).get("minutes_per_round", 60) or 60)
        return (round_num * minutes // 60) % 24

    @classmethod
    def _pick_round_agents(cls, agents: List[WorldFishAgent], round_num: int) -> List[WorldFishAgent]:
        if not agents:
            return []
        picked = [agent for idx, agent in enumerate(agents) if (idx + round_num) % 3 == 0]
        return (picked or [agents[round_num % len(agents)]])[:12]

    @classmethod
    def _build_worldfish_action(
        cls,
        config: Dict[str, Any],
        agent: WorldFishAgent,
        round_num: int,
        simulated_hour: int,
    ) -> Dict[str, Any]:
        requirement = str(config.get("simulation_requirement") or "当前世界推演")
        event_types = config.get("worldfish_config", {}).get("event_types") or [
            "observe_world", "state_position", "adjust_plan", "spread_influence"
        ]
        action_type = event_types[(round_num + agent.agent_id) % len(event_types)]
        focus = agent.focus or "世界局势"
        result = f"{agent.name} 围绕「{focus}」观察到新的变化，并根据「{requirement[:48]}」调整自身立场。"
        return {
            "round": round_num,
            "round_num": round_num,
            "timestamp": datetime.now().isoformat(),
            "stream": cls.STREAM,
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "action_type": action_type,
            "action_args": {
                "focus": focus,
                "faction": agent.faction,
                "simulated_hour": simulated_hour,
                "runner": "worldfish_builtin",
            },
            "result": result,
            "success": True,
        }

    @classmethod
    def _append_event(cls, sim_dir: str, data: Dict[str, Any]):
        target_dir = os.path.join(sim_dir, cls.STREAM)
        os.makedirs(target_dir, exist_ok=True)
        path = os.path.join(target_dir, "actions.jsonl")
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write(json.dumps(data, ensure_ascii=False) + '\n')

    @classmethod
    def _queue_graph_memory_update(cls, simulation_id: str, action: AgentAction):
        # 图谱记忆更新已移除，保留空方法占位
        pass

    @classmethod
    def _write_log(cls, log_file, message: str):
        log_file.write(f"[{datetime.now().isoformat()}] {message}\n")
        log_file.flush()

    @classmethod
    def _write_env_status(cls, sim_dir: str, status: str):
        with open(os.path.join(sim_dir, "env_status.json"), 'w', encoding='utf-8') as handle:
            json.dump({
                "status": status,
                "stream": cls.STREAM,
                "available": status == "running",
                "timestamp": datetime.now().isoformat(),
                "runner": "worldfish_builtin",
            }, handle, ensure_ascii=False, indent=2)

    @classmethod
    def _read_actions_from_file(
        cls,
        file_path: str,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None,
    ) -> List[AgentAction]:
        if not os.path.exists(file_path):
            return []

        actions = []
        with open(file_path, 'r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "event_type" in data or "agent_id" not in data:
                    continue
                if agent_id is not None and data.get("agent_id") != agent_id:
                    continue
                if round_num is not None and data.get("round", data.get("round_num")) != round_num:
                    continue
                actions.append(cls._action_from_dict(data))
        return actions

    @classmethod
    def stop_simulation(cls, simulation_id: str) -> SimulationRunState:
        state = cls.get_run_state(simulation_id)
        if not state:
            raise ValueError(f"模拟不存在: {simulation_id}")
        if state.runner_status not in [RunnerStatus.RUNNING, RunnerStatus.PAUSED, RunnerStatus.STARTING]:
            raise ValueError(f"模拟未在运行: {simulation_id}, status={state.runner_status}")

        state.runner_status = RunnerStatus.STOPPING
        cls._save_run_state(state)
        stop_flag = cls._stop_flags.get(simulation_id)
        if stop_flag:
            stop_flag.set()
        thread = cls._runner_threads.get(simulation_id)
        if thread and thread.is_alive():
            thread.join(timeout=5)

        state = cls.get_run_state(simulation_id) or state
        if state.runner_status == RunnerStatus.STOPPING:
            state.runner_status = RunnerStatus.STOPPED
            state.stream_running = False
            state.completed_at = datetime.now().isoformat()
            cls._save_run_state(state)

        if cls._graph_memory_enabled.get(simulation_id, False):
            cls._graph_memory_enabled.pop(simulation_id, None)
        logger.info(f"模拟已停止: {simulation_id}")
        return state

    @classmethod
    def get_all_actions(
        cls,
        simulation_id: str,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None,
    ) -> List[AgentAction]:
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        path = os.path.join(sim_dir, cls.STREAM, "actions.jsonl")
        actions = cls._read_actions_from_file(path, agent_id=agent_id, round_num=round_num)
        actions.sort(key=lambda item: item.timestamp, reverse=True)
        return actions

    @classmethod
    def get_actions(
        cls,
        simulation_id: str,
        limit: int = 100,
        offset: int = 0,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None,
    ) -> List[AgentAction]:
        actions = cls.get_all_actions(simulation_id, agent_id=agent_id, round_num=round_num)
        return actions[offset:offset + limit]

    @classmethod
    def get_timeline(
        cls,
        simulation_id: str,
        start_round: int = 0,
        end_round: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        actions = cls.get_actions(simulation_id, limit=10000)
        rounds: Dict[int, Dict[str, Any]] = {}
        for action in actions:
            if action.round_num < start_round:
                continue
            if end_round is not None and action.round_num > end_round:
                continue
            item = rounds.setdefault(action.round_num, {
                "round_num": action.round_num,
                "actions_count": 0,
                "active_agents": set(),
                "action_types": {},
                "first_action_time": action.timestamp,
                "last_action_time": action.timestamp,
            })
            item["actions_count"] += 1
            item["active_agents"].add(action.agent_id)
            item["action_types"][action.action_type] = item["action_types"].get(action.action_type, 0) + 1
            item["last_action_time"] = action.timestamp

        result = []
        for round_num in sorted(rounds.keys()):
            item = rounds[round_num]
            result.append({
                "round_num": round_num,
                "total_actions": item["actions_count"],
                "actions_count": item["actions_count"],
                "active_agents_count": len(item["active_agents"]),
                "active_agents": list(item["active_agents"]),
                "action_types": item["action_types"],
                "first_action_time": item["first_action_time"],
                "last_action_time": item["last_action_time"],
            })
        return result

    @classmethod
    def get_agent_stats(cls, simulation_id: str) -> List[Dict[str, Any]]:
        actions = cls.get_actions(simulation_id, limit=10000)
        stats: Dict[int, Dict[str, Any]] = {}
        for action in actions:
            item = stats.setdefault(action.agent_id, {
                "agent_id": action.agent_id,
                "agent_name": action.agent_name,
                "total_actions": 0,
                "action_types": {},
                "first_action_time": action.timestamp,
                "last_action_time": action.timestamp,
            })
            item["total_actions"] += 1
            item["action_types"][action.action_type] = item["action_types"].get(action.action_type, 0) + 1
            item["last_action_time"] = action.timestamp
        return sorted(stats.values(), key=lambda item: item["total_actions"], reverse=True)

    @classmethod
    def cleanup_simulation_logs(cls, simulation_id: str) -> Dict[str, Any]:
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return {"success": True, "message": "模拟目录不存在，无需清理"}

        cleaned_files = []
        errors = []
        for filename in ["run_state.json", "simulation.log", "stdout.log", "stderr.log", "env_status.json"]:
            path = os.path.join(sim_dir, filename)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    cleaned_files.append(filename)
                except Exception as exc:
                    errors.append(f"删除 {filename} 失败: {exc}")

        actions_path = os.path.join(sim_dir, cls.STREAM, "actions.jsonl")
        if os.path.exists(actions_path):
            try:
                os.remove(actions_path)
                cleaned_files.append(f"{cls.STREAM}/actions.jsonl")
            except Exception as exc:
                errors.append(f"删除 {cls.STREAM}/actions.jsonl 失败: {exc}")

        cls._run_states.pop(simulation_id, None)
        return {"success": len(errors) == 0, "cleaned_files": cleaned_files, "errors": errors or None}

    @classmethod
    def cleanup_all_simulations(cls):
        if cls._cleanup_done:
            return
        cls._cleanup_done = True
        if not cls._runner_threads and not cls._graph_memory_enabled:
            return

        logger.info("正在清理所有模拟线程...")
        for stop_flag in list(cls._stop_flags.values()):
            stop_flag.set()
        for simulation_id, thread in list(cls._runner_threads.items()):
            if thread.is_alive():
                thread.join(timeout=5)
            state = cls.get_run_state(simulation_id)
            if state and state.runner_status in [RunnerStatus.RUNNING, RunnerStatus.STARTING, RunnerStatus.STOPPING]:
                state.runner_status = RunnerStatus.STOPPED
                state.stream_running = False
                state.completed_at = datetime.now().isoformat()
                state.error = "服务器关闭，模拟被终止"
                cls._save_run_state(state)

        try:
            cls._runner_threads.clear()
            cls._stop_flags.clear()
            cls._graph_memory_enabled.clear()
        except Exception:
            pass
        logger.info("模拟线程清理完成")

    @classmethod
    def register_cleanup(cls):
        global _cleanup_registered
        if _cleanup_registered:
            return

        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        has_sighup = hasattr(signal, 'SIGHUP')
        original_sighup = signal.getsignal(signal.SIGHUP) if has_sighup else None

        def cleanup_handler(signum=None, frame=None):
            if cls._runner_threads or cls._graph_memory_enabled:
                logger.info(f"收到信号 {signum}，开始清理...")
            cls.cleanup_all_simulations()
            if signum == signal.SIGINT and callable(original_sigint):
                original_sigint(signum, frame)
            elif signum == signal.SIGTERM and callable(original_sigterm):
                original_sigterm(signum, frame)
            elif has_sighup and signum == signal.SIGHUP and callable(original_sighup):
                original_sighup(signum, frame)
            elif signum in (signal.SIGINT, signal.SIGTERM):
                raise KeyboardInterrupt

        atexit.register(cls.cleanup_all_simulations)
        try:
            signal.signal(signal.SIGTERM, cleanup_handler)
            signal.signal(signal.SIGINT, cleanup_handler)
            if has_sighup:
                signal.signal(signal.SIGHUP, cleanup_handler)
        except ValueError:
            logger.warning("无法注册信号处理器（不在主线程），仅使用 atexit")
        _cleanup_registered = True

    @classmethod
    def get_running_simulations(cls) -> List[str]:
        running = []
        for simulation_id, thread in cls._runner_threads.items():
            state = cls.get_run_state(simulation_id)
            if thread.is_alive() and state and state.runner_status == RunnerStatus.RUNNING:
                running.append(simulation_id)
        return running

    @classmethod
    def check_env_alive(cls, simulation_id: str) -> bool:
        state = cls.get_run_state(simulation_id)
        return bool(state and state.runner_status == RunnerStatus.RUNNING)

    @classmethod
    def get_env_status_detail(cls, simulation_id: str) -> Dict[str, Any]:
        state = cls.get_run_state(simulation_id)
        if not state:
            return {"status": "stopped", "available": False, "stream": cls.STREAM, "timestamp": None}
        return {
            "status": "running" if state.runner_status == RunnerStatus.RUNNING else state.runner_status.value,
            "available": state.stream_running,
            "stream": state.stream,
            "timestamp": state.updated_at,
            "runner": "worldfish_builtin",
        }

    @classmethod
    def interview_agent(
        cls,
        simulation_id: str,
        agent_id: int,
        prompt: str,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        state = cls.get_run_state(simulation_id)
        if not state:
            raise ValueError(f"模拟不存在: {simulation_id}")
        actions = cls.get_actions(simulation_id, agent_id=agent_id, limit=5)
        memory = "；".join([action.result or action.action_type for action in actions]) or "暂无行动记录"
        result = {
            "response": f"我是 Agent {agent_id}。基于目前记录：{memory}。对于问题「{prompt}」，我会优先保持自身立场并观察下一轮变化。",
            "runner": "worldfish_builtin",
        }
        return {
            "success": True,
            "agent_id": agent_id,
            "prompt": prompt,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }

    @classmethod
    def interview_agents_batch(
        cls,
        simulation_id: str,
        interviews: List[Dict[str, Any]],
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        results = {}
        for item in interviews:
            agent_id = item.get("agent_id")
            if agent_id is None:
                continue
            result = cls.interview_agent(
                simulation_id=simulation_id,
                agent_id=int(agent_id),
                prompt=item.get("prompt", ""),
                timeout=timeout,
            )
            results[str(agent_id)] = result.get("result")
        return {
            "success": True,
            "interviews_count": len(results),
            "result": {"results": results},
            "timestamp": datetime.now().isoformat(),
        }

    @classmethod
    def interview_all_agents(
        cls,
        simulation_id: str,
        prompt: str,
        timeout: float = 180.0,
    ) -> Dict[str, Any]:
        config_path = os.path.join(cls.RUN_STATE_DIR, simulation_id, "simulation_config.json")
        if not os.path.exists(config_path):
            raise ValueError(f"模拟配置不存在: {simulation_id}")
        with open(config_path, 'r', encoding='utf-8') as handle:
            config = json.load(handle)
        agents = cls._load_agents(os.path.join(cls.RUN_STATE_DIR, simulation_id), config)
        interviews = [{"agent_id": agent.agent_id, "prompt": prompt} for agent in agents]
        return cls.interview_agents_batch(simulation_id, interviews, timeout=timeout)

    @classmethod
    def close_simulation_env(cls, simulation_id: str, timeout: float = 30.0) -> Dict[str, Any]:
        state = cls.get_run_state(simulation_id)
        if not state or state.runner_status != RunnerStatus.RUNNING:
            return {"success": True, "message": "环境已经关闭"}
        cls.stop_simulation(simulation_id)
        return {"success": True, "message": "环境已关闭", "timestamp": datetime.now().isoformat()}

    @classmethod
    def get_interview_history(
        cls,
        simulation_id: str,
        agent_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        actions = cls.get_actions(simulation_id, agent_id=agent_id, limit=limit)
        return [
            {
                "agent_id": action.agent_id,
                "response": action.result,
                "prompt": action.action_type,
                "timestamp": action.timestamp,
                "stream": action.stream,
            }
            for action in actions
        ]
