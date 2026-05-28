"""模块注册表与生命周期管理。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional

from .events import get_event_bus


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ModuleManifest:
    """模块元数据。"""

    id: str
    name: str
    version: str = '0.1.0'
    description: str = ''
    category: str = 'general'
    depends: List[str] = field(default_factory=list)
    routes: List[str] = field(default_factory=list)
    nav: List[Dict[str, Any]] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    enabled_by_default: bool = True
    private: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'category': self.category,
            'depends': list(self.depends),
            'routes': list(self.routes),
            'nav': list(self.nav),
            'capabilities': list(self.capabilities),
            'enabled_by_default': self.enabled_by_default,
            'private': self.private,
        }


@dataclass
class ModuleRuntime:
    """模块运行态。"""

    loaded: bool = False
    enabled: bool = False
    error: Optional[str] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'loaded': self.loaded,
            'enabled': self.enabled,
            'error': self.error,
            'started_at': self.started_at,
            'updated_at': self.updated_at,
        }


class ModuleBase:
    """模块基类。"""

    manifest: ModuleManifest

    def __init__(self, manifest: ModuleManifest):
        self.manifest = manifest

    def load(self, context: Dict[str, Any]):
        """加载模块定义。"""

    def init(self, context: Dict[str, Any]):
        """初始化模块资源。"""

    def enable(self, context: Dict[str, Any]):
        """启用模块能力。"""

    def disable(self, context: Dict[str, Any]):
        """停用模块能力。"""

    def reload(self, context: Dict[str, Any]):
        """重载模块配置。"""
        self.disable(context)
        self.enable(context)

    def destroy(self, context: Dict[str, Any]):
        """销毁模块资源。"""


class ManifestModule(ModuleBase):
    """仅声明元数据的内置模块。"""


class ModuleRegistry:
    """模块注册表，负责生命周期与热启停。"""

    def __init__(self):
        self._lock = RLock()
        self._modules: Dict[str, ModuleBase] = {}
        self._runtime: Dict[str, ModuleRuntime] = {}
        self._context: Dict[str, Any] = {'events': get_event_bus()}

    def bind_context(self, **kwargs):
        with self._lock:
            self._context.update(kwargs)

    def register(self, module: ModuleBase):
        module_id = module.manifest.id
        if not module_id:
            raise ValueError('模块 id 不能为空')
        with self._lock:
            if module_id in self._modules:
                raise ValueError(f'模块已注册: {module_id}')
            self._modules[module_id] = module
            self._runtime[module_id] = ModuleRuntime(updated_at=_now_iso())

    def load_all(self):
        with self._lock:
            modules = list(self._modules.values())
        for module in modules:
            self.load(module.manifest.id)
            if module.manifest.enabled_by_default:
                self.enable(module.manifest.id)

    def load(self, module_id: str):
        module = self._get_module(module_id)
        runtime = self._get_runtime(module_id)
        try:
            self._ensure_dependencies_loaded(module)
            module.load(self._context)
            module.init(self._context)
            runtime.loaded = True
            runtime.error = None
            runtime.updated_at = _now_iso()
        except Exception as exc:
            runtime.error = str(exc)
            runtime.updated_at = _now_iso()
            raise

    def enable(self, module_id: str):
        module = self._get_module(module_id)
        runtime = self._get_runtime(module_id)
        try:
            self._ensure_dependencies_enabled(module)
            if not runtime.loaded:
                self.load(module_id)
            module.enable(self._context)
            runtime.enabled = True
            runtime.error = None
            runtime.started_at = runtime.started_at or _now_iso()
            runtime.updated_at = _now_iso()
            get_event_bus().emit('module.enabled', {'module_id': module_id})
        except Exception as exc:
            runtime.error = str(exc)
            runtime.updated_at = _now_iso()
            raise

    def disable(self, module_id: str):
        module = self._get_module(module_id)
        runtime = self._get_runtime(module_id)
        dependents = self.enabled_dependents(module_id)
        if dependents:
            raise ValueError(f'模块 {module_id} 被启用模块依赖: {", ".join(dependents)}')
        try:
            module.disable(self._context)
            get_event_bus().unsubscribe_module(module_id)
            runtime.enabled = False
            runtime.error = None
            runtime.updated_at = _now_iso()
            get_event_bus().emit('module.disabled', {'module_id': module_id})
        except Exception as exc:
            runtime.error = str(exc)
            runtime.updated_at = _now_iso()
            raise

    def reload(self, module_id: str):
        module = self._get_module(module_id)
        runtime = self._get_runtime(module_id)
        try:
            module.reload(self._context)
            runtime.loaded = True
            runtime.error = None
            runtime.updated_at = _now_iso()
            get_event_bus().emit('module.reloaded', {'module_id': module_id})
        except Exception as exc:
            runtime.error = str(exc)
            runtime.updated_at = _now_iso()
            raise

    def is_enabled(self, module_id: str) -> bool:
        runtime = self._runtime.get(module_id)
        return bool(runtime and runtime.enabled)

    def enabled_dependents(self, module_id: str) -> List[str]:
        with self._lock:
            return [
                item.manifest.id
                for item in self._modules.values()
                if module_id in item.manifest.depends and self._runtime[item.manifest.id].enabled
            ]

    def get(self, module_id: str) -> Dict[str, Any]:
        module = self._get_module(module_id)
        runtime = self._get_runtime(module_id)
        return {'manifest': module.manifest.to_dict(), 'runtime': runtime.to_dict()}

    def list(self, include_private: bool = False) -> List[Dict[str, Any]]:
        with self._lock:
            modules = list(self._modules.values())
        rows = []
        for module in modules:
            if module.manifest.private and not include_private:
                continue
            rows.append(self.get(module.manifest.id))
        return sorted(rows, key=lambda item: (item['manifest']['category'], item['manifest']['id']))

    def navigation(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        with self._lock:
            modules = list(self._modules.values())
        for module in modules:
            if not self.is_enabled(module.manifest.id):
                continue
            for item in module.manifest.nav:
                entry = dict(item)
                entry.setdefault('module_id', module.manifest.id)
                entry.setdefault('module_name', module.manifest.name)
                items.append(entry)
        return sorted(items, key=lambda item: item.get('order', 1000))

    def _get_module(self, module_id: str) -> ModuleBase:
        with self._lock:
            module = self._modules.get(module_id)
        if not module:
            raise KeyError(f'模块不存在: {module_id}')
        return module

    def _get_runtime(self, module_id: str) -> ModuleRuntime:
        runtime = self._runtime.get(module_id)
        if not runtime:
            raise KeyError(f'模块不存在: {module_id}')
        return runtime

    def _ensure_dependencies_loaded(self, module: ModuleBase):
        for dep in module.manifest.depends:
            if dep not in self._modules:
                raise ValueError(f'缺少依赖模块: {dep}')
            if not self._runtime[dep].loaded:
                self.load(dep)

    def _ensure_dependencies_enabled(self, module: ModuleBase):
        for dep in module.manifest.depends:
            if dep not in self._modules:
                raise ValueError(f'缺少依赖模块: {dep}')
            if not self._runtime[dep].enabled:
                self.enable(dep)


_MODULE_REGISTRY = ModuleRegistry()


def get_module_registry() -> ModuleRegistry:
    return _MODULE_REGISTRY
