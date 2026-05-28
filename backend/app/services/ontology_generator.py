"""
本体生成服务
接口1：分析文本内容，生成适合社会模拟的实体和关系类型定义
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient
from ..utils.locale import get_language_instruction

logger = logging.getLogger(__name__)


def _to_pascal_case(name: str) -> str:
    """将任意格式的名称转换为 PascalCase（如 'works_for' -> 'WorksFor', 'person' -> 'Person'）"""
    # 按非字母数字字符分割
    parts = re.split(r'[^a-zA-Z0-9]+', name)
    # 再按 camelCase 边界分割（如 'camelCase' -> ['camel', 'Case']）
    words = []
    for part in parts:
        words.extend(re.sub(r'([a-z])([A-Z])', r'\1_\2', part).split('_'))
    # 每个词首字母大写，过滤空串
    result = ''.join(word.capitalize() for word in words if word)
    return result if result else 'Unknown'


# 兼容旧引用的短提示；实际系统提示由 OntologyGenerator._compose_system_prompt 分段生成。
ONTOLOGY_SYSTEM_PROMPT = "请输出满足 WorldFish 本体约束的 JSON，不要输出额外文本。"


class OntologyGenerator:
    """
    本体生成器
    分析文本内容，生成实体和关系类型定义
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient(role="subagent")

    def _compose_system_prompt(self) -> str:
        """分段组装本体设计提示词，避免单一大块模板。"""
        role_block = (
            "你是 WorldFish 的知识图谱本体设计器。请基于原始资料和模拟目标，"
            "输出适合社会行为推演的实体类型与关系类型。只返回 JSON。"
        )
        entity_scope = "\n".join([
            "实体必须是可行动、可发声或可被观察的主体：个人、机构、媒体、平台、公司、群体代表等。",
            "不要把抽象概念、情绪、话题、立场本身作为实体类型。",
            "实体类型数量必须为 10 个：前 8 个根据材料定制，最后保留 Person 与 Organization 兜底。",
        ])
        schema_block = """
输出 JSON 结构：
{
  "entity_types": [{"name": "PascalCase", "description": "<=100 chars", "attributes": [], "examples": []}],
  "edge_types": [{"name": "UPPER_SNAKE_CASE", "description": "<=100 chars", "source_targets": [], "attributes": []}],
  "analysis_summary": "简要说明"
}
""".strip()
        naming_rules = "\n".join([
            "命名规则：实体名必须是英文 PascalCase；关系名必须是英文 UPPER_SNAKE_CASE；属性名必须是英文 snake_case。",
            "保留字段不可用作属性名：name、uuid、group_id、created_at、summary。可使用 full_name、org_name、role、position、location。",
            "description 与 analysis_summary 使用当前界面语言。",
        ])
        design_hints = "\n".join([
            "关系类型应表达现实中的联系、互动或影响，例如任职、监管、评论、支持、反对、合作、报道。",
            "每个实体类型保留 1-3 个关键属性，宁可少而清晰，不要制造大量弱属性。",
            "如果资料不足，优先设计稳健通用类型，而不是编造过细分类。",
        ])
        return "\n\n".join([
            role_block,
            entity_scope,
            schema_block,
            naming_rules,
            design_hints,
            get_language_instruction(),
        ])
    
    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成本体定义
        
        Args:
            document_texts: 文档文本列表
            simulation_requirement: 模拟需求描述
            additional_context: 额外上下文
            
        Returns:
            本体定义（entity_types, edge_types等）
        """
        # 构建用户消息
        user_message = self._build_user_message(
            document_texts, 
            simulation_requirement,
            additional_context
        )
        
        system_prompt = self._compose_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # 调用LLM
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        # 验证和后处理
        result = self._validate_and_process(result)
        
        return result
    
    # 传给 LLM 的文本最大长度（5万字）
    MAX_TEXT_LENGTH_FOR_LLM = 50000
    
    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """构建用户消息"""
        
        # 合并文本
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        # 如果文本超过5万字，截断（仅影响传给LLM的内容，不影响图谱构建）
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(原文共{original_length}字，已截取前{self.MAX_TEXT_LENGTH_FOR_LLM}字用于本体分析)..."
        
        message = f"""## 模拟需求

{simulation_requirement}

## 文档内容

{combined_text}
"""
        
        if additional_context:
            message += f"""
## 额外说明

{additional_context}
"""
        
        message += """
请根据以上内容，设计适合社会舆论模拟的实体类型和关系类型。

