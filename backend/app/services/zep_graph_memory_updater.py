"""
WorldFish 图谱记忆更新服务。

接收内置 runner 产生的 WorldFish 事件，把角色观察、立场、计划和影响扩散
批量写入 Zep 图谱。该模块不再理解旧社交平台动作，也不再读取旧数据库。
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

from zep_cloud.client import Zep

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_locale, set_locale

logger = get_logger('worldfish.zep_graph_memory_updater')


@dataclass
class AgentActivity:
    """WorldFish 角色活动记录。"""

    stream: str
    agent_id: int
    agent_name: str
    action_type: str
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str

    def to_episode_text(self) -> str:
        focus = self.action_args.get("focus") or "当前局势"
        faction = self.action_args.get("faction") or ""
        result = self.action_args.get("result") or ""
        simulated_hour = self.action_args.get("simulated_hour")

        if self.action_type == "observe_world":
            event_text = f"观察到「{focus}」出现新变化"
        elif self.action_type == "state_position":
            event_text = f"围绕「{focus}」重新确认自身位置"
        elif self.action_type == "adjust_plan":
            event_text = f"根据「{focus}」调整后续计划"
        elif self.action_type == "spread_influence":
            event_text = f"尝试围绕「{focus}」扩散影响"
        else:
            event_text = f"执行 WorldFish 事件「{self.action_type}」"

        details = []
        if faction:
            details.append(f"身份/阵营：{faction}")
        if simulated_hour is not None:
            details.append(f"模拟小时：{simulated_hour}")
        if result:
            details.append(f"结果：{result}")

        suffix = "；" + "；".join(details) if details else ""
        return f"第 {self.round_num} 轮，{self.agent_name} {event_text}{suffix}。"


class ZepGraphMemoryUpdater:
    """把 WorldFish 事件批量写入 Zep 图谱。"""

    BATCH_SIZE = 5
    SEND_INTERVAL = 0.5
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self, graph_id: str, api_key: Optional[str] = None):
        self.graph_id = graph_id
        self.api_key = api_key or Config.ZEP_API_KEY
        if not self.api_key:
            raise ValueError("ZEP_API_KEY未配置")

        self.client = Zep(api_key=self.api_key)
        self._activity_queue: Queue[AgentActivity] = Queue()
        self._buffer: List[AgentActivity] = []
        self._buffer_lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        self._total_activities = 0
        self._total_sent = 0
        self._total_items_sent = 0
        self._failed_count = 0
        self._skipped_count = 0

        logger.info(f"WorldFish 图谱记忆更新器初始化完成: graph_id={graph_id}")

    def start(self):
        if self._running:
            return

        current_locale = get_locale()
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(current_locale,),
            daemon=True,
            name=f"WorldFishMemoryUpdater-{self.graph_id[:8]}",
        )
        self._worker_thread.start()
        logger.info(f"WorldFish 图谱记忆更新器已启动: graph_id={self.graph_id}")

    def stop(self):
        self._running = False
        self._flush_remaining()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
        logger.info(
            f"WorldFish 图谱记忆更新器已停止: graph_id={self.graph_id}, "
            f"total_activities={self._total_activities}, batches_sent={self._total_sent}, "
            f"items_sent={self._total_items_sent}, failed={self._failed_count}, skipped={self._skipped_count}"
        )

    def add_activity(self, activity: AgentActivity):
        if not activity.action_type:
            self._skipped_count += 1
            return
        self._activity_queue.put(activity)
        self._total_activities += 1

    def add_activity_from_dict(self, data: Dict[str, Any]):
        if "event_type" in data:
            return
        self.add_activity(AgentActivity(
            stream=data.get("stream") or "worldfish",
            agent_id=int(data.get("agent_id", 0) or 0),
            agent_name=str(data.get("agent_name") or ""),
            action_type=str(data.get("action_type") or ""),
            action_args=data.get("action_args", {}) or {},
            round_num=int(data.get("round", data.get("round_num", 0)) or 0),
            timestamp=str(data.get("timestamp") or datetime.now().isoformat()),
        ))

    def _worker_loop(self, locale: str = 'zh'):
        set_locale(locale)
        while self._running or not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get(timeout=1)
            except Empty:
                continue

            batch = None
            with self._buffer_lock:
                self._buffer.append(activity)
                if len(self._buffer) >= self.BATCH_SIZE:
                    batch = self._buffer[:self.BATCH_SIZE]
                    self._buffer = self._buffer[self.BATCH_SIZE:]

            if batch:
                self._send_batch_activities(batch)
                time.sleep(self.SEND_INTERVAL)

    def _send_batch_activities(self, activities: List[AgentActivity]):
        if not activities:
            return

        combined_text = "\n".join(activity.to_episode_text() for activity in activities)
        for attempt in range(self.MAX_RETRIES):
            try:
                self.client.graph.add(
                    graph_id=self.graph_id,
                    type="text",
                    data=combined_text,
                )
                self._total_sent += 1
                self._total_items_sent += len(activities)
                logger.info(f"成功写入 {len(activities)} 条 WorldFish 活动到图谱 {self.graph_id}")
                return
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"WorldFish 活动写入 Zep 失败 ({attempt + 1}/{self.MAX_RETRIES}): {e}")
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"WorldFish 活动写入 Zep 失败，已重试 {self.MAX_RETRIES} 次: {e}")
                    self._failed_count += 1

    def _flush_remaining(self):
        while not self._activity_queue.empty():
            try:
                with self._buffer_lock:
                    self._buffer.append(self._activity_queue.get_nowait())
            except Empty:
                break

        with self._buffer_lock:
            remaining = self._buffer
            self._buffer = []

        if remaining:
            self._send_batch_activities(remaining)

    def get_stats(self) -> Dict[str, Any]:
        with self._buffer_lock:
            buffer_size = len(self._buffer)
        return {
            "graph_id": self.graph_id,
            "batch_size": self.BATCH_SIZE,
            "total_activities": self._total_activities,
            "batches_sent": self._total_sent,
            "items_sent": self._total_items_sent,
            "failed_count": self._failed_count,
            "skipped_count": self._skipped_count,
            "queue_size": self._activity_queue.qsize(),
            "buffer_size": buffer_size,
            "running": self._running,
            "runner": "worldfish_builtin",
        }


class ZepGraphMemoryManager:
    """管理多个模拟的 Zep 图谱记忆更新器。"""

    _updaters: Dict[str, ZepGraphMemoryUpdater] = {}
    _lock = threading.Lock()
    _stop_all_done = False

    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> ZepGraphMemoryUpdater:
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
            updater = ZepGraphMemoryUpdater(graph_id)
            updater.start()
            cls._updaters[simulation_id] = updater
            cls._stop_all_done = False
            logger.info(f"创建 WorldFish 图谱记忆更新器: simulation_id={simulation_id}, graph_id={graph_id}")
            return updater

    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[ZepGraphMemoryUpdater]:
        return cls._updaters.get(simulation_id)

    @classmethod
    def stop_updater(cls, simulation_id: str):
        with cls._lock:
            updater = cls._updaters.pop(simulation_id, None)
        if updater:
            updater.stop()
            logger.info(f"已停止 WorldFish 图谱记忆更新器: simulation_id={simulation_id}")

    @classmethod
    def stop_all(cls):
        if cls._stop_all_done:
            return
        cls._stop_all_done = True
        with cls._lock:
            items = list(cls._updaters.items())
            cls._updaters.clear()
        for simulation_id, updater in items:
            try:
                updater.stop()
            except Exception as e:
                logger.error(f"停止更新器失败: simulation_id={simulation_id}, error={e}")
        if items:
            logger.info("已停止所有 WorldFish 图谱记忆更新器")

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        return {sim_id: updater.get_stats() for sim_id, updater in cls._updaters.items()}
