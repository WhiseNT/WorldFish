"""联机协作模型与文件持久化仓库。"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import Config


def _now() -> str:
    return datetime.now().isoformat()


def _parse_time(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except Exception:
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
        data['online'] = bool(seen_at and datetime.now() - seen_at < timedelta(seconds=45))
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


class CollabManager:
    """文件持久化协作仓库。"""

    BASE_DIR = os.path.join(Config.UPLOAD_FOLDER, 'collab')
    _lock = threading.RLock()

    @classmethod
    def configure_base_dir(cls, base_dir: str):
        cls.BASE_DIR = base_dir

    @classmethod
    def _base(cls) -> Path:
        base = Path(cls.BASE_DIR)
        base.mkdir(parents=True, exist_ok=True)
        (base / 'events').mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def _json_file(cls, name: str) -> Path:
        return cls._base() / name

    @classmethod
    def _read_list(cls, name: str) -> List[Dict[str, Any]]:
        path = cls._json_file(name)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @classmethod
    def _write_list(cls, name: str, rows: List[Dict[str, Any]]):
        path = cls._json_file(name)
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temp.replace(path)

    @classmethod
    def ensure_local_defaults(cls) -> Dict[str, Any]:
        with cls._lock:
            users = [CollabUser.from_dict(item) for item in cls._read_list('users.json')]
            if not any(user.id == 'local_user' for user in users):
                users.append(CollabUser(id='local_user', name='本地用户'))
                cls._write_list('users.json', [user.to_dict() for user in users])

            workspaces = [Workspace.from_dict(item) for item in cls._read_list('workspaces.json')]
            if not any(ws.id == 'local_workspace' for ws in workspaces):
                workspaces.append(Workspace(id='local_workspace', name='本地工作区', owner_id='local_user'))
                cls._write_list('workspaces.json', [ws.to_dict() for ws in workspaces])

            rooms = [Room.from_dict(item) for item in cls._read_list('rooms.json')]
            if not any(room.id == 'local_room' for room in rooms):
                rooms.append(Room(id='local_room', workspace_id='local_workspace', name='本地房间', owner_id='local_user'))
                cls._write_list('rooms.json', [room.to_dict() for room in rooms])

            cls.join_room('local_room', 'local_user', '本地用户', role='owner', emit_event=False)
            return {
                'user': cls.get_user('local_user').to_dict(),
                'workspace': cls.get_workspace('local_workspace').to_dict(),
                'room': cls.get_room('local_room').to_dict(),
            }

    @classmethod
    def get_user(cls, user_id: str) -> Optional[CollabUser]:
        for item in cls._read_list('users.json'):
            user = CollabUser.from_dict(item)
            if user.id == user_id:
                return user
        return None

    @classmethod
    def get_workspace(cls, workspace_id: str) -> Optional[Workspace]:
        for item in cls._read_list('workspaces.json'):
            ws = Workspace.from_dict(item)
            if ws.id == workspace_id:
                return ws
        return None

    @classmethod
    def list_workspaces(cls) -> List[Workspace]:
        cls.ensure_local_defaults()
        return [Workspace.from_dict(item) for item in cls._read_list('workspaces.json')]

    @classmethod
    def create_workspace(cls, name: str, owner_id: str = 'local_user', description: str = '') -> Workspace:
        with cls._lock:
            cls.ensure_local_defaults()
            rows = cls._read_list('workspaces.json')
            workspace = Workspace(id=f'ws_{uuid.uuid4().hex[:12]}', name=name or '新工作区', owner_id=owner_id, description=description)
            rows.append(workspace.to_dict())
            cls._write_list('workspaces.json', rows)
            return workspace

    @classmethod
    def list_rooms(cls, workspace_id: str = '') -> List[Room]:
        cls.ensure_local_defaults()
        rooms = [Room.from_dict(item) for item in cls._read_list('rooms.json')]
        return [room for room in rooms if not workspace_id or room.workspace_id == workspace_id]

    @classmethod
    def get_room(cls, room_id: str) -> Optional[Room]:
        for item in cls._read_list('rooms.json'):
            room = Room.from_dict(item)
            if room.id == room_id:
                return room
        return None

    @classmethod
    def find_room_by_world(cls, world_id: str) -> Optional[Room]:
        target = str(world_id or '').strip()
        if not target:
            return None
        for room in cls.list_rooms():
            if room.linked_world_id == target:
                return room
        return None

    @classmethod
    def ensure_world_room(cls, world_id: str, world_name: str = '', workspace_id: str = 'local_workspace', owner_id: str = 'local_user') -> Room:
        target = str(world_id or '').strip()
        if not target:
            raise ValueError('world_id 不能为空')
        with cls._lock:
            cls.ensure_local_defaults()
            existing = cls.find_room_by_world(target)
            if existing:
                cls.join_room(existing.id, owner_id, '本地用户', role='owner', emit_event=False)
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

    @classmethod
    def create_room(cls, name: str, workspace_id: str = 'local_workspace', owner_id: str = 'local_user', **kwargs) -> Room:
        with cls._lock:
            cls.ensure_local_defaults()
            rows = cls._read_list('rooms.json')
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
            rows.append(room.to_dict())
            cls._write_list('rooms.json', rows)
            cls.join_room(room.id, owner_id, kwargs.get('display_name') or '本地用户', role='owner', emit_event=False)
            cls.append_event(room.id, 'room.created', owner_id, {'room': room.to_dict()})
            return room

    @classmethod
    def _members_file(cls) -> str:
        return 'members.json'

    @classmethod
    def list_members(cls, room_id: str) -> List[RoomMember]:
        members = [RoomMember.from_dict(item) for item in cls._read_list(cls._members_file())]
        return [member for member in members if member.room_id == room_id]

    @classmethod
    def join_room(cls, room_id: str, user_id: str = 'local_user', display_name: str = '本地用户', role: str = 'member', emit_event: bool = True) -> RoomMember:
        with cls._lock:
            room = cls.get_room(room_id)
            if not room:
                raise ValueError(f'房间不存在: {room_id}')
            rows = cls._read_list(cls._members_file())
            now = _now()
            found = None
            joined_new = False
            for item in rows:
                if item.get('room_id') == room_id and item.get('user_id') == user_id:
                    found = item
                    break
            if found:
                found.update({'display_name': display_name or found.get('display_name'), 'role': role or found.get('role'), 'last_seen_at': now})
                member = RoomMember.from_dict(found)
            else:
                member = RoomMember(room_id=room_id, user_id=user_id, role=role, display_name=display_name, joined_at=now, last_seen_at=now)
                rows.append(member.to_dict())
                joined_new = True
            cls._write_list(cls._members_file(), rows)
            if emit_event and joined_new:
                cls.append_event(room_id, 'member.joined', user_id, {'member': member.to_dict()})
            return member

    @classmethod
    def leave_room(cls, room_id: str, user_id: str = 'local_user') -> bool:
        with cls._lock:
            rows = cls._read_list(cls._members_file())
            kept = [item for item in rows if not (item.get('room_id') == room_id and item.get('user_id') == user_id)]
            changed = len(kept) != len(rows)
            cls._write_list(cls._members_file(), kept)
            if changed:
                cls.append_event(room_id, 'member.left', user_id, {'user_id': user_id})
            return changed

    @classmethod
    def heartbeat(cls, room_id: str, user_id: str = 'local_user') -> RoomMember:
        with cls._lock:
            members = cls.list_members(room_id)
            target = next((member for member in members if member.user_id == user_id), None)
            if not target:
                return cls.join_room(room_id, user_id=user_id, role='member')
            rows = cls._read_list(cls._members_file())
            now = _now()
            for item in rows:
                if item.get('room_id') == room_id and item.get('user_id') == user_id:
                    item['last_seen_at'] = now
                    target = RoomMember.from_dict(item)
                    break
            cls._write_list(cls._members_file(), rows)
            return target

    @classmethod
    def _events_file(cls, room_id: str) -> Path:
        safe = ''.join(ch for ch in room_id if ch.isalnum() or ch in {'_', '-'}) or 'room'
        return cls._base() / 'events' / f'{safe}.jsonl'

    @classmethod
    def _read_events(cls, room_id: str) -> List[RoomEvent]:
        path = cls._events_file(room_id)
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                events.append(RoomEvent.from_dict(json.loads(line)))
            except Exception:
                continue
        return events

    @classmethod
    def append_event(cls, room_id: str, event_type: str, actor_id: str = 'system', payload: Optional[Dict[str, Any]] = None) -> RoomEvent:
        with cls._lock:
            if not cls.get_room(room_id):
                raise ValueError(f'房间不存在: {room_id}')
            events = cls._read_events(room_id)
            seq = (events[-1].seq if events else 0) + 1
            event = RoomEvent(
                id=f'evt_{uuid.uuid4().hex[:12]}',
                room_id=room_id,
                seq=seq,
                type=event_type,
                actor_id=actor_id,
                payload=payload or {},
            )
            path = cls._events_file(room_id)
            with path.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')
            return event

    @classmethod
    def post_message(cls, room_id: str, content: str, actor_id: str = 'local_user') -> RoomEvent:
        text = str(content or '').strip()
        if not text:
            raise ValueError('消息内容不能为空')
        return cls.append_event(room_id, 'message', actor_id, {'content': text})

    @classmethod
    def list_events(cls, room_id: str, since: int = 0, limit: int = 100) -> Dict[str, Any]:
        events = [event for event in cls._read_events(room_id) if event.seq > int(since or 0)]
        limited = events[:max(1, min(int(limit or 100), 500))]
        latest_seq = cls._read_events(room_id)[-1].seq if cls._read_events(room_id) else 0
        return {
            'events': [event.to_dict() for event in limited],
            'latest_seq': latest_seq,
            'has_more': len(events) > len(limited),
        }
