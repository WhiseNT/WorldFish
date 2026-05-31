import os

from flask import Flask

from app.config import Config
from app.core.module_store import ModuleStateStore
from app.core.modules import ModuleRegistry
from app.models.world import WorldManager
from app.modules.loader import install_modules
from app.services.enhanced_world_extractor import EnhancedWorldExtractor
from app.services.world_templates import (
    DEFAULT_WORLD_TEMPLATE_ID,
    build_extraction_system_prompt,
    get_world_template_detail,
    list_world_templates,
)


def use_tmp_world_dir(tmp_path):
    old_upload = Config.UPLOAD_FOLDER
    old_worlds_dir = WorldManager.WORLDS_DIR
    Config.UPLOAD_FOLDER = str(tmp_path / 'uploads')
    WorldManager.WORLDS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'worlds')
    return old_upload, old_worlds_dir


def test_builtin_world_templates_are_listed():
    templates = list_world_templates()
    assert len(templates) == 1
    assert templates[0]['id'] == DEFAULT_WORLD_TEMPLATE_ID
    assert templates[0]['name'] == '通用模板'
    assert [section['name'] for section in templates[0]['detail_sections']] == [
        '核心简介',
        '关键事实',
        '关系网络',
        '阶段/演变',
        '设定补充说明',
    ]
    assert templates[0]['setting_collections'] == []

    detail = get_world_template_detail(DEFAULT_WORLD_TEMPLATE_ID)
    assert detail['default_data']['world_info']['name'] == ''
    assert detail['default_data']['entities'] == []
    assert detail['default_data']['settings']['items'] == []


def test_template_prompt_and_cache_key_are_template_specific():
    prompt = build_extraction_system_prompt('legacy-template')
    assert '模板名称：通用模板' in prompt
    assert '核心简介' in prompt
    assert 'default_collection_character' not in prompt
    assert '详细设定集' not in prompt

    text = '测试文本'
    generic = EnhancedWorldExtractor(template_id='generic')
    fallback = EnhancedWorldExtractor(template_id='legacy-template')
    volume_profile = generic.get_text_volume_profile(len(text))

    assert generic.build_cache_key(text, 'fast', volume_profile) == fallback.build_cache_key(text, 'fast', volume_profile)


def test_world_template_api_and_world_persistence(tmp_path):
    old_upload, old_worlds_dir = use_tmp_world_dir(tmp_path)
    try:
        app = Flask(__name__)
        registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
        install_modules(app, object, registry=registry)
        client = app.test_client()

        response = client.get('/api/world/templates')
        assert response.status_code == 200
        body = response.get_json()
        assert body['default_template_id'] == DEFAULT_WORLD_TEMPLATE_ID
        assert [item['id'] for item in body['templates']] == [DEFAULT_WORLD_TEMPLATE_ID]

        response = client.get('/api/world/templates/generic')
        assert response.status_code == 200
        template_body = response.get_json()
        assert template_body['template']['id'] == DEFAULT_WORLD_TEMPLATE_ID
        assert template_body['template']['default_data']['events'] == []

        response = client.post('/api/world/create', json={
            'name': '测试世界',
            'template_id': 'legacy-template',
        })
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['world']['template_id'] == DEFAULT_WORLD_TEMPLATE_ID
        assert payload['world']['template_name'] == '通用模板'

        world_id = payload['world_id']
        response = client.put(f'/api/world/{world_id}', json={
            'template_id': 'legacy-template-2',
        })
        assert response.status_code == 200
        updated = response.get_json()['world']
        assert updated['template_id'] == DEFAULT_WORLD_TEMPLATE_ID
        assert updated['template_name'] == '通用模板'
    finally:
        Config.UPLOAD_FOLDER = old_upload
        WorldManager.WORLDS_DIR = old_worlds_dir
