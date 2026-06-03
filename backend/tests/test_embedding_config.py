import os

import pytest

from app import config as config_module
from app.config import Config


EMBEDDING_ENV_KEYS = [
    'EMBEDDING_PROVIDER',
    'EMBEDDING_API_KEY',
    'EMBEDDING_BASE_URL',
    'EMBEDDING_MODEL_NAME',
    'EMBEDDING_API_TYPE',
    'EMBEDDING_URL_MODE',
    'LLM_API_KEY',
    'LLM_BASE_URL',
    'LLM_MODEL_NAME',
]


def isolate_env(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, 'project_root_env', str(tmp_path / '.env'))
    monkeypatch.setattr(config_module, 'load_dotenv', lambda *args, **kwargs: None)
    for key in EMBEDDING_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_embedding_config_does_not_fallback_to_agent(monkeypatch, tmp_path):
    isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv('LLM_API_KEY', 'agent-key')
    monkeypatch.setenv('LLM_BASE_URL', 'https://agent.example/v1')
    monkeypatch.setenv('LLM_MODEL_NAME', 'agent-chat-model')

    Config.reload()

    config = Config.get_embedding_config()
    status = Config.get_embedding_config_status()

    assert config['provider'] == 'api'
    assert config['api_key'] == ''
    assert config['base_url'] == ''
    assert config['model_name'] == 'text-embedding-3-small'
    assert config['available'] is False
    assert status['api_key_configured'] is False
    assert status['available'] is False
    assert status['resolved_from'] == 'embedding'


def test_local_embedding_config_is_available_without_api_key(monkeypatch, tmp_path):
    isolate_env(monkeypatch, tmp_path)
    monkeypatch.setenv('EMBEDDING_PROVIDER', 'local')

    Config.reload()

    config = Config.get_embedding_config()
    status = Config.get_embedding_config_status()

    assert config['provider'] == 'local'
    assert config['api_key'] == ''
    assert config['available'] is True
    assert config['model_name'] == Config.LOCAL_EMBEDDING_MODEL_NAME
    assert config['local_model_source'] == Config.LOCAL_EMBEDDING_MODEL_SOURCE
    assert status['available'] is True
    assert status['provider'] == 'local'
    assert status['model_name'] == Config.LOCAL_EMBEDDING_MODEL_NAME


def test_save_embedding_local_provider_persists_model(monkeypatch, tmp_path):
    isolate_env(monkeypatch, tmp_path)
    Config.reload()

    status = Config.save_embedding_config(provider='local')

    embedding = status['embedding']
    assert embedding['provider'] == 'local'
    assert embedding['available'] is True
    assert embedding['model_name'] == Config.LOCAL_EMBEDDING_MODEL_NAME
    assert os.environ['EMBEDDING_PROVIDER'] == 'local'
    assert os.environ['EMBEDDING_MODEL_NAME'] == Config.LOCAL_EMBEDDING_MODEL_NAME


def test_save_embedding_api_requires_openai_compatible(monkeypatch, tmp_path):
    isolate_env(monkeypatch, tmp_path)
    Config.reload()

    with pytest.raises(ValueError, match='Embedding API 目前仅支持 OpenAI 兼容格式'):
        Config.save_embedding_config(provider='api', api_type='anthropic')
