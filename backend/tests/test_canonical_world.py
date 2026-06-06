from app.domain.canonical_world import (
    CANONICAL_WORLD_MODEL_ID,
    CANONICAL_WORLD_MODEL_VERSION,
    build_canonical_world,
    summarize_canonical_world,
)
from app.models.world import WorldSetting


def make_legacy_world():
    return WorldSetting.from_dict({
        'id': 'world_legacy',
        'name': '旧格式世界',
        'description': '一个没有 schema_version 的旧世界观。',
        'era': '星海纪元',
        'anchor_time': '1024 年',
        'settings': {
            'items': [
                {
                    'id': 'collection_character',
                    'name': '角色设定',
                    'settingType': 'collection',
                    'category': 'character',
                },
                {
                    'id': 'setting_magic',
                    'name': '潮汐魔法',
                    'category': 'ability',
                    'description': '以双月潮汐驱动的规则体系。',
                    'detailContent': '施法者必须记录月相。',
                    'sourceType': 'manual',
                },
            ],
            'mapData': {
                'structuredMaps': [
                    {
                        'id': 'map_main',
                        'name': '主大陆',
                        'type': 'continent',
                        'width': 3,
                        'height': 3,
                        'cells': [
                            {'id': 'cell_0_0', 'q': 0, 'r': 0, 'name': '潮汐港', 'terrain': 'city', 'faction': '银帆会'},
                            {'id': 'cell_1_0', 'q': 1, 'r': 0, 'terrain': 'forest'},
                        ],
                    }
                ]
            },
            'calendars': [{'id': 'calendar_lunar', 'name': '双月历'}],
        },
        'entities': [
            {
                'id': 'ent_hero',
                'name': '洛汐',
                'type': '人物',
                'aliases': ['潮汐使'],
                'attributes': {'简介': '能听见海潮预言的少女'},
            }
        ],
        'events': [
            {
                'id': 'evt_first_tide',
                'name': '第一次黑潮',
                'description': '海面出现黑色潮线。',
                'date': '1018 年',
                'entities': ['ent_hero'],
            }
        ],
    })


def test_legacy_world_defaults_to_canonical_schema_version():
    world = make_legacy_world()

    assert world.schema_version == CANONICAL_WORLD_MODEL_VERSION

    canonical = build_canonical_world(world)

    assert canonical['schema_id'] == CANONICAL_WORLD_MODEL_ID
    assert canonical['schema_version'] == CANONICAL_WORLD_MODEL_VERSION
    assert canonical['source_schema_version'] == CANONICAL_WORLD_MODEL_VERSION
    assert canonical['world_info']['name'] == '旧格式世界'
    assert canonical['entities'][0]['name'] == '洛汐'
    assert canonical['events'][0]['name'] == '第一次黑潮'
    assert canonical['maps']['items'][0]['name'] == '主大陆'
    assert canonical['maps']['items'][0]['notable_cells'][0]['name'] == '潮汐港'
    assert any(rule['name'] == '潮汐魔法' for rule in canonical['rules'])
    assert any(reference.get('target_id') == 'setting_magic' for reference in canonical['references'])
    assert canonical['warnings'] == []


def test_canonical_summary_is_stable_and_counted():
    canonical = build_canonical_world(make_legacy_world())

    summary = summarize_canonical_world(canonical)

    assert summary['title'] == '旧格式世界'
    assert '世界观：旧格式世界' in summary['text']
    assert summary['counts']['entities'] >= 1
    assert summary['counts']['events'] == 1
    assert summary['counts']['settings'] >= 1
    assert summary['counts']['maps'] == 1
    assert '洛汐' in summary['entity_names']


def test_canonical_world_uses_warnings_instead_of_hard_failure():
    world = WorldSetting.from_dict({'id': 'world_empty', 'name': ''})

    canonical = build_canonical_world(world)
    codes = {item['code'] for item in canonical['warnings']}

    assert 'missing_world_name' in codes
    assert 'empty_entities' in codes
    assert 'empty_events' in codes
