"""模块启停保护。"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import current_app, jsonify

from .modules import get_module_registry


def _registry():
    return current_app.extensions.get('worldfish_modules') or get_module_registry()


def module_disabled_response(module_id: str):
    return jsonify({
        'success': False,
        'error': f'模块已停用: {module_id}',
        'message': f'模块已停用: {module_id}',
        'module_id': module_id,
    }), 503


def require_module(module_id: str):
    """函数级模块保护。"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _registry().is_enabled(module_id):
                return module_disabled_response(module_id)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def guard_blueprint(blueprint, module_id: str):
    """蓝图级模块保护。"""

    endpoint = f'_worldfish_module_guard_{module_id.replace("-", "_")}'

    @blueprint.before_request
    def _module_guard():
        if not _registry().is_enabled(module_id):
            return module_disabled_response(module_id)

    _module_guard.__name__ = endpoint
    return blueprint
