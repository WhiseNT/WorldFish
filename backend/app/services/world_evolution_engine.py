"""LLM 驱动的世界观进化推演引擎 — 规划→分阶段推演→整合"""

import threading
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..models.evolution import Evolution, EvolutionRound, EvolutionManager
from ..models.world import WorldSetting

logger = get_logger("worldfish.evolution")


def _world_to_context(world: WorldSetting) -> str:
    """将世界观数据转换为 LLM 上下文文本"""
    parts = []

    parts.append(f"世界观名称: {world.name or '未命名'}")
    parts.append(f"时代背景: {world.era or '未知'}")
    parts.append(f"锚定时间: {world.anchor_time or '未知'}")
    parts.append(f"描述: {world.description or '无'}")

    if world.entities:
        parts.append(f"\n## 核心实体 ({len(world.entities)} 个)")
        for ent in world.entities:
            name = ent.name or "?"
            etype = ent.type or "?"
            attrs = ent.attributes or {}
            bio = attrs.get("简介", "")
            if bio:
                parts.append(f"- [{etype}] {name}: {bio[:200]}")
            else:
                attr_str = "；".join(f"{k}: {v}" for k, v in attrs.items() if v and k != "简介")
                parts.append(f"- [{etype}] {name}" + (f" ({attr_str})" if attr_str else ""))

    if world.events:
        parts.append(f"\n## 关键事件 ({len(world.events)} 个)")
        for evt in world.events:
            date = evt.date or "?"
            name = evt.name or "?"
            desc = evt.description or ""
            parts.append(f"- {date}: {name} — {desc[:150]}")

    settings = world.settings if isinstance(world.settings, dict) else {}
    items = settings.get("items") or []
    if items:
        parts.append(f"\n## 世界观设定 ({len(items)} 个)")
        for item in items:
            if isinstance(item, dict):
                name = item.get("name", "?")
                cat = item.get("category", "?")
                desc = item.get("description") or item.get("detailContent") or ""
                parts.append(f"- [{cat}] {name}: {desc[:120]}")

    calendars = settings.get("calendars") or []
    if calendars:
        parts.append(f"\n## 历法体系 ({len(calendars)} 个)")
        for cal in calendars:
            if isinstance(cal, dict):
                parts.append(f"- {cal.get('name', '?')}: {cal.get('timeRange', '?')} ({cal.get('type', '?')})")

    map_data = settings.get("mapData") or {}
    if isinstance(map_data, dict):
        for key, label in [("regionRelations", "区域关系"), ("countryRelations", "国家关系"), ("importantLocations", "重要地点")]:
            text = map_data.get(key, "")
            if text:
                parts.append(f"\n## {label}\n{text[:500]}")

    return "\n".join(parts)


def _build_cumulative_state(rounds_data: List[Dict], world_entities: set) -> str:
    """从已完成的轮次中构建累计世界状态摘要"""
    if not rounds_data:
        return ""

    parts = ["## 推演累计状态\n"]
    all_affected = {}
    all_events = []
    current_year = "未知"

    for rd in rounds_data:
        if rd.get("year_advanced_to"):
            current_year = rd["year_advanced_to"]
        for ae in rd.get("affected_entities") or []:
            name = ae.get("name", "")
            if name:
                if name not in all_affected:
                    all_affected[name] = []
                all_affected[name].append({
                    "state_changes": ae.get("state_changes", ""),
                    "new_status": ae.get("new_status", ""),
                })
        for evt in rd.get("new_events") or []:
            if evt.get("name"):
                all_events.append(evt)

    parts.append(f"当前时间: {current_year}")

    if all_affected:
        parts.append(f"\n已变化的实体 ({len(all_affected)} 个):")
        for name, changes in all_affected.items():
            latest = changes[-1]
            parts.append(f"- {name}: {latest['new_status'] or latest['state_changes'][:100]}")
            if name not in world_entities:
                parts[-1] += " [新实体]"

    if all_events:
        parts.append(f"\n新发生的事件 ({len(all_events)} 个):")
        for evt in all_events[-10:]:  # 最近 10 个
            parts.append(f"- {evt.get('date', '?')}: {evt.get('name', '?')}")

    return "\n".join(parts)


def _coerce_rounds(value: Any, default: int = 5, minimum: int = 1, maximum: int = 50) -> int:
    try:
        rounds = int(value)
    except (TypeError, ValueError):
        rounds = default
    return max(minimum, min(rounds, maximum))


