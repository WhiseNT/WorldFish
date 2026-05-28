"""世界观进化推演 API"""

import re
from typing import Any, Dict, List

from flask import Blueprint, request, jsonify

from ..config import Config
from ..models.world import WorldManager
from ..models.evolution import Evolution, EvolutionManager
from ..services.world_evolution_engine import WorldEvolutionEngine, _coerce_focus_areas, _coerce_rounds, _coerce_temperature
from ..utils.logger import get_logger

evolution_bp = Blueprint('evolution', __name__)
logger = get_logger('worldfish.api.evolution')


ENTITY_TYPE_TO_SETTING_CATEGORY = {
    '人物': 'character', '角色': 'character', 'person': 'character', 'character': 'character',
    '种族': 'character', '生物': 'character',
    '国家': 'organization', '政权': 'organization', '组织': 'organization', '势力': 'organization',
    'nation': 'organization', 'organization': 'organization', 'faction': 'organization',
    '团体': 'organization', '教会': 'organization', '公司': 'organization', '公会': 'organization',
    '地点': 'geography', '位置': 'geography', '城市': 'geography', 'location': 'geography',
    '地理': 'geography', '区域': 'geography',
    '物品': 'item', '道具': 'item', '装备': 'item', '武器': 'item', 'item': 'item',
    '能力': 'ability', '魔法': 'ability', '技能': 'ability', '体系': 'ability', 'ability': 'ability',
}


def _resolve_setting_category(entity_type: str) -> str:
    normalized_type = str(entity_type or '').strip()
    return ENTITY_TYPE_TO_SETTING_CATEGORY.get(normalized_type, 'other')


def _ensure_settings_items(world) -> List[Dict[str, Any]]:
    if not isinstance(world.settings, dict):
        world.settings = {'items': [], 'mapData': {}, 'calendars': []}
    items = world.settings.setdefault('items', [])
    if not isinstance(items, list):
        world.settings['items'] = []
        items = world.settings['items']
    return items


def _build_stage_payload(evolution_id: str, round_number: int, year_advanced_to: str, entity_change: Dict[str, Any]) -> Dict[str, Any]:
    new_status = str(entity_change.get('new_status', '') or '').strip()
    state_changes = str(entity_change.get('state_changes', '') or '').strip()
    stage_name = str(entity_change.get('stage_name', '') or '').strip()

    if not stage_name:
        if year_advanced_to and new_status:
            stage_name = f'{year_advanced_to} · {new_status}'
        elif year_advanced_to:
            stage_name = year_advanced_to
        elif new_status:
            stage_name = new_status
        else:
            stage_name = f'推演第{round_number}轮'

    return {
        'id': f'stage_{evolution_id}_{round_number}_{abs(hash(entity_change.get("name", ""))) % 100000}',
        'name': stage_name,
        'era': year_advanced_to,
        'description': state_changes or new_status,
        'attributes': {
            '状态': new_status,
            '状态变化': state_changes,
        },
        'source': {
            'type': 'evolution',
            'evolution_id': evolution_id,
            'round': round_number,
        },
    }


def _upsert_stage(entity, stage_payload: Dict[str, Any]) -> None:
    if not isinstance(entity.stages, list):
        entity.stages = []

    source = stage_payload.get('source') or {}
    for index, existing in enumerate(entity.stages):
        existing_source = existing.get('source') if isinstance(existing, dict) else None
        if not isinstance(existing_source, dict):
            continue
        if existing_source.get('evolution_id') == source.get('evolution_id') and existing_source.get('round') == source.get('round'):
            merged_attributes = dict(existing.get('attributes') or {})
            merged_attributes.update(stage_payload.get('attributes') or {})
            entity.stages[index] = {
                **existing,
                **stage_payload,
                'attributes': merged_attributes,
            }
            return

    entity.stages.append(stage_payload)


