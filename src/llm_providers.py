"""
LLM Provider Abstraction Layer
Supports multiple LLM providers with a unified interface.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or self.get_default_model()

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the default model name for this provider"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available and configured"""
        pass

    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Generate a response from the LLM

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional provider-specific parameters

        Returns:
            Dict containing response data
        """
        pass

    def prepare_messages_for_function_calling(self, messages: List[Dict[str, str]],
                                            function_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare messages and function schema for function calling

        Args:
            messages: Conversation messages
            function_schema: Function schema for structured output

        Returns:
            Prepared data for the provider
        """
        return {
            "messages": messages,
            "function_schema": function_schema
        }

class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""

    def __init__(self, api_key: str = None, model_name: str = "gpt-4"):
        try:
            import openai
            self.openai = openai
            self.openai.api_key = api_key
        except ImportError:
            logger.error("OpenAI package not installed")
            self.openai = None

        super().__init__(model_name)

    def get_default_model(self) -> str:
        return "gpt-4"

    def is_available(self) -> bool:
        return self.openai is not None and self.openai.api_key is not None

    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("OpenAI provider not available")

        functions = kwargs.get("functions", [])
        function_call = kwargs.get("function_call", None)

        response = self.openai.ChatCompletion.create(
            model=self.model_name,
            messages=messages,
            functions=functions if functions else None,
            function_call=function_call,
            temperature=kwargs.get("temperature", 0.3),
            max_tokens=kwargs.get("max_tokens", 1000)
        )

        return {
            "content": response.choices[0].message.content,
            "function_call": response.choices[0].message.get("function_call"),
            "usage": response.usage,
            "raw_response": response
        }

class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama2"):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name

    def get_default_model(self) -> str:
        return "llama2"

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        # Convert OpenAI format to Ollama format
        ollama_messages = []
        system_message = None

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_message = content
            elif role == "user":
                ollama_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                ollama_messages.append({"role": "assistant", "content": content})

        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": False
        }

        if system_message:
            payload["system"] = system_message

        # Add optional parameters
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

            return {
                "content": result["message"]["content"],
                "function_call": None,  # Ollama doesn't support function calling natively
                "usage": getattr(result, 'usage', None),
                "raw_response": result
            }

        except requests.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise RuntimeError(f"Ollama API error: {e}")

class DeepSeekProvider(LLMProvider):
    """DeepSeek LLM provider"""

    def __init__(self, api_key: str = None, base_url: str = "https://api.deepseek.com",
                 model_name: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name

    def get_default_model(self) -> str:
        return "deepseek-chat"

    def is_available(self) -> bool:
        return self.api_key is not None

    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("DeepSeek provider not available - API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }

        # Add function calling support if provided
        if "functions" in kwargs:
            payload["functions"] = kwargs["functions"]
        if "function_call" in kwargs:
            payload["function_call"] = kwargs["function_call"]

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

            return {
                "content": result["choices"][0]["message"].get("content"),
                "function_call": result["choices"][0]["message"].get("function_call"),
                "usage": result.get("usage"),
                "raw_response": result
            }

        except requests.RequestException as e:
            logger.error(f"DeepSeek API error: {e}")
            raise RuntimeError(f"DeepSeek API error: {e}")

class LLMProviderRegistry:
    """Registry for LLM providers"""

    def __init__(self):
        self.providers = {}
        self.register_builtin_providers()

    def register_builtin_providers(self):
        """Register built-in providers"""
        from config import OPENAI_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_MODEL

        # OpenAI
        if OPENAI_API_KEY:
            self.providers["openai"] = OpenAIProvider(api_key=OPENAI_API_KEY)

        # Ollama
        ollama_url = OLLAMA_BASE_URL or "http://localhost:11434"
        ollama_model = OLLAMA_MODEL or "llama2"
        self.providers["ollama"] = OllamaProvider(base_url=ollama_url, model_name=ollama_model)

        # DeepSeek
        if DEEPSEEK_API_KEY:
            deepseek_model = DEEPSEEK_MODEL or "deepseek-chat"
            self.providers["deepseek"] = DeepSeekProvider(api_key=DEEPSEEK_API_KEY, model_name=deepseek_model)

    def register_provider(self, name: str, provider: LLMProvider):
        """Register a custom provider"""
        self.providers[name] = provider

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """Get a provider by name"""
        return self.providers.get(name)

    def get_available_providers(self) -> Dict[str, LLMProvider]:
        """Get all available (configured) providers"""
        return {name: provider for name, provider in self.providers.items() if provider.is_available()}

    def list_providers(self) -> List[str]:
        """List all registered provider names"""
        return list(self.providers.keys())

# Global registry instance
registry = LLMProviderRegistry()