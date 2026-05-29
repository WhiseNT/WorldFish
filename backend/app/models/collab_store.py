"""联机协作 SQLite 持久化层。

使用标准库 sqlite3 + WAL 模式，提供并发安全的房间 / 成员 / 事件存储，
替代早期 JSON 整文件读写原型。设计目标：

- 单机零部署（标准库自带）
- 事件序列由数据库自增主键保证全局唯一递增
- 读写走索引，避免整文件扫描
- 线程安全（每线程独立连接 + busy_timeout）
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS collab_users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'local',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    room_type TEXT NOT NULL DEFAULT 'general',
    linked_world_id TEXT NOT NULL DEFAULT '',
    settings TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rooms_workspace ON rooms(workspace_id);
CREATE INDEX IF NOT EXISTS idx_rooms_world ON rooms(linked_world_id);

CREATE TABLE IF NOT EXISTS room_members (
    room_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    display_name TEXT NOT NULL DEFAULT '成员',
    joined_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY (room_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_members_room ON room_members(room_id);

CREATE TABLE IF NOT EXISTS room_events (
    global_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL,
    room_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_room_seq ON room_events(room_id, seq);
CREATE INDEX IF NOT EXISTS idx_events_room ON room_events(room_id);
"""


def _now() -> str:
    return datetime.now().isoformat()


