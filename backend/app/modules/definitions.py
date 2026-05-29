"""模块定义与 Flask 蓝图绑定。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from flask import Blueprint

from app.core.modules import ModuleManifest


@dataclass
class BlueprintBinding:
    """一个模块对 Flask 蓝图的绑定声明。"""

    blueprint: Blueprint
    url_prefix: str
    guard: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'blueprint': self.blueprint.name,
            'url_prefix': self.url_prefix,
            'guard': self.guard,
        }


@dataclass
class BackendModuleDefinition:
    """后端模块定义。"""

    manifest: ModuleManifest
    blueprints: List[BlueprintBinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'manifest': self.manifest.to_dict(),
            'blueprints': [binding.to_dict() for binding in self.blueprints],
        }
