"""联机协作模型与持久化仓库。

数据访问走 SQLite（collab_store），提供并发安全的房间 / 成员 / 事件存储。
对外方法签名保持向后兼容，新增权限校验与乐观并发能力。
"""

from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..config import Config
from ..core import identity
from .collab_store import CollabStore, migrate_json_if_needed

MEMBER_ONLINE_WINDOW_SECONDS = 45
MAX_EVENT_LIMIT = 500


def _now() -> str:
    return datetime.now().isoformat()


def _parse_time(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


@dataclass
class CollabUser:
    id: str
    name: str
    kind: str = 'local'
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CollabUser':
        return cls(
            id=data.get('id') or f'user_{uuid.uuid4().hex[:12]}',
            name=data.get('name') or '本地用户',
            kind=data.get('kind') or 'local',
            created_at=data.get('created_at') or _now(),
            updated_at=data.get('updated_at') or _now(),
        )


@dataclass
class Workspace:
    id: str
    name: str
    owner_id: str
    description: str = ''
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workspace':
        return cls(
            id=data.get('id') or f'ws_{uuid.uuid4().hex[:12]}',
            name=data.get('name') or '默认工作区',
            owner_id=data.get('owner_id') or 'local_user',
            description=data.get('description') or '',
            created_at=data.get('created_at') or _now(),
            updated_at=data.get('updated_at') or _now(),
        )


@dataclass
class Room:
    id: str
    workspace_id: str
    name: str
    owner_id: str
    description: str = ''
    room_type: str = 'general'
    linked_world_id: str = ''
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Room':
        return cls(
            id=data.get('id') or f'room_{uuid.uuid4().hex[:12]}',
            workspace_id=data.get('workspace_id') or 'local_workspace',
            name=data.get('name') or '本地房间',
            owner_id=data.get('owner_id') or 'local_user',
            description=data.get('description') or '',
            room_type=data.get('room_type') or 'general',
            linked_world_id=data.get('linked_world_id') or '',
            settings=data.get('settings') if isinstance(data.get('settings'), dict) else {},
            created_at=data.get('created_at') or _now(),
            updated_at=data.get('updated_at') or _now(),
        )


@dataclass
class RoomMember:
    room_id: str
    user_id: str
    role: str = 'owner'
    display_name: str = '本地用户'
    joined_at: str = field(default_factory=_now)
    last_seen_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        data = self.__dict__.copy()
        seen_at = _parse_time(self.last_seen_at)
        data['online'] = bool(seen_at and datetime.now() - seen_at < timedelta(seconds=MEMBER_ONLINE_WINDOW_SECONDS))
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoomMember':
        return cls(
            room_id=data.get('room_id') or '',
            user_id=data.get('user_id') or 'local_user',
            role=data.get('role') or 'member',
            display_name=data.get('display_name') or data.get('user_id') or '成员',
            joined_at=data.get('joined_at') or _now(),
            last_seen_at=data.get('last_seen_at') or _now(),
        )


@dataclass
class RoomEvent:
    id: str
    room_id: str
    seq: int
    type: str
    actor_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoomEvent':
        return cls(
            id=data.get('id') or f'evt_{uuid.uuid4().hex[:12]}',
            room_id=data.get('room_id') or '',
            seq=int(data.get('seq') or 0),
            type=data.get('type') or 'event',
            actor_id=data.get('actor_id') or 'system',
            payload=data.get('payload') if isinstance(data.get('payload'), dict) else {},
            created_at=data.get('created_at') or _now(),
        )


class ConflictError(Exception):
    """乐观并发冲突。"""

    def __init__(self, message: str, latest_event: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.latest_event = latest_event


class CollabManager:
    """基于 SQLite 的协作仓库。对外方法保持向后兼容。"""

    BASE_DIR = os.path.join(Config.UPLOAD_FOLDER, 'collab')
    _store: Optional[CollabStore] = None
    _store_path: Optional[str] = None
    _lock = threading.RLock()
    _defaults_ready = False

    # ---------- 存储管理 ----------

    @classmethod
    def configure_base_dir(cls, base_dir: str):
        with cls._lock:
            cls.BASE_DIR = base_dir
            cls._store = None
            cls._store_path = None
            cls._defaults_ready = False

    @classmethod
    def _db_path(cls) -> str:
        return os.path.join(cls.BASE_DIR, 'collab.db')

    @classmethod
    def store(cls) -> CollabStore:
        with cls._lock:
            db_path = cls._db_path()
            if cls._store is None or cls._store_path != db_path:
                cls._store = CollabStore(db_path)
                cls._store_path = db_path
                migrate_json_if_needed(cls._store, cls.BASE_DIR)
            return cls._store

    # ---------- 默认本地数据 ----------

    @classmethod
    def ensure_local_defaults(cls) -> Dict[str, Any]:
        with cls._lock:
            store = cls.store()
            if not store.get_user('local_user'):
                store.upsert_user(CollabUser(id='local_user', name='本地用户').to_dict())
            if not store.get_workspace('local_workspace'):
                store.upsert_workspace(Workspace(id='local_workspace', name='本地工作区', owner_id='local_user').to_dict())
            if not store.get_room('local_room'):
                store.upsert_room(Room(id='local_room', workspace_id='local_workspace', name='本地房间', owner_id='local_user').to_dict())
            if not store.get_member('local_room', 'local_user'):
                store.upsert_member(RoomMember(room_id='local_room', user_id='local_user', role=identity.ROLE_OWNER, display_name='本地用户').to_dict(), update_existing=False)
            return {
                'user': store.get_user('local_user'),
                'workspace': store.get_workspace('local_workspace'),
                'room': cls.get_room('local_room').to_dict(),
            }

    # ---------- 用户 / 工作区 ----------

    @classmethod
    def get_user(cls, user_id: str) -> Optional[CollabUser]:
        data = cls.store().get_user(user_id)
        return CollabUser.from_dict(data) if data else None

    @classmethod
    def get_workspace(cls, workspace_id: str) -> Optional[Workspace]:
        data = cls.store().get_workspace(workspace_id)
        return Workspace.from_dict(data) if data else None

    @classmethod
    def list_workspaces(cls) -> List[Workspace]:
        cls.ensure_local_defaults()
        return [Workspace.from_dict(item) for item in cls.store().list_workspaces()]

    @classmethod
    def create_workspace(cls, name: str, owner_id: str = 'local_user', description: str = '') -> Workspace:
        with cls._lock:
            cls.ensure_local_defaults()
            workspace = Workspace(id=f'ws_{uuid.uuid4().hex[:12]}', name=name or '新工作区', owner_id=owner_id, description=description)
            cls.store().upsert_workspace(workspace.to_dict())
            return workspace

    # ---------- 房间 ----------

    @classmethod
    def list_rooms(cls, workspace_id: str = '') -> List[Room]:
        cls.ensure_local_defaults()
        return [Room.from_dict(item) for item in cls.store().list_rooms(workspace_id)]

    @classmethod
    def get_room(cls, room_id: str) -> Optional[Room]:
        data = cls.store().get_room(room_id)
        return Room.from_dict(data) if data else None

    @classmethod
    def find_room_by_world(cls, world_id: str) -> Optional[Room]:
        target = str(world_id or '').strip()
        if not target:
            return None
        data = cls.store().find_room_by_world(target)
        return Room.from_dict(data) if data else None

    @classmethod
    def create_room(cls, name: str, workspace_id: str = 'local_workspace', owner_id: str = 'local_user', **kwargs) -> Room:
        with cls._lock:
            cls.ensure_local_defaults()
            room = Room(
                id=f'room_{uuid.uuid4().hex[:12]}',
                workspace_id=workspace_id,
                name=name or '新房间',
                owner_id=owner_id,
                description=kwargs.get('description') or '',
                room_type=kwargs.get('room_type') or 'general',
                linked_world_id=kwargs.get('linked_world_id') or '',
                settings=kwargs.get('settings') if isinstance(kwargs.get('settings'), dict) else {},
            )
            cls.store().upsert_room(room.to_dict())
            cls.join_room(room.id, owner_id, kwargs.get('display_name') or '本地用户', role=identity.ROLE_OWNER, emit_event=False)
            cls.append_event(room.id, 'room.created', owner_id, {'room': room.to_dict()})
            return room

    @classmethod
    def ensure_world_room(cls, world_id: str, world_name: str = '', workspace_id: str = 'local_workspace', owner_id: str = 'local_user') -> Room:
        target = str(world_id or '').strip()
        if not target:
            raise ValueError('world_id 不能为空')
        with cls._lock:
            cls.ensure_local_defaults()
            existing = cls.find_room_by_world(target)
            if existing:
                cls.join_room(existing.id, owner_id, '本地用户', role=identity.ROLE_OWNER, emit_event=False)
                return existing
            room = cls.create_room(
                name=world_name or f'世界观房间 {target}',
                workspace_id=workspace_id,
                owner_id=owner_id,
                room_type='world',
                linked_world_id=target,
                display_name='本地用户',
            )
            cls.append_event(room.id, 'world.room.created', owner_id, {'world_id': target, 'world_name': world_name or ''})
            return room

    # ---------- 成员 ----------

    @classmethod
    def list_members(cls, room_id: str) -> List[RoomMember]:
        return [RoomMember.from_dict(item) for item in cls.store().list_members(room_id)]

    @classmethod
    def get_member(cls, room_id: str, user_id: str) -> Optional[RoomMember]:
        data = cls.store().get_member(room_id, user_id)
        return RoomMember.from_dict(data) if data else None

    @classmethod
    def join_room(cls, room_id: str, user_id: str = 'local_user', display_name: str = '本地用户', role: str = 'member', emit_event: bool = True) -> RoomMember:
        with cls._lock:
            room = cls.get_room(room_id)
            if not room:
                raise ValueError(f'房间不存在: {room_id}')
            normalized_role = identity.normalize_role(role, default=identity.ROLE_EDITOR)
            member = RoomMember(
                room_id=room_id,
                user_id=user_id,
                role=normalized_role,
                display_name=display_name or '成员',
                joined_at=_now(),
                last_seen_at=_now(),
            )
            joined_new = cls.store().upsert_member(member.to_dict())
            stored = cls.store().get_member(room_id, user_id)
            member = RoomMember.from_dict(stored) if stored else member
            if emit_event and joined_new:
                cls.append_event(room_id, 'member.joined', user_id, {'member': member.to_dict()})
            return member

    @classmethod
    def leave_room(cls, room_id: str, user_id: str = 'local_user') -> bool:
        with cls._lock:
            changed = cls.store().remove_member(room_id, user_id)
            if changed:
                cls.append_event(room_id, 'member.left', user_id, {'user_id': user_id})
            return changed

    @classmethod
    def heartbeat(cls, room_id: str, user_id: str = 'local_user') -> RoomMember:
        with cls._lock:
            if not cls.get_room(room_id):
                raise ValueError(f'房间不存在: {room_id}')
            updated = cls.store().touch_member(room_id, user_id, _now())
            if not updated:
                return cls.join_room(room_id, user_id=user_id, role=identity.ROLE_EDITOR)
            return cls.get_member(room_id, user_id)

    # ---------- 权限 ----------

    @classmethod
    def require_member(cls, room_id: str, user_id: str) -> RoomMember:
        member = cls.get_member(room_id, user_id)
        if not member:
            raise identity.PermissionError(f'用户 {user_id} 不是房间成员', status=403)
        return member

    @classmethod
    def require_writer(cls, room_id: str, user_id: str) -> RoomMember:
        member = cls.require_member(room_id, user_id)
        if not identity.can_write(member.role):
            raise identity.PermissionError(f'用户 {user_id} 没有写入权限（当前角色 {member.role}）', status=403)
        return member

    # ---------- 事件 ----------

    @classmethod
    def append_event(cls, room_id: str, event_type: str, actor_id: str = 'system', payload: Optional[Dict[str, Any]] = None) -> RoomEvent:
        if not cls.get_room(room_id):
            raise ValueError(f'房间不存在: {room_id}')
        event_id = f'evt_{uuid.uuid4().hex[:12]}'
        created_at = _now()
        seq = cls.store().append_event(event_id, room_id, event_type, actor_id, payload or {}, created_at)
        return RoomEvent(id=event_id, room_id=room_id, seq=seq, type=event_type, actor_id=actor_id, payload=payload or {}, created_at=created_at)

    @classmethod
    def post_message(cls, room_id: str, content: str, actor_id: str = 'local_user') -> RoomEvent:
        text = str(content or '').strip()
        if not text:
            raise ValueError('消息内容不能为空')
        return cls.append_event(room_id, 'message', actor_id, {'content': text})

    @classmethod
    def append_world_event(cls, room_id: str, event_type: str, actor_id: str, payload: Dict[str, Any], base_seq: Optional[int] = None) -> RoomEvent:
        """世界观事件写入，支持乐观并发检测。

        若 base_seq 不为 None，且房间内已存在更新的、来自其他 client 的 world.saved 事件，
        则抛出 ConflictError。
        """
        if base_seq is not None and event_type == 'world.saved':
            latest = cls.store().find_latest_event(room_id, 'world.saved')
            if latest and latest['seq'] > int(base_seq):
                latest_client = (latest.get('payload') or {}).get('client_id')
                current_client = (payload or {}).get('client_id')
                if latest_client and latest_client != current_client:
                    raise ConflictError('世界观已被其他成员更新，请先同步', latest_event=latest)
        return cls.append_event(room_id, event_type, actor_id, payload)

    @classmethod
    def list_events(cls, room_id: str, since: int = 0, limit: int = 100) -> Dict[str, Any]:
        bounded_limit = max(1, min(int(limit or 100), MAX_EVENT_LIMIT))
        events = cls.store().list_events(room_id, since=int(since or 0), limit=bounded_limit)
        latest_seq = cls.store().latest_seq(room_id)
        remaining = cls.store().count_remaining(room_id, since=int(since or 0), limit=bounded_limit)
        return {
            'events': events,
            'latest_seq': latest_seq,
            'cursor': events[-1]['seq'] if events else int(since or 0),
            'has_more': remaining > 0,
        }

    @classmethod
    def latest_seq(cls, room_id: str) -> int:
        return cls.store().latest_seq(room_id)

    @classmethod
    def stats(cls) -> Dict[str, Any]:
        return cls.store().stats()