def _upsert_entity_setting(world, entity, stage_payload: Dict[str, Any]) -> bool:
    items = _ensure_settings_items(world)
    entity_id = getattr(entity, 'id', '')
    setting_item = None

    for item in items:
        if not isinstance(item, dict):
            continue
        if entity.setting_item_id and item.get('id') == entity.setting_item_id:
            setting_item = item
            break
        if item.get('linkedEntityId') == entity_id:
            setting_item = item
            break
        if item.get('name') == entity.name:
            setting_item = item
            break

    stage_label = stage_payload.get('name') or stage_payload.get('era') or '最新阶段'
    stage_summary = stage_payload.get('description') or stage_payload.get('attributes', {}).get('状态') or ''
    detail_line = f'[{stage_label}] {stage_summary}'.strip()

    if setting_item is None:
        setting_item = {
            'id': f'setting_{entity_id or entity.name}',
            'name': entity.name,
            'settingType': 'setting',
            'category': _resolve_setting_category(getattr(entity, 'type', '')),
            'description': stage_summary or getattr(entity, 'type', '') or '实体设定',
            'detailContent': detail_line,
            'aliases': [],
            'linkedEntityId': entity_id,
        }
        items.append(setting_item)
        entity.setting_item_id = setting_item['id']
        return True

    existing_detail = str(setting_item.get('detailContent', '') or '').strip()
    if detail_line and detail_line not in existing_detail:
        setting_item['detailContent'] = f'{existing_detail}\n{detail_line}'.strip() if existing_detail else detail_line

    setting_item['description'] = stage_summary or setting_item.get('description') or getattr(entity, 'type', '') or '实体设定'
    setting_item['linkedEntityId'] = entity_id
    if not entity.setting_item_id:
        entity.setting_item_id = str(setting_item.get('id') or '')
    return False


def _normalize_entity_key(value: Any) -> str:
    return re.sub(r"[\s\-—_·•・()（）\[\]{}《》<>“”\"'`]+", "", str(value or '').strip().lower())


def _names_match(left: Any, right: Any) -> bool:
    left_key = _normalize_entity_key(left)
    right_key = _normalize_entity_key(right)
    if not left_key or not right_key:
        return False
    if left_key == right_key:
        return True
    if min(len(left_key), len(right_key)) < 3:
        return False
    return left_key in right_key or right_key in left_key


def _find_world_entity(world, entity_name: str):
    exact_match = None
    fuzzy_match = None
    for entity in world.entities or []:
        candidate_names = [entity.name] + list(getattr(entity, 'aliases', []) or [])
        for candidate in candidate_names:
            if _normalize_entity_key(candidate) == _normalize_entity_key(entity_name):
                exact_match = entity
                break
            if fuzzy_match is None and _names_match(candidate, entity_name):
                fuzzy_match = entity
        if exact_match is not None:
            break
    return exact_match or fuzzy_match


def _find_consolidated_state(evolution: Evolution, entity_name: str) -> Dict[str, Any]:
    consolidation = getattr(evolution, 'consolidation', None) or {}
    final_states = consolidation.get('final_entity_states') or []
    for item in final_states:
        if isinstance(item, dict) and _names_match(item.get('name'), entity_name):
            return item
    return {}


def _find_latest_entity_change(evolution: Evolution, entity_name: str) -> Dict[str, Any]:
    for round_data in sorted(evolution.rounds or [], key=lambda item: getattr(item, 'round_number', 0), reverse=True):
        if getattr(round_data, 'round_number', 0) <= 0:
            continue
        for entity_change in round_data.affected_entities or []:
            if isinstance(entity_change, dict) and _names_match(entity_change.get('name'), entity_name):
                return {
                    'round_number': round_data.round_number,
                    'year_advanced_to': round_data.year_advanced_to,
                    'name': entity_change.get('name') or entity_name,
                    'new_status': str(entity_change.get('new_status') or '').strip(),
                    'state_changes': str(entity_change.get('state_changes') or '').strip(),
                }
    return {}


def _collect_related_world_events(world, entity_name: str, limit: int = 6) -> List[str]:
    lines: List[str] = []
    for event in world.events or []:
        event_entities = getattr(event, 'entities', []) or []
        if any(_names_match(name, entity_name) for name in event_entities):
            time_label = getattr(event, 'date', '') or getattr(event, 'estimated_date', '') or '?'
            lines.append(f"- [世界观] {time_label}: {event.name} — {(event.description or '')[:140]}")
        if len(lines) >= limit:
            break
    return lines


def _collect_related_evolution_events(evolution: Evolution, entity_name: str, limit: int = 8) -> List[str]:
    lines: List[str] = []
    for round_data in sorted(evolution.rounds or [], key=lambda item: getattr(item, 'round_number', 0)):
        if getattr(round_data, 'round_number', 0) <= 0:
            continue
        round_time = getattr(round_data, 'year_advanced_to', '') or '?'
        for event in round_data.new_events or []:
            if not isinstance(event, dict):
                continue
            involved_entities = event.get('involved_entities') or event.get('entities') or []
            description = str(event.get('description') or '').strip()
            if any(_names_match(name, entity_name) for name in involved_entities) or _names_match(description, entity_name):
                event_time = str(event.get('date') or round_time or '?').strip() or '?'
                lines.append(f"- [推演第{round_data.round_number}轮] {event_time}: {event.get('name', '未命名事件')} — {description[:160]}")
            if len(lines) >= limit:
                return lines
    return lines


