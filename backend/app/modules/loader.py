"""模块安装器。"""

from __future__ import annotations

from typing import Dict, List

from flask import Flask

from app.core.guards import register_module_guard
from app.core.modules import ManifestModule, ModuleRegistry, get_module_registry

from .builtin import get_builtin_module_definitions
from .definitions import BackendModuleDefinition


def install_modules(app: Flask, config_class, registry: ModuleRegistry | None = None) -> ModuleRegistry:
    """注册内置模块并安装它们声明的蓝图。"""
    module_registry = registry or get_module_registry()
    definitions = get_builtin_module_definitions()

    module_registry.bind_context(app=app, config=config_class)
    app.extensions['worldfish_modules'] = module_registry
    app.extensions['worldfish_module_definitions'] = {
        item.manifest.id: item for item in definitions
    }

    _register_manifests(module_registry, definitions)
    module_registry.load_all()
    _register_blueprints(app, definitions)
    return module_registry


def module_definition_map(app: Flask) -> Dict[str, BackendModuleDefinition]:
    return app.extensions.get('worldfish_module_definitions', {})


def module_bindings_snapshot(app: Flask) -> Dict[str, List[dict]]:
    return {
        module_id: [binding.to_dict() for binding in definition.blueprints]
        for module_id, definition in module_definition_map(app).items()
    }


def _register_manifests(registry: ModuleRegistry, definitions: List[BackendModuleDefinition]):
    existing = {item['manifest']['id'] for item in registry.list(include_private=True)}
    for definition in definitions:
        if definition.manifest.id not in existing:
            registry.register(ManifestModule(definition.manifest))


def _register_blueprints(app: Flask, definitions: List[BackendModuleDefinition]):
    registered_names = set(app.blueprints.keys())
    for definition in definitions:
        module_id = definition.manifest.id
        for binding in definition.blueprints:
            blueprint = binding.blueprint
            if blueprint.name in registered_names:
                continue
            if binding.guard:
                register_module_guard(blueprint, module_id)
            app.register_blueprint(blueprint, url_prefix=binding.url_prefix)
            registered_names.add(blueprint.name)
