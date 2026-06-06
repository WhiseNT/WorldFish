from app.domain.world_events import (
    WORLD_EVENT_SCHEMA_ID,
    WORLD_EVENT_SCHEMA_VERSION,
    build_world_event,
    event_to_context_line,
    normalize_world_event,
)


def test_build_world_event_includes_required_schema_fields():
    event = build_world_event(
        event_type='entity.updated',
        world_id='world_1',
        payload={'entity_id': 'ent_1', 'summary': '更新角色状态'},
        source='test',
        actor_id='user_1',
        event_id='wevt_test',
        created_at='2026-01-01T00:00:00',
    )

    assert event['schema_id'] == WORLD_EVENT_SCHEMA_ID
    assert event['schema_version'] == WORLD_EVENT_SCHEMA_VERSION
    assert event['event_id'] == 'wevt_test'
    assert event['world_id'] == 'world_1'
    assert event['event_type'] == 'entity.updated'
    assert event['source'] == 'test'
    assert event['actor_id'] == 'user_1'
    assert event['payload']['world_id'] == 'world_1'
    assert event['payload']['entity_id'] == 'ent_1'


def test_normalize_world_event_accepts_collab_event_shape():
    event = normalize_world_event({
        'id': 'evt_collab_1',
        'type': 'world.saved',
        'actor_id': 'local_user',
        'payload': {
            'world_id': 'world_2',
            'summary': '保存世界观',
        },
        'created_at': '2026-02-01T12:00:00',
    })

    assert event['event_id'] == 'evt_collab_1'
    assert event['world_id'] == 'world_2'
    assert event['event_type'] == 'world.saved'
    assert event['payload']['summary'] == '保存世界观'
    assert event['created_at'] == '2026-02-01T12:00:00'


def test_event_to_context_line_is_readable():
    line = event_to_context_line({
        'event_type': 'simulation.event.recorded',
        'world_id': 'world_3',
        'actor_id': 'sim_runner',
        'payload': {
            'target_id': 'branch_1',
            'summary': '分支进入寒冬结局',
        },
        'created_at': '2026-03-01T08:30:00',
    })

    assert '2026-03-01T08:30:00' in line
    assert 'simulation.event.recorded' in line
    assert 'actor=sim_runner' in line
    assert 'target=branch_1' in line
    assert '分支进入寒冬结局' in line
