"""联机协作 API。

生产级加固：
- 输入长度 / 范围校验，统一错误码（400/403/404/409/413）
- 写操作校验房间成员与角色（identity）
- 世界观保存乐观并发检测（409）
- 增量同步 cursor + 长轮询 sync 端点
- health 健康检查
"""

from __future__ import annotations

import json
import re
import time

from flask import Blueprint, jsonify, request

from app.core import identity
from app.models.collab import CollabManager, ConflictError
from app.utils.logger import get_logger

collab_bp = Blueprint('collab', __name__)
logger = get_logger('worldfish.api.collab')

# 输入限制
MAX_NAME_LEN = 200
MAX_DESCRIPTION_LEN = 2000
MAX_MESSAGE_LEN = 4000
MAX_PAYLOAD_BYTES = 32 * 1024
MAX_SUMMARY_LEN = 2000
ID_PATTERN = re.compile(r'^[A-Za-z0-9_\-:.]{1,128}$')
SYNC_TIMEOUT_SECONDS = 25
SYNC_INTERVAL_SECONDS = 1.0


def _ok(**payload):
    return jsonify({'success': True, **payload})


def _error(message: str, status: int = 400, **extra):
    return jsonify({'success': False, 'message': message, 'error': message, **extra}), status


def _body():
    return request.get_json(silent=True) or {}


def _actor_id(data=None):
    data = data or {}
    raw = data.get('user_id') or request.headers.get('X-WorldFish-User') or 'local_user'
    actor = str(raw).strip()
    if not ID_PATTERN.match(actor):
        raise ValueError('user_id 非法')
    return actor


def _valid_id(value: str) -> bool:
    return bool(ID_PATTERN.match(str(value or '')))


def _bounded_text(value, max_len: int, field_name: str) -> str:
    text = str(value or '').strip()
    if len(text) > max_len:
        raise ValueError(f'{field_name} 超过最大长度 {max_len}')
    return text


