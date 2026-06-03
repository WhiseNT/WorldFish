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


EMBEDDING_ENV_KEYS = [
    'EMBEDDING_PROVIDER',
    'EMBEDDING_API_KEY',
    'EMBEDDING_BASE_URL',
    'EMBEDDING_MODEL_NAME',
    'EMBEDDING_API_TYPE',
    'EMBEDDING_URL_MODE',
]


def make_app(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, 'project_root_env', str(tmp_path / '.env'))
    monkeypatch.setattr(config_module, 'load_dotenv', lambda *args, **kwargs: None)
    for key in EMBEDDING_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
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


def assert_embedding_missing_response(response):
    assert response.status_code == 400
    body = response.get_json()
    assert body['success'] is False
    assert 'Embedding' in (body.get('error') or body.get('message') or '')


def test_rag_add_documents_requires_embedding_config(monkeypatch, tmp_path):
    _app, client, world_id, old_upload, old_worlds_dir = make_app(tmp_path, monkeypatch)
    try:
        response = client.post(f'/api/{world_id}/rag/documents', json={'text': '测试知识库文本'})
        assert_embedding_missing_response(response)
    finally:
        restore_world_dirs(old_upload, old_worlds_dir)


def test_rag_index_task_requires_embedding_config(monkeypatch, tmp_path):
    _app, client, world_id, old_upload, old_worlds_dir = make_app(tmp_path, monkeypatch)
    try:
        response = client.post(f'/api/{world_id}/rag/index-task', json={'text': '测试知识库文本'})
        assert_embedding_missing_response(response)
    finally:
        restore_world_dirs(old_upload, old_worlds_dir)


def test_rag_search_requires_embedding_config(monkeypatch, tmp_path):
    _app, client, world_id, old_upload, old_worlds_dir = make_app(tmp_path, monkeypatch)
    try:
        response = client.post(f'/api/{world_id}/rag/search', json={'query': '检索问题'})
        assert_embedding_missing_response(response)
    finally:
        restore_world_dirs(old_upload, old_worlds_dir)
