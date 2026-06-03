"""
配置管理
启动时不强制要求 .env；API Key 可通过 GUI 配置页保存。
"""

import os
from typing import Any, Dict

from dotenv import load_dotenv

# 可选加载项目根目录的 .env 文件
# 路径: WorldFish/.env (相对于 backend/app/config.py)
# GUI 配置页会在需要时创建/更新该文件，但后端启动不依赖它存在。
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')


def _load_environment():
    if os.path.exists(project_root_env):
        load_dotenv(project_root_env, override=True)
    else:
        load_dotenv(override=True)


def _serialize_env_value(value: Any) -> str:
    text = str(value)
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _parse_bool_env(value: Any, default: Any = None):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'enabled', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'disabled', 'no', 'off'}:
        return False
    return default


def _parse_int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def _parse_float_env(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def _parse_reasoning_effort(value: Any) -> str:
    normalized = str(value or 'max').strip().lower()
    return normalized if normalized in {'high', 'max'} else 'max'


def _persist_env_updates(updates: Dict[str, Any]):
    existing_lines = []
    if os.path.exists(project_root_env):
        with open(project_root_env, 'r', encoding='utf-8') as handle:
            existing_lines = handle.readlines()

    found_keys = set()
    new_lines = []

    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in line:
            new_lines.append(line)
            continue

        key, _ = line.split('=', 1)
        normalized_key = key.strip()
        if normalized_key in updates:
            new_lines.append(f"{normalized_key}={_serialize_env_value(updates[normalized_key])}\n")
            found_keys.add(normalized_key)
        else:
            new_lines.append(line)

    if new_lines and new_lines[-1] and not new_lines[-1].endswith('\n'):
        new_lines[-1] += '\n'

    for key, value in updates.items():
        if key not in found_keys:
            new_lines.append(f"{key}={_serialize_env_value(value)}\n")

    with open(project_root_env, 'w', encoding='utf-8') as handle:
        handle.writelines(new_lines)


_load_environment()


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'worldfish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）
    # Agent LLM API：保留旧变量名以兼容现有 .env
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    LLM_API_TYPE = os.environ.get('LLM_API_TYPE', 'openai_compatible')
    LLM_URL_MODE = os.environ.get('LLM_URL_MODE', 'base_url')
    # SubAgent LLM API：不填时按 Agent > Parser 回退
    SUBAGENT_LLM_API_KEY = os.environ.get('SUBAGENT_LLM_API_KEY', '')
    SUBAGENT_LLM_BASE_URL = os.environ.get('SUBAGENT_LLM_BASE_URL', '')
    SUBAGENT_LLM_MODEL_NAME = os.environ.get('SUBAGENT_LLM_MODEL_NAME', '')
    SUBAGENT_LLM_API_TYPE = os.environ.get('SUBAGENT_LLM_API_TYPE', '')
    SUBAGENT_LLM_URL_MODE = os.environ.get('SUBAGENT_LLM_URL_MODE', '')
    # 解析 Agent LLM API：不填时按 Agent > SubAgent 回退
    PARSER_LLM_API_KEY = os.environ.get('PARSER_LLM_API_KEY', '')
    PARSER_LLM_BASE_URL = os.environ.get('PARSER_LLM_BASE_URL', '')
    PARSER_LLM_MODEL_NAME = os.environ.get('PARSER_LLM_MODEL_NAME', '')
    PARSER_LLM_API_TYPE = os.environ.get('PARSER_LLM_API_TYPE', '')
    PARSER_LLM_URL_MODE = os.environ.get('PARSER_LLM_URL_MODE', '')
    LLM_THINKING_ENABLED = _parse_bool_env(os.environ.get('LLM_THINKING_ENABLED'), None)
    LLM_REASONING_EFFORT = _parse_reasoning_effort(os.environ.get('LLM_REASONING_EFFORT'))
    LLM_DEFAULT_CONTEXT_WINDOW = _parse_int_env('LLM_DEFAULT_CONTEXT_WINDOW', 128 * 1024)
    LLM_DEEPSEEK_V4_CONTEXT_WINDOW = _parse_int_env('LLM_DEEPSEEK_V4_CONTEXT_WINDOW', 1_000_000)
    LLM_CONTEXT_WINDOW = _parse_int_env('LLM_CONTEXT_WINDOW', 0)
    AGENT_CONTEXT_COMPRESSION_RATIO = _parse_float_env('AGENT_CONTEXT_COMPRESSION_RATIO', 0.70)
    
    # Embedding 配置（RAG 向量化）
    # Embedding 必须显式配置；不再复用主 Agent 的 API。
    LOCAL_EMBEDDING_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
    LOCAL_EMBEDDING_MODEL_SOURCE = "https://www.modelscope.cn/models/Qwen/Qwen3-Embedding-0.6B"
    EMBEDDING_REQUIRED_MESSAGE = "请先配置 Embedding 模型，或在 LLM 配置页选择本地 Embedding 模型后再开始需要向量化的操作。"
    EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "api")
    EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
    EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_BASE_URL", "")
    EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
    EMBEDDING_API_TYPE = os.environ.get("EMBEDDING_API_TYPE", "openai_compatible")
    EMBEDDING_URL_MODE = os.environ.get("EMBEDDING_URL_MODE", "base_url")

    @classmethod
    def get_llm_config(cls, role: str = 'agent') -> Dict[str, Any]:
        """按用途获取 LLM 配置，并在缺项时按 Agent > SubAgent > Parser 回退。"""
        normalized_role = str(role or 'agent').strip().lower()
        role_order = {
            'agent': ['agent', 'subagent', 'parser'],
            'subagent': ['subagent', 'agent', 'parser'],
            'parser': ['parser', 'agent', 'subagent'],
        }.get(normalized_role, ['agent', 'subagent', 'parser'])

        configs = {
            'agent': {
                'api_key': cls.LLM_API_KEY or '',
                'base_url': cls.LLM_BASE_URL or 'https://api.openai.com/v1',
                'model_name': cls.LLM_MODEL_NAME or 'gpt-4o-mini',
                'api_type': cls.LLM_API_TYPE or 'openai_compatible',
                'url_mode': cls.LLM_URL_MODE or 'base_url',
            },
            'subagent': {
                'api_key': cls.SUBAGENT_LLM_API_KEY or '',
                'base_url': cls.SUBAGENT_LLM_BASE_URL or '',
                'model_name': cls.SUBAGENT_LLM_MODEL_NAME or '',
                'api_type': cls.SUBAGENT_LLM_API_TYPE or '',
                'url_mode': cls.SUBAGENT_LLM_URL_MODE or '',
            },
            'parser': {
                'api_key': cls.PARSER_LLM_API_KEY or '',
                'base_url': cls.PARSER_LLM_BASE_URL or '',
                'model_name': cls.PARSER_LLM_MODEL_NAME or '',
                'api_type': cls.PARSER_LLM_API_TYPE or '',
                'url_mode': cls.PARSER_LLM_URL_MODE or '',
            },
        }

        selected_role = role_order[-1]
        for candidate in role_order:
            if configs[candidate]['api_key']:
                selected_role = candidate
                break

        selected = configs[selected_role]
        agent_defaults = configs['agent']
        return {
            'role': normalized_role,
            'resolved_from': selected_role,
            'api_key': selected['api_key'],
            'base_url': selected['base_url'] or agent_defaults['base_url'] or 'https://api.openai.com/v1',
            'model_name': selected['model_name'] or agent_defaults['model_name'] or 'gpt-4o-mini',
            'api_type': selected.get('api_type') or agent_defaults.get('api_type') or 'openai_compatible',
            'url_mode': selected.get('url_mode') or agent_defaults.get('url_mode') or 'base_url',
            'explicitly_configured': bool(configs[normalized_role]['api_key']) if normalized_role in configs else False,
        }

    @classmethod
    def get_embedding_config(cls) -> dict:
        """获取 Embedding 配置；必须显式配置 API 或选择本地 provider。"""
        provider = str(cls.EMBEDDING_PROVIDER or 'api').strip().lower()
        provider = provider if provider in {'api', 'local'} else 'api'
        model_name = cls.LOCAL_EMBEDDING_MODEL_NAME if provider == 'local' else (cls.EMBEDDING_MODEL_NAME or 'text-embedding-3-small')
        available = provider == 'local' or bool(cls.EMBEDDING_API_KEY)
        return {
            "provider": provider,
            "api_key": cls.EMBEDDING_API_KEY or '',
            "base_url": cls.EMBEDDING_BASE_URL or '',
            "model_name": model_name,
            "api_type": cls.EMBEDDING_API_TYPE or "openai_compatible",
            "url_mode": cls.EMBEDDING_URL_MODE or "base_url",
            "explicitly_configured": provider == 'local' or bool(cls.EMBEDDING_API_KEY),
            "available": available,
            "local_model_name": cls.LOCAL_EMBEDDING_MODEL_NAME,
            "local_model_source": cls.LOCAL_EMBEDDING_MODEL_SOURCE,
        }

    @classmethod
    def is_embedding_configured(cls) -> bool:
        return bool(cls.get_embedding_config().get('available'))

    # RAG 配置
    RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))

    # 大文本提取配置
    EXTRACTION_MAX_WORKERS = int(os.environ.get("EXTRACTION_MAX_WORKERS", "12"))
    EXTRACTION_HUGE_WORKERS = int(os.environ.get("EXTRACTION_HUGE_WORKERS", "10"))
    EXTRACTION_MASSIVE_WORKERS = int(os.environ.get("EXTRACTION_MASSIVE_WORKERS", "12"))
    EXTRACTION_DEFAULT_MODE = os.environ.get("EXTRACTION_DEFAULT_MODE", "fast")
    EXTRACTION_TOKENIZER_ESTIMATE = _parse_float_env("EXTRACTION_TOKENIZER_ESTIMATE", 1.2)
    EXTRACTION_TARGET_CONTEXT_RATIO = _parse_float_env("EXTRACTION_TARGET_CONTEXT_RATIO", 0.28)
    EXTRACTION_OUTPUT_RESERVE_RATIO = _parse_float_env("EXTRACTION_OUTPUT_RESERVE_RATIO", 0.25)
    EXTRACTION_MIN_CHUNK_CHARS = _parse_int_env("EXTRACTION_MIN_CHUNK_CHARS", 8000)
    EXTRACTION_MAX_CHUNK_CHARS = _parse_int_env("EXTRACTION_MAX_CHUNK_CHARS", 220000)
    EXTRACTION_CHUNK_PROFILE_VERSION = _parse_int_env("EXTRACTION_CHUNK_PROFILE_VERSION", 2)
    EXTRACTION_CHECKPOINT_DIR = os.environ.get("EXTRACTION_CHECKPOINT_DIR", "extraction_cache")
    EXTRACTION_ENTITY_INTRO_MAX_CHARS = _parse_int_env("EXTRACTION_ENTITY_INTRO_MAX_CHARS", 1200)
    DEEP_EXTRACTION_STATE_RESERVE_RATIO = _parse_float_env("DEEP_EXTRACTION_STATE_RESERVE_RATIO", 0.06)
    DEEP_EXTRACTION_SUMMARY_MAX_CHARS = _parse_int_env("DEEP_EXTRACTION_SUMMARY_MAX_CHARS", 4000)
    DEEP_EXTRACTION_ENTITY_SNAPSHOT_MAX_CHARS = _parse_int_env("DEEP_EXTRACTION_ENTITY_SNAPSHOT_MAX_CHARS", 10000)
    DEEP_EXTRACTION_ACTIVE_ENTITY_LIMIT = _parse_int_env("DEEP_EXTRACTION_ACTIVE_ENTITY_LIMIT", 80)
    DEEP_EXTRACTION_RECENT_CHUNKS = _parse_int_env("DEEP_EXTRACTION_RECENT_CHUNKS", 2)
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # WorldFish 模拟配置
    WORLD_FISH_DEFAULT_MAX_ROUNDS = int(os.environ.get('WORLD_FISH_DEFAULT_MAX_ROUNDS', '10'))
    WORLD_FISH_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    WORLD_FISH_ACTIONS = [
        'observe_world', 'state_position', 'adjust_plan', 'spread_influence'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    @classmethod
    def reload(cls):
        _load_environment()
        cls.SECRET_KEY = os.environ.get('SECRET_KEY', 'worldfish-secret-key')
        cls.DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
        cls.JSON_AS_ASCII = False
        cls.LLM_API_KEY = os.environ.get('LLM_API_KEY')
        cls.LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
        cls.LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
        cls.LLM_API_TYPE = os.environ.get('LLM_API_TYPE', 'openai_compatible')
        cls.LLM_URL_MODE = os.environ.get('LLM_URL_MODE', 'base_url')
        cls.SUBAGENT_LLM_API_KEY = os.environ.get('SUBAGENT_LLM_API_KEY', '')
        cls.SUBAGENT_LLM_BASE_URL = os.environ.get('SUBAGENT_LLM_BASE_URL', '')
        cls.SUBAGENT_LLM_MODEL_NAME = os.environ.get('SUBAGENT_LLM_MODEL_NAME', '')
        cls.SUBAGENT_LLM_API_TYPE = os.environ.get('SUBAGENT_LLM_API_TYPE', '')
        cls.SUBAGENT_LLM_URL_MODE = os.environ.get('SUBAGENT_LLM_URL_MODE', '')
        cls.PARSER_LLM_API_KEY = os.environ.get('PARSER_LLM_API_KEY', '')
        cls.PARSER_LLM_BASE_URL = os.environ.get('PARSER_LLM_BASE_URL', '')
        cls.PARSER_LLM_MODEL_NAME = os.environ.get('PARSER_LLM_MODEL_NAME', '')
        cls.PARSER_LLM_API_TYPE = os.environ.get('PARSER_LLM_API_TYPE', '')
        cls.PARSER_LLM_URL_MODE = os.environ.get('PARSER_LLM_URL_MODE', '')
        cls.LLM_THINKING_ENABLED = _parse_bool_env(os.environ.get('LLM_THINKING_ENABLED'), None)
        cls.LLM_REASONING_EFFORT = _parse_reasoning_effort(os.environ.get('LLM_REASONING_EFFORT'))
        cls.LLM_DEFAULT_CONTEXT_WINDOW = _parse_int_env('LLM_DEFAULT_CONTEXT_WINDOW', 128 * 1024)
        cls.LLM_DEEPSEEK_V4_CONTEXT_WINDOW = _parse_int_env('LLM_DEEPSEEK_V4_CONTEXT_WINDOW', 1_000_000)
        cls.LLM_CONTEXT_WINDOW = _parse_int_env('LLM_CONTEXT_WINDOW', 0)
        cls.AGENT_CONTEXT_COMPRESSION_RATIO = _parse_float_env('AGENT_CONTEXT_COMPRESSION_RATIO', 0.70)
        cls.EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "api")
        cls.EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
        cls.EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_BASE_URL", "")
        cls.EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
        cls.EMBEDDING_API_TYPE = os.environ.get("EMBEDDING_API_TYPE", "openai_compatible")
        cls.EMBEDDING_URL_MODE = os.environ.get("EMBEDDING_URL_MODE", "base_url")
        cls.RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
        cls.EXTRACTION_MAX_WORKERS = int(os.environ.get("EXTRACTION_MAX_WORKERS", "12"))
        cls.EXTRACTION_HUGE_WORKERS = int(os.environ.get("EXTRACTION_HUGE_WORKERS", "10"))
        cls.EXTRACTION_MASSIVE_WORKERS = int(os.environ.get("EXTRACTION_MASSIVE_WORKERS", "12"))
        cls.WORLD_FISH_DEFAULT_MAX_ROUNDS = int(os.environ.get('WORLD_FISH_DEFAULT_MAX_ROUNDS', '10'))
        cls.WORLD_FISH_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
        cls.WORLD_FISH_ACTIONS = ['observe_world', 'state_position', 'adjust_plan', 'spread_influence']
        cls.REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
        cls.REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
        cls.REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    @classmethod
    def mask_secret(cls, value: Any) -> str:
        if not value:
            return ''
        text = str(value)
        if len(text) <= 8:
            return '*' * len(text)
        return f"{text[:4]}...{text[-4:]}"

    @classmethod
    def get_embedding_config_status(cls) -> Dict[str, Any]:
        resolved = cls.get_embedding_config()
        provider = resolved.get('provider') or 'api'
        return {
            'provider': provider,
            'available': bool(resolved.get('available')),
            'api_key_configured': bool(resolved.get('api_key')),
            'api_key_masked': cls.mask_secret(resolved.get('api_key')),
            'base_url': resolved.get('base_url') or '',
            'model_name': resolved.get('model_name') or '',
            'api_type': resolved.get('api_type') or 'openai_compatible',
            'url_mode': resolved.get('url_mode') or 'base_url',
            'resolved_from': 'embedding',
            'explicitly_configured': resolved.get('explicitly_configured', bool(cls.EMBEDDING_API_KEY)),
            'explicit_api_key_configured': bool(cls.EMBEDDING_API_KEY),
            'explicit_api_key_masked': cls.mask_secret(cls.EMBEDDING_API_KEY),
            'explicit_base_url': cls.EMBEDDING_BASE_URL or '',
            'explicit_model_name': resolved.get('model_name') or '',
            'explicit_api_type': cls.EMBEDDING_API_TYPE or 'openai_compatible',
            'explicit_url_mode': cls.EMBEDDING_URL_MODE or 'base_url',
            'local_model_name': cls.LOCAL_EMBEDDING_MODEL_NAME,
            'local_model_source': cls.LOCAL_EMBEDDING_MODEL_SOURCE,
        }

    @classmethod
    def get_llm_config_status(cls) -> Dict[str, Any]:
        cls.reload()
        agent_settings = cls.get_agent_settings_status(reload_first=False)

        explicit_configs = {
            'agent': {
                'api_key': cls.LLM_API_KEY or '',
                'base_url': cls.LLM_BASE_URL or 'https://api.openai.com/v1',
                'model_name': cls.LLM_MODEL_NAME or 'gpt-4o-mini',
                'api_type': cls.LLM_API_TYPE or 'openai_compatible',
                'url_mode': cls.LLM_URL_MODE or 'base_url',
            },
            'subagent': {
                'api_key': cls.SUBAGENT_LLM_API_KEY or '',
                'base_url': cls.SUBAGENT_LLM_BASE_URL or '',
                'model_name': cls.SUBAGENT_LLM_MODEL_NAME or '',
                'api_type': cls.SUBAGENT_LLM_API_TYPE or '',
                'url_mode': cls.SUBAGENT_LLM_URL_MODE or '',
            },
            'parser': {
                'api_key': cls.PARSER_LLM_API_KEY or '',
                'base_url': cls.PARSER_LLM_BASE_URL or '',
                'model_name': cls.PARSER_LLM_MODEL_NAME or '',
                'api_type': cls.PARSER_LLM_API_TYPE or '',
                'url_mode': cls.PARSER_LLM_URL_MODE or '',
            },
        }

        def role_status(role: str) -> Dict[str, Any]:
            resolved = cls.get_llm_config(role)
            explicit = explicit_configs.get(role, {})
            return {
                'api_key_configured': bool(resolved['api_key']),
                'api_key_masked': cls.mask_secret(resolved['api_key']),
                'base_url': resolved['base_url'],
                'model_name': resolved['model_name'],
                'api_type': resolved.get('api_type') or 'openai_compatible',
                'url_mode': resolved.get('url_mode') or 'base_url',
                'resolved_from': resolved['resolved_from'],
                'explicitly_configured': resolved['explicitly_configured'],
                'explicit_api_key_configured': bool(explicit.get('api_key')),
                'explicit_api_key_masked': cls.mask_secret(explicit.get('api_key')),
                'explicit_base_url': explicit.get('base_url') or '',
                'explicit_model_name': explicit.get('model_name') or '',
                'explicit_api_type': explicit.get('api_type') or '',
                'explicit_url_mode': explicit.get('url_mode') or '',
            }

        agent_llm = role_status('agent')
        return {
            'api_key_configured': agent_llm['api_key_configured'],
            'api_key_masked': agent_llm['api_key_masked'],
            'base_url': agent_llm['base_url'],
            'model_name': agent_llm['model_name'],
            'api_type': agent_llm['api_type'],
            'url_mode': agent_llm['url_mode'],
            'agent_llm': agent_llm,
            'subagent_llm': role_status('subagent'),
            'parser_llm': role_status('parser'),
            'embedding': cls.get_embedding_config_status(),
            **agent_settings,
        }

    @classmethod
    def get_agent_settings_status(cls, reload_first: bool = True) -> Dict[str, Any]:
        if reload_first:
            cls.reload()
        model_name = cls.LLM_MODEL_NAME
        normalized_model = (model_name or '').strip().lower()
        is_deepseek_v4 = normalized_model in {'deepseek-v4-pro', 'deepseek-v4-flash'} or (
            'deepseek' in normalized_model and 'v4' in normalized_model
        )
        context_window = cls.LLM_CONTEXT_WINDOW or (
            cls.LLM_DEEPSEEK_V4_CONTEXT_WINDOW if is_deepseek_v4 else cls.LLM_DEFAULT_CONTEXT_WINDOW
        )
        return {
            'model_name': model_name,
            'thinking_enabled': cls.LLM_THINKING_ENABLED if cls.LLM_THINKING_ENABLED is not None else is_deepseek_v4,
            'reasoning_effort': cls.LLM_REASONING_EFFORT,
            'context_window': context_window,
            'context_window_override': cls.LLM_CONTEXT_WINDOW,
            'default_context_window': cls.LLM_DEFAULT_CONTEXT_WINDOW,
            'deepseek_v4_context_window': cls.LLM_DEEPSEEK_V4_CONTEXT_WINDOW,
            'compression_threshold': cls.AGENT_CONTEXT_COMPRESSION_RATIO,
            'model_profile': 'deepseek-v4' if is_deepseek_v4 else 'openai-compatible',
        }

    @classmethod
    def save_agent_settings(
        cls,
        thinking_enabled: Any = None,
        reasoning_effort: Any = None,
        context_window: Any = None,
        compression_threshold: Any = None,
    ) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}

        if thinking_enabled is not None:
            parsed = _parse_bool_env(thinking_enabled, None)
            if parsed is None:
                raise ValueError('thinking_enabled 必须是布尔值')
            updates['LLM_THINKING_ENABLED'] = 'true' if parsed else 'false'

        if reasoning_effort is not None:
            parsed_effort = _parse_reasoning_effort(reasoning_effort)
            if str(reasoning_effort).strip().lower() not in {'high', 'max'}:
                raise ValueError('reasoning_effort 只能是 high 或 max')
            updates['LLM_REASONING_EFFORT'] = parsed_effort

        if context_window is not None:
            try:
                parsed_window = int(context_window)
            except (TypeError, ValueError):
                raise ValueError('context_window 必须是整数')
            if parsed_window < 0:
                raise ValueError('context_window 不能小于 0')
            updates['LLM_CONTEXT_WINDOW'] = parsed_window

        if compression_threshold is not None:
            try:
                parsed_threshold = float(compression_threshold)
            except (TypeError, ValueError):
                raise ValueError('compression_threshold 必须是数字')
            if parsed_threshold < 0.50 or parsed_threshold > 0.95:
                raise ValueError('compression_threshold 必须在 0.50 到 0.95 之间')
            updates['AGENT_CONTEXT_COMPRESSION_RATIO'] = parsed_threshold

        if updates:
            _persist_env_updates(updates)
            for key, value in updates.items():
                os.environ[key] = str(value)

        cls.reload()
        return cls.get_agent_settings_status(reload_first=False)

    @classmethod
    def _validate_api_type(cls, api_type: Any) -> str:
        cleaned_type = str(api_type or 'openai_compatible').strip().lower()
        if cleaned_type not in {'openai_compatible', 'anthropic'}:
            raise ValueError('api_type 只能是 openai_compatible 或 anthropic')
        return cleaned_type

    @classmethod
    def _validate_url_mode(cls, url_mode: Any) -> str:
        cleaned_mode = str(url_mode or 'base_url').strip().lower()
        if cleaned_mode not in {'base_url', 'full_url'}:
            raise ValueError('url_mode 只能是 base_url 或 full_url')
        return cleaned_mode

    @classmethod
    def save_llm_config(
        cls,
        api_key: Any = None,
        base_url: Any = None,
        model_name: Any = None,
        role: str = 'agent',
        api_type: Any = None,
        url_mode: Any = None,
    ) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        normalized_role = str(role or 'agent').strip().lower()
        key_map = {
            'agent': ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL_NAME', 'LLM_API_TYPE', 'LLM_URL_MODE'),
            'subagent': ('SUBAGENT_LLM_API_KEY', 'SUBAGENT_LLM_BASE_URL', 'SUBAGENT_LLM_MODEL_NAME', 'SUBAGENT_LLM_API_TYPE', 'SUBAGENT_LLM_URL_MODE'),
            'parser': ('PARSER_LLM_API_KEY', 'PARSER_LLM_BASE_URL', 'PARSER_LLM_MODEL_NAME', 'PARSER_LLM_API_TYPE', 'PARSER_LLM_URL_MODE'),
        }
        if normalized_role not in key_map:
            raise ValueError('role 只能是 agent、subagent 或 parser')

        api_key_key, base_url_key, model_name_key, api_type_key, url_mode_key = key_map[normalized_role]

        if api_key is not None:
            cleaned_key = str(api_key).strip()
            if not cleaned_key:
                raise ValueError('LLM API Key 不能为空')
            updates[api_key_key] = cleaned_key

        if base_url is not None:
            default_url = 'https://api.openai.com/v1' if normalized_role == 'agent' else ''
            updates[base_url_key] = str(base_url).strip() or default_url

        if model_name is not None:
            default_model = 'gpt-4o-mini' if normalized_role == 'agent' else ''
            updates[model_name_key] = str(model_name).strip() or default_model

        if api_type is not None:
            updates[api_type_key] = cls._validate_api_type(api_type)

        if url_mode is not None:
            updates[url_mode_key] = cls._validate_url_mode(url_mode)

        if not updates:
            return cls.get_llm_config_status()

        _persist_env_updates(updates)
        for key, value in updates.items():
            os.environ[key] = str(value)

        cls.reload()
        return cls.get_llm_config_status()

    @classmethod
    def save_embedding_config(
        cls,
        api_key: Any = None,
        base_url: Any = None,
        model_name: Any = None,
        api_type: Any = None,
        url_mode: Any = None,
        provider: Any = None,
    ) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        cleaned_provider = str(provider if provider is not None else cls.EMBEDDING_PROVIDER or 'api').strip().lower()
        if cleaned_provider not in {'api', 'local'}:
            raise ValueError('Embedding provider 只能是 api 或 local')
        if provider is not None:
            updates['EMBEDDING_PROVIDER'] = cleaned_provider

        if cleaned_provider == 'local':
            updates['EMBEDDING_MODEL_NAME'] = cls.LOCAL_EMBEDDING_MODEL_NAME
            updates['EMBEDDING_API_TYPE'] = 'openai_compatible'
            updates['EMBEDDING_URL_MODE'] = 'base_url'

        if api_key is not None and cleaned_provider == 'api':
            cleaned_key = str(api_key).strip()
            if not cleaned_key:
                raise ValueError('Embedding API Key 不能为空')
            updates['EMBEDDING_API_KEY'] = cleaned_key

        if base_url is not None and cleaned_provider == 'api':
            updates['EMBEDDING_BASE_URL'] = str(base_url).strip()

        if model_name is not None and cleaned_provider == 'api':
            updates['EMBEDDING_MODEL_NAME'] = str(model_name).strip() or 'text-embedding-3-small'

        if api_type is not None:
            cleaned_api_type = cls._validate_api_type(api_type)
            if cleaned_api_type != 'openai_compatible':
                raise ValueError('Embedding API 目前仅支持 OpenAI 兼容格式')
            updates['EMBEDDING_API_TYPE'] = cleaned_api_type

        if url_mode is not None:
            updates['EMBEDDING_URL_MODE'] = cls._validate_url_mode(url_mode)

        if not updates:
            return cls.get_llm_config_status()

        _persist_env_updates(updates)
        for key, value in updates.items():
            os.environ[key] = str(value)

        cls.reload()
        return cls.get_llm_config_status()
    
    @classmethod
    def validate(cls):
        """验证启动所需配置。

        LLM / Embedding API Key 改为通过 GUI 配置页按需保存，
        因此后端启动阶段不再强制要求 .env 或 API Key 存在。
        """
        return []


Config.reload()

