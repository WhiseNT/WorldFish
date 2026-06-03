import os
import sys
import types

from flask import Flask


chromadb_stub = types.ModuleType('chromadb')
chromadb_stub.PersistentClient = lambda *args, **kwargs: object()
chromadb_config_stub = types.ModuleType('chromadb.config')
chromadb_config_stub.Settings = lambda *args, **kwargs: object()
sys.modules.setdefault('chromadb', chromadb_stub)
sys.modules.setdefault('chromadb.config', chromadb_config_stub)

from app import config as config_module
from app.config import Config
from app.core.module_store import ModuleStateStore
from app.core.modules import ModuleRegistry
from app.models.world import WorldManager
from app.modules.loader import install_modules


ENV_KEYS = [
    'LLM_API_KEY',
    'LLM_BASE_URL',
    'LLM_MODEL_NAME',
    'PARSER_LLM_API_KEY',
    'PARSER_LLM_BASE_URL',
    'PARSER_LLM_MODEL_NAME',
    'EMBEDDING_PROVIDER',
    'EMBEDDING_API_KEY',
    'EMBEDDING_BASE_URL',
    'EMBEDDING_MODEL_NAME',
]


def make_world_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, 'project_root_env', str(tmp_path / '.env'))
    monkeypatch.setattr(config_module, 'load_dotenv', lambda *args, **kwargs: None)
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('LLM_API_KEY', 'parser-capable-key')
    monkeypatch.setenv('LLM_BASE_URL', 'https://llm.example/v1')
    monkeypatch.setenv('LLM_MODEL_NAME', 'chat-model')
    Config.reload()

    old_upload = Config.UPLOAD_FOLDER
    old_worlds_dir = WorldManager.WORLDS_DIR
    Config.UPLOAD_FOLDER = str(tmp_path / 'uploads')
    WorldManager.WORLDS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'worlds')

    app = Flask(__name__)
    registry = ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))
    install_modules(app, object, registry=registry)
    client = app.test_client()
    response = client.post('/api/world/create', json={'name': '测试世界'})
    world_id = response.get_json()['world_id']
    return app, client, world_id, old_upload, old_worlds_dir


def restore_world_dirs(old_upload, old_worlds_dir):
    Config.UPLOAD_FOLDER = old_upload
    WorldManager.WORLDS_DIR = old_worlds_dir


def test_world_extraction_with_input_requires_embedding_before_task_start(monkeypatch, tmp_path):
    _app, client, world_id, old_upload, old_worlds_dir = make_world_client(tmp_path, monkeypatch)
    try:
        response = client.post('/api/world/extract', json={
            'world_id': world_id,
            'scan_source': 'input',
            'text': '这是需要提取并写入 RAG 的世界观文本。',
        })

        assert response.status_code == 400
        body = response.get_json()
        assert body['success'] is False
        assert 'Embedding' in body['message']
        assert '配置' in body['message']
        assert 'task_id' not in body
    finally:
        restore_world_dirs(old_upload, old_worlds_dir)


def test_world_extraction_direct_json_does_not_require_embedding(monkeypatch, tmp_path):
    _app, client, _world_id, old_upload, old_worlds_dir = make_world_client(tmp_path, monkeypatch)
    try:
        response = client.post('/api/world/extract', json={
            'world_info': {'name': 'JSON 世界'},
            'entities': [],
            'events': [],
            'settings': {'items': []},
        })

        assert response.status_code == 200
        body = response.get_json()
        assert body['success'] is True
        assert body['message'] == '结构化 JSON 已导入，无需进行文本扫描。'
    finally:
        restore_world_dirs(old_upload, old_worlds_dir)