def _coerce_temperature(value: Any, default: float = 0.7, minimum: float = 0.0, maximum: float = 1.5) -> float:
    try:
        temperature = float(value)
    except (TypeError, ValueError):
        temperature = default
    return max(minimum, min(temperature, maximum))


def _coerce_focus_areas(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _build_parent_rounds_data(accumulated_context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    accumulated_context = accumulated_context or {}
    parent_rounds = accumulated_context.get("parent_rounds") or []
    if parent_rounds:
        return [rd for rd in parent_rounds if isinstance(rd, dict)]

    affected = accumulated_context.get("parent_affected_entities") or []
    events = accumulated_context.get("parent_new_events") or []
    parent_anchor = accumulated_context.get("parent_anchor") or {}
    if not affected and not events:
        return []
    return [{
        "year_advanced_to": parent_anchor.get("year_advanced_to") or parent_anchor.get("time_span_start") or "",
        "affected_entities": [item for item in affected if isinstance(item, dict)],
        "new_events": [item for item in events if isinstance(item, dict)],
    }]


def _extract_time_sort_key(value: Any) -> Optional[Tuple[int, int]]:
    """提取粗略时间排序键。无法确定时返回 None，避免误判。"""
    text = str(value or "").strip()
    if not text or text in {"未知", "当前世界主线"}:
        return None

    year_matches = re.findall(r"(?<!\d)(\d{1,6})(?:\s*年|\b)", text)
    if not year_matches:
        year_matches = re.findall(r"Year\s*(\d{1,6})", text, flags=re.IGNORECASE)
    if not year_matches:
        return None

    year = int(year_matches[-1])
    season_order = {"春": 1, "夏": 2, "秋": 3, "冬": 4}
    season = 0
    for label, order in season_order.items():
        if label in text:
            season = order
            break
    month_match = re.search(r"(\d{1,2})\s*月", text)
    if month_match:
        month = max(1, min(int(month_match.group(1)), 12))
        season = 10 + month
    return year, season


def _is_time_regression(previous: Any, current: Any) -> bool:
    previous_key = _extract_time_sort_key(previous)
    current_key = _extract_time_sort_key(current)
    return bool(previous_key and current_key and current_key < previous_key)


class WorldEvolutionEngine:
    """世界观进化推演引擎 — 规划→分阶段推演→整合"""

    def __init__(self):
        self.llm_client = LLMClient(role="subagent")

    @staticmethod
    def _normalize_match_key(value: Any) -> str:
        return re.sub(r"\s+", "", str(value or "").strip().lower())

    @staticmethod
    def _is_meaningful_time(value: Any) -> bool:
        text = str(value or "").strip()
        return bool(text and text.lower() not in {"unknown", "none", "null"} and text not in {"未知", "未定义", "待定", "暂无", "无"})

    def _extract_time_hint_from_scenario(self, scenario: str) -> str:
        if not scenario:
            return ""

        patterns = [
            r"(?:时间|时间点|起点|基点|锚点)\s*[：:]\s*(?P<value>[^，。；\n]{2,40})",
            r"(?:从|在|自|以)(?P<value>[^，。；\n]{2,40}?)(?:开始|起|之后|以后|为起点|为基点|作为起点|作为基点)",
        ]

        for pattern in patterns:
            match = re.search(pattern, scenario)
            if not match:
                continue
            value = str(match.group("value") or "").strip(" ：:,.，。；;\n")
            if self._is_meaningful_time(value):
                return value

        return ""

    def _event_time_label(self, event: Any) -> str:
        if not event:
            return ""
        date = str(getattr(event, "date", "") or (event.get("date") if isinstance(event, dict) else "") or "").strip()
        estimated = str(getattr(event, "estimated_date", "") or (event.get("estimated_date") if isinstance(event, dict) else "") or "").strip()
        if self._is_meaningful_time(date):
            return date
        if self._is_meaningful_time(estimated):
            return estimated
        return ""

    def _find_matching_event(self, world: WorldSetting, raw_text: str) -> Optional[Any]:
        normalized_text = self._normalize_match_key(raw_text)
        if not normalized_text:
            return None

        best_match = None
        best_length = -1
        for event in world.events or []:
            event_name = str(getattr(event, "name", "") or (event.get("name") if isinstance(event, dict) else "") or "").strip()
            event_key = self._normalize_match_key(event_name)
            if not event_key or len(event_key) < 2:
                continue
            if normalized_text == event_key or normalized_text in event_key or event_key in normalized_text:
                if len(event_key) > best_length:
                    best_match = event
                    best_length = len(event_key)
        return best_match

    def resolve_anchor(
        self,
        world: WorldSetting,
        scenario: str,
        config: Dict[str, Any],
        accumulated_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        config = dict(config or {})
        accumulated_context = dict(accumulated_context or {})

        explicit_event_name = str(config.get("anchor_event") or "").strip()
        explicit_time = str(config.get("time_span_start") or "").strip()
        parent_anchor = accumulated_context.get("parent_anchor") or config.get("parent_anchor") or {}
        parent_time = str(parent_anchor.get("year_advanced_to") or parent_anchor.get("time_span_start") or "").strip()

        def build_time_anchor(source: str, label: str, reason: str = "") -> Dict[str, Any]:
            clean_label = str(label or "").strip()
            return {
                "anchor_type": "time",
                "source": source,
                "label": clean_label or "当前世界主线",
                "start_time": clean_label or "",
                "event_name": "",
                "event_time": "",
                "event_description": "",
                "reason": reason,
            }

        def build_event_anchor(source: str, event: Any, reason: str = "") -> Dict[str, Any]:
            event_name = str(getattr(event, "name", "") or (event.get("name") if isinstance(event, dict) else "") or "").strip()
            event_time = self._event_time_label(event)
            event_description = str(getattr(event, "description", "") or (event.get("description") if isinstance(event, dict) else "") or "").strip()
            label = event_name if not event_time else f"{event_name}（{event_time}）"
            return {
                "anchor_type": "event",
                "source": source,
                "label": label,
                "start_time": event_time,
                "event_name": event_name,
                "event_time": event_time,
                "event_description": event_description,
                "reason": reason,
            }

        if explicit_event_name:
            matched_event = self._find_matching_event(world, explicit_event_name)
            if matched_event is not None:
                return build_event_anchor("config.anchor_event", matched_event, "用户显式指定了起始事件。")
            if self._is_meaningful_time(explicit_event_name):
                return build_time_anchor("config.anchor_event", explicit_event_name, "用户输入了未匹配到事件的锚点文本。")

        if self._is_meaningful_time(explicit_time):
            return build_time_anchor("config.time_span_start", explicit_time, "用户显式指定了起始时间。")

        if self._is_meaningful_time(parent_time):
            return build_time_anchor("parent_round", parent_time, "沿用父推演轮次的结束时间作为新起点。")

        scenario_event = self._find_matching_event(world, scenario)
        if scenario_event is not None:
            return build_event_anchor("scenario.event_match", scenario_event, "根据推演场景中的事件关键词匹配到世界观事件。")

        scenario_time = self._extract_time_hint_from_scenario(scenario)
        if self._is_meaningful_time(scenario_time):
            return build_time_anchor("scenario.time_hint", scenario_time, "根据推演场景中的时间提示解析到起始时间。")

        if self._is_meaningful_time(world.anchor_time):
            return build_time_anchor("world.anchor_time", world.anchor_time, "回退到世界观锚定时间。")

        return build_time_anchor("default", "当前世界主线", "未提供明确时间，使用当前世界主线继续推演。")

    def _build_anchor_instruction(self, anchor_context: Dict[str, Any]) -> str:
        if not anchor_context:
            return ""

        anchor_type = anchor_context.get("anchor_type") or "time"
        label = str(anchor_context.get("label") or anchor_context.get("start_time") or "当前世界主线").strip()
        reason = str(anchor_context.get("reason") or "").strip()
        event_name = str(anchor_context.get("event_name") or "").strip()
        event_time = str(anchor_context.get("event_time") or anchor_context.get("start_time") or "").strip()
        event_description = str(anchor_context.get("event_description") or "").strip()

        if anchor_type == "event" and event_name:
            lines = [
                "## 推演锚点（硬约束）",
                f"- 起始事件: {event_name}",
                f"- 事件时间: {event_time or '未知'}",
            ]
            if event_description:
                lines.append(f"- 事件摘要: {event_description[:180]}")
            lines.append("- 规则: 第一轮必须以该事件已经发生为前提展开，禁止擅自改写为其他时间节点或跳回事件发生前。")
            if reason:
                lines.append(f"- 依据: {reason}")
            return "\n".join(lines)

        lines = [
            "## 推演锚点（硬约束）",
            f"- 起始时间: {label}",
            "- 规则: 第一轮必须从该时间点继续推进，禁止擅自改写为更早或无关的时间节点。",
        ]
        if reason:
            lines.append(f"- 依据: {reason}")
        return "\n".join(lines)

    def _normalize_phase_plan(self, phases: List[Dict[str, Any]], total_rounds: int, anchor_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        remaining_rounds = max(1, int(total_rounds or 1))
        anchor_label = str(anchor_context.get("label") or anchor_context.get("start_time") or "当前世界主线").strip()

        for index, phase in enumerate(phases or []):
            if remaining_rounds <= 0:
                break
            if not isinstance(phase, dict):
                continue

            try:
                phase_rounds = int(phase.get("rounds", 1) or 1)
            except (TypeError, ValueError):
                phase_rounds = 1
            phase_rounds = max(1, min(phase_rounds, remaining_rounds))
            remaining_rounds -= phase_rounds
            phase_time_span = str(phase.get("time_span") or "").strip()
            if not phase_time_span:
                phase_time_span = f"从{anchor_label}开始" if index == 0 else "承接上一阶段继续推进"

            normalized.append({
                "phase_name": str(phase.get("phase_name") or f"第{index + 1}阶段").strip() or f"第{index + 1}阶段",
                "rounds": phase_rounds,
                "time_span": phase_time_span,
                "focus": str(phase.get("focus") or phase.get("plan_summary") or "延续既有世界状态继续发展").strip() or "延续既有世界状态继续发展",
                "key_turning_points": [
                    str(item).strip() for item in (phase.get("key_turning_points") or [])
                    if str(item).strip()
                ],
            })

        if not normalized:
            return [{
                "phase_name": "主线推演",
                "rounds": max(1, int(total_rounds or 1)),
                "time_span": f"从{anchor_label}开始",
                "focus": "延续当前世界主线继续推演",
                "key_turning_points": [],
            }]

        if remaining_rounds > 0:
            normalized[-1]["rounds"] += remaining_rounds

        return normalized

    def evolve_async(self, evolution_id: str, world: WorldSetting, scenario: str, config: Dict[str, Any],
                     accumulated_context: Dict[str, Any] = None):
        """在后台线程中运行进化推演"""
        thread = threading.Thread(
            target=self._evolve_worker,
            args=(evolution_id, world, scenario, config, accumulated_context),
            daemon=True,
        )
        thread.start()

    def _evolve_worker(self, evolution_id: str, world: WorldSetting, scenario: str, config: Dict[str, Any],
                       accumulated_context: Dict[str, Any] = None):
        try:
            config = dict(config or {})
            rounds = _coerce_rounds(config.get("rounds", 5))
            temperature = _coerce_temperature(config.get("temperature", 0.7))
            config["rounds"] = rounds
            config["temperature"] = temperature
            resolved_anchor = config.get("resolved_anchor") or self.resolve_anchor(
                world,
                scenario,
                config,
                accumulated_context=accumulated_context,
            )
            time_span_start = resolved_anchor.get("start_time") or config.get("time_span_start") or world.anchor_time or "未知"
            focus_areas = _coerce_focus_areas(config.get("focus_areas") or [])
            anchor_instruction = self._build_anchor_instruction(resolved_anchor)

            world_context = _world_to_context(world)
            known_entity_names = {e.name for e in (world.entities or []) if e.name}
            parent_rounds_data = _build_parent_rounds_data(accumulated_context)
            for parent_round in parent_rounds_data:
                known_entity_names.update(
                    ae.get("name", "") for ae in (parent_round.get("affected_entities") or [])
                    if isinstance(ae, dict) and ae.get("name")
                )

            accumulated_narrative = []
            if accumulated_context and accumulated_context.get('parent_narratives'):
                accumulated_narrative = list(accumulated_context['parent_narratives'])

            # === 阶段1: 推演规划 ===
            EvolutionManager.update_status(evolution_id, "planning")
            logger.info(f"开始推演规划 (evolution_id={evolution_id})")
            plan = self._plan_evolution(
                world_context,
                scenario,
                rounds,
                time_span_start,
                focus_areas,
                temperature,
                anchor_context=resolved_anchor,
                anchor_instruction=anchor_instruction,
            )
            phases = self._normalize_phase_plan(plan.get("phases") or [], rounds, resolved_anchor)
            logger.info(f"推演规划完成: {len(phases)} 个阶段")

            # === 阶段2: 逐轮执行 ===
            EvolutionManager.update_status(evolution_id, "running")
            round_num = 0
            current_year = time_span_start

            for phase_idx, phase in enumerate(phases):
                phase_name = phase.get("phase_name", f"第{phase_idx + 1}阶段")
                phase_rounds = int(phase.get("rounds", 1))
                phase_focus = phase.get("focus", "")
                phase_time = phase.get("time_span", current_year)
                turning_points = phase.get("key_turning_points") or []

                logger.info(f"阶段 {phase_idx + 1}/{len(phases)}: {phase_name} ({phase_rounds} 轮)")

                for pr in range(phase_rounds):
                    round_num += 1
                    logger.info(f"轮次 {round_num}/{rounds} [{phase_name}] (evolution_id={evolution_id})")

                    # 构建累计状态上下文
                    completed_rounds = parent_rounds_data + self._get_completed_rounds(evolution_id, round_num - 1)
                    cumulative_state = _build_cumulative_state(completed_rounds, known_entity_names)

                    # RAG 检索：查找与当前阶段场景相关的原始资料
                    rag_context = ""
                    try:
                        from .rag_service import RagService
                        rag = RagService(world.id)
                        if rag.count() > 0:
                            search_query = f"{scenario} {phase_focus} {phase_name}"
                            rag_context = rag.search_text(search_query, top_k=3)
                            if rag_context:
                                logger.debug(f"RAG 注入上下文: {len(rag_context)} 字符")
                    except Exception as rag_err:
                        logger.debug(f"RAG 检索跳过: {rag_err}")

                    round_result = self._run_round(
                        world_context=world_context,
                        scenario=scenario,
                        round_number=round_num,
                        total_rounds=rounds,
                        time_span_start=current_year,
                        focus_areas=focus_areas,
                        previous_rounds=accumulated_narrative,
                        temperature=temperature,
                        anchor_instruction=anchor_instruction,
                        rag_context=rag_context,
                        phase_context={
                            "phase_name": phase_name,
                            "phase_focus": phase_focus,
                            "phase_time": phase_time,
                            "turning_points": turning_points,
                            "phase_round": pr + 1,
                            "phase_total_rounds": phase_rounds,
                        },
                        cumulative_state=cumulative_state,
                    )

                    round_result = self._validate_round_result(
                        round_result,
                        known_entity_names,
                        round_num,
                        previous_time=current_year,
                    )

                    known_entity_names.update(
                        ae.get("name", "") for ae in (round_result.get("affected_entities") or [])
                        if ae.get("name")
                    )
                    if round_result.get("year_advanced_to") and not _is_time_regression(current_year, round_result.get("year_advanced_to")):
                        current_year = round_result["year_advanced_to"]

                    evolution_round = EvolutionRound(
                        round_number=round_num,
                        narrative=round_result.get("narrative", ""),
                        year_advanced_to=round_result.get("year_advanced_to", ""),
                        affected_entities=round_result.get("affected_entities") or [],
                        new_events=round_result.get("new_events") or [],
                        warnings=round_result.get("warnings") or [],
                    )
                    EvolutionManager.add_round(evolution_id, evolution_round)
                    accumulated_narrative.append(round_result.get("narrative", ""))

            # === 阶段3: 推演后整合 ===
            EvolutionManager.update_status(evolution_id, "consolidating")
            logger.info(f"开始推演后整合 (evolution_id={evolution_id})")
            try:
                summary = self._consolidate_evolution(world_context, evolution_id, rounds, temperature)
                if summary:
                    # 将整合结果附加到 evolution 的额外数据中
                    evo = EvolutionManager.get(evolution_id)
                    if evo:
                        evo.consolidation = summary
                        EvolutionManager.save(evo)
            except Exception as e:
                logger.warning(f"推演后整合失败（不影响推演结果）: {e}")

            EvolutionManager.update_status(evolution_id, "completed")
            logger.info(f"进化完成: {evolution_id}, {rounds} 轮, {len(phases)} 阶段")

        except Exception as e:
            logger.error(f"进化失败: {evolution_id}: {e}")
            try:
                EvolutionManager.update_status(evolution_id, "failed", error=str(e))
            except Exception:
                pass

    def _get_completed_rounds(self, evolution_id: str, up_to_round: int) -> List[Dict]:
        """获取已完成轮次的数据"""
        try:
            evo = EvolutionManager.get(evolution_id)
            if not evo:
                return []
            result = []
            for rd in evo.rounds:
                if rd.round_number <= up_to_round:
                    result.append({
                        "year_advanced_to": rd.year_advanced_to,
                        "affected_entities": rd.affected_entities,
                        "new_events": rd.new_events,
                    })
            return result
        except Exception:
            return []

    # ==================== 推演规划 ====================

    def _plan_evolution(self, world_context: str, scenario: str, total_rounds: int,
                        time_start: str, focus_areas: List[str], temperature: float,
                        anchor_context: Optional[Dict[str, Any]] = None,
                        anchor_instruction: str = "") -> Dict[str, Any]:
        """LLM 分析世界观和场景，生成结构化的推演阶段计划"""
        focus_str = ", ".join(focus_areas) if focus_areas else "全面推演"

        prompt = """你是世界观推演规划专家。请分析当前世界观状态和用户推演需求，将 %d 轮推演拆分为合理的阶段。

## 当前世界观
%s

## 推演需求
%s

%s

## 参数
- 总轮数: %d
- 起始时间: %s
- 关注领域: %s

请将推演拆分为 2-5 个阶段，每个阶段有明确的时间跨度和焦点。

返回 JSON：
{
  "plan_summary": "整体推演计划的一句话概述",
  "phases": [
    {
      "phase_name": "阶段名称（如：动荡纪元、黄金时代、大分裂时期）",
      "rounds": 3,
      "time_span": "该阶段覆盖的时间范围（如：第三纪元 1200-1350 年）",
      "focus": "该阶段的推演焦点（50-100字）",
      "key_turning_points": ["该阶段预期发生的关键转折（可为空数组，LLM将在推演中自然生成）"]
    }
  ]
}

要求：
- 阶段数根据总轮数合理分配：%d 轮建议 2-5 个阶段
- 每个阶段至少 1 轮
- 阶段之间要有逻辑递进关系
- time_span 必须严格承接起始时间 %s，不得擅自改写成其他历史时期或随机时间节点
- 如果锚点是某个事件，则第一阶段必须以该事件已经发生为前提""" % (
        total_rounds,
        world_context[:3000],
        scenario[:1000],
        anchor_instruction,
        total_rounds,
        time_start,
        focus_str,
        total_rounds,
        time_start,
    )

        try:
            result = self.llm_client.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=min(temperature, 0.5),
                max_tokens=4096,
            )
            if isinstance(result, dict) and result.get("phases"):
                # 校验各阶段轮数加起来不超过总轮数
                planned = sum(int(p.get("rounds", 1)) for p in result["phases"])
                if planned != total_rounds:
                    logger.info(f"规划轮数 {planned} != 总轮数 {total_rounds}，将按比例调整")
                return result
        except Exception as e:
            logger.warning(f"推演规划失败，使用默认单阶段: {e}")

        return {"phases": []}

    # ==================== 逐轮执行 ====================

    def _run_round(
        self,
        world_context: str,
        scenario: str,
        round_number: int,
        total_rounds: int,
        time_span_start: str,
        focus_areas: List[str],
        previous_rounds: List[str],
        temperature: float,
        anchor_instruction: str = "",
        phase_context: Dict[str, Any] = None,
        cumulative_state: str = "",
        rag_context: str = "",
    ) -> Dict[str, Any]:
        focus_text = ""
        if focus_areas:
            focus_text = "重点关注的领域: %s。请在推演中着重展开这些方面的变化。" % ", ".join(focus_areas)

        # 阶段上下文
        phase_text = ""
        if phase_context:
            phase_text = """
## 当前阶段信息
- 阶段名称: %s
- 阶段焦点: %s
- 阶段时间范围: %s
- 阶段内轮次: 第 %d/%d 轮""" % (
                phase_context.get("phase_name", ""),
                phase_context.get("phase_focus", ""),
                phase_context.get("phase_time", ""),
                phase_context.get("phase_round", 1),
                phase_context.get("phase_total_rounds", 1),
            )
            turning_points = phase_context.get("turning_points") or []
            if turning_points:
                phase_text += "\n- 预期关键转折: %s" % "; ".join(turning_points)

        # 之前的叙事
        previous_text = ""
        if previous_rounds:
            recent = previous_rounds[-3:] if len(previous_rounds) > 3 else previous_rounds
            previous_text = "## 之前的推演进程\n" + "\n---\n".join(
                "第%d轮: %s" % (i + 1, n[:400]) for i, n in enumerate(recent)
            )

        # RAG 上下文
        rag_text = ""
        if rag_context and rag_context.strip():
            rag_text = "\n## 知识库相关资料（从原始文本中检索，仅供参考）\n%s\n" % rag_context.strip()

        prompt = """你是一个客观的世界观推演引擎。基于给定的世界观设定，以客观第三方视角陈述世界演化的进程。

## 当前世界观状态
%s

## 用户的推演需求/场景
%s

%s
%s
%s
%s
%s
%s

## 当前推演进度
这是第 %d 轮，共 %d 轮。当前时间为 %s。

请基于当前世界观状态和之前的推演进程，以客观的第三方视角陈述这一轮的世界演化。

请严格以 JSON 格式返回：
{
    "narrative": "本轮的叙事文本（300-800字），客观第三方视角，类似历史记载或百科全书。要详尽——描述这段时间内发生的重大事件、各方势力的互动、关键人物的作为与变化。",
    "year_advanced_to": "本轮结束时的时间点",
    "affected_entities": [
        {
            "name": "受影响的实体名称",
            "state_changes": "具体变化描述（实力、性格、地位、关系等变化）",
            "new_status": "变化后的状态"
        }
    ],
    "new_events": [
        {
            "name": "新事件名称",
            "date": "事件发生时间",
            "description": "事件描述（起因+经过+结果）",
            "involved_entities": ["涉及的实体名"]
        }
    ]
}

注意事项：
- narrative 必须使用客观第三方视角，平实陈述
- 叙事要详尽（300-800字），不要过于简短
- 叙事要有逻辑连贯性，承接前文和累计状态
- 严格遵守给定的时间/事件锚点，不得另选历史时期作为基点
- 变化要基于世界观设定的内在逻辑
- 可以在合理范围内引入新的次要角色或组织
- affected_entities 必须描述具体的变化内容
- 如果是最后一轮，叙事应有一个合理的阶段性收尾
- new_events 要详尽列出本轮发生的所有重要事件（至少3-5个）""" % (
            world_context[:4000],
            scenario[:800],
            rag_text,
            focus_text,
            phase_text,
            cumulative_state[:2000] if cumulative_state else "",
            previous_text,
            anchor_instruction,
            round_number, total_rounds, time_span_start,
        )

        last_error = None
        for attempt in range(3):
            try:
                result = self.llm_client.chat_json(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=max(0.0, temperature - (attempt * 0.1)),
                    max_tokens=8192,
                )
                if not isinstance(result, dict):
                    raise ValueError("LLM 返回格式无效: %s" % type(result))
                return result
            except Exception as e:
                last_error = e
                logger.warning("轮次%d 第%d次尝试失败: %s" % (round_number, attempt + 1, str(e)[:100]))
                if attempt < 2:
                    import time
                    time.sleep(2 * (attempt + 1))

        raise ValueError("轮次%d LLM调用3次均失败: %s" % (round_number, last_error))

    # ==================== 推演后整合 ====================

    def _consolidate_evolution(self, world_context: str, evolution_id: str,
                               total_rounds: int, temperature: float) -> Dict[str, Any]:
        """推演后 LLM 整合：一致性校验、因果链识别、最终总结"""
        evo = EvolutionManager.get(evolution_id)
        if not evo or not evo.rounds:
            return {}

        rounds_summary = []
        for rd in evo.rounds:
            rounds_summary.append({
                "round": rd.round_number,
                "year": rd.year_advanced_to,
                "narrative": rd.narrative[:300],
                "affected_entities": [ae.get("name") for ae in (rd.affected_entities or [])],
                "new_events": [{"name": e.get("name"), "date": e.get("date")}
                              for e in (rd.new_events or [])],
            })

        prompt = """你是世界观推演整合专家。请对以下 %d 轮推演结果进行整合分析。

## 世界观背景
%s

## 推演结果
%s

请完成以下分析并返回 JSON：
{
  "summary": "整个推演的最终总结（300-500字），以客观视角叙述这一段历史的全貌",
  "causal_chains": [
    {"chain": "事件因果链描述（如：A导致B，B引发C和D）", "involved_events": ["事件名1", "事件名2"]}
  ],
  "final_entity_states": [
    {"name": "实体名", "final_status": "推演结束时的最终状态"}
  ],
  "key_themes": ["推演中突出的主题1", "主题2"],
  "inconsistencies": ["发现的不一致之处（如时间线矛盾），没有则填空数组"],
  "timeline": [
    {"time": "时间点", "event": "事件描述"}
  ]
}""" % (total_rounds, world_context[:2000], json.dumps(rounds_summary, ensure_ascii=False, indent=2)[:6000])

        try:
            result = self.llm_client.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=min(temperature, 0.4),
                max_tokens=8192,
            )
            if isinstance(result, dict):
                logger.info("推演整合完成: 发现 %d 条因果链, %d 个最终实体状态" % (
                    len(result.get("causal_chains", [])),
                    len(result.get("final_entity_states", [])),
                ))
                return result
        except Exception as e:
            logger.warning("推演整合 LLM 调用失败: %s" % e)

        return {}

    # ==================== 事实校验 ====================

    def _validate_round_result(
        self,
        result: Dict[str, Any],
        known_entities: set,
        round_num: int,
        previous_time: Any = None,
    ) -> Dict[str, Any]:
        """事实一致性校验。保持返回 dict，警告写入 result['warnings']。"""
        if not isinstance(result, dict):
            result = {}

        warnings = [str(item).strip() for item in (result.get("warnings") or []) if str(item).strip()]

        year_advanced_to = str(result.get("year_advanced_to", "") or "").strip()
        if not year_advanced_to:
            logger.warning("轮次%d: year_advanced_to 为空" % round_num)
            warnings.append("year_advanced_to 为空，已标记为未知")
            result["year_advanced_to"] = "未知"
        elif previous_time is not None and _is_time_regression(previous_time, year_advanced_to):
            warnings.append(f"本轮结束时间可能早于上一轮时间：{year_advanced_to} < {previous_time}")
            logger.warning("轮次%d: 检测到时间倒退: %s < %s" % (round_num, year_advanced_to, previous_time))

        affected = result.get("affected_entities") or []
        if not isinstance(affected, list):
            warnings.append("affected_entities 不是列表，已丢弃")
            affected = []
        validated_affected = []
        for ae in affected:
            if not isinstance(ae, dict):
                warnings.append("存在非对象实体变化，已丢弃")
                continue
            name = str(ae.get("name", "")).strip()
            if not name:
                warnings.append("存在缺少 name 的实体变化，已丢弃")
                continue
            if name not in known_entities:
                logger.info("轮次%d: 接受推演中新引入的实体'%s'" % (round_num, name))
                ae.setdefault("is_new_entity", True)
            else:
                ae.setdefault("is_new_entity", False)
            ae.setdefault("state_changes", "")
            ae.setdefault("new_status", "")
            if not str(ae.get("state_changes") or ae.get("new_status") or "").strip():
                warnings.append(f"实体 {name} 缺少具体状态变化")
            validated_affected.append(ae)
        result["affected_entities"] = validated_affected

        events = result.get("new_events") or []
        if not isinstance(events, list):
            warnings.append("new_events 不是列表，已丢弃")
            events = []
        validated_events = []
        for evt in events:
            if not isinstance(evt, dict):
                warnings.append("存在非对象事件，已丢弃")
                continue
            name = str(evt.get("name", "")).strip()
            if not name:
                warnings.append("存在缺少 name 的事件，已丢弃")
                continue
            evt.setdefault("date", "")
            evt.setdefault("description", "")
            if not str(evt.get("date") or "").strip():
                warnings.append(f"事件 {name} 缺少发生时间")
            if not isinstance(evt.get("involved_entities"), list):
                warnings.append(f"事件 {name} 的 involved_entities 不是列表，已修正为空列表")
                evt["involved_entities"] = []
            validated_events.append(evt)
        result["new_events"] = validated_events
        if len(validated_events) < 3:
            warnings.append(f"本轮重要事件数量少于建议值：{len(validated_events)} < 3")

        narrative = str(result.get("narrative", "") or "").strip()
        if not narrative:
            warnings.append("narrative 为空，已填充占位文本")
            result["narrative"] = "第%d轮推演未产生有效叙事。" % round_num
        elif len(narrative) < 120:
            warnings.append(f"narrative 可能过短：{len(narrative)} 字符")

        result["warnings"] = list(dict.fromkeys(warnings))
        return result