class CollabStore:
    """SQLite 协作存储。线程局部连接，WAL 并发安全。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_lock = threading.Lock()
        self._initialized = False

    # ---------- 连接管理 ----------

    def _connect(self) -> sqlite3.Connection:
        conn = getattr(self._local, 'conn', None)
        if conn is not None:
            return conn
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA synchronous=NORMAL')
        self._local.conn = conn
        self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection):
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            conn.executescript(_SCHEMA)
            conn.commit()
            self._initialized = True

    def close(self):
        conn = getattr(self._local, 'conn', None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    def reset(self):
        """关闭连接并强制下次重新初始化（测试切库用）。"""
        self.close()
        self._initialized = False

    # ---------- 通用辅助 ----------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    @staticmethod
    def _load_json(value: Any) -> Dict[str, Any]:
        if not value:
            return {}
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}

    # ---------- 用户 ----------

    def upsert_user(self, user: Dict[str, Any]):
        conn = self._connect()
        conn.execute(
            """INSERT INTO collab_users (id, name, kind, created_at, updated_at)
               VALUES (:id, :name, :kind, :created_at, :updated_at)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name, updated_at=excluded.updated_at""",
            {
                'id': user['id'],
                'name': user.get('name') or '本地用户',
                'kind': user.get('kind') or 'local',
                'created_at': user.get('created_at') or _now(),
                'updated_at': user.get('updated_at') or _now(),
            },
        )
        conn.commit()

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        row = conn.execute('SELECT * FROM collab_users WHERE id=?', (user_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    # ---------- 工作区 ----------

    def upsert_workspace(self, workspace: Dict[str, Any]):
        conn = self._connect()
        conn.execute(
            """INSERT INTO workspaces (id, name, owner_id, description, created_at, updated_at)
               VALUES (:id, :name, :owner_id, :description, :created_at, :updated_at)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name, description=excluded.description, updated_at=excluded.updated_at""",
            {
                'id': workspace['id'],
                'name': workspace.get('name') or '默认工作区',
                'owner_id': workspace.get('owner_id') or 'local_user',
                'description': workspace.get('description') or '',
                'created_at': workspace.get('created_at') or _now(),
                'updated_at': workspace.get('updated_at') or _now(),
            },
        )
        conn.commit()

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        row = conn.execute('SELECT * FROM workspaces WHERE id=?', (workspace_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_workspaces(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute('SELECT * FROM workspaces ORDER BY created_at').fetchall()
        return [self._row_to_dict(row) for row in rows]

    # ---------- 房间 ----------

    def upsert_room(self, room: Dict[str, Any]):
        conn = self._connect()
        conn.execute(
            """INSERT INTO rooms (id, workspace_id, name, owner_id, description, room_type, linked_world_id, settings, created_at, updated_at)
               VALUES (:id, :workspace_id, :name, :owner_id, :description, :room_type, :linked_world_id, :settings, :created_at, :updated_at)
               ON CONFLICT(id) DO UPDATE SET
                   name=excluded.name, description=excluded.description, room_type=excluded.room_type,
                   linked_world_id=excluded.linked_world_id, settings=excluded.settings, updated_at=excluded.updated_at""",
            {
                'id': room['id'],
                'workspace_id': room.get('workspace_id') or 'local_workspace',
                'name': room.get('name') or '新房间',
                'owner_id': room.get('owner_id') or 'local_user',
                'description': room.get('description') or '',
                'room_type': room.get('room_type') or 'general',
                'linked_world_id': room.get('linked_world_id') or '',
                'settings': json.dumps(room.get('settings') or {}, ensure_ascii=False),
                'created_at': room.get('created_at') or _now(),
                'updated_at': room.get('updated_at') or _now(),
            },
        )
        conn.commit()

    def _room_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = self._row_to_dict(row)
        data['settings'] = self._load_json(data.get('settings'))
        return data

    def get_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        row = conn.execute('SELECT * FROM rooms WHERE id=?', (room_id,)).fetchone()
        return self._room_row(row) if row else None

    def list_rooms(self, workspace_id: str = '') -> List[Dict[str, Any]]:
        conn = self._connect()
        if workspace_id:
            rows = conn.execute('SELECT * FROM rooms WHERE workspace_id=? ORDER BY created_at', (workspace_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM rooms ORDER BY created_at').fetchall()
        return [self._room_row(row) for row in rows]

    def find_room_by_world(self, world_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        row = conn.execute('SELECT * FROM rooms WHERE linked_world_id=? ORDER BY created_at LIMIT 1', (world_id,)).fetchone()
        return self._room_row(row) if row else None

    # ---------- 成员 ----------

    def get_member(self, room_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        row = conn.execute('SELECT * FROM room_members WHERE room_id=? AND user_id=?', (room_id, user_id)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_members(self, room_id: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute('SELECT * FROM room_members WHERE room_id=? ORDER BY joined_at', (room_id,)).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def upsert_member(self, member: Dict[str, Any], update_existing: bool = True) -> bool:
        """写入成员。返回是否是新加入（用于决定是否发 joined 事件）。"""
        conn = self._connect()
        existing = self.get_member(member['room_id'], member['user_id'])
        if existing:
            if update_existing:
                conn.execute(
                    'UPDATE room_members SET display_name=?, role=?, last_seen_at=? WHERE room_id=? AND user_id=?',
                    (
                        member.get('display_name') or existing.get('display_name'),
                        member.get('role') or existing.get('role'),
                        member.get('last_seen_at') or _now(),
                        member['room_id'],
                        member['user_id'],
                    ),
                )
                conn.commit()
            return False
        conn.execute(
            """INSERT INTO room_members (room_id, user_id, role, display_name, joined_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                member['room_id'],
                member['user_id'],
                member.get('role') or 'member',
                member.get('display_name') or '成员',
                member.get('joined_at') or _now(),
                member.get('last_seen_at') or _now(),
            ),
        )
        conn.commit()
        return True

    def touch_member(self, room_id: str, user_id: str, last_seen_at: str) -> bool:
        conn = self._connect()
        cur = conn.execute(
            'UPDATE room_members SET last_seen_at=? WHERE room_id=? AND user_id=?',
            (last_seen_at, room_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def remove_member(self, room_id: str, user_id: str) -> bool:
        conn = self._connect()
        cur = conn.execute('DELETE FROM room_members WHERE room_id=? AND user_id=?', (room_id, user_id))
        conn.commit()
        return cur.rowcount > 0

    # ---------- 事件 ----------

    def append_event(self, event_id: str, room_id: str, event_type: str, actor_id: str, payload: Dict[str, Any], created_at: str) -> int:
        """在单个事务内分配房间内递增 seq 并写入，返回 seq。"""
        conn = self._connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT COALESCE(MAX(seq), 0) AS max_seq FROM room_events WHERE room_id=?', (room_id,)).fetchone()
            seq = int(row['max_seq']) + 1
            conn.execute(
                """INSERT INTO room_events (id, room_id, seq, type, actor_id, payload, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_id, room_id, seq, event_type, actor_id, json.dumps(payload or {}, ensure_ascii=False), created_at),
            )
            conn.commit()
            return seq
        except Exception:
            conn.rollback()
            raise

    def list_events(self, room_id: str, since: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute(
            'SELECT * FROM room_events WHERE room_id=? AND seq > ? ORDER BY seq LIMIT ?',
            (room_id, int(since or 0), int(limit)),
        ).fetchall()
        events = []
        for row in rows:
            data = self._row_to_dict(row)
            data.pop('global_seq', None)
            data['payload'] = self._load_json(data.get('payload'))
            events.append(data)
        return events

    def latest_seq(self, room_id: str) -> int:
        conn = self._connect()
        row = conn.execute('SELECT COALESCE(MAX(seq), 0) AS max_seq FROM room_events WHERE room_id=?', (room_id,)).fetchone()
        return int(row['max_seq'])

    def count_remaining(self, room_id: str, since: int, limit: int) -> int:
        conn = self._connect()
        row = conn.execute(
            'SELECT COUNT(*) AS n FROM room_events WHERE room_id=? AND seq > ?',
            (room_id, int(since or 0)),
        ).fetchone()
        return max(0, int(row['n']) - int(limit))

    def find_latest_event(self, room_id: str, event_type: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        row = conn.execute(
            'SELECT * FROM room_events WHERE room_id=? AND type=? ORDER BY seq DESC LIMIT 1',
            (room_id, event_type),
        ).fetchone()
        if not row:
            return None
        data = self._row_to_dict(row)
        data.pop('global_seq', None)
        data['payload'] = self._load_json(data.get('payload'))
        return data

    def stats(self) -> Dict[str, Any]:
        conn = self._connect()
        rooms = conn.execute('SELECT COUNT(*) AS n FROM rooms').fetchone()['n']
        events = conn.execute('SELECT COUNT(*) AS n FROM room_events').fetchone()['n']
        members = conn.execute('SELECT COUNT(*) AS n FROM room_members').fetchone()['n']
        return {'rooms': int(rooms), 'events': int(events), 'members': int(members)}

    def has_any_data(self) -> bool:
        conn = self._connect()
        row = conn.execute('SELECT COUNT(*) AS n FROM rooms').fetchone()
        return int(row['n']) > 0


def migrate_json_if_needed(store: CollabStore, json_dir: str):
    """若检测到旧 JSON 数据且数据库为空，则一次性导入。"""
    base = Path(json_dir)
    if not base.exists() or store.has_any_data():
        return

    def _read(name: str) -> list:
        path = base / name
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return data if isinstance(data, list) else []
        except (ValueError, OSError):
            return []

    for user in _read('users.json'):
        if user.get('id'):
            store.upsert_user(user)
    for workspace in _read('workspaces.json'):
        if workspace.get('id'):
            store.upsert_workspace(workspace)
    for room in _read('rooms.json'):
        if room.get('id'):
            store.upsert_room(room)
    for member in _read('members.json'):
        if member.get('room_id') and member.get('user_id'):
            store.upsert_member(member, update_existing=False)

    events_dir = base / 'events'
    if events_dir.exists():
        for event_file in sorted(events_dir.glob('*.jsonl')):
            for line in event_file.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                room_id = event.get('room_id')
                if not room_id:
                    continue
                store.append_event(
                    event_id=event.get('id') or f"evt_{os.urandom(6).hex()}",
                    room_id=room_id,
                    event_type=event.get('type') or 'event',
                    actor_id=event.get('actor_id') or 'system',
                    payload=event.get('payload') if isinstance(event.get('payload'), dict) else {},
                    created_at=event.get('created_at') or _now(),
                )
