"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
from typing import Any, Dict

from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
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
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）
    # Agent LLM API：保留旧变量名以兼容现有 .env
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    # SubAgent LLM API：不填时按 Agent > Parser 回退
    SUBAGENT_LLM_API_KEY = os.environ.get('SUBAGENT_LLM_API_KEY', '')
    SUBAGENT_LLM_BASE_URL = os.environ.get('SUBAGENT_LLM_BASE_URL', '')
    SUBAGENT_LLM_MODEL_NAME = os.environ.get('SUBAGENT_LLM_MODEL_NAME', '')
    # 解析 Agent LLM API：不填时按 Agent > SubAgent 回退
    PARSER_LLM_API_KEY = os.environ.get('PARSER_LLM_API_KEY', '')
    PARSER_LLM_BASE_URL = os.environ.get('PARSER_LLM_BASE_URL', '')
    PARSER_LLM_MODEL_NAME = os.environ.get('PARSER_LLM_MODEL_NAME', '')
    LLM_THINKING_ENABLED = _parse_bool_env(os.environ.get('LLM_THINKING_ENABLED'), None)
    LLM_REASONING_EFFORT = _parse_reasoning_effort(os.environ.get('LLM_REASONING_EFFORT'))
    LLM_DEFAULT_CONTEXT_WINDOW = _parse_int_env('LLM_DEFAULT_CONTEXT_WINDOW', 128 * 1024)
    LLM_DEEPSEEK_V4_CONTEXT_WINDOW = _parse_int_env('LLM_DEEPSEEK_V4_CONTEXT_WINDOW', 1_000_000)
    LLM_CONTEXT_WINDOW = _parse_int_env('LLM_CONTEXT_WINDOW', 0)
    AGENT_CONTEXT_COMPRESSION_RATIO = _parse_float_env('AGENT_CONTEXT_COMPRESSION_RATIO', 0.70)
    
    # Embedding 配置（RAG 向量化）
    # 可独立配置 Embedding API（不填则复用 LLM 的 key/url）
    EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
    EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_BASE_URL", "")
    EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "text-embedding-3-small")

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
            },
            'subagent': {
                'api_key': cls.SUBAGENT_LLM_API_KEY or '',
                'base_url': cls.SUBAGENT_LLM_BASE_URL or '',
                'model_name': cls.SUBAGENT_LLM_MODEL_NAME or '',
            },
            'parser': {
                'api_key': cls.PARSER_LLM_API_KEY or '',
                'base_url': cls.PARSER_LLM_BASE_URL or '',
                'model_name': cls.PARSER_LLM_MODEL_NAME or '',
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
            'explicitly_configured': bool(configs[normalized_role]['api_key']) if normalized_role in configs else False,
        }

    @classmethod
    def get_embedding_config(cls) -> dict:
        """获取 Embedding 配置（独立配置优先，否则复用 Agent LLM 配置）。"""
        llm_config = cls.get_llm_config('agent')
        return {
            "api_key": cls.EMBEDDING_API_KEY or llm_config['api_key'],
            "base_url": cls.EMBEDDING_BASE_URL or llm_config['base_url'],
            "model_name": cls.EMBEDDING_MODEL_NAME,
        }
    
    # RAG 配置
    RAG_CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "800"))
    RAG_CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "100"))
    RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
    
    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    @classmethod
    def reload(cls):
        _load_environment()
        cls.SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
        cls.DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
        cls.JSON_AS_ASCII = False
        cls.LLM_API_KEY = os.environ.get('LLM_API_KEY')
        cls.LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
        cls.LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
        cls.SUBAGENT_LLM_API_KEY = os.environ.get('SUBAGENT_LLM_API_KEY', '')
        cls.SUBAGENT_LLM_BASE_URL = os.environ.get('SUBAGENT_LLM_BASE_URL', '')
        cls.SUBAGENT_LLM_MODEL_NAME = os.environ.get('SUBAGENT_LLM_MODEL_NAME', '')
        cls.PARSER_LLM_API_KEY = os.environ.get('PARSER_LLM_API_KEY', '')
        cls.PARSER_LLM_BASE_URL = os.environ.get('PARSER_LLM_BASE_URL', '')
        cls.PARSER_LLM_MODEL_NAME = os.environ.get('PARSER_LLM_MODEL_NAME', '')
        cls.LLM_THINKING_ENABLED = _parse_bool_env(os.environ.get('LLM_THINKING_ENABLED'), None)
        cls.LLM_REASONING_EFFORT = _parse_reasoning_effort(os.environ.get('LLM_REASONING_EFFORT'))
        cls.LLM_DEFAULT_CONTEXT_WINDOW = _parse_int_env('LLM_DEFAULT_CONTEXT_WINDOW', 128 * 1024)
        cls.LLM_DEEPSEEK_V4_CONTEXT_WINDOW = _parse_int_env('LLM_DEEPSEEK_V4_CONTEXT_WINDOW', 1_000_000)
        cls.LLM_CONTEXT_WINDOW = _parse_int_env('LLM_CONTEXT_WINDOW', 0)
        cls.AGENT_CONTEXT_COMPRESSION_RATIO = _parse_float_env('AGENT_CONTEXT_COMPRESSION_RATIO', 0.70)
        cls.ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
        cls.EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
        cls.EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_BASE_URL", "")
        cls.EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
        cls.RAG_CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "800"))
        cls.RAG_CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "100"))
        cls.RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
        cls.OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
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
    def get_llm_config_status(cls) -> Dict[str, Any]:
        cls.reload()
        agent_settings = cls.get_agent_settings_status(reload_first=False)

        def role_status(role: str) -> Dict[str, Any]:
            resolved = cls.get_llm_config(role)
            return {
                'api_key_configured': bool(resolved['api_key']),
                'api_key_masked': cls.mask_secret(resolved['api_key']),
                'base_url': resolved['base_url'],
                'model_name': resolved['model_name'],
                'resolved_from': resolved['resolved_from'],
                'explicitly_configured': resolved['explicitly_configured'],
            }

        agent_llm = role_status('agent')
        return {
            'api_key_configured': agent_llm['api_key_configured'],
            'api_key_masked': agent_llm['api_key_masked'],
            'base_url': agent_llm['base_url'],
            'model_name': agent_llm['model_name'],
            'agent_llm': agent_llm,
            'subagent_llm': role_status('subagent'),
            'parser_llm': role_status('parser'),
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
    def save_llm_config(
        cls,
        api_key: Any = None,
        base_url: Any = None,
        model_name: Any = None,
    ) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}

        if api_key is not None:
            cleaned_key = str(api_key).strip()
            if not cleaned_key:
                raise ValueError('LLM API Key 不能为空')
            updates['LLM_API_KEY'] = cleaned_key

        if base_url is not None:
            updates['LLM_BASE_URL'] = str(base_url).strip() or 'https://api.openai.com/v1'

        if model_name is not None:
            updates['LLM_MODEL_NAME'] = str(model_name).strip() or 'gpt-4o-mini'

        if not updates:
            return cls.get_llm_config_status()

        _persist_env_updates(updates)
        for key, value in updates.items():
            os.environ[key] = str(value)

        cls.reload()
        return cls.get_llm_config_status()
    
    @classmethod
    def validate(cls):
        """验证必要配置"""
        errors = []
        if not any([
            cls.LLM_API_KEY,
            cls.SUBAGENT_LLM_API_KEY,
            cls.PARSER_LLM_API_KEY,
        ]):
            errors.append("至少需要配置一组 LLM API Key（LLM_API_KEY / SUBAGENT_LLM_API_KEY / PARSER_LLM_API_KEY）")
        return errors


Config.reload()

