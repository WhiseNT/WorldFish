import os

from flask import Flask

from app.config import Config
from app.core.module_store import ModuleStateStore
from app.core.modules import ModuleRegistry
from app.domain.canonical_world import CANONICAL_WORLD_MODEL_ID, CANONICAL_WORLD_MODEL_VERSION
from app.models.world import WorldManager
from app.modules.loader import install_modules


def use_tmp_world_dir(tmp_path):
    old_upload = Config.UPLOAD_FOLDER
    old_worlds_dir = WorldManager.WORLDS_DIR
    Config.UPLOAD_FOLDER = str(tmp_path / 'uploads')
    WorldManager.WORLDS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'worlds')
    return old_upload, old_worlds_dir


def make_app(tmp_path):
    app = Flask(__name__)
    registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
    install_modules(app, object, registry=registry)
    return app


def test_world_canonical_api_returns_v1_contract(tmp_path):
    old_upload, old_worlds_dir = use_tmp_world_dir(tmp_path)
    try:
        world = WorldManager.create_world(
            name='接口测试世界',
            description='用于测试 canonical API。',
            era='灰烬纪元',
            settings={
                'items': [
                    {
                        'id': 'setting_law',
                        'name': '灰烬法则',
                        'category': 'ability',
                        'description': '所有魔法都需要燃烧记忆。',
                    }
                ]
            },
        )
        WorldManager.add_entity(world.id, '记忆术士', '人物', {'简介': '保存旧世界记忆的人。'})
        WorldManager.add_event(world.id, '灰烬雨', '天空降下灰烬。', '元年')

        client = make_app(tmp_path).test_client()
        response = client.get(f'/api/world/{world.id}/canonical')

        assert response.status_code == 200
        body = response.get_json()
        assert body['success'] is True
        assert body['schema_id'] == CANONICAL_WORLD_MODEL_ID
        assert body['schema_version'] == CANONICAL_WORLD_MODEL_VERSION
        assert body['canonical']['world_info']['name'] == '接口测试世界'
        assert any(entity['name'] == '记忆术士' for entity in body['canonical']['entities'])
        assert any(event['name'] == '灰烬雨' for event in body['canonical']['events'])
    finally:
        Config.UPLOAD_FOLDER = old_upload
        WorldManager.WORLDS_DIR = old_worlds_dir


def test_world_context_api_returns_purpose_and_sections_without_ai_config(tmp_path):
    old_upload, old_worlds_dir = use_tmp_world_dir(tmp_path)
    old_embedding_base = getattr(Config, 'EMBEDDING_BASE_URL', None)
    old_embedding_key = getattr(Config, 'EMBEDDING_API_KEY', None)
    try:
        Config.EMBEDDING_BASE_URL = ''
        Config.EMBEDDING_API_KEY = ''
        world = WorldManager.create_world(
            name='上下文测试世界',
            description='不依赖 LLM 或 Embedding。',
            settings={'items': []},
        )
        WorldManager.add_entity(world.id, '本地角色', '人物', {'简介': '只依赖本地数据。'})

        client = make_app(tmp_path).test_client()
        response = client.get(f'/api/world/{world.id}/context?purpose=simulation')

        assert response.status_code == 200
        body = response.get_json()
        assert body['success'] is True
        assert body['purpose'] == 'simulation'
        assert body['schema_id'] == CANONICAL_WORLD_MODEL_ID
        context = body['context']
        assert context['purpose'] == 'simulation'
        assert 'world_info' in context['sections']
        assert 'entities' in context['sections']
        assert '上下文测试世界' in context['context_text']
        assert '本地角色' in context['context_text']
    finally:
        Config.UPLOAD_FOLDER = old_upload
        WorldManager.WORLDS_DIR = old_worlds_dir
        Config.EMBEDDING_BASE_URL = old_embedding_base
        Config.EMBEDDING_API_KEY = old_embedding_key


def test_world_context_api_falls_back_to_general_for_unknown_purpose(tmp_path):
    old_upload, old_worlds_dir = use_tmp_world_dir(tmp_path)
    try:
        world = WorldManager.create_world(name='回退测试世界')
        client = make_app(tmp_path).test_client()

        response = client.get(f'/api/world/{world.id}/context?purpose=unknown-cloud-mode')

        assert response.status_code == 200
        body = response.get_json()
        assert body['purpose'] == 'general'
        assert body['context']['purpose'] == 'general'
    finally:
        Config.UPLOAD_FOLDER = old_upload
        WorldManager.WORLDS_DIR = old_worlds_dir


def test_world_schema_api_returns_404_for_missing_world(tmp_path):
    client = make_app(tmp_path).test_client()

    response = client.get('/api/world/world_missing/canonical')

    assert response.status_code == 404
    assert response.get_json()['success'] is False
