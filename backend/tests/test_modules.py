from flask import Blueprint, Flask

from app.core.guards import guard_blueprint
from app.core.module_store import ModuleStateStore
from app.core.modules import ManifestModule, ModuleDependencyError, ModuleManifest, ModuleRegistry
from app.modules.builtin import get_builtin_module_definitions
from app.modules.loader import install_modules


def make_module(module_id, depends=None, enabled_by_default=True):
    return ManifestModule(ModuleManifest(
        id=module_id,
        name=module_id,
        depends=depends or [],
        enabled_by_default=enabled_by_default,
    ))


def make_registry(tmp_path):
    return ModuleRegistry(ModuleStateStore(str(tmp_path / 'modules.json')))


def test_load_all_uses_default_enabled_state(tmp_path):
    registry = make_registry(tmp_path)
    registry.register(make_module('core'))
    registry.register(make_module('optional', enabled_by_default=False))

    registry.load_all()

    assert registry.is_enabled('core') is True
    assert registry.is_enabled('optional') is False


def test_disabled_state_is_persisted_across_registry_instances(tmp_path):
    state_file = tmp_path / 'modules.json'
    first = ModuleRegistry(ModuleStateStore(str(state_file)))
    first.register(make_module('rag'))
    first.load_all()
    first.disable('rag')

    second = ModuleRegistry(ModuleStateStore(str(state_file)))
    second.register(make_module('rag'))
    second.load_all()

    assert second.is_enabled('rag') is False


def test_enable_turns_on_dependencies_and_prevents_direct_disable(tmp_path):
    registry = make_registry(tmp_path)
    registry.register(make_module('world-builder', enabled_by_default=False))
    registry.register(make_module('rag', depends=['world-builder'], enabled_by_default=False))
    registry.load_all()

    registry.enable('rag')

    assert registry.is_enabled('world-builder') is True
    assert registry.is_enabled('rag') is True
    try:
        registry.disable('world-builder')
    except ModuleDependencyError as exc:
        assert exc.dependents == ['rag']
    else:
        raise AssertionError('停用被依赖模块时应抛出 ModuleDependencyError')


def test_cascade_disable_turns_off_dependents_first(tmp_path):
    registry = make_registry(tmp_path)
    registry.register(make_module('world-builder'))
    registry.register(make_module('simulation', depends=['world-builder']))
    registry.register(make_module('report', depends=['simulation']))
    registry.load_all()

    registry.disable('world-builder', cascade=True)

    assert registry.is_enabled('report') is False
    assert registry.is_enabled('simulation') is False
    assert registry.is_enabled('world-builder') is False


def test_builtin_module_definitions_include_blueprint_bindings():
    definitions = get_builtin_module_definitions()
    by_id = {item.manifest.id: item for item in definitions}

    assert 'world-builder' in by_id
    assert by_id['world-builder'].blueprints
    assert by_id['settings'].blueprints[0].guard is False


def test_install_modules_registers_blueprints_and_keeps_settings_available(tmp_path):
    app = Flask(__name__)
    registry = make_registry(tmp_path)

    install_modules(app, object, registry=registry)

    assert registry.is_enabled('world-builder') is True
    assert 'world_build' in app.blueprints
    assert 'modules' in app.blueprints

    client = app.test_client()
    response = client.get('/api/modules')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert any(item['blueprints'] for item in payload['modules'])


def test_installed_module_route_is_guarded_when_disabled(tmp_path):
    app = Flask(__name__)
    registry = make_registry(tmp_path)
    install_modules(app, object, registry=registry)
    registry.disable('rag')

    response = app.test_client().get('/api/rag/chunk-presets')

    assert response.status_code == 503
    assert response.get_json()['module_id'] == 'rag'


def test_blueprint_guard_returns_503_when_module_disabled(tmp_path):
    registry = make_registry(tmp_path)
    registry.register(make_module('rag', enabled_by_default=False))
    registry.load_all()

    app = Flask(__name__)
    app.extensions['worldfish_modules'] = registry
    bp = Blueprint('rag_test', __name__)

    @bp.route('/ping')
    def ping():
        return {'success': True}

    app.register_blueprint(guard_blueprint(bp, 'rag'), url_prefix='/api/rag')

    client = app.test_client()
    response = client.get('/api/rag/ping')

    assert response.status_code == 503
    assert response.get_json()['module_id'] == 'rag'

    registry.enable('rag')
    response = client.get('/api/rag/ping')

    assert response.status_code == 200
    assert response.get_json()['success'] is True
