"""模块管理 API。"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.core.modules import ModuleDependencyError, get_module_registry
from app.utils.logger import get_logger

modules_bp = Blueprint('modules', __name__)
logger = get_logger('worldfish.api.modules')


def _ok(**payload):
    return jsonify({'success': True, **payload})


def _registry():
    return current_app.extensions.get('worldfish_modules') or get_module_registry()


def _module_bindings_snapshot() -> dict:
    definitions = current_app.extensions.get('worldfish_module_definitions', {})
    return {
        module_id: [binding.to_dict() for binding in definition.blueprints]
        for module_id, definition in definitions.items()
    }


def _with_bindings(module: dict) -> dict:
    bindings = _module_bindings_snapshot()
    manifest = module.get('manifest', {})
    module['blueprints'] = bindings.get(manifest.get('id'), [])
    return module


def _modules_with_bindings(modules: list) -> list:
    return [_with_bindings(item) for item in modules]


def _handle_error(action: str, module_id: str, exc: Exception):
    logger.error(f'{action}模块失败: {module_id}: {exc}')
    status = 404 if isinstance(exc, KeyError) else 400
    payload = {
        'success': False,
        'message': f'{action}模块失败: {exc}',
        'error': str(exc),
        'module_id': module_id,
    }
    if isinstance(exc, ModuleDependencyError):
        payload['message'] = '模块被启用模块依赖，请先停用依赖方或使用级联停用'
        payload['dependents'] = exc.dependents
        payload['dependency_tree'] = _registry().dependency_tree(module_id)
    return jsonify(payload), status


@modules_bp.route('', methods=['GET'])
@modules_bp.route('/', methods=['GET'])
def list_modules():
    registry = _registry()
    return _ok(modules=_modules_with_bindings(registry.list()))


@modules_bp.route('/navigation', methods=['GET'])
def get_navigation():
    registry = _registry()
    return _ok(navigation=registry.navigation())


@modules_bp.route('/<module_id>', methods=['GET'])
def get_module(module_id: str):
    try:
        return _ok(module=_with_bindings(_registry().get(module_id)))
    except Exception as exc:
        return _handle_error('读取', module_id, exc)


@modules_bp.route('/<module_id>/enable', methods=['POST'])
def enable_module(module_id: str):
    try:
        registry = _registry()
        registry.enable(module_id)
        return _ok(module=_with_bindings(registry.get(module_id)), message='模块已启用')
    except Exception as exc:
        return _handle_error('启用', module_id, exc)


@modules_bp.route('/<module_id>/disable', methods=['POST'])
def disable_module(module_id: str):
    cascade = str(request.args.get('cascade', '')).lower() in {'1', 'true', 'yes', 'on'}
    if module_id == 'settings':
        return jsonify({
            'success': False,
            'message': '系统设置模块不能停用',
            'module_id': module_id,
        }), 400
    try:
        registry = _registry()
        registry.disable(module_id, cascade=cascade)
        return _ok(module=_with_bindings(registry.get(module_id)), message='模块已停用')
    except Exception as exc:
        return _handle_error('停用', module_id, exc)


@modules_bp.route('/<module_id>/reload', methods=['POST'])
def reload_module(module_id: str):
    try:
        registry = _registry()
        registry.reload(module_id)
        return _ok(module=_with_bindings(registry.get(module_id)), message='模块已重载')
    except Exception as exc:
        return _handle_error('重载', module_id, exc)
