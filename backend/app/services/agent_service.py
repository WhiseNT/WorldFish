"""
Agent 核心服务 — LLM 驱动的 Tool-Use Agent
支持：ReACT 循环、MCP 协议、Skill、多 Session、记忆、子 Agent、文件上传
"""

import json
import os
import re
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Optional

from ..config import Config
from ..models.world import WorldManager
from ..models.agent import (
    AgentManager, AgentSession, AgentMessage,
)
from ..services.agent_tools import (
    ALL_TOOLS, get_tool_by_name,
    get_all_tool_schemas_openai,
    get_all_tool_schemas_mcp,
    ToolCallResult,
)
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger("mirofish.agent_service")

# ============================================================
# 系统 Prompt
# ============================================================

SYSTEM_PROMPT_TEMPLATE = """你是一个世界观构建与管理的智能助手 "WorldFish Agent"。

## 你的能力
- **检索**：search_knowledge（RAG语义检索，最省Token）/ read_world / list_entities / list_events / read_settings / list_calendars / get_calendar_detail
- **修改**：添加/修改/删除实体、添加/修改/删除事件、更新世界观元信息、管理时间线历法（纪元/纪年）、创设定集/设定项
- **管理**：Agent.md 读写、Skills 管理、记忆存取
- **交互**：向用户提问、提供选项列表让用户选择

## Token 节省原则（重要！）
1. **优先用 search_knowledge** 查询具体内容，而不是 list_entities 返回全部实体再筛选
2. **list_entities/list_events 默认返回 20 条**，需要更多时指定 limit 参数
3. **时间线历法修改前先用 list_calendars 或 get_calendar_detail 确认目标**
4. **避免反复调用同一个工具**
5. **get_entity_detail 只在需要完整属性时才调用**

## 工作原则
1. **主动了解**：先读取当前世界观数据，了解全貌再提出建议
2. **先确认后操作**：修改/删除前先向用户确认
3. **提供选项**：当有多个可行方案时，使用 plan_options 工具
4. **结构化展示**：用清晰格式展示信息

## 🔴 诚实原则（最高优先级）
- **只回答知识库和世界观数据中实际存在的内容**
- **如果 search_knowledge 返回空或低分，直接说"暂未收录"**
- **绝不编造、猜测、或使用你自身的训练数据来补充世界观内容**
- **你的训练数据≠世界观数据，混淆两者会误导用户**

## 当前上下文
{context_info}

## 语言
{language_instruction}"""


def _build_system_prompt(world_id: str = "") -> str:
    """构建系统 Prompt"""
    context_parts = []

    if world_id:
        world = WorldManager.get_world(world_id)
        if world:
            context_parts.append(f"- 当前世界观: {world.name} (ID: {world.id})")
            context_parts.append(f"- 实体数量: {len(world.entities)}，事件数量: {len(world.events)}")
        else:
            context_parts.append(f"- 当前世界观 ID: {world_id}（未找到，可能需要重新选择）")
    else:
        context_parts.append("- 当前未选择世界观（全局模式），可用的世界观列表需用 list_worlds 工具查看")

    # Agent.md 内容
    agent_md = AgentManager.get_agent_md(world_id)
    if agent_md:
        context_parts.insert(0, f"## Agent.md 自定义指令\n\n{agent_md}\n")

    # 记忆摘要
    memories = AgentManager.get_memories(world_id)
    if memories:
        mem_text = "\n".join(f"- {k}: {str(v)[:200]}" for k, v in list(memories.items())[:10])
        context_parts.append(f"## 已存储记忆\n{mem_text}")

    # Skills
    skills = AgentManager.list_skills(world_id)
    global_skill_names = [s.name for s in skills if not s.world_id]
    world_skill_names = [s.name for s in skills if s.world_id == world_id]
    if world_skill_names or global_skill_names:
        context_parts.append(f"## 可用 Skills\n"
                             f"- 全局: {', '.join(global_skill_names) if global_skill_names else '无'}\n"
                             f"- 世界观: {', '.join(world_skill_names) if world_skill_names else '无'}")

    context_info = "\n".join(context_parts) if context_parts else "无特殊上下文"

    return SYSTEM_PROMPT_TEMPLATE.format(
        context_info=context_info,
        language_instruction="请用中文与用户对话。",
    )


