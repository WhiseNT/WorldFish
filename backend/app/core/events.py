"""轻量事件总线。"""

from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Any, Callable, Dict, List, Optional

EventHandler = Callable[[Dict[str, Any]], None]


class EventBus:
    """进程内事件总线，用于模块之间低耦合通信。"""

    def __init__(self):
        self._lock = RLock()
        self._listeners: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler, module_id: Optional[str] = None):
        if not event_name or not callable(handler):
            raise ValueError('事件名和处理器不能为空')
        item = {'handler': handler, 'module_id': module_id}
        with self._lock:
            self._listeners[event_name].append(item)
        return lambda: self.unsubscribe(event_name, handler)

    def unsubscribe(self, event_name: str, handler: EventHandler):
        with self._lock:
            listeners = self._listeners.get(event_name, [])
            self._listeners[event_name] = [item for item in listeners if item['handler'] is not handler]

    def unsubscribe_module(self, module_id: str):
        with self._lock:
            for event_name, listeners in list(self._listeners.items()):
                self._listeners[event_name] = [item for item in listeners if item.get('module_id') != module_id]

    def emit(self, event_name: str, payload: Optional[Dict[str, Any]] = None):
        data = payload or {}
        with self._lock:
            targets = list(self._listeners.get(event_name, []))
            wildcard = list(self._listeners.get('*', []))
        for item in targets + wildcard:
            item['handler']({'name': event_name, 'payload': data})

    def snapshot(self):
        with self._lock:
            return {
                name: [item.get('module_id') for item in listeners]
                for name, listeners in self._listeners.items()
            }


_EVENT_BUS = EventBus()


def get_event_bus() -> EventBus:
    return _EVENT_BUS
