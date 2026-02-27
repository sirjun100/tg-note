"""
Async LLM Provider Abstraction Layer.

Each provider implements `generate_response` as an async method
using httpx instead of blocking requests.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from src.constants import LLM_DEFAULT_MAX_TOKENS, LLM_DEFAULT_TEMPERATURE, LLM_REQUEST_TIMEOUT
from src.exceptions import LLMError, LLMProviderUnavailable
from src.settings import get_settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or self.get_default_model()

    @abstractmethod
    def get_default_model(self) -> str: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    async def generate_response(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> Dict[str, Any]: ...


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider (uses the openai SDK which handles its own async)."""

    def __init__(self, api_key: str | None = None, model_name: str = "gpt-4"):
        self._api_key = api_key
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=api_key)
        except ImportError:
            logger.error("OpenAI package not installed")
            self.client = None
        super().__init__(model_name)

    def get_default_model(self) -> str:
        return "gpt-4"

    def is_available(self) -> bool:
        return self.client is not None

    async def generate_response(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise LLMProviderUnavailable("OpenAI provider not available")

        tools = kwargs.get("functions", [])
        tool_choice = kwargs.get("function_call")

        if tools and not isinstance(tools[0], dict):
            tools = [{"type": "function", "function": func} for func in tools]
            if isinstance(tool_choice, str):
                tool_choice = {"type": "function", "function": {"name": tool_choice}}
            elif isinstance(tool_choice, dict):
                tool_choice = {"type": "function", "function": tool_choice}

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=tools or None,
            tool_choice=tool_choice,
            temperature=kwargs.get("temperature", LLM_DEFAULT_TEMPERATURE),
            max_tokens=kwargs.get("max_tokens", LLM_DEFAULT_MAX_TOKENS),
        )

        function_call = None
        if response.choices[0].message.tool_calls:
            tc = response.choices[0].message.tool_calls[0]
            function_call = {"name": tc.function.name, "arguments": tc.function.arguments}

        return {
            "content": response.choices[0].message.content,
            "function_call": function_call,
            "usage": response.usage,
            "raw_response": response,
        }


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider — uses httpx for async HTTP."""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama2"):
        self.base_url = base_url.rstrip("/")
        super().__init__(model_name)

    def get_default_model(self) -> str:
        return "llama3.2:3b"

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5) as c:
                resp = c.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def generate_response(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> Dict[str, Any]:
        prompt_parts = []
        for msg in messages:
            role, content = msg["role"], msg["content"]
            if role == "system":
                prompt_parts.insert(0, f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": "\n\n".join(prompt_parts),
            "stream": False,
        }
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["num_predict"] = kwargs["max_tokens"]

        async with httpx.AsyncClient(timeout=LLM_REQUEST_TIMEOUT) as client:
            try:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMError(f"Ollama API error: {exc}") from exc

        result = resp.json()
        return {
            "content": result["response"],
            "function_call": None,
            "usage": {
                "prompt_tokens": result.get("prompt_eval_count"),
                "completion_tokens": result.get("eval_count"),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            },
            "raw_response": result,
        }


class DeepSeekProvider(LLMProvider):
    """DeepSeek LLM provider — uses httpx for async HTTP."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.deepseek.com",
        model_name: str = "deepseek-chat",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        super().__init__(model_name)

    def get_default_model(self) -> str:
        return "deepseek-chat"

    def is_available(self) -> bool:
        return self.api_key is not None

    async def generate_response(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise LLMProviderUnavailable("DeepSeek API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", LLM_DEFAULT_TEMPERATURE),
            "max_tokens": kwargs.get("max_tokens", LLM_DEFAULT_MAX_TOKENS),
        }
        if "functions" in kwargs:
            payload["functions"] = kwargs["functions"]
        if "function_call" in kwargs:
            payload["function_call"] = kwargs["function_call"]

        async with httpx.AsyncClient(timeout=LLM_REQUEST_TIMEOUT) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMError(f"DeepSeek API error: {exc}") from exc

        result = resp.json()
        return {
            "content": result["choices"][0]["message"].get("content"),
            "function_call": result["choices"][0]["message"].get("function_call"),
            "usage": result.get("usage"),
            "raw_response": result,
        }


class LLMProviderRegistry:
    """Registry for LLM providers — built from settings."""

    def __init__(self) -> None:
        self.providers: Dict[str, LLMProvider] = {}
        self._register_builtin()

    def _register_builtin(self) -> None:
        cfg = get_settings().llm

        if cfg.openai_api_key:
            self.providers["openai"] = OpenAIProvider(api_key=cfg.openai_api_key)

        self.providers["ollama"] = OllamaProvider(
            base_url=cfg.ollama_base_url, model_name=cfg.ollama_model
        )

        if cfg.deepseek_api_key:
            self.providers["deepseek"] = DeepSeekProvider(
                api_key=cfg.deepseek_api_key, model_name=cfg.deepseek_model
            )

    def get_provider(self, name: str) -> LLMProvider | None:
        return self.providers.get(name)

    def get_available_providers(self) -> Dict[str, LLMProvider]:
        return {n: p for n, p in self.providers.items() if p.is_available()}

    def list_providers(self) -> List[str]:
        return list(self.providers.keys())


_registry: LLMProviderRegistry | None = None


def get_registry() -> LLMProviderRegistry:
    global _registry
    if _registry is None:
        _registry = LLMProviderRegistry()
    return _registry