def _validate_payload(payload) -> dict:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError('payload 必须是对象')
    try:
        size = len(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    except (TypeError, ValueError):
        raise ValueError('payload 无法序列化')
    if size > MAX_PAYLOAD_BYTES:
        raise ValueError(f'payload 超过最大大小 {MAX_PAYLOAD_BYTES} 字节')
    return payload


def _handle(action, status_on_value=400):
    """统一异常 → HTTP 映射。返回 (response, None) 或 (None, result)。"""
    try:
        return None, action()
    except identity.PermissionError as exc:
        return _error(exc.message, exc.status), None
    except ConflictError as exc:
        return _error(exc.message, 409, latest_event=exc.latest_event), None
    except ValueError as exc:
        message = str(exc)
        if '超过最大' in message:
            return _error(message, 413), None
        status = 404 if '不存在' in message else status_on_value
        return _error(message, status), None
    except Exception as exc:  # noqa: BLE001
        logger.error(f'{getattr(action, "__name__", "collab")} 失败: {exc}')
        return _error(str(exc), 500), None


@collab_bp.route('/health', methods=['GET'])
def health():
    try:
        stats = CollabManager.stats()
        return _ok(status='ok', stats=stats)
    except Exception as exc:  # noqa: BLE001
        return _error(f'协作存储不可用: {exc}', 500)


@collab_bp.route('/bootstrap', methods=['GET'])
def bootstrap():
    defaults = CollabManager.ensure_local_defaults()
    rooms = [room.to_dict() for room in CollabManager.list_rooms(defaults['workspace']['id'])]
    return _ok(**defaults, rooms=rooms)


@collab_bp.route('/workspaces', methods=['GET'])
def list_workspaces():
    return _ok(workspaces=[workspace.to_dict() for workspace in CollabManager.list_workspaces()])


@collab_bp.route('/workspaces', methods=['POST'])
def create_workspace():
    data = _body()

    def action():
        return CollabManager.create_workspace(
            name=_bounded_text(data.get('name') or '新工作区', MAX_NAME_LEN, '工作区名称'),
            owner_id=_actor_id(data),
            description=_bounded_text(data.get('description'), MAX_DESCRIPTION_LEN, '描述'),
        )

    response, workspace = _handle(action)
    return response or _ok(workspace=workspace.to_dict())


@collab_bp.route('/rooms', methods=['GET'])
def list_rooms():
    workspace_id = request.args.get('workspace_id') or ''
    if workspace_id and not _valid_id(workspace_id):
        return _error('workspace_id 非法', 400)
    rooms = [room.to_dict() for room in CollabManager.list_rooms(workspace_id)]
    return _ok(rooms=rooms)


@collab_bp.route('/rooms', methods=['POST'])
def create_room():
    data = _body()

    def action():
        return CollabManager.create_room(
            name=_bounded_text(data.get('name') or '新房间', MAX_NAME_LEN, '房间名称'),
            workspace_id=data.get('workspace_id') or 'local_workspace',
            owner_id=_actor_id(data),
            description=_bounded_text(data.get('description'), MAX_DESCRIPTION_LEN, '描述'),
            room_type=str(data.get('room_type') or 'general')[:40],
            linked_world_id=str(data.get('linked_world_id') or '')[:128],
            settings=data.get('settings') if isinstance(data.get('settings'), dict) else {},
            display_name=_bounded_text(data.get('display_name') or '本地用户', MAX_NAME_LEN, '显示名'),
        )

    response, room = _handle(action)
    return response or _ok(room=room.to_dict())


@collab_bp.route('/rooms/<room_id>', methods=['GET'])
def get_room(room_id: str):
    if not _valid_id(room_id):
        return _error('room_id 非法', 400)
    room = CollabManager.get_room(room_id)
    if not room:
        return _error(f'房间不存在: {room_id}', 404)
    return _ok(room=room.to_dict())


@collab_bp.route('/rooms/<room_id>/join', methods=['POST'])
def join_room(room_id: str):
    data = _body()

    def action():
        if not _valid_id(room_id):
            raise ValueError('room_id 非法')
        return CollabManager.join_room(
            room_id,
            user_id=_actor_id(data),
            display_name=_bounded_text(data.get('display_name') or data.get('name') or '本地用户', MAX_NAME_LEN, '显示名'),
            role=data.get('role') or identity.ROLE_EDITOR,
        )

    response, member = _handle(action)
    return response or _ok(member=member.to_dict())


@collab_bp.route('/rooms/<room_id>/leave', methods=['POST'])
def leave_room(room_id: str):
    data = _body()

    def action():
        if not _valid_id(room_id):
            raise ValueError('room_id 非法')
        return CollabManager.leave_room(room_id, _actor_id(data))

    response, left = _handle(action)
    return response or _ok(left=left)


@collab_bp.route('/rooms/<room_id>/heartbeat', methods=['POST'])
def heartbeat(room_id: str):
    data = _body()

    def action():
        if not _valid_id(room_id):
            raise ValueError('room_id 非法')
        return CollabManager.heartbeat(room_id, _actor_id(data))

    response, member = _handle(action)
    return response or _ok(member=member.to_dict())


@collab_bp.route('/rooms/<room_id>/members', methods=['GET'])
def list_members(room_id: str):
    if not _valid_id(room_id):
        return _error('room_id 非法', 400)
    if not CollabManager.get_room(room_id):
        return _error(f'房间不存在: {room_id}', 404)
    return _ok(members=[member.to_dict() for member in CollabManager.list_members(room_id)])


@collab_bp.route('/worlds/<world_id>/room', methods=['POST'])
def ensure_world_room(world_id: str):
    data = _body()

    def action():
        if not _valid_id(world_id):
            raise ValueError('world_id 非法')
        actor = _actor_id(data)
        room = CollabManager.ensure_world_room(
            world_id,
            world_name=_bounded_text(data.get('world_name') or data.get('name'), MAX_NAME_LEN, '世界观名称'),
            workspace_id=data.get('workspace_id') or 'local_workspace',
            owner_id=actor,
        )
        member = CollabManager.join_room(
            room.id,
            user_id=actor,
            display_name=_bounded_text(data.get('display_name') or '本地用户', MAX_NAME_LEN, '显示名'),
            role=data.get('role') or identity.ROLE_OWNER,
            emit_event=False,
        )
        return room, member

    response, result = _handle(action)
    if response:
        return response
    room, member = result
    return _ok(
        room=room.to_dict(),
        member=member.to_dict(),
        members=[item.to_dict() for item in CollabManager.list_members(room.id)],
        latest_seq=CollabManager.latest_seq(room.id),
    )


@collab_bp.route('/worlds/<world_id>/events', methods=['POST'])
def append_world_event(world_id: str):
    data = _body()

    def action():
        if not _valid_id(world_id):
            raise ValueError('world_id 非法')
        actor = _actor_id(data)
        room = CollabManager.ensure_world_room(
            world_id,
            world_name=_bounded_text(data.get('world_name'), MAX_NAME_LEN, '世界观名称'),
            owner_id=actor,
        )
        CollabManager.require_writer(room.id, actor)
        raw_payload = data.get('payload') if isinstance(data.get('payload'), dict) else {}
        payload = _validate_payload({
            **raw_payload,
            'world_id': world_id,
            'world_name': _bounded_text(data.get('world_name') or raw_payload.get('world_name'), MAX_NAME_LEN, '世界观名称'),
            'summary': _bounded_text(data.get('summary') or raw_payload.get('summary'), MAX_SUMMARY_LEN, '摘要'),
            'client_id': str(data.get('client_id') or raw_payload.get('client_id') or '')[:128],
        })
        base_seq = data.get('base_seq')
        base_seq = int(base_seq) if base_seq is not None else None
        event = CollabManager.append_world_event(
            room.id,
            event_type=str(data.get('type') or 'world.updated')[:64],
            actor_id=actor,
            payload=payload,
            base_seq=base_seq,
        )
        return room, event

    response, result = _handle(action)
    if response:
        return response
    room, event = result
    return _ok(room=room.to_dict(), event=event.to_dict())


@collab_bp.route('/rooms/<room_id>/events', methods=['GET'])
def list_events(room_id: str):
    if not _valid_id(room_id):
        return _error('room_id 非法', 400)
    if not CollabManager.get_room(room_id):
        return _error(f'房间不存在: {room_id}', 404)
    since = request.args.get('since', 0, type=int)
    limit = request.args.get('limit', 100, type=int)
    return _ok(**CollabManager.list_events(room_id, since=since, limit=limit))


@collab_bp.route('/rooms/<room_id>/sync', methods=['GET'])
def sync_events(room_id: str):
    """长轮询：有新事件立即返回，否则最多挂起 SYNC_TIMEOUT_SECONDS。"""
    if not _valid_id(room_id):
        return _error('room_id 非法', 400)
    if not CollabManager.get_room(room_id):
        return _error(f'房间不存在: {room_id}', 404)
    since = request.args.get('since', 0, type=int)
    limit = request.args.get('limit', 100, type=int)
    deadline = time.monotonic() + SYNC_TIMEOUT_SECONDS
    while True:
        result = CollabManager.list_events(room_id, since=since, limit=limit)
        if result['events'] or time.monotonic() >= deadline:
            return _ok(**result)
        time.sleep(SYNC_INTERVAL_SECONDS)


@collab_bp.route('/rooms/<room_id>/events', methods=['POST'])
def append_event(room_id: str):
    data = _body()

    def action():
        if not _valid_id(room_id):
            raise ValueError('room_id 非法')
        actor = _actor_id(data)
        CollabManager.require_writer(room_id, actor)
        payload = _validate_payload(data.get('payload') if isinstance(data.get('payload'), dict) else {})
        return CollabManager.append_event(
            room_id,
            event_type=str(data.get('type') or 'action')[:64],
            actor_id=actor,
            payload=payload,
        )

    response, event = _handle(action)
    return response or _ok(event=event.to_dict())


@collab_bp.route('/rooms/<room_id>/messages', methods=['POST'])
def post_message(room_id: str):
    data = _body()

    def action():
        if not _valid_id(room_id):
            raise ValueError('room_id 非法')
        actor = _actor_id(data)
        CollabManager.require_writer(room_id, actor)
        content = _bounded_text(data.get('content') or data.get('message'), MAX_MESSAGE_LEN, '消息内容')
        return CollabManager.post_message(room_id, content=content, actor_id=actor)

    response, event = _handle(action)
    return response or _ok(event=event.to_dict())