**必须遵守的规则**：
1. 必须正好输出10个实体类型
2. 最后2个必须是兜底类型：Person（个人兜底）和 Organization（组织兜底）
3. 前8个是根据文本内容设计的具体类型
4. 所有实体类型必须是现实中可以发声的主体，不能是抽象概念
5. 属性名不能使用 name、uuid、group_id 等保留字，用 full_name、org_name 等替代
"""
        
        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化 LLM 返回的本体结构。"""
        result = self._ensure_ontology_shape(result)
        entity_name_map = self._normalize_entity_types(result["entity_types"])
        self._normalize_edge_types(result["edge_types"], entity_name_map)
        result["entity_types"] = self._dedupe_entity_types(result["entity_types"])
        result["entity_types"] = self._ensure_fallback_entity_types(result["entity_types"])
        result["edge_types"] = result["edge_types"][:10]
        return result

    def _ensure_ontology_shape(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result, dict):
            result = {}
        result.setdefault("entity_types", [])
        result.setdefault("edge_types", [])
        result.setdefault("analysis_summary", "")
        return result

    def _normalize_entity_types(self, entities: List[Dict[str, Any]]) -> Dict[str, str]:
        rename_map: Dict[str, str] = {}
        for entity in entities:
            original_name = entity.get("name", "")
            if original_name:
                normalized_name = _to_pascal_case(original_name)
                entity["name"] = normalized_name
                rename_map[original_name] = normalized_name
                if normalized_name != original_name:
                    logger.warning(f"Entity type name '{original_name}' auto-converted to '{normalized_name}'")
            entity.setdefault("attributes", [])
            entity.setdefault("examples", [])
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."
        return rename_map

    def _normalize_edge_types(self, edges: List[Dict[str, Any]], entity_name_map: Dict[str, str]) -> None:
        for edge in edges:
            original_name = edge.get("name", "")
            if original_name:
                normalized_name = original_name.upper()
                edge["name"] = normalized_name
                if normalized_name != original_name:
                    logger.warning(f"Edge type name '{original_name}' auto-converted to '{normalized_name}'")
            edge.setdefault("source_targets", [])
            edge.setdefault("attributes", [])
            for source_target in edge["source_targets"]:
                if source_target.get("source") in entity_name_map:
                    source_target["source"] = entity_name_map[source_target["source"]]
                if source_target.get("target") in entity_name_map:
                    source_target["target"] = entity_name_map[source_target["target"]]
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."

    def _dedupe_entity_types(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique_entities = []
        seen_names = set()
        for entity in entities:
            name = entity.get("name", "")
            if not name:
                continue
            if name in seen_names:
                logger.warning(f"Duplicate entity type '{name}' removed during validation")
                continue
            seen_names.add(name)
            unique_entities.append(entity)
        return unique_entities

    def _fallback_entity_types(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Person",
                "description": "Any individual person not fitting other specific person types.",
                "attributes": [
                    {"name": "full_name", "type": "text", "description": "Full name of the person"},
                    {"name": "role", "type": "text", "description": "Role or occupation"},
                ],
                "examples": ["ordinary citizen", "anonymous netizen"],
            },
            {
                "name": "Organization",
                "description": "Any organization not fitting other specific organization types.",
                "attributes": [
                    {"name": "org_name", "type": "text", "description": "Name of the organization"},
                    {"name": "org_type", "type": "text", "description": "Type of organization"},
                ],
                "examples": ["small business", "community group"],
            },
        ]

    def _ensure_fallback_entity_types(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        max_entity_types = 10
        current_names = {entity.get("name") for entity in entities}
        missing_fallbacks = [fallback for fallback in self._fallback_entity_types() if fallback["name"] not in current_names]
        room_needed = len(missing_fallbacks)
        if room_needed and len(entities) + room_needed > max_entity_types:
            entities = entities[:max_entity_types - room_needed]
        entities.extend(missing_fallbacks)
        return entities[:max_entity_types]
    
    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """将本体 JSON 转换为 Zep 可加载的 Python 类型定义。"""
        builder: List[str] = []
        builder.extend(self._python_header_lines())
        builder.extend(self._python_model_block(ontology.get("entity_types", []), "entity"))
        builder.extend(self._python_model_block(ontology.get("edge_types", []), "edge"))
        builder.extend(self._python_registry_block(ontology))
        return '\n'.join(builder)

    def _python_header_lines(self) -> List[str]:
        return [
            '"""WorldFish 自动生成的图谱本体类型。"""',
            '# 注意：当前使用本地图谱，无需 zep_cloud 依赖。',
            '',
        ]

    def _python_class_name_for_edge(self, edge_name: str) -> str:
        return ''.join(piece.capitalize() for piece in edge_name.split('_') if piece)

    def _python_field_lines(self, attrs: List[Dict[str, Any]]) -> List[str]:
        if not attrs:
            return ['    pass']
        lines: List[str] = []
        for attr in attrs:
            field_name = attr["name"]
            field_desc = attr.get("description", field_name)
            lines.extend([
                f'    {field_name}: EntityText = Field(',
                f'        description="{field_desc}",',
                '        default=None',
                '    )',
            ])
        return lines

    def _python_model_block(self, items: List[Dict[str, Any]], model_kind: str) -> List[str]:
        # 本地图谱模式：不再生成 Zep ontology model，仅输出实体注册表。
        title = '# ---- 实体注册 ----' if model_kind == 'entity' else '# ---- 关系注册 ----'
        lines = [title, '']
        for item in items:
            raw_name = item["name"]
            lines.append(f"# {raw_name}: {item.get('description', '')}")
        return lines

    def _python_registry_block(self, ontology: Dict[str, Any]) -> List[str]:
        entity_lines = ['ENTITY_TYPES = {']
        for entity in ontology.get("entity_types", []):
            entity_lines.append(f'    "{entity["name"]}": {entity["name"]},')
        entity_lines.append('}')

        edge_lines = ['EDGE_TYPES = {']
        for edge in ontology.get("edge_types", []):
            edge_lines.append(f'    "{edge["name"]}": {self._python_class_name_for_edge(edge["name"])},')
        edge_lines.append('}')

        source_target_lines = ['EDGE_SOURCE_TARGETS = {']
        for edge in ontology.get("edge_types", []):
            st_list = edge.get("source_targets", [])
            if not st_list:
                continue
            serialized = ', '.join(
                f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                for st in st_list
            )
            source_target_lines.append(f'    "{edge["name"]}": [{serialized}],')
        source_target_lines.append('}')
        return ['', '# ---- 注册表 ----', '', *entity_lines, '', *edge_lines, '', *source_target_lines]

