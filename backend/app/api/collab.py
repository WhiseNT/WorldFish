"""联机协作 API。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.models.collab import CollabManager
from app.utils.logger import get_logger

collab_bp = Blueprint('collab', __name__)
logger = get_logger('worldfish.api.collab')


def _ok(**payload):
    return jsonify({'success': True, **payload})


def _error(message: str, status: int = 400):
    return jsonify({'success': False, 'message': message, 'error': message}), status


def _body():
    return request.get_json(silent=True) or {}


def _actor_id(data=None):
    data = data or {}
    return data.get('user_id') or request.headers.get('X-WorldFish-User') or 'local_user'


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
    workspace = CollabManager.create_workspace(
        name=data.get('name') or '新工作区',
        owner_id=_actor_id(data),
        description=data.get('description') or '',
    )
    return _ok(workspace=workspace.to_dict())


@collab_bp.route('/rooms', methods=['GET'])
def list_rooms():
    workspace_id = request.args.get('workspace_id') or ''
    rooms = [room.to_dict() for room in CollabManager.list_rooms(workspace_id)]
    return _ok(rooms=rooms)


@collab_bp.route('/rooms', methods=['POST'])
def create_room():
    data = _body()
    room = CollabManager.create_room(
        name=data.get('name') or '新房间',
        workspace_id=data.get('workspace_id') or 'local_workspace',
        owner_id=_actor_id(data),
        description=data.get('description') or '',
        room_type=data.get('room_type') or 'general',
        linked_world_id=data.get('linked_world_id') or '',
        settings=data.get('settings') or {},
        display_name=data.get('display_name') or '本地用户',
    )
    return _ok(room=room.to_dict())


@collab_bp.route('/rooms/<room_id>', methods=['GET'])
def get_room(room_id: str):
    room = CollabManager.get_room(room_id)
    if not room:
        return _error(f'房间不存在: {room_id}', 404)
    return _ok(room=room.to_dict())


@collab_bp.route('/rooms/<room_id>/join', methods=['POST'])
def join_room(room_id: str):
    data = _body()
    try:
        member = CollabManager.join_room(
            room_id,
            user_id=_actor_id(data),
            display_name=data.get('display_name') or data.get('name') or '本地用户',
            role=data.get('role') or 'member',
        )
        return _ok(member=member.to_dict())
    except ValueError as exc:
        return _error(str(exc), 404)


@collab_bp.route('/rooms/<room_id>/leave', methods=['POST'])
def leave_room(room_id: str):
    data = _body()
    return _ok(left=CollabManager.leave_room(room_id, _actor_id(data)))


@collab_bp.route('/rooms/<room_id>/heartbeat', methods=['POST'])
def heartbeat(room_id: str):
    data = _body()
    try:
        member = CollabManager.heartbeat(room_id, _actor_id(data))
        return _ok(member=member.to_dict())
    except ValueError as exc:
        return _error(str(exc), 404)


@collab_bp.route('/rooms/<room_id>/members', methods=['GET'])
def list_members(room_id: str):
    if not CollabManager.get_room(room_id):
        return _error(f'房间不存在: {room_id}', 404)
    return _ok(members=[member.to_dict() for member in CollabManager.list_members(room_id)])


@collab_bp.route('/worlds/<world_id>/room', methods=['POST'])
def ensure_world_room(world_id: str):
    data = _body()
    try:
        room = CollabManager.ensure_world_room(
            world_id,
            world_name=data.get('world_name') or data.get('name') or '',
            workspace_id=data.get('workspace_id') or 'local_workspace',
            owner_id=_actor_id(data),
        )
        member = CollabManager.join_room(
            room.id,
            user_id=_actor_id(data),
            display_name=data.get('display_name') or '本地用户',
            role=data.get('role') or 'owner',
            emit_event=False,
        )
        event_state = CollabManager.list_events(room.id, since=0, limit=1)
        return _ok(
            room=room.to_dict(),
            member=member.to_dict(),
            members=[item.to_dict() for item in CollabManager.list_members(room.id)],
            latest_seq=event_state['latest_seq'],
        )
    except ValueError as exc:
        return _error(str(exc), 400)


@collab_bp.route('/worlds/<world_id>/events', methods=['POST'])
def append_world_event(world_id: str):
    data = _body()
    try:
        room = CollabManager.ensure_world_room(
            world_id,
            world_name=data.get('world_name') or '',
            workspace_id=data.get('workspace_id') or 'local_workspace',
            owner_id=_actor_id(data),
        )
        payload = data.get('payload') if isinstance(data.get('payload'), dict) else {}
        payload = {
            **payload,
            'world_id': world_id,
            'world_name': data.get('world_name') or payload.get('world_name') or '',
            'summary': data.get('summary') or payload.get('summary') or '',
            'client_id': data.get('client_id') or payload.get('client_id') or '',
        }
        event = CollabManager.append_event(
            room.id,
            event_type=data.get('type') or 'world.updated',
            actor_id=_actor_id(data),
            payload=payload,
        )
        return _ok(room=room.to_dict(), event=event.to_dict())
    except ValueError as exc:
        return _error(str(exc), 400)


@collab_bp.route('/rooms/<room_id>/events', methods=['GET'])
def list_events(room_id: str):
    if not CollabManager.get_room(room_id):
        return _error(f'房间不存在: {room_id}', 404)
    since = request.args.get('since', 0, type=int)
    limit = request.args.get('limit', 100, type=int)
    return _ok(**CollabManager.list_events(room_id, since=since, limit=limit))


@collab_bp.route('/rooms/<room_id>/events', methods=['POST'])
def append_event(room_id: str):
    data = _body()
    try:
        event = CollabManager.append_event(
            room_id,
            event_type=data.get('type') or 'action',
            actor_id=_actor_id(data),
            payload=data.get('payload') if isinstance(data.get('payload'), dict) else {},
        )
        return _ok(event=event.to_dict())
    except ValueError as exc:
        return _error(str(exc), 404)
    except Exception as exc:
        logger.error(f'追加房间事件失败: {exc}')
        return _error(str(exc), 500)


@collab_bp.route('/rooms/<room_id>/messages', methods=['POST'])
def post_message(room_id: str):
    data = _body()
    try:
        event = CollabManager.post_message(
            room_id,
            content=data.get('content') or data.get('message') or '',
            actor_id=_actor_id(data),
        )
        return _ok(event=event.to_dict())
    except ValueError as exc:
        return _error(str(exc), 400)
    except Exception as exc:
        logger.error(f'发送房间消息失败: {exc}')
        return _error(str(exc), 500)
