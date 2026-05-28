"""模块管理 API。"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.core.modules import get_module_registry
from app.utils.logger import get_logger

modules_bp = Blueprint('modules', __name__)
logger = get_logger('worldfish.api.modules')


def _ok(**payload):
    return jsonify({'success': True, **payload})


def _handle_error(action: str, module_id: str, exc: Exception):
    logger.error(f'{action}模块失败: {module_id}: {exc}')
    status = 404 if isinstance(exc, KeyError) else 400
    return jsonify({
        'success': False,
        'message': f'{action}模块失败: {exc}',
        'error': str(exc),
        'module_id': module_id,
    }), status


@modules_bp.route('', methods=['GET'])
@modules_bp.route('/', methods=['GET'])
def list_modules():
    registry = get_module_registry()
    return _ok(modules=registry.list())


@modules_bp.route('/navigation', methods=['GET'])
def get_navigation():
    registry = get_module_registry()
    return _ok(navigation=registry.navigation())


@modules_bp.route('/<module_id>', methods=['GET'])
def get_module(module_id: str):
    try:
        return _ok(module=get_module_registry().get(module_id))
    except Exception as exc:
        return _handle_error('读取', module_id, exc)


@modules_bp.route('/<module_id>/enable', methods=['POST'])
def enable_module(module_id: str):
    try:
        registry = get_module_registry()
        registry.enable(module_id)
        return _ok(module=registry.get(module_id), message='模块已启用')
    except Exception as exc:
        return _handle_error('启用', module_id, exc)


@modules_bp.route('/<module_id>/disable', methods=['POST'])
def disable_module(module_id: str):
    if module_id == 'settings':
        return jsonify({
            'success': False,
            'message': '系统设置模块不能停用',
            'module_id': module_id,
        }), 400
    try:
        registry = get_module_registry()
        registry.disable(module_id)
        return _ok(module=registry.get(module_id), message='模块已停用')
    except Exception as exc:
        return _handle_error('停用', module_id, exc)


@modules_bp.route('/<module_id>/reload', methods=['POST'])
def reload_module(module_id: str):
    try:
        registry = get_module_registry()
        registry.reload(module_id)
        return _ok(module=registry.get(module_id), message='模块已重载')
    except Exception as exc:
        return _handle_error('重载', module_id, exc)
