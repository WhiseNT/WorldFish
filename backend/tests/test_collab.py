from flask import Flask

from app.core.module_store import ModuleStateStore
from app.core.modules import ModuleRegistry
from app.core import identity
from app.models.collab import CollabManager, ConflictError
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


def test_sqlite_persists_across_manager_reconfigure(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        CollabManager.ensure_local_defaults()
        room = CollabManager.create_room('持久化房间')
        CollabManager.post_message(room.id, '持久化消息')
        # 重新指向同一目录，模拟进程重启
        CollabManager.configure_base_dir(str(tmp_path / 'collab'))
        rooms = CollabManager.list_rooms()
        assert any(item.id == room.id for item in rooms)
        events = CollabManager.list_events(room.id)['events']
        assert any(event['type'] == 'message' for event in events)
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_concurrent_append_event_seq_is_unique_and_increasing(tmp_path):
    import threading

    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        CollabManager.ensure_local_defaults()
        seqs = []
        lock = threading.Lock()

        def worker():
            event = CollabManager.append_event('local_room', 'action', 'local_user', {'n': 1})
            with lock:
                seqs.append(event.seq)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(seqs) == 20
        assert len(set(seqs)) == 20
        assert sorted(seqs) == list(range(min(seqs), min(seqs) + 20))
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_viewer_cannot_write_and_non_member_rejected(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        app = Flask(__name__)
        registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
        install_modules(app, object, registry=registry)
        client = app.test_client()

        CollabManager.ensure_local_defaults()
        CollabManager.join_room('local_room', 'viewer_user', '只读用户', role=identity.ROLE_VIEWER)

        # viewer 写消息被拒
        response = client.post('/api/collab/rooms/local_room/messages', json={
            'user_id': 'viewer_user',
            'content': '我想发言',
        })
        assert response.status_code == 403

        # 非成员写消息被拒
        response = client.post('/api/collab/rooms/local_room/messages', json={
            'user_id': 'stranger',
            'content': '陌生人',
        })
        assert response.status_code == 403

        # owner 写成功
        response = client.post('/api/collab/rooms/local_room/messages', json={
            'user_id': 'local_user',
            'content': '管理员发言',
        })
        assert response.status_code == 200
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_optimistic_concurrency_conflict(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        room = CollabManager.ensure_world_room('world_conflict', '冲突世界')
        first = CollabManager.append_world_event(room.id, 'world.saved', 'local_user', {'client_id': 'client_a'}, base_seq=0)
        # client_b 基于过期 base_seq 提交，应冲突
        try:
            CollabManager.append_world_event(room.id, 'world.saved', 'local_user', {'client_id': 'client_b'}, base_seq=0)
            raise AssertionError('应抛出 ConflictError')
        except ConflictError as exc:
            assert exc.latest_event['seq'] == first.seq
        # 同一 client 重复提交不冲突
        CollabManager.append_world_event(room.id, 'world.saved', 'local_user', {'client_id': 'client_a'}, base_seq=0)
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_world_event_conflict_returns_409(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        app = Flask(__name__)
        registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
        install_modules(app, object, registry=registry)
        client = app.test_client()

        client.post('/api/collab/worlds/world_409/room', json={'world_name': '冲突'})
        client.post('/api/collab/worlds/world_409/events', json={
            'type': 'world.saved', 'client_id': 'client_a', 'base_seq': 0,
        })
        response = client.post('/api/collab/worlds/world_409/events', json={
            'type': 'world.saved', 'client_id': 'client_b', 'base_seq': 0,
        })
        assert response.status_code == 409
        assert 'latest_event' in response.get_json()
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_message_length_limit_returns_413(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        app = Flask(__name__)
        registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
        install_modules(app, object, registry=registry)
        client = app.test_client()

        CollabManager.ensure_local_defaults()
        response = client.post('/api/collab/rooms/local_room/messages', json={
            'user_id': 'local_user',
            'content': 'x' * 5000,
        })
        assert response.status_code == 413
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_sync_endpoint_returns_new_events(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        app = Flask(__name__)
        registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
        install_modules(app, object, registry=registry)
        client = app.test_client()

        CollabManager.ensure_local_defaults()
        CollabManager.post_message('local_room', '同步消息')
        response = client.get('/api/collab/rooms/local_room/sync?since=0&limit=50')
        assert response.status_code == 200
        body = response.get_json()
        assert body['events']
        assert 'cursor' in body
    finally:
        CollabManager.configure_base_dir(old_dir)


def test_health_endpoint(tmp_path):
    old_dir = use_tmp_collab_dir(tmp_path)
    try:
        app = Flask(__name__)
        registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
        install_modules(app, object, registry=registry)
        client = app.test_client()

        response = client.get('/api/collab/health')
        assert response.status_code == 200
        body = response.get_json()
        assert body['status'] == 'ok'
        assert 'rooms' in body['stats']
    finally:
        CollabManager.configure_base_dir(old_dir)