def _infer_current_time(evolution: Evolution) -> str:
    for round_data in sorted(evolution.rounds or [], key=lambda item: getattr(item, 'round_number', 0), reverse=True):
        if getattr(round_data, 'round_number', 0) > 0 and str(getattr(round_data, 'year_advanced_to', '') or '').strip():
            return str(round_data.year_advanced_to).strip()

    consolidation = getattr(evolution, 'consolidation', None) or {}
    timeline = consolidation.get('timeline') or []
    for item in reversed(timeline):
        time_text = str((item or {}).get('time') or '').strip()
        if time_text:
            return time_text

    config = getattr(evolution, 'config', None) or {}
    resolved_anchor = config.get('resolved_anchor') or {}
    return str(resolved_anchor.get('start_time') or config.get('time_span_start') or '').strip()


def _build_current_entity_brief(world, evolution: Evolution, requested_name: str) -> Dict[str, Any]:
    base_entity = _find_world_entity(world, requested_name)
    consolidated_state = _find_consolidated_state(evolution, requested_name) if evolution else {}
    latest_change = _find_latest_entity_change(evolution, requested_name) if evolution else {}

    canonical_name = (
        str(consolidated_state.get('name') or '').strip()
        or str(latest_change.get('name') or '').strip()
        or str(getattr(base_entity, 'name', '') or '').strip()
        or str(requested_name or '').strip()
    )

    current_time = _infer_current_time(evolution) if evolution else ''
    current_status = (
        str(consolidated_state.get('final_status') or '').strip()
        or str(latest_change.get('new_status') or '').strip()
        or str(latest_change.get('state_changes') or '').strip()
        or str((getattr(base_entity, 'attributes', {}) or {}).get('当前状态') or '').strip()
    )

    base_attrs = dict(getattr(base_entity, 'attributes', {}) or {}) if base_entity else {}
    base_intro = str(base_attrs.get('简介') or '').strip()

    relationship_lines: List[str] = []
    if base_entity:
        for relationship in (getattr(base_entity, 'relationships', None) or [])[:6]:
            if not isinstance(relationship, dict):
                continue
            target = str(relationship.get('target') or '').strip()
            relation_type = str(relationship.get('type') or '关联').strip() or '关联'
            description = str(relationship.get('description') or '').strip()
            if target:
                summary = f"- {target}（{relation_type}）"
                if description:
                    summary += f": {description}"
                relationship_lines.append(summary)

    evolution_lines: List[str] = []
    if latest_change:
        round_label = f"第{latest_change.get('round_number')}轮" if latest_change.get('round_number') else '最近一轮'
        round_time = str(latest_change.get('year_advanced_to') or '').strip()
        headline = f"- {round_label}"
        if round_time:
            headline += f"（{round_time}）"
        status_text = str(latest_change.get('new_status') or latest_change.get('state_changes') or '').strip()
        if status_text:
            headline += f": {status_text}"
        evolution_lines.append(headline)

    if consolidated_state:
        final_status = str(consolidated_state.get('final_status') or '').strip()
        if final_status and final_status not in evolution_lines:
            evolution_lines.append(f"- 推演结局: {final_status}")

    related_events = []
    if evolution:
        related_events.extend(_collect_related_evolution_events(evolution, canonical_name))
    related_events.extend(line for line in _collect_related_world_events(world, canonical_name) if line not in related_events)

    if not base_entity and not consolidated_state and not latest_change and not related_events:
        return {}

    lines = [f"姓名: {canonical_name}"]
    if base_entity and getattr(base_entity, 'type', ''):
        lines.append(f"类型: {base_entity.type}")
    if current_time or current_status:
        lines.append("当前角色锚点（最高优先级）:")
        if current_time:
            lines.append(f"- 当前时间: {current_time}")
        if current_status:
            lines.append(f"- 当前身份/状态: {current_status}")
    if evolution_lines:
        lines.append("本次推演中的角色演化:")
        lines.extend(evolution_lines)
    if base_intro:
        lines.append("原始设定简介（完整保留；其中可能混有其他人物、旧阶段或档案摘录。它们只能作为背景资料，不能改变你的当前身份锚点）:")
        lines.append(base_intro)
    if relationship_lines:
        lines.append("稳定关系网络:")
        lines.extend(relationship_lines)
    if related_events:
        lines.append("与该角色直接相关的事件:")
        lines.extend(related_events[:8])

    return {
        'entity_name': canonical_name,
        'current_time': current_time,
        'current_status': current_status,
        'character_brief': "\n".join(lines),
    }


