"""
国际化翻译工具
支持多语言消息查找和插值，线程安全。
"""

import json
import os
import threading
from flask import request, has_request_context

_STORAGE = threading.local()
_ROOT = os.path.dirname(__file__)
_LOCALE_DIR = os.path.join(_ROOT, '..', '..', '..', 'locales')


def _load_json(name):
    with open(os.path.join(_LOCALE_DIR, name), 'r', encoding='utf-8') as handle:
        return json.load(handle)


_LANG_INDEX = _load_json('languages.json')
_MESSAGE_BUNDLES = {
    entry.name[:-5]: _load_json(entry.name)
    for entry in os.scandir(_LOCALE_DIR)
    if entry.name.endswith('.json') and entry.name != 'languages.json'
}


def _walk_dotted(mapping, key):
    """沿点分隔键逐层取值，失败返回 None。"""
    cur = mapping
    for segment in key.split('.'):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(segment)
    return cur


def set_locale(locale: str):
    _STORAGE.locale = locale


def get_locale() -> str:
    if has_request_context():
        candidate = request.headers.get('Accept-Language', 'zh')
        return candidate if candidate in _MESSAGE_BUNDLES else 'zh'
    return getattr(_STORAGE, 'locale', 'zh')


def t(key: str, **kwargs) -> str:
    lang = get_locale()
    bundle = _MESSAGE_BUNDLES.get(lang, _MESSAGE_BUNDLES.get('zh', {}))
    value = _walk_dotted(bundle, key)
    if value is None and lang != 'zh':
        value = _walk_dotted(_MESSAGE_BUNDLES.get('zh', {}), key)
    if value is None:
        return key
    if kwargs:
        for placeholder, replacement in kwargs.items():
            value = value.replace(f'{{{placeholder}}}', str(replacement))
    return value


def get_language_instruction() -> str:
    lang = get_locale()
    entry = _LANG_INDEX.get(lang, _LANG_INDEX.get('zh', {}))
    return entry.get('llmInstruction', '请使用中文回答。')
