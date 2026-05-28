"""模块运行状态持久化。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional


class ModuleStateStore:
    """使用 JSON 文件保存模块启停状态。"""

    def __init__(self, path: Optional[str] = None):
        self.path = Path(path or self.default_path())
        self._lock = RLock()

    @staticmethod
    def default_path() -> str:
        env_path = os.environ.get('WORLDFISH_MODULE_STATE_FILE')
        if env_path:
            return env_path
        return str(Path(__file__).resolve().parents[2] / 'module_state.json')

    def load(self) -> Dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return {'version': 1, 'modules': {}}
            try:
                with self.path.open('r', encoding='utf-8') as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError):
                return {'version': 1, 'modules': {}}

        if not isinstance(data, dict):
            return {'version': 1, 'modules': {}}
        modules = data.get('modules')
        if not isinstance(modules, dict):
            modules = {}
        return {'version': int(data.get('version') or 1), 'modules': modules}

    def save(self, data: Dict[str, Any]):
        normalized = {
            'version': int(data.get('version') or 1),
            'modules': data.get('modules') if isinstance(data.get('modules'), dict) else {},
        }
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(self.path.suffix + '.tmp')
            with temp_path.open('w', encoding='utf-8') as handle:
                json.dump(normalized, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
            temp_path.replace(self.path)

    def get_module_state(self, module_id: str) -> Optional[Dict[str, Any]]:
        data = self.load()
        state = data.get('modules', {}).get(module_id)
        return state if isinstance(state, dict) else None

    def set_module_enabled(self, module_id: str, enabled: bool, updated_at: str):
        data = self.load()
        modules = data.setdefault('modules', {})
        modules[module_id] = {
            **(modules.get(module_id) if isinstance(modules.get(module_id), dict) else {}),
            'enabled': bool(enabled),
            'updated_at': updated_at,
        }
        self.save(data)

    def remove_module_state(self, module_id: str):
        data = self.load()
        data.setdefault('modules', {}).pop(module_id, None)
        self.save(data)

    def clear(self):
        self.save({'version': 1, 'modules': {}})
