"""
时间线管理服务
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from app.utils.logger import get_logger

logger = get_logger('mirofish.service.timeline_manager')


class TimelineManager:
    """时间线管理器"""
    
    def __init__(self):
        pass
    
    def create_timeline(self, world_id, events):
        """创建时间线"""
        try:
            # 按时间排序事件
            sorted_events = sorted(events, key=lambda x: x.get('date', ''))
            
            timeline = {
                "world_id": world_id,
                "events": sorted_events,
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"为世界观 {world_id} 创建时间线，包含 {len(sorted_events)} 个事件")
            return timeline
            
        except Exception as e:
            logger.error(f"创建时间线失败: {str(e)}")
            return {
                "world_id": world_id,
                "events": [],
                "created_at": datetime.now().isoformat()
            }
    
    def get_timeline_range(self, timeline, start_date, end_date):
        """获取时间线指定范围的事件"""
        try:
            filtered_events = [
                event for event in timeline.get('events', [])
                if start_date <= event.get('date', '') <= end_date
            ]
            
            return {
                "world_id": timeline.get('world_id'),
                "events": filtered_events,
                "start_date": start_date,
                "end_date": end_date
            }
            
        except Exception as e:
            logger.error(f"获取时间线范围失败: {str(e)}")
            return {
                "world_id": timeline.get('world_id'),
                "events": [],
                "start_date": start_date,
                "end_date": end_date
            }
    
    def add_event_to_timeline(self, timeline, event):
        """向时间线添加事件"""
        try:
            events = timeline.get('events', [])
            events.append(event)
            # 重新排序
            sorted_events = sorted(events, key=lambda x: x.get('date', ''))
            
            timeline['events'] = sorted_events
            timeline['updated_at'] = datetime.now().isoformat()
            
            logger.info(f"向时间线添加事件: {event.get('name')}")
            return timeline
            
        except Exception as e:
            logger.error(f"添加事件失败: {str(e)}")
            return timeline

    def _ensure_calendar_list(self, world):
        """确保 world.settings.calendars 是可写列表。"""
        if not world:
            return []
        if not isinstance(getattr(world, "settings", None), dict):
            world.settings = {}

        calendars = world.settings.get("calendars")
        if not isinstance(calendars, list):
            calendars = []
            world.settings["calendars"] = calendars
        return calendars

    def _normalize_calendar(self, calendar: Dict[str, Any], fallback_index: int = 0) -> Dict[str, Any]:
        """标准化历法字段，兼容前端和 agent 写入格式。"""
        payload = dict(calendar) if isinstance(calendar, dict) else {}
        normalized = dict(payload)

        calendar_id = str(
            payload.get("id")
            or payload.get("calendar_id")
            or ""
        ).strip()
        if not calendar_id or calendar_id == "0":
            calendar_id = f"calendar_{uuid.uuid4().hex[:12]}"

        name = str(payload.get("name") or "").strip() or "未命名历法"
        calendar_type = str(payload.get("type") or payload.get("timeline_type") or "纪元").strip() or "纪元"
        base_time = str(
            payload.get("baseTime")
            or payload.get("base_time")
            or payload.get("startYear")
            or ""
        ).strip()
        time_range = str(payload.get("timeRange") or payload.get("time_range") or "").strip()
        end_time = str(payload.get("endYear") or payload.get("end_time") or "").strip()
        if not time_range and base_time:
            if end_time:
                time_range = f"{base_time} ~ {end_time}"
            elif payload.get("noEndTime") or payload.get("no_end_time"):
                time_range = f"{base_time} ~ 无"

        unit = str(payload.get("unit") or "年").strip() or "年"
        ratio = str(payload.get("ratio") or payload.get("ratioValue") or "×1").strip()
        if not ratio:
            ratio = "×1"
        elif not ratio.startswith("×"):
            ratio = f"×{ratio}"

        calendar_kind = str(
            payload.get("calendarType")
            or payload.get("calendar_type")
            or payload.get("calendar_system")
            or "未开启"
        ).strip() or "未开启"
        description = str(payload.get("description") or "").strip()

        normalized.update({
            "id": calendar_id,
            "name": name,
            "type": calendar_type,
            "baseTime": base_time,
            "timeRange": time_range,
            "unit": unit,
            "ratio": ratio,
            "calendarType": calendar_kind,
            "description": description,
        })

        return normalized

    def list_calendars(self, world, calendar_type: str = "", keyword: str = "", limit: int = 50):
        """列出世界观中的历法/时间线条目。"""
        calendars = [
            self._normalize_calendar(calendar, index)
            for index, calendar in enumerate(self._ensure_calendar_list(world))
            if isinstance(calendar, dict)
        ]

        keyword_text = str(keyword or "").strip().lower()
        if calendar_type:
            normalized_type = str(calendar_type).strip()
            calendars = [
                calendar for calendar in calendars
                if str(calendar.get("type", "")).strip() == normalized_type
                or str(calendar.get("calendarType", "")).strip() == normalized_type
            ]

        if keyword_text:
            calendars = [
                calendar for calendar in calendars
                if keyword_text in str(calendar.get("name", "")).lower()
                or keyword_text in str(calendar.get("timeRange", "")).lower()
                or keyword_text in str(calendar.get("baseTime", "")).lower()
                or keyword_text in str(calendar.get("description", "")).lower()
            ]

        try:
            limit_value = min(max(1, int(limit or 50)), 100)
        except (TypeError, ValueError):
            limit_value = 50

        return calendars[:limit_value]

    def find_calendar_matches(self, world, calendar_id: str = "", calendar_name: str = ""):
        """按 ID 或名称定位历法，返回匹配项列表。"""
        calendars = self._ensure_calendar_list(world)
        normalized_id = str(calendar_id or "").strip()
        normalized_name = str(calendar_name or "").strip()

        matches = []
        if normalized_id:
            for index, calendar in enumerate(calendars):
                if isinstance(calendar, dict) and str(calendar.get("id") or "").strip() == normalized_id:
                    matches.append((index, calendar))
            if matches:
                return matches

        if normalized_name:
            for index, calendar in enumerate(calendars):
                if isinstance(calendar, dict) and str(calendar.get("name") or "").strip() == normalized_name:
                    matches.append((index, calendar))

        return matches

    def create_calendar(self, world, calendar_data: Dict[str, Any]):
        """创建历法条目。"""
        calendars = self._ensure_calendar_list(world)
        normalized = self._normalize_calendar(calendar_data, len(calendars))
        calendars.append(normalized)
        if hasattr(world, "updated_at"):
            world.updated_at = datetime.now().isoformat()
        return normalized

    def update_calendar(self, world, calendar_id: str = "", calendar_name: str = "", updates: Dict[str, Any] = None):
        """更新指定历法。"""
        updates = updates or {}
        calendars = self._ensure_calendar_list(world)
        matches = self.find_calendar_matches(world, calendar_id=calendar_id, calendar_name=calendar_name)

        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError("匹配到多个同名历法，请使用 calendar_id 精确指定。")

        index, existing = matches[0]
        merged = dict(existing)
        merged.update(updates)
        for canonical_key, aliases in {
            "name": ("name",),
            "type": ("type", "timeline_type"),
            "baseTime": ("baseTime", "base_time", "startYear"),
            "timeRange": ("timeRange", "time_range"),
            "endYear": ("endYear", "end_time"),
            "unit": ("unit",),
            "ratio": ("ratio", "ratioValue"),
            "calendarType": ("calendarType", "calendar_type", "calendar_system"),
            "description": ("description",),
            "noEndTime": ("noEndTime", "no_end_time"),
        }.items():
            for alias in aliases:
                if alias in updates and updates.get(alias) is not None:
                    merged[canonical_key] = updates.get(alias)
                    break
        normalized = self._normalize_calendar(merged, index)
        calendars[index] = normalized

        if hasattr(world, "updated_at"):
            world.updated_at = datetime.now().isoformat()
        return normalized

    def delete_calendar(self, world, calendar_id: str = "", calendar_name: str = ""):
        """删除指定历法。"""
        calendars = self._ensure_calendar_list(world)
        matches = self.find_calendar_matches(world, calendar_id=calendar_id, calendar_name=calendar_name)

        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError("匹配到多个同名历法，请使用 calendar_id 精确指定。")

        index, removed = matches[0]
        calendars.pop(index)

        if hasattr(world, "updated_at"):
            world.updated_at = datetime.now().isoformat()
        return removed
