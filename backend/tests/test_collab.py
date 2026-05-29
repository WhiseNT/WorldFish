from flask import Flask

from app.core.module_store import ModuleStateStore
from app.core.modules import ModuleRegistry
from app.models.collab import CollabManager
from app.modules.loader import install_modules


def use_tmp_collab_dir(tmp_path):
    old_dir = CollabManager.BASE_DIR
    CollabManager.configure_base_dir(str(tmp_path / 'collab'))
    return old_dir


def test_ensure_local_defaults_creates_single_user_workspace_and_room(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        defaults = CollabManager.ensure_local_defaults()
        assert defaults['user']['id'] == 'local_user'
        assert defaults['workspace']['id'] == 'local_workspace'
        assert defaults['room']['id'] == 'local_room'
        assert CollabManager.list_members('local_room')[0].user_id == 'local_user'
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_create_room_and_list_rooms(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        room = CollabManager.create_room('测试房间')
        rooms = CollabManager.list_rooms('local_workspace')
        assert any(item.id == room.id for item in rooms)
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_join_room_writes_member_event_once(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        CollabManager.ensure_local_defaults()
        member = CollabManager.join_room('local_room', 'u_2', '玩家二')
        CollabManager.join_room('local_room', 'u_2', '玩家二')
        events = CollabManager.list_events('local_room')['events']
        joined = [event for event in events if event['type'] == 'member.joined' and event['actor_id'] == 'u_2']
        assert member.user_id == 'u_2'
        assert len(joined) == 1
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_post_message_increments_sequence_and_since_filter(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        CollabManager.ensure_local_defaults()
        first = CollabManager.post_message('local_room', 'hello')
        second = CollabManager.post_message('local_room', 'world')
        result = CollabManager.list_events('local_room', since=first.seq)
        assert second.seq == first.seq + 1
        assert [event['id'] for event in result['events']] == [second.id]
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_ensure_world_room_is_idempotent_and_linked(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        first = CollabManager.ensure_world_room('world_1', '测试世界')
        second = CollabManager.ensure_world_room('world_1', '测试世界')
        assert first.id == second.id
        assert first.linked_world_id == 'world_1'
        assert first.room_type == 'world'
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_world_room_api_and_world_event(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        app = Flask(__name__)
        registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
        install_modules(app, object, registry=registry)
        client = app.test_client()

        response = client.post('/api/collab/worlds/world_2/room', json={'world_name': '世界二'})
        assert response.status_code == 200
        room = response.get_json()['room']
        assert room['linked_world_id'] == 'world_2'

        response = client.post('/api/collab/worlds/world_2/events', json={
            'type': 'world.saved',
            'world_name': '世界二',
            'client_id': 'client_test',
            'summary': '保存测试',
        })
        assert response.status_code == 200
        event = response.get_json()['event']
        assert event['type'] == 'world.saved'
        assert event['payload']['world_id'] == 'world_2'
        assert event['payload']['client_id'] == 'client_test'
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_collab_api_bootstrap_and_module_guard(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        app = Flask(__name__)
        registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
        install_modules(app, object, registry=registry)
        client = app.test_client()

        response = client.get('/api/collab/bootstrap')
        assert response.status_code == 200
        assert response.get_json()['room']['id'] == 'local_room'

        registry.disable('collaboration')
        response = client.get('/api/collab/bootstrap')
        assert response.status_code == 503
        assert response.get_json()['module_id'] == 'collaboration'
    finally:
        CollabManager.configure_base_dir(old_dir)
