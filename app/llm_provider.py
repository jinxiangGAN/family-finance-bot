"""Abstract LLM provider supporting OpenAI-compatible APIs.

Supports: MiniMax, OpenAI, DeepSeek, Qwen, and any OpenAI-compatible endpoint.
Switch providers by changing LLM_PROVIDER, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL in .env.
"""

import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class LLMProvider:
    """Unified LLM interface for chat completion with function calling."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def chat_completion(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> tuple[dict, Optional[dict]]:
        """Call chat completion API. Returns (message, usage).

        Compatible with OpenAI, MiniMax, DeepSeek, Qwen API formats.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()

        data = resp.json()
        logger.debug("LLM response: %s", json.dumps(data, ensure_ascii=False)[:500])

        message = data.get("choices", [{}])[0].get("message", {})
        usage = data.get("usage")
        return message, usage

    async def chat_completion_with_image(
        self,
        text: str,
        image_url: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> tuple[str, Optional[dict]]:
        """Call vision-capable chat completion with an image.

        Returns (content_text, usage).
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()

        data = resp.json()
        logger.debug("LLM vision response: %s", json.dumps(data, ensure_ascii=False)[:500])

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage")
        return content, usage


# ─────────────── Provider presets ───────────────

PROVIDER_PRESETS: dict[str, dict] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "vision_model": "gpt-4o",
    },
    "minimax": {
        "base_url": "https://api.minimax.chat/v1/text",
        "default_model": "abab6.5s-chat",
        "vision_model": "abab6.5s-chat",
        # MiniMax uses a slightly different endpoint
        "chat_endpoint": "chatcompletion_v2",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "vision_model": "deepseek-chat",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "vision_model": "qwen-vl-plus",
    },
    "custom": {
        "base_url": "",
        "default_model": "",
        "vision_model": "",
    },
}


class MiniMaxProvider(LLMProvider):
    """MiniMax-specific provider (slightly different endpoint structure)."""

    async def chat_completion(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> tuple[dict, Optional[dict]]:
        url = f"{self.base_url}/chatcompletion_v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()

        data = resp.json()
        logger.debug("MiniMax response: %s", json.dumps(data, ensure_ascii=False)[:500])

        message = data.get("choices", [{}])[0].get("message", {})
        usage = data.get("usage")
        return message, usage

    async def chat_completion_with_image(
        self,
        text: str,
        image_url: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> tuple[str, Optional[dict]]:
        """MiniMax vision via the same endpoint."""
        url = f"{self.base_url}/chatcompletion_v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        })
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage")
        return content, usage


def create_provider(
    provider_name: str,
    api_key: str,
    model: str = "",
    base_url: str = "",
) -> LLMProvider:
    """Factory function to create an LLM provider."""
    preset = PROVIDER_PRESETS.get(provider_name, PROVIDER_PRESETS["custom"])

    effective_base_url = base_url or preset.get("base_url", "")
    effective_model = model or preset.get("default_model", "")

    if not effective_base_url:
        raise ValueError(f"No base_url configured for provider '{provider_name}'")

    if provider_name == "minimax":
        return MiniMaxProvider(
            api_key=api_key,
            model=effective_model,
            base_url=effective_base_url,
        )

    return LLMProvider(
        api_key=api_key,
        model=effective_model,
        base_url=effective_base_url,
    )
