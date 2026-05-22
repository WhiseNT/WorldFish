"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI
from openai.types.chat import ChatCompletion

from ..config import Config
from .logger import get_logger


DEEPSEEK_V4_MODELS = {"deepseek-v4-pro", "deepseek-v4-flash"}
logger = get_logger("mirofish.llm_client")


def is_deepseek_v4_model(model: str) -> bool:
    normalized = (model or "").strip().lower()
    return normalized in DEEPSEEK_V4_MODELS or ("deepseek" in normalized and "v4" in normalized)


class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        role: str = "agent",
    ):
        resolved_config = Config.get_llm_config(role)
        self.role = role
        self.resolved_from = resolved_config.get("resolved_from", role)
        self.api_key = api_key or resolved_config["api_key"]
        self.base_url = base_url or resolved_config["base_url"]
        self.model = model or resolved_config["model_name"]
        
        if not self.api_key:
            raise ValueError("LLM API Key 未配置，请配置 LLM_API_KEY / SUBAGENT_LLM_API_KEY / PARSER_LLM_API_KEY 中至少一个")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    @property
    def is_deepseek_v4(self) -> bool:
        return is_deepseek_v4_model(self.model)

    @property
    def thinking_enabled(self) -> bool:
        if Config.LLM_THINKING_ENABLED is not None:
            return bool(Config.LLM_THINKING_ENABLED)
        return self.is_deepseek_v4

    @property
    def reasoning_effort(self) -> str:
        return Config.LLM_REASONING_EFFORT if Config.LLM_REASONING_EFFORT in {"high", "max"} else "max"

    @property
    def context_window(self) -> int:
        if Config.LLM_CONTEXT_WINDOW > 0:
            return Config.LLM_CONTEXT_WINDOW
        if self.is_deepseek_v4:
            return Config.LLM_DEEPSEEK_V4_CONTEXT_WINDOW
        return Config.LLM_DEFAULT_CONTEXT_WINDOW

    @property
    def default_max_tokens(self) -> int:
        return 8192 if self.is_deepseek_v4 else 4096

    @staticmethod
    def _is_unsupported_thinking_error(exc: Exception) -> bool:
        message = str(exc).lower()
        if "thinking" not in message:
            return False
        patterns = (
            "unexpected keyword argument 'thinking'",
            'unexpected keyword argument "thinking"',
            "unknown parameter: thinking",
            "unsupported parameter: thinking",
            "unsupported argument: thinking",
        )
        return any(pattern in message for pattern in patterns)

    @staticmethod
    def _without_thinking_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
        fallback_kwargs = dict(kwargs)
        fallback_kwargs.pop("thinking", None)
        fallback_kwargs.pop("reasoning_effort", None)

        extra_body = dict(fallback_kwargs.get("extra_body") or {})
        extra_body.pop("thinking", None)
        if extra_body:
            fallback_kwargs["extra_body"] = extra_body
        else:
            fallback_kwargs.pop("extra_body", None)

        messages = fallback_kwargs.get("messages") or []
        if messages:
            sanitized_messages = []
            for message in messages:
                if not isinstance(message, dict):
                    sanitized_messages.append(message)
                    continue
                sanitized = dict(message)
                sanitized.pop("reasoning_content", None)
                sanitized_messages.append(sanitized)
            fallback_kwargs["messages"] = sanitized_messages

        return fallback_kwargs

    def _create_chat_completion_raw(self, **kwargs: Any) -> ChatCompletion:
        payload = dict(kwargs)
        extra_body = dict(payload.pop("extra_body") or {})
        if extra_body:
            payload.update(extra_body)
        return self.client.post(
            "/chat/completions",
            cast_to=ChatCompletion,
            body=payload,
        )

    def create_chat_completion(
        self,
        *,
        thinking_enabled: Optional[bool] = None,
        reasoning_effort: Optional[str] = None,
        **kwargs: Any,
    ):
        """创建聊天补全，并按模型族注入兼容参数。"""
        kwargs.setdefault("model", self.model)
        if self.is_deepseek_v4:
            enabled = self.thinking_enabled if thinking_enabled is None else bool(thinking_enabled)
            if enabled:
                kwargs["reasoning_effort"] = reasoning_effort or self.reasoning_effort
            provider_extra_body = dict(kwargs.get("extra_body") or {})
            provider_extra_body["thinking"] = {"type": "enabled" if enabled else "disabled"}
            kwargs["extra_body"] = provider_extra_body
        create_completion = self._create_chat_completion_raw if self.is_deepseek_v4 else self.client.chat.completions.create
        try:
            return create_completion(**kwargs)
        except Exception as exc:
            if self.is_deepseek_v4 and self._is_unsupported_thinking_error(exc):
                fallback_kwargs = self._without_thinking_kwargs(kwargs)
                if fallback_kwargs != kwargs:
                    logger.warning(
                        "LLM provider rejected thinking parameter for model %s; retrying without it",
                        kwargs.get("model", self.model),
                    )
                    return self._create_chat_completion_raw(**fallback_kwargs)
            raise

    @staticmethod
    def usage_to_dict(usage: Any) -> Dict[str, Any]:
        if usage is None:
            return {}
        if isinstance(usage, dict):
            return dict(usage)
        if hasattr(usage, "model_dump"):
            data = usage.model_dump()
        else:
            data = {
                key: getattr(usage, key)
                for key in (
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "prompt_cache_hit_tokens",
                    "prompt_cache_miss_tokens",
                )
                if hasattr(usage, key)
            }
        model_extra = getattr(usage, "model_extra", None)
        if isinstance(model_extra, dict):
            data.update(model_extra)
        return data

    @classmethod
    def test_connection(
        cls,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = cls(api_key=api_key, base_url=base_url, model=model)
        reply = client.chat(
            messages=[{"role": "user", "content": "Reply with OK only."}],
            temperature=0,
            max_tokens=16,
            thinking_enabled=False,
        )
        return {
            "ok": True,
            "model": client.model,
            "reply": reply.strip(),
        }
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        thinking_enabled: Optional[bool] = None,
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.create_chat_completion(**kwargs, thinking_enabled=thinking_enabled)
        content = response.choices[0].message.content or ""
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        thinking_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            thinking_enabled=thinking_enabled,
        )
        # 清理markdown代码块标记
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned_response}")