# ============================================================
# Agent Service
# ============================================================

@dataclass
class AgentResponseChunk:
    """流式响应的单个 Chunk"""
    type: str  # "text" | "tool_call" | "tool_result" | "context" | "usage" | "user_prompt" | "done"
    content: str = ""
    data: Any = None


class AgentService:
    """核心 Agent 服务"""

    MAX_TOOL_CALLS = 15  # 单轮最大工具调用次数
    MAX_MESSAGES = 50    # 最大保留消息数
    LONG_CONTEXT_MAX_MESSAGES = 4000
    CONTEXT_SAFETY_TOKENS = 4096
    CONTEXT_SNAPSHOT_LIMIT = 30
    COMPACT_KEEP_RECENT_MESSAGES = 12
    COMPACT_SUMMARY_PREFIX = "[自动压缩上下文摘要]"

    def __init__(self):
        pass

    # ---- 构建消息列表 ----

    @staticmethod
    def _stringify_for_token_estimate(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except TypeError:
            return str(value)

    @classmethod
    def _estimate_text_tokens(cls, value: Any) -> int:
        text = cls._stringify_for_token_estimate(value)
        if not text:
            return 0
        ascii_count = sum(1 for char in text if ord(char) < 128)
        non_ascii_count = len(text) - ascii_count
        return max(1, (ascii_count + 3) // 4 + non_ascii_count)

    @classmethod
    def _estimate_message_tokens(cls, message: Dict[str, Any]) -> int:
        total = 4
        for key, value in message.items():
            total += cls._estimate_text_tokens(key)
            total += cls._estimate_text_tokens(value)
        return total

    @classmethod
    def _estimate_messages_tokens(cls, messages: List[Dict[str, Any]]) -> int:
        return sum(cls._estimate_message_tokens(message) for message in messages)

    def _max_messages_for_context(self, context_window: int) -> int:
        if context_window >= 512 * 1024:
            return self.LONG_CONTEXT_MAX_MESSAGES
        return self.MAX_MESSAGES

    def _context_token_budget(self, context_window: int, max_output_tokens: int) -> int:
        reserve = max(max_output_tokens, 1024) + self.CONTEXT_SAFETY_TOKENS
        return max(2048, context_window - reserve)

    def _build_context_stats(
        self,
        messages: List[Dict[str, Any]],
        llm: LLMClient,
        max_output_tokens: int,
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
        compacted: bool = False,
    ) -> Dict[str, Any]:
        message_tokens = self._estimate_messages_tokens(messages)
        tool_schema_tokens = self._estimate_text_tokens(tool_schemas or [])
        estimated_context_tokens = message_tokens + tool_schema_tokens
        reserved_tokens = max(max_output_tokens, 1024) + self.CONTEXT_SAFETY_TOKENS
        estimated_total_tokens = estimated_context_tokens + reserved_tokens
        context_window = max(llm.context_window, 1)
        compression_threshold = max(0.50, min(0.95, Config.AGENT_CONTEXT_COMPRESSION_RATIO))
        ratio = estimated_total_tokens / context_window
        return {
            "model": llm.model,
            "model_profile": "deepseek-v4" if llm.is_deepseek_v4 else "openai-compatible",
            "context_window": context_window,
            "message_count": len(messages),
            "message_tokens": message_tokens,
            "tool_schema_tokens": tool_schema_tokens,
            "estimated_context_tokens": estimated_context_tokens,
            "reserved_tokens": reserved_tokens,
            "estimated_total_tokens": estimated_total_tokens,
            "context_ratio": round(ratio, 4),
            "compression_threshold": compression_threshold,
            "compression_due": ratio >= compression_threshold,
            "compacted": compacted,
            "updated_at": datetime.now().isoformat(),
        }

    def _record_context_stats(self, session: AgentSession, stats: Dict[str, Any]) -> None:
        session.context_stats = dict(stats)
        snapshots = list(session.context_snapshots or [])
        snapshots.append(dict(stats))
        session.context_snapshots = snapshots[-self.CONTEXT_SNAPSHOT_LIMIT:]

    @staticmethod
    def _add_numeric_usage(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(target or {})
        for key, value in source.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                result[key] = result.get(key, 0) + value
        return result

    @staticmethod
    def _cache_hit_tokens(usage: Dict[str, Any]) -> Any:
        prompt_details = usage.get("prompt_tokens_details")
        cache_hit = usage.get("prompt_cache_hit_tokens")
        if cache_hit is None and isinstance(prompt_details, dict):
            cache_hit = prompt_details.get("cached_tokens")
        return cache_hit

    def _normalize_usage(self, usage: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(usage or {})
        cache_hit = self._cache_hit_tokens(normalized)
        if cache_hit is not None and normalized.get("prompt_cache_hit_tokens") is None:
            normalized["prompt_cache_hit_tokens"] = cache_hit

        prompt_tokens = normalized.get("prompt_tokens")
        if (
            isinstance(prompt_tokens, (int, float))
            and isinstance(cache_hit, (int, float))
            and normalized.get("prompt_cache_miss_tokens") is None
        ):
            normalized["prompt_cache_miss_tokens"] = max(0, prompt_tokens - cache_hit)
        return normalized

    def _record_llm_usage(self, session: AgentSession, llm: LLMClient, usage: Dict[str, Any]) -> None:
        if not usage:
            return

        current = dict(session.usage or {})
        total = self._add_numeric_usage(current.get("total", {}), usage)
        total["requests"] = total.get("requests", 0) + 1

        by_model = dict(current.get("by_model", {}))
        model_usage = self._add_numeric_usage(by_model.get(llm.model, {}), usage)
        model_usage["requests"] = model_usage.get("requests", 0) + 1
        by_model[llm.model] = model_usage

        session.usage = {
            **current,
            "last": usage,
            "total": total,
            "by_model": by_model,
            "updated_at": datetime.now().isoformat(),
        }

    def _log_llm_usage(
        self,
        response: Any,
        llm: LLMClient,
        messages: List[Dict[str, Any]],
        session: AgentSession,
    ) -> Dict[str, Any]:
        usage = LLMClient.usage_to_dict(getattr(response, "usage", None))
        if not usage:
            return {}

        usage = self._normalize_usage(usage)
        self._record_llm_usage(session, llm, usage)
        cache_hit = self._cache_hit_tokens(usage)

        session.context_stats = {
            **dict(session.context_stats or {}),
            "actual_prompt_tokens": usage.get("prompt_tokens"),
            "actual_completion_tokens": usage.get("completion_tokens"),
            "actual_total_tokens": usage.get("total_tokens"),
            "actual_cache_hit_tokens": cache_hit,
            "usage_updated_at": datetime.now().isoformat(),
        }

        logger.info(
            "Agent LLM usage: model=%s profile=%s window=%s messages=%s estimated_context_tokens=%s "
            "prompt_tokens=%s completion_tokens=%s cache_hit=%s cache_miss=%s",
            llm.model,
            "deepseek-v4" if llm.is_deepseek_v4 else "openai-compatible",
            llm.context_window,
            len(messages),
            self._estimate_messages_tokens(messages),
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            cache_hit,
            usage.get("prompt_cache_miss_tokens"),
        )
        return usage

    def _can_compact_session(self, session: AgentSession) -> bool:
        meaningful = [m for m in session.messages if m.role in {"user", "assistant", "tool", "system"}]
        if len(meaningful) <= self.COMPACT_KEEP_RECENT_MESSAGES + 4:
            return False
        return True

    def _build_compaction_source(self, messages: List[AgentMessage]) -> str:
        lines: List[str] = []
        total_chars = 0
        max_chars = 120_000
        for msg in messages:
            payload = {
                "role": msg.role,
                "name": msg.name,
                "content": (msg.content or "")[:1800],
                "tool_calls": msg.tool_calls,
                "tool_call_id": msg.tool_call_id,
                "timestamp": msg.timestamp,
            }
            line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            if total_chars + len(line) > max_chars:
                lines.append(json.dumps({
                    "role": "system",
                    "content": f"以上为可压缩上下文的一部分，后续 {len(messages) - len(lines)} 条消息因长度限制省略。"
                }, ensure_ascii=False))
                break
            lines.append(line)
            total_chars += len(line)
        return "\n".join(lines)

    def _compact_session_context(
        self,
        session: AgentSession,
        llm: LLMClient,
        stats: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not self._can_compact_session(session):
            return None

        split_index = max(0, len(session.messages) - self.COMPACT_KEEP_RECENT_MESSAGES)
        while split_index < len(session.messages) and session.messages[split_index].role == "tool":
            split_index += 1

        compact_messages = session.messages[:split_index]
        retained_messages = session.messages[split_index:]
        if len(compact_messages) < 4:
            return None

        source = self._build_compaction_source(compact_messages)
        prompt = f"""请把下面的 WorldFish Agent 历史对话压缩成后续可继续使用的上下文摘要。

要求：
1. 保留用户明确需求、已确认的事实、已执行的修改、工具结论、未完成事项。
2. 删除寒暄、重复过程、失败重试细节，只保留影响后续判断的信息。
3. 不要编造世界观内容；不确定的信息标为“未确认”。
4. 输出中文 Markdown，控制在 1200 字以内。

历史对话 JSONL：
{source}
"""
        try:
            summary = llm.chat(
                messages=[
                    {"role": "system", "content": "你是上下文压缩器，只输出压缩摘要。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2048,
                thinking_enabled=False,
            ).strip()
        except Exception as exc:
            logger.warning(f"Agent 上下文压缩失败: {exc}")
            return None

        if not summary:
            return None

        summary_message = AgentMessage(
            role="system",
            content=(
                f"{self.COMPACT_SUMMARY_PREFIX}\n"
                f"- 压缩时间: {datetime.now().isoformat()}\n"
                f"- 压缩前估算上下文: {stats.get('estimated_context_tokens', 0)} tokens\n\n"
                f"{summary}"
            ),
        )
        session.messages = [summary_message] + retained_messages
        compact_record = {
            "compacted_at": datetime.now().isoformat(),
            "compacted_messages": len(compact_messages),
            "retained_messages": len(retained_messages),
            "before_estimated_context_tokens": stats.get("estimated_context_tokens", 0),
            "context_ratio": stats.get("context_ratio", 0),
        }
        session.context_stats = {
            **dict(session.context_stats or {}),
            "last_compaction": compact_record,
            "compacted": True,
        }
        AgentManager.save_session(session)
        return compact_record

    def _build_messages(self, session: AgentSession, user_message: str = "",
                        system_prompt: str = "", context_window: int = 128 * 1024,
                        max_output_tokens: int = 4096,
                        thinking_enabled: bool = False) -> List[Dict[str, Any]]:
        """构建 LLM 格式的消息列表"""
        messages = [{"role": "system", "content": system_prompt}]

        # 对话历史按“非 tool 消息 + 其后 tool 回复”分组，避免截断后出现孤立 tool 消息
        grouped_messages: List[List[Dict[str, Any]]] = []
        current_group: List[Dict[str, Any]] = []
        pending_tool_call_ids: set[str] = set()

        def flush_current_group() -> None:
            nonlocal current_group, pending_tool_call_ids
            if current_group:
                grouped_messages.append(current_group)
            current_group = []
            pending_tool_call_ids = set()

        for msg in session.messages:
            if msg.role == "tool":
                tool_call_id = msg.tool_call_id or ""
                if not current_group or not pending_tool_call_ids:
                    continue
                if not tool_call_id or tool_call_id not in pending_tool_call_ids:
                    continue
                current_group.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": msg.content,
                })
                continue

            flush_current_group()

            if msg.role == "user":
                current_group = [{"role": "user", "content": msg.content}]
            elif msg.role == "system":
                current_group = [{"role": "system", "content": msg.content}]
            elif msg.role == "assistant":
                entry = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    entry["tool_calls"] = msg.tool_calls
                    pending_tool_call_ids = {
                        str(tc.get("id") or "").strip()
                        for tc in msg.tool_calls
                        if isinstance(tc, dict) and str(tc.get("id") or "").strip()
                    }
                if msg.reasoning_content:
                    entry["reasoning_content"] = msg.reasoning_content
                elif thinking_enabled:
                    # DeepSeek thinking 模式重放 assistant 消息时需要该字段，即使为空。
                    entry["reasoning_content"] = ""
                current_group = [entry]
            else:
                current_group = []

        flush_current_group()

        if user_message:
            grouped_messages.append([{"role": "user", "content": user_message}])

        # 按组从尾部截断，保证 assistant.tool_calls 与对应 tool 回复不会被切散
        if grouped_messages:
            retained_groups: List[List[Dict[str, Any]]] = []
            total_count = 1  # system message
            total_tokens = self._estimate_message_tokens(messages[0])
            max_messages = self._max_messages_for_context(context_window)
            token_budget = self._context_token_budget(context_window, max_output_tokens)
            skipped_groups = 0

            for group in reversed(grouped_messages):
                group_size = len(group)
                group_tokens = self._estimate_messages_tokens(group)
                if retained_groups and total_count + group_size > max_messages:
                    skipped_groups += 1
                    break
                if retained_groups and total_tokens + group_tokens > token_budget:
                    skipped_groups += 1
                    break
                retained_groups.append(group)
                total_count += group_size
                total_tokens += group_tokens

            messages = [messages[0]]
            for group in reversed(retained_groups):
                messages.extend(group)

            if skipped_groups:
                logger.debug(
                    "Agent context trimmed: skipped_groups=%s retained_messages=%s estimated_tokens=%s budget=%s",
                    skipped_groups,
                    len(messages),
                    total_tokens,
                    token_budget,
                )

        return messages

    # ---- 核心 Chat 流式 ----

    def chat_stream(
        self,
        session: AgentSession,
        user_message: str = "",
        world_id: str = "",
    ) -> Generator[AgentResponseChunk, None, None]:
        """
        Agent 主循环 - 流式返回
        1. 发送用户消息给 LLM
        2. LLM 可能返回 text 或 tool_calls
        3. 执行 tool_calls 并发送结果回去
        4. 直到 LLM 不再调用工具或达到上限
        """

        llm = LLMClient()
        system_prompt = _build_system_prompt(world_id)
        tool_schemas = get_all_tool_schemas_openai()
        max_tokens = llm.default_max_tokens

        # 添加用户消息到 session
        if user_message:
            session.messages.append(AgentMessage(role="user", content=user_message))

        tool_call_count = 0

        try:
            while tool_call_count < self.MAX_TOOL_CALLS:
                messages = self._build_messages(
                    session,
                    system_prompt=system_prompt,
                    context_window=llm.context_window,
                    max_output_tokens=max_tokens,
                    thinking_enabled=llm.thinking_enabled,
                )
                context_stats = self._build_context_stats(messages, llm, max_tokens, tool_schemas=tool_schemas)
                self._record_context_stats(session, context_stats)
                yield AgentResponseChunk(type="context", data=context_stats)

                if context_stats["compression_due"] and self._can_compact_session(session):
                    compact_record = self._compact_session_context(session, llm, context_stats)
                    if compact_record:
                        messages = self._build_messages(
                            session,
                            system_prompt=system_prompt,
                            context_window=llm.context_window,
                            max_output_tokens=max_tokens,
                            thinking_enabled=llm.thinking_enabled,
                        )
                        context_stats = self._build_context_stats(
                            messages,
                            llm,
                            max_tokens,
                            tool_schemas=tool_schemas,
                            compacted=True,
                        )
                        context_stats["last_compaction"] = compact_record
                        self._record_context_stats(session, context_stats)
                        yield AgentResponseChunk(
                            type="context",
                            content="已自动压缩上下文",
                            data=context_stats,
                        )

                # 调用 LLM
                response = llm.create_chat_completion(
                    model=llm.model,
                    messages=messages,
                    tools=tool_schemas,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                usage = self._log_llm_usage(response, llm, messages, session)
                if usage:
                    yield AgentResponseChunk(
                        type="usage",
                        data={
                            "last": usage,
                            "total": (session.usage or {}).get("total", {}),
                            "context_stats": session.context_stats,
                            "cache_hit_tokens": self._cache_hit_tokens(usage),
                        },
                    )
                choice = response.choices[0]
                msg = choice.message

                # 提取 DeepSeek 等推理模型的 thinking 内容
                reasoning = getattr(msg, "reasoning_content", "") or ""
                if not reasoning and hasattr(msg, "model_extra"):
                    reasoning = msg.model_extra.get("reasoning_content", "") or ""

                # 检查是否需要用户响应（上一次工具调用要求了需要用户响应）
                # 如果有 tool_calls，处理它们
                if msg.tool_calls:
                    # 记录 assistant 的工具调用
                    tc_list = []
                    for tc in msg.tool_calls:
                        tc_list.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        })
                        yield AgentResponseChunk(
                            type="tool_call",
                            content=f"调用工具: {tc.function.name}",
                            data={"name": tc.function.name, "arguments": tc.function.arguments}
                        )

                    # 保存 assistant 消息（含 tool_calls 和 reasoning_content）
                    assistant_text = msg.content or ""
                    session.messages.append(AgentMessage(
                        role="assistant", content=assistant_text,
                        tool_calls=tc_list,
                        reasoning_content=reasoning,
                    ))

                    # 执行每个工具调用
                    tool_results = []
                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        tool = get_tool_by_name(tool_name)
                        if not tool:
                            result_content = f"错误: 未知工具 '{tool_name}'"
                            result = ToolCallResult(False, result_content)
                        else:
                            try:
                                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                            except json.JSONDecodeError:
                                args = {}
                            try:
                                result = tool.execute(world_id=world_id, **args)
                            except Exception as e:
                                logger.error(f"工具执行失败 [{tool_name}]: {e}")
                                result = ToolCallResult(False, f"工具执行失败: {str(e)}")

                        tool_results.append((tc.id, tool_name, result))

                    # 发送工具结果并添加到 session
                    for tc_id, tool_name, result in tool_results:
                        result_content = result.content
                        if result.success:
                            result_content = f"[{tool_name}] ✅\n{result.content}"
                        else:
                            result_content = f"[{tool_name}] ❌\n{result.content}"

                        yield AgentResponseChunk(
                            type="tool_result",
                            content=result_content,
                            data={
                                "name": tool_name,
                                "success": result.success,
                                "result": result.data,
                            },
                        )

                        session.messages.append(AgentMessage(
                            role="tool",
                            content=result.content,
                            tool_call_id=tc_id,
                            name=tool_name,
                        ))

                        # 如果需要用户响应，暂停并等待
                        if result.needs_user_response:
                            if result.user_options:
                                session.messages.append(AgentMessage(
                                    role="assistant",
                                    content=result.content,
                                    options=result.user_options,
                                ))
                            yield AgentResponseChunk(
                                type="user_prompt",
                                content=result.content,
                                data=result.user_options,
                            )
                            # 保存 session 后返回
                            AgentManager.save_session(session)
                            yield AgentResponseChunk(type="done", content="等待用户响应")
                            return

                    tool_call_count += 1

                # 没有 tool_calls，纯文本回复
                else:
                    text = msg.content or ""
                    session.messages.append(AgentMessage(
                        role="assistant", content=text,
                        reasoning_content=reasoning,
                    ))
                    yield AgentResponseChunk(type="text", content=text)
                    yield AgentResponseChunk(type="done", content="完成")
                    break

            # 超过最大工具调用次数
            if tool_call_count >= self.MAX_TOOL_CALLS:
                final_msg = f"\n\n⚠️ 已达到单轮最大工具调用次数 ({self.MAX_TOOL_CALLS})，如果你还有更多需求，请在新消息中继续。"
                session.messages.append(AgentMessage(role="assistant", content=final_msg))
                yield AgentResponseChunk(type="text", content=final_msg)
                yield AgentResponseChunk(type="done")

        except Exception as e:
            logger.error(f"Agent chat error: {e}")
            error_msg = f"❌ Agent 运行出错: {str(e)}"
            session.messages.append(AgentMessage(role="assistant", content=error_msg))
            yield AgentResponseChunk(type="text", content=error_msg)
            yield AgentResponseChunk(type="done")

        finally:
            # 保存 session
            AgentManager.save_session(session)
            # 自动生成会话标题（首次有意义对话后）
            try:
                self.generate_title(session)
            except Exception:
                pass  # 标题生成失败不影响主流程

    # ---- 用户选项响应 ----

    def respond_to_options(
        self,
        session: AgentSession,
        selected_options: List[str],
        world_id: str = "",
    ) -> Generator[AgentResponseChunk, None, None]:
        """用户选择了选项后继续执行"""
        user_response = f"用户的选择: {', '.join(selected_options)}"
        session.messages.append(AgentMessage(role="user", content=user_response))
        yield from self.chat_stream(session, user_message="", world_id=world_id)

    # ---- MCP 协议支持 ----

    def mcp_handle(self, method: str, params: dict = None) -> dict:
        """
        处理 MCP (Model Context Protocol) JSON-RPC 请求
        支持: tools/list, tools/call, resources/list, resources/read
        """
        params = params or {}

        if method == "tools/list":
            tools = get_all_tool_schemas_mcp()
            return {"tools": tools}

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            world_id = params.get("world_id", "")
            tool = get_tool_by_name(tool_name)
            if not tool:
                return {"error": f"Unknown tool: {tool_name}"}
            result = tool.execute(world_id=world_id, **arguments)
            return {
                "content": [{"type": "text", "text": result.content}],
                "isError": not result.success,
            }

        elif method == "resources/list":
            worlds = WorldManager.list_worlds()
            resources = [{
                "uri": f"world://{w.id}",
                "name": w.name,
                "description": w.description[:200] if w.description else "",
                "mimeType": "application/json",
            } for w in worlds]
            return {"resources": resources}

        elif method == "resources/read":
            uri = params.get("uri", "")
            if uri.startswith("world://"):
                world_id = uri.replace("world://", "")
                world = WorldManager.get_world(world_id)
                if world:
                    return {
                        "contents": [{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(world.to_dict(), ensure_ascii=False, indent=2),
                        }]
                    }
            return {"error": f"Resource not found: {uri}"}

        else:
            return {"error": f"Unknown method: {method}"}

    # ---- 文件上传处理 ----

    def process_uploaded_file(
        self,
        session: AgentSession,
        file_path: str,
        file_name: str,
        world_id: str = "",
    ) -> str:
        """处理上传的文件，提取文本并加入对话"""
        from ..utils.file_parser import FileParser

        try:
            text = FileParser.extract_text(file_path)
            summary = f"📎 用户上传了文件: **{file_name}** ({len(text)} 字符)\n\n文件内容已提取。"
            session.messages.append(AgentMessage(role="system", content=summary))

            # 将文本内容也发送给 Agent（作为上下文）
            truncated = text[:5000]  # 限制长度
            context_msg = f"[上传文件内容片段 - {file_name}]\n\n{truncated}"
            if len(text) > 5000:
                context_msg += f"\n\n...（共 {len(text)} 字符，以上为前 5000 字符）"
            session.messages.append(AgentMessage(role="user",
                content=f"请分析我上传的文件 '{file_name}' 的内容:\n\n{context_msg}"))

            AgentManager.save_session(session)
            return summary
        except Exception as e:
            error_msg = f"❌ 文件处理失败: {str(e)}"
            session.messages.append(AgentMessage(role="system", content=error_msg))
            return error_msg

    # ---- 标题自动生成 ----

    def generate_title(self, session: AgentSession) -> str:
        """使用 LLM 根据对话内容自动生成简洁标题。

        仅在标题为默认值时调用，避免覆盖用户手动设置的标题。
        """
        # 已有人工标题则不覆盖
        if session.title and not session.title.startswith("Conversation "):
            return session.title

        # 收集对话摘要供 LLM 生成标题
        user_msgs = [m for m in session.messages if m.role == "user" and m.content]
        assistant_msgs = [m for m in session.messages if m.role == "assistant" and m.content and not m.options]
        if not user_msgs and not assistant_msgs:
            return session.title

        # 构建摘要上下文（最多取前 3 轮对话 + 工具调用结果）
        context_parts = []
        for m in session.messages[-12:]:  # 最近 12 条消息
            if m.role == "user" and m.content:
                context_parts.append(f"用户: {m.content[:200]}")
            elif m.role == "assistant" and m.content and not m.options:
                context_parts.append(f"助手: {m.content[:200]}")
            elif m.role == "tool" and m.content:
                context_parts.append(f"工具: {m.content[:150]}")

        conversation_snippet = "\n".join(context_parts[-8:])  # 最多取最近8条

        if len(conversation_snippet) < 20:
            # 对话太短，用第一条用户消息的前30字符
            first_msg = user_msgs[0].content[:100].replace("\n", " ")
            title = first_msg[:30]
            if len(first_msg) > 30:
                title += "..."
            session.title = title
            AgentManager.save_session(session)
            return title

        # 调用 LLM 生成标题
        try:
            llm = LLMClient()
            prompt = f"""请根据以下对话内容，生成一个简洁的会话标题（不超过20个字）。
只返回标题文本，不要加引号、标点或其他修饰。

对话内容:
{conversation_snippet}

标题:"""

            messages = [{"role": "user", "content": prompt}]
            title = llm.chat(messages, temperature=0.3, max_tokens=30, thinking_enabled=False).strip()
            # 清理常见的 LLM 多余输出
            title = title.replace('"', '').replace("'", "").replace("标题:", "").replace("标题：", "").strip()
            if not title or len(title) > 40:
                # 回退：取第一条用户消息的前30字符
                first_msg = user_msgs[0].content[:100].replace("\n", " ")
                title = first_msg[:30]

            session.title = title[:40]
            AgentManager.save_session(session)
            logger.info(f"Session [{session.session_id}] 标题已生成: {session.title}")
            return session.title
        except Exception as e:
            logger.warning(f"LLM 标题生成失败，使用回退方案: {e}")
            first_msg = user_msgs[0].content[:100].replace("\n", " ")
            title = first_msg[:30]
            session.title = title
            AgentManager.save_session(session)
            return title
