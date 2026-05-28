"""
异步任务生命周期管理
单例 TaskManager 提供线程安全的 create / update / query / cleanup。
"""

import uuid
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from ..utils.locale import t


class TaskPhase(str, Enum):
    QUEUED = "pending"
    RUNNING = "processing"
    DONE = "completed"
    FAULTED = "failed"


@dataclass
class AsyncTask:
    """描述一次异步作业的轻量记录。"""

    uid: str
    category: str
    phase: TaskPhase
    created: datetime
    touched: datetime
    pct: int = 0
    note: str = ""
    outcome: Optional[Dict] = None
    fault: Optional[str] = None
    extra: Dict = field(default_factory=dict)
    detail: Dict = field(default_factory=dict)

    def serialize(self) -> Dict[str, Any]:
        return {
            "task_id": self.uid,
            "task_type": self.category,
            "status": self.phase.value,
            "created_at": self.created.isoformat(),
            "updated_at": self.touched.isoformat(),
            "progress": self.pct,
            "message": self.note,
            "progress_detail": self.detail,
            "result": self.outcome,
            "error": self.fault,
            "metadata": self.extra,
        }


class TaskManager:
    _singleton: Optional["TaskManager"] = None
    _singleton_guard = threading.Lock()

    def __new__(cls):
        if cls._singleton is None:
            with cls._singleton_guard:
                if cls._singleton is None:
                    obj = super().__new__(cls)
                    obj._journal: Dict[str, AsyncTask] = {}
                    obj._journal_guard = threading.Lock()
                    cls._singleton = obj
        return cls._singleton

    def spawn(self, category: str, extra: Optional[Dict] = None) -> str:
        uid = str(uuid.uuid4())
        now = datetime.now()
        task = AsyncTask(
            uid=uid,
            category=category,
            phase=TaskPhase.QUEUED,
            created=now,
            touched=now,
            extra=extra or {},
        )
        with self._journal_guard:
            self._journal[uid] = task
        return uid

    def fetch(self, uid: str) -> Optional[AsyncTask]:
        with self._journal_guard:
            return self._journal.get(uid)

    def patch(
        self,
        uid: str,
        *,
        phase: Optional[TaskPhase] = None,
        pct: Optional[int] = None,
        note: Optional[str] = None,
        outcome: Optional[Dict] = None,
        fault: Optional[str] = None,
        detail: Optional[Dict] = None,
    ):
        with self._journal_guard:
            task = self._journal.get(uid)
            if not task:
                return
            task.touched = datetime.now()
            if phase is not None:
                task.phase = phase
            if pct is not None:
                task.pct = pct
            if note is not None:
                task.note = note
            if outcome is not None:
                task.outcome = outcome
            if fault is not None:
                task.fault = fault
            if detail is not None:
                task.detail = detail

    def mark_done(self, uid: str, outcome: Dict):
        self.patch(uid, phase=TaskPhase.DONE, pct=100, note=t('progress.taskComplete'), outcome=outcome)

    def mark_faulted(self, uid: str, fault: str):
        self.patch(uid, phase=TaskPhase.FAULTED, note=t('progress.taskFailed'), fault=fault)

    def list_tasks(self, category: Optional[str] = None) -> list:
        with self._journal_guard:
            entries = list(self._journal.values())
            if category:
                entries = [e for e in entries if e.category == category]
            return [e.serialize() for e in sorted(entries, key=lambda x: x.created, reverse=True)]

    def purge_stale(self, max_age_hours: int = 24):
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        with self._journal_guard:
            stale = [
                uid for uid, task in self._journal.items()
                if task.created < cutoff and task.phase in (TaskPhase.DONE, TaskPhase.FAULTED)
            ]
            for uid in stale:
                del self._journal[uid]


# 兼容旧名称，避免调用方大规模改动
TaskStatus = TaskPhase
Task = AsyncTask

# 兼容旧方法名
TaskManager.create_task = TaskManager.spawn
TaskManager.get_task = TaskManager.fetch
TaskManager.update_task = TaskManager.patch
TaskManager.complete_task = TaskManager.mark_done
TaskManager.fail_task = TaskManager.mark_faulted
TaskManager.cleanup_old_tasks = TaskManager.purge_stale
