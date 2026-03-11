"""
APEX — Unified AI Client
One interface for all 6 AI models: GPT-4o, Claude, Gemini, DeepSeek, Grok, Qwen
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, List   # ALL typing imports at the top

from loguru import logger
import openai
import anthropic

# Google Gemini — try new SDK first, fall back to deprecated one
try:
    from google import genai as _google_genai
    _GENAI_NEW = True
except ImportError:
    try:
        import google.generativeai as _google_genai   # type: ignore
        _GENAI_NEW = False
    except ImportError:
        _google_genai = None
        _GENAI_NEW = False

from config.settings import settings


# ─────────────────────────────────────────────
# Response Dataclass
# ─────────────────────────────────────────────

@dataclass
class AIResponse:
    model: str
    content: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


# ─────────────────────────────────────────────
# Base AI Client
# ─────────────────────────────────────────────

class BaseAIClient(ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    async def complete(self, system: str, user: str) -> AIResponse:
        pass

    async def safe_complete(self, system: str, user: str) -> AIResponse:
        import time
        for attempt in range(settings.ai.max_retries):
            try:
                start = time.time()
                response = await self.complete(system, user)
                response.latency_ms = (time.time() - start) * 1000
                return response
            except Exception as e:
                logger.warning(f"{self.model_name} attempt {attempt + 1} failed: {e}")
                if attempt == settings.ai.max_retries - 1:
                    return AIResponse(model=self.model_name, content="", error=str(e))
                await asyncio.sleep(2 ** attempt)
        return AIResponse(model=self.model_name, content="", error="Max retries exceeded")


# ─────────────────────────────────────────────
# GPT-4o
# ─────────────────────────────────────────────

class GPT4oClient(BaseAIClient):
    def __init__(self):
        super().__init__("gpt4o")
        self.client = openai.AsyncOpenAI(api_key=settings.ai.openai_api_key)

    async def complete(self, system: str, user: str) -> AIResponse:
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=settings.ai.temperature,
            timeout=settings.ai.request_timeout,
        )
        return AIResponse(
            model=self.model_name,
            content=response.choices[0].message.content or "",
            tokens_used=response.usage.total_tokens if response.usage else 0,
        )


# ─────────────────────────────────────────────
# Claude
# ─────────────────────────────────────────────

class ClaudeClient(BaseAIClient):
    def __init__(self):
        super().__init__("claude")
        self.client = anthropic.AsyncAnthropic(api_key=settings.ai.anthropic_api_key)

    async def complete(self, system: str, user: str) -> AIResponse:
        response = await self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=settings.ai.temperature,
        )
        return AIResponse(
            model=self.model_name,
            content=response.content[0].text,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )


# ─────────────────────────────────────────────
# Gemini — supports both old and new SDK
# ─────────────────────────────────────────────

class GeminiClient(BaseAIClient):
    def __init__(self):
        super().__init__("gemini")
        if _google_genai is None:
            raise ImportError("Install Google Gemini SDK: pip install google-genai")
        if _GENAI_NEW:
            self._client = _google_genai.Client(api_key=settings.ai.google_api_key)
        else:
            _google_genai.configure(api_key=settings.ai.google_api_key)
            self._model = _google_genai.GenerativeModel(
                model_name="gemini-1.5-pro",
                generation_config={"temperature": settings.ai.temperature},
            )

    async def complete(self, system: str, user: str) -> AIResponse:
        prompt = f"{system}\n\n{user}"
        if _GENAI_NEW:
            response = await self._client.aio.models.generate_content(
                model="gemini-2.0-flash", contents=prompt,
            )
            text = response.text
        else:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._model.generate_content(prompt)
            )
            text = response.text
        return AIResponse(model=self.model_name, content=text)


# ─────────────────────────────────────────────
# DeepSeek  (OpenAI-compatible)
# ─────────────────────────────────────────────

class DeepSeekClient(BaseAIClient):
    def __init__(self):
        super().__init__("deepseek")
        self.client = openai.AsyncOpenAI(
            api_key=settings.ai.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )

    async def complete(self, system: str, user: str) -> AIResponse:
        response = await self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=settings.ai.temperature,
            timeout=settings.ai.request_timeout,
        )
        return AIResponse(
            model=self.model_name,
            content=response.choices[0].message.content or "",
            tokens_used=response.usage.total_tokens if response.usage else 0,
        )


# ─────────────────────────────────────────────
# Grok  (OpenAI-compatible)
# ─────────────────────────────────────────────

class GrokClient(BaseAIClient):
    def __init__(self):
        super().__init__("grok")
        self.client = openai.AsyncOpenAI(
            api_key=settings.ai.grok_api_key,
            base_url="https://api.x.ai/v1",
        )

    async def complete(self, system: str, user: str) -> AIResponse:
        response = await self.client.chat.completions.create(
            model="grok-2-latest",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=settings.ai.temperature,
            timeout=settings.ai.request_timeout,
        )
        return AIResponse(
            model=self.model_name,
            content=response.choices[0].message.content or "",
            tokens_used=response.usage.total_tokens if response.usage else 0,
        )


# ─────────────────────────────────────────────
# Qwen  (OpenAI-compatible via DashScope)
# ─────────────────────────────────────────────

class QwenClient(BaseAIClient):
    def __init__(self):
        super().__init__("qwen")
        self.client = openai.AsyncOpenAI(
            api_key=settings.ai.qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    async def complete(self, system: str, user: str) -> AIResponse:
        response = await self.client.chat.completions.create(
            model="qwen-max",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=settings.ai.temperature,
            timeout=settings.ai.request_timeout,
        )
        return AIResponse(
            model=self.model_name,
            content=response.choices[0].message.content or "",
            tokens_used=response.usage.total_tokens if response.usage else 0,
        )


# ─────────────────────────────────────────────
# AI Manager
# ─────────────────────────────────────────────

class AIManager:
    MODEL_DISPLAY_NAMES: Dict[str, str] = {
        "gpt4o":    "GPT-4o (OpenAI)",
        "claude":   "Claude 3.5 (Anthropic)",
        "gemini":   "Gemini 2.0 (Google)",
        "deepseek": "DeepSeek-V3",
        "grok":     "Grok-2 (xAI)",
        "qwen":     "Qwen-Max (Alibaba)",
    }

    def __init__(self):
        self.clients: Dict[str, BaseAIClient] = {}
        self._initialize_clients()

    def _initialize_clients(self) -> None:
        configs = [
            ("gpt4o",    GPT4oClient,    settings.ai.openai_api_key),
            ("claude",   ClaudeClient,   settings.ai.anthropic_api_key),
            ("gemini",   GeminiClient,   settings.ai.google_api_key),
            ("deepseek", DeepSeekClient, settings.ai.deepseek_api_key),
            ("grok",     GrokClient,     settings.ai.grok_api_key),
            ("qwen",     QwenClient,     settings.ai.qwen_api_key),
        ]
        for name, client_class, api_key in configs:
            if not api_key:
                logger.info(f"Skipping {name} (no API key in .env)")
                continue
            try:
                self.clients[name] = client_class()
                logger.info(f"✅ AI client ready: {name}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to init {name}: {e}")

        if not self.clients:
            logger.warning("No AI clients initialized — add at least one API key to .env")
        else:
            logger.info(f"AI Manager: {len(self.clients)} models active: {list(self.clients.keys())}")

    async def ask(self, model: str, system: str, user: str) -> AIResponse:
        if model not in self.clients:
            return AIResponse(model=model, content="", error=f"Model '{model}' not configured")
        return await self.clients[model].safe_complete(system, user)

    async def ask_all(self, system: str, user: str) -> Dict[str, AIResponse]:
        tasks = {name: client.safe_complete(system, user) for name, client in self.clients.items()}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return {
            name: result if isinstance(result, AIResponse)
                  else AIResponse(model=name, content="", error=str(result))
            for name, result in zip(tasks.keys(), results)
        }

    async def ask_default(self, system: str, user: str) -> AIResponse:
        return await self.ask(settings.ai.default_model, system, user)

    def available_models(self) -> List[str]:
        return list(self.clients.keys())

    def get_display_name(self, model: str) -> str:
        return self.MODEL_DISPLAY_NAMES.get(model, model)


# ─────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────

_manager: Optional[AIManager] = None


def get_ai_manager() -> AIManager:
    global _manager
    if _manager is None:
        _manager = AIManager()
    return _manager