@evolution_bp.route('/create', methods=['POST'])
def create_evolution():
    """创建进化推演。支持向后推演 (forward) 和重新推演 (branch)"""
    try:
        data = request.get_json(silent=True) or {}
        world_id = data.get('world_id', '').strip()
        scenario = data.get('scenario', '').strip()
        config = data.get('config') or {}
        if not isinstance(config, dict):
            config = {}
        else:
            config = dict(config)
        evolution_type = data.get('evolution_type', 'forward')  # "forward" | "branch"
        parent_evolution_id = data.get('parent_evolution_id', '')
        parent_round = data.get('parent_round', -1)

        if not world_id:
            return jsonify({'success': False, 'message': '请提供世界观 ID'}), 400
        if not scenario:
            return jsonify({'success': False, 'message': '请提供推演场景'}), 400
        if not Config.get_llm_config('subagent').get('api_key'):
            return jsonify({'success': False, 'message': 'LLM API Key 未配置'}), 400

        config['rounds'] = _coerce_rounds(config.get('rounds', 5))
        config['temperature'] = _coerce_temperature(config.get('temperature', 0.7))
        config['focus_areas'] = _coerce_focus_areas(config.get('focus_areas') or [])

        world = WorldManager.get_world(world_id)
        if not world:
            return jsonify({'success': False, 'message': '世界观不存在'}), 404

        # 如果是分支推演，积累父进化状态
        accumulated_context = None
        if parent_evolution_id and parent_round >= 0:
            parent_evo = EvolutionManager.get(parent_evolution_id)
            if parent_evo:
                selected_parent_rounds = [
                    r for r in (parent_evo.rounds or [])
                    if getattr(r, 'round_number', 0) > 0 and getattr(r, 'round_number', 0) <= parent_round
                ]
                if not selected_parent_rounds:
                    selected_parent_rounds = [r for r in (parent_evo.rounds or []) if getattr(r, 'round_number', 0) > 0]

                last_parent_round = selected_parent_rounds[-1] if selected_parent_rounds else None
                accumulated_context = {
                    'parent_evolution_id': parent_evolution_id,
                    'parent_round': parent_round,
                    'parent_narratives': [
                        r.narrative for r in selected_parent_rounds
                    ],
                    'parent_affected_entities': [],
                    'parent_new_events': [],
                    'parent_rounds': [],
                }
                if last_parent_round:
                    accumulated_context['parent_anchor'] = {
                        'round_number': last_parent_round.round_number,
                        'year_advanced_to': last_parent_round.year_advanced_to,
                        'time_span_start': last_parent_round.year_advanced_to,
                    }
                    if not str(config.get('time_span_start') or '').strip() and str(last_parent_round.year_advanced_to or '').strip():
                        config['time_span_start'] = last_parent_round.year_advanced_to

                for r in selected_parent_rounds:
                    round_affected_entities = []
                    round_new_events = []
                    for ent in (r.affected_entities or []):
                        if isinstance(ent, dict):
                            accumulated_context['parent_affected_entities'].append(ent)
                            round_affected_entities.append(ent)
                    for evt in (r.new_events or []):
                        if isinstance(evt, dict):
                            accumulated_context['parent_new_events'].append(evt)
                            round_new_events.append(evt)
                    accumulated_context['parent_rounds'].append({
                        'round_number': r.round_number,
                        'year_advanced_to': r.year_advanced_to,
                        'affected_entities': round_affected_entities,
                        'new_events': round_new_events,
                    })

        engine = WorldEvolutionEngine()
        resolved_anchor = engine.resolve_anchor(
            world,
            scenario,
            config,
            accumulated_context=accumulated_context,
        )
        if resolved_anchor:
            config['resolved_anchor'] = resolved_anchor
            if resolved_anchor.get('start_time') and not str(config.get('time_span_start') or '').strip():
                config['time_span_start'] = resolved_anchor['start_time']
            if resolved_anchor.get('event_name') and not str(config.get('anchor_event') or '').strip():
                config['anchor_event'] = resolved_anchor['event_name']

        evolution = Evolution.create(
            world_id=world_id, scenario=scenario, config=config,
            parent_evolution_id=parent_evolution_id, parent_round=parent_round,
            evolution_type=evolution_type,
        )
        EvolutionManager.save(evolution)

        engine.evolve_async(
            evolution.id, world, scenario, config,
            accumulated_context=accumulated_context,
        )

        logger.info(f"进化推演已启动: {evolution.id} (type={evolution_type}, world={world_id})")
        return jsonify({'success': True, 'evolution_id': evolution.id})

    except Exception as e:
        logger.error(f"创建进化推演失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@evolution_bp.route('/<evolution_id>/continue', methods=['POST'])
def continue_evolution(evolution_id: str):
    """在当前推演项目内继续向后推演，追加新轮次。"""
    try:
        evolution = EvolutionManager.get(evolution_id)
        if not evolution:
            return jsonify({'success': False, 'message': '推演不存在'}), 404
        if evolution.status in {'planning', 'running', 'consolidating'}:
            return jsonify({'success': False, 'message': '当前推演仍在进行中，不能重复启动继续推演'}), 409

        data = request.get_json(silent=True) or {}
        scenario = str(data.get('scenario') or '').strip()
        config = data.get('config') or {}
        if not isinstance(config, dict):
            config = {}
        else:
            config = dict(config)

        if not scenario:
            return jsonify({'success': False, 'message': '请提供继续推演场景'}), 400
        if not Config.get_llm_config('subagent').get('api_key'):
            return jsonify({'success': False, 'message': 'LLM API Key 未配置'}), 400

        world = WorldManager.get_world(evolution.world_id)
        if not world:
            return jsonify({'success': False, 'message': '世界观不存在'}), 404

        existing_rounds = [r for r in (evolution.rounds or []) if getattr(r, 'round_number', 0) > 0]
        round_offset = len(existing_rounds)
        last_round = existing_rounds[-1] if existing_rounds else None
        append_rounds = _coerce_rounds(config.get('rounds', 3))
        previous_config = dict(evolution.config or {})

        config['rounds'] = append_rounds
        config['temperature'] = _coerce_temperature(config.get('temperature', previous_config.get('temperature', 0.7)))
        config['focus_areas'] = _coerce_focus_areas(config.get('focus_areas') or previous_config.get('focus_areas') or [])
        if last_round and not str(config.get('time_span_start') or '').strip():
            config['time_span_start'] = last_round.year_advanced_to

        accumulated_context = {
            'parent_evolution_id': evolution_id,
            'parent_round': round_offset,
            'parent_narratives': [r.narrative for r in existing_rounds],
            'parent_affected_entities': [],
            'parent_new_events': [],
            'parent_rounds': [],
        }
        if last_round:
            accumulated_context['parent_anchor'] = {
                'round_number': last_round.round_number,
                'year_advanced_to': last_round.year_advanced_to,
                'time_span_start': last_round.year_advanced_to,
            }
        for r in existing_rounds:
            round_affected_entities = [ent for ent in (r.affected_entities or []) if isinstance(ent, dict)]
            round_new_events = [evt for evt in (r.new_events or []) if isinstance(evt, dict)]
            accumulated_context['parent_affected_entities'].extend(round_affected_entities)
            accumulated_context['parent_new_events'].extend(round_new_events)
            accumulated_context['parent_rounds'].append({
                'round_number': r.round_number,
                'year_advanced_to': r.year_advanced_to,
                'affected_entities': round_affected_entities,
                'new_events': round_new_events,
            })

        engine = WorldEvolutionEngine()
        resolved_anchor = engine.resolve_anchor(
            world,
            scenario,
            config,
            accumulated_context=accumulated_context,
        )
        if resolved_anchor:
            config['resolved_anchor'] = resolved_anchor
            if resolved_anchor.get('start_time') and not str(config.get('time_span_start') or '').strip():
                config['time_span_start'] = resolved_anchor['start_time']
            if resolved_anchor.get('event_name') and not str(config.get('anchor_event') or '').strip():
                config['anchor_event'] = resolved_anchor['event_name']

        evolution.scenario = f"{evolution.scenario}\n\n继续推演：{scenario}" if evolution.scenario else scenario
        evolution.config = {
            **previous_config,
            **config,
            'rounds': round_offset + append_rounds,
            'last_continue_rounds': append_rounds,
        }
        evolution.status = 'running'
        evolution.error = ''
        evolution.consolidation = None
        EvolutionManager.save(evolution)

        engine.evolve_async(
            evolution_id,
            world,
            scenario,
            config,
            accumulated_context=accumulated_context,
            round_offset=round_offset,
        )

        logger.info(f"继续推演已启动: {evolution_id}, append_rounds={append_rounds}, round_offset={round_offset}")
        return jsonify({
            'success': True,
            'evolution_id': evolution_id,
            'appended_rounds': append_rounds,
            'total_rounds': round_offset + append_rounds,
        })

    except Exception as e:
        logger.error(f"继续进化推演失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@evolution_bp.route('/world/<world_id>', methods=['GET'])
def list_world_evolutions(world_id: str):
    """获取某世界观的所有进化推演（用于推演树）"""
    try:
        evolutions = EvolutionManager.list_by_world(world_id)
        return jsonify({
            'success': True,
            'evolutions': [e.to_dict() for e in evolutions],
        })
    except Exception as e:
        logger.error(f"获取推演列表失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@evolution_bp.route('/<evolution_id>/apply', methods=['POST'])
def apply_evolution_changes(evolution_id: str):
    """将推演中选定的变更应用到世界观"""
    try:
        evolution = EvolutionManager.get(evolution_id)
        if not evolution:
            return jsonify({'success': False, 'message': '推演不存在'}), 404

        data = request.get_json(silent=True) or {}
        selected_entities = data.get('entities', [])  # [{name, state_changes, new_status, round}]
        selected_events = data.get('events', [])       # [{name, date, description, involved_entities}]
        selected_round_numbers = data.get('rounds', [])  # 来自哪些轮次

        world = WorldManager.get_world(evolution.world_id)
        if not world:
            return jsonify({'success': False, 'message': '世界观不存在'}), 404

        applied = {'entities': 0, 'events': 0, 'settings_items': 0}

        round_year_map = {
            r.round_number: r.year_advanced_to
            for r in evolution.rounds
        }

        # 合并实体状态变化到世界观实体，并沉淀为阶段
        for ent in selected_entities:
            name = ent.get('name', '')
            try:
                round_number = int(ent.get('round') or (selected_round_numbers[-1] if selected_round_numbers else 0) or 0)
            except (TypeError, ValueError):
                round_number = 0
            year_advanced_to = round_year_map.get(round_number, '')
            stage_payload = _build_stage_payload(evolution_id, round_number, year_advanced_to, ent)
            # 查找已有实体或创建新实体
            target_entity = _find_world_entity(world, name) if name else None
            if target_entity and name and target_entity.name != name:
                if not isinstance(target_entity.aliases, list):
                    target_entity.aliases = []
                if name not in target_entity.aliases:
                    target_entity.aliases.append(name)

            if not target_entity and name:
                from ..models.world import Entity
                target_entity = Entity.create(
                    world_id=world.id, name=name, type='推演实体',
                    attributes={
                        '当前状态': ent.get('new_status', ''),
                        '最近变化': ent.get('state_changes', ''),
                        '演化来源': f"evol:{evolution_id}",
                    },
                    stages=[stage_payload],
                    evolution_refs=[f'evol:{evolution_id}'],
                )
                world.entities.append(target_entity)

            if not target_entity:
                continue

            if not isinstance(target_entity.attributes, dict):
                target_entity.attributes = {}
            target_entity.attributes['当前状态'] = ent.get('new_status', '')
            target_entity.attributes['最近变化'] = ent.get('state_changes', '')
            target_entity.attributes['演化来源'] = f"evol:{evolution_id}"

            if not isinstance(target_entity.evolution_refs, list):
                target_entity.evolution_refs = []
            evolution_ref = f'evol:{evolution_id}'
            if evolution_ref not in target_entity.evolution_refs:
                target_entity.evolution_refs.append(evolution_ref)

            _upsert_stage(target_entity, stage_payload)
            created_setting = _upsert_entity_setting(world, target_entity, stage_payload)
            if created_setting:
                applied['settings_items'] += 1

            applied['entities'] += 1

        # 添加选定事件到世界观
        for evt in selected_events:
            name = evt.get('name', '')
            if name:
                from ..models.world import Event
                new_event = Event.create(
                    world_id=world.id,
                    name=name,
                    description=evt.get('description', ''),
                    date=evt.get('date', ''),
                    entities=evt.get('involved_entities') or [],
                )
                # 添加演化来源属性
                if not new_event.__dict__.get('evolution_ref'):
                    new_event.__dict__['evolution_ref'] = f"evol:{evolution_id}"
                world.events.append(new_event)
                applied['events'] += 1

        WorldManager.save_world(world)

        return jsonify({
            'success': True,
            'message': f"已应用 {applied['entities']} 实体变更, {applied['events']} 事件, {applied['settings_items']} 设定项",
            'applied': applied,
        })

    except Exception as e:
        logger.error(f"应用推演变更失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@evolution_bp.route('/<evolution_id>', methods=['GET'])
def get_evolution(evolution_id: str):
    """获取进化推演完整数据"""
    try:
        evolution = EvolutionManager.get(evolution_id)
        if not evolution:
            return jsonify({'success': False, 'message': '推演不存在'}), 404

        return jsonify({'success': True, 'evolution': evolution.to_dict()})

    except Exception as e:
        logger.error(f"获取进化推演失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@evolution_bp.route('/entity-chat', methods=['POST'])
def entity_chat():
    """与当前推演中的实体进行角色扮演对话。"""
    try:
        data = request.get_json(silent=True) or {}
        world_id = data.get('world_id', '')
        evolution_id = data.get('evolution_id', '')
        entity_name = data.get('entity_name', '')
        question = str(data.get('question', '') or '').strip()
        history = data.get('history') or []

        if not all([world_id, entity_name]):
            return jsonify({'success': False, 'message': '缺少参数'}), 400

        world = WorldManager.get_world(world_id)
        if not world:
            return jsonify({'success': False, 'message': '世界观不存在'}), 404

        evolution = EvolutionManager.get(evolution_id) if evolution_id else None
        profile = _build_current_entity_brief(world, evolution, entity_name)
        if not profile:
            return jsonify({'success': False, 'message': f'实体 "{entity_name}" 不存在于当前推演或世界观中'}), 404

        canonical_name = profile['entity_name']
        current_time = profile.get('current_time', '')
        current_status = profile.get('current_status', '')
        character_brief = profile.get('character_brief', '')

        if not question:
            return jsonify({
                'success': True,
                'entity_name': canonical_name,
                'character_brief': character_brief,
                'current_time': current_time,
                'current_status': current_status,
            })

        if not Config.get_llm_config('subagent').get('api_key'):
            return jsonify({'success': False, 'message': 'LLM API Key 未配置'}), 400

        world_context = f"世界观名称: {world.name or '未命名'}\n"
        world_context += f"时代背景: {world.era or '未知'}\n"
        world_context += f"世界观描述: {world.description or '无'}\n"
        if world.writing_style:
            world_context += f"\n文风参考: {world.writing_style}"
        if evolution:
            world_context += f"\n推演场景: {evolution.scenario or '无'}"
            resolved_anchor = (evolution.config or {}).get('resolved_anchor') or {}
            if resolved_anchor.get('label'):
                world_context += f"\n推演锚点: {resolved_anchor['label']}"

        system_prompt = f"""你正在角色扮演一个虚构世界中的角色。你必须完全沉浸在这个角色中，并且始终以当前推演结局时点的角色状态回答。

{world_context}

【你要扮演的角色（以当前推演状态为准）】
{character_brief}

    【角色锚定优先级——必须按这个顺序理解角色】
    A. 当前角色锚点（最高优先级）
    - 你此刻就是“{canonical_name}”。
    - 默认当前时间是“{current_time or '当前推演终点'}”。
    - 默认当前身份/状态是“{current_status or '以当前角色锚点和推演演化为准'}”。
    - 除非用户明确要求你“回忆过去某一阶段”，否则一律以当前时点开口说话。

    B. 本次推演中的角色演化（第二优先级）
    - 推演中发生的身份变化、立场变化、关系变化、能力变化，都已经真实发生并构成你当前人格和处境的一部分。
    - 当原始设定与推演演化冲突时，必须以后者为准。

    C. 原始设定简介（第三优先级）
    - 原始设定可以完整吸收，用来保留角色的长期人格、过去经历、说话习惯、基础世界知识与历史关系。
    - 但原始设定只能解释“你以前是谁、你怎么走到今天”，不能覆盖你“现在是谁”。
    - 如果原始设定里出现其他人物姓名、其他角色档案、旁注、旧阶段记录或混杂条目，把它们视为与你有关的背景资料或外部档案，不要因此把自己错认成别人，也不要把说话视角切换成其他人。

    【回答前必须进行的隐式锚定检查——不要把检查过程输出给用户】
    1. 先确认“我现在是谁”。
    2. 再确认“我现在处于哪个时间点、什么身份、什么处境”。
    3. 再确认“原始设定里出现的其他姓名或旧档案，是否会让我误把自己认成别人”。如果会，忽略这种错误映射。
    4. 再确认“这句回答有没有滑回早期身份、早期记忆视角或新手阶段”。如果有，立刻改写成当前时点版本。
    5. 如果用户问的是过去经历，你要以“当前的我在回忆过去”的方式回答，而不是把自己退回过去那个阶段。

    【角色扮演规则——必须严格遵守】
    1. 你**就是**{canonical_name}本人。用第一人称“我”回答。永远不要用“作为一个AI”“根据设定”等出戏表达。
    2. 若原始设定与本次推演后的身份/状态冲突，永远以“当前推演状态”为准，不得退回新手期、早期身份或旧人格。
    3. 你拥有角色在当前时间点之前应有的记忆，包括世界观原始经历和本次推演中与你相关的事件。
    4. 如果被问到你不知道或不该知道的内容，要用符合身份的方式表示不知情，但不要跳出角色。
    5. 回答长度按问题自然调整；涉及剧情、立场、身份、能力、关系时可以详细回答。
    6. 说话风格要符合该角色的身份、处境和世界观文风。"""

        messages = [{"role": "system", "content": system_prompt}]
        for item in history[-12:] if isinstance(history, list) else []:
            if not isinstance(item, dict):
                continue
            role = str(item.get('role') or '').strip()
            content = str(item.get('content') or '').strip()
            if role in {'user', 'assistant'} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})

        from ..utils.llm_client import LLMClient
        llm = LLMClient()
        reply = llm.chat(
            messages=messages,
            temperature=0.8,
            max_tokens=1024,
        )

        return jsonify({
            'success': True,
            'reply': reply,
            'entity_name': canonical_name,
            'character_brief': character_brief,
            'current_time': current_time,
            'current_status': current_status,
        })

    except Exception as e:
        logger.error(f"实体对话失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@evolution_bp.route('/<evolution_id>/status', methods=['GET'])
def get_evolution_status(evolution_id: str):
    """获取进化推演状态（轻量轮询端点），包含新工作流的状态字段。"""
    try:
        evolution = EvolutionManager.get(evolution_id)
        if not evolution:
            return jsonify({'success': False, 'message': '推演不存在'}), 404

        visible_rounds = [
            round_data for round_data in (evolution.rounds or [])
            if getattr(round_data, 'round_number', 0) > 0
        ]
        last_narrative = ''
        if visible_rounds:
            last_narrative = visible_rounds[-1].narrative[:200]

        warning_count = sum(len(getattr(round_data, 'warnings', []) or []) for round_data in visible_rounds)
        latest_warnings = []
        for round_data in reversed(visible_rounds):
            latest_warnings = getattr(round_data, 'warnings', []) or []
            if latest_warnings:
                break

        # ── 新工作流字段 ──
        active_pressures: List[Dict[str, Any]] = []
        evolution_pattern: Dict[str, Any] = {}
        causal_graph_summary: Dict[str, Any] = {}
        if visible_rounds:
            latest_round = visible_rounds[-1]
            if getattr(latest_round, 'pressures', None):
                active_pressures = latest_round.pressures
            if getattr(latest_round, 'evolution_pattern', None):
                evolution_pattern = latest_round.evolution_pattern

        # 全局因果图摘要
        global_graph = getattr(evolution, 'global_causal_graph', None) or {}
        if global_graph:
            causal_graph_summary = {
                "node_count": len((global_graph.get("nodes") or {})),
                "edge_count": len((global_graph.get("edges") or [])),
                "latest_edges": (global_graph.get("edges") or [])[-5:],
            }

        return jsonify({
            'success': True,
            'status': evolution.status,
            'current_round': len(visible_rounds),
            'total_rounds': evolution.config.get('rounds', 5) if evolution.config else 5,
            'last_narrative': last_narrative,
            'error': getattr(evolution, 'error', ''),
            'warning_count': warning_count,
            'latest_warnings': latest_warnings[:5],
            # 新字段
            'active_pressures': active_pressures,
            'evolution_pattern': evolution_pattern,
            'causal_graph_summary': causal_graph_summary,
        })

    except Exception as e:
        logger.error(f"获取进化推演状态失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@evolution_bp.route('/<evolution_id>/round/<int:round_num>', methods=['GET'])
def get_evolution_round(evolution_id: str, round_num: int):
    """获取特定轮次数据"""
    try:
        evolution = EvolutionManager.get(evolution_id)
        if not evolution:
            return jsonify({'success': False, 'message': '推演不存在'}), 404

        for r in evolution.rounds:
            if r.round_number == round_num:
                return jsonify({'success': True, 'round': r.to_dict()})

        return jsonify({'success': False, 'message': '轮次不存在'}), 404

    except Exception as e:
        logger.error(f"获取进化轮次失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
