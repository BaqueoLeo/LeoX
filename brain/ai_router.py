"""AI Router with fallback: Claude → Gemini → OpenAI.

Tries each provider in order. If one fails (timeout, error, rate limit),
falls through to the next. Logs which model actually responded.
"""

import os
import logging
from dataclasses import dataclass

import anthropic
from google import genai
import openai

logger = logging.getLogger(__name__)

AI_TIMEOUT = int(os.getenv("AI_TIMEOUT_SECONDS", "15"))


@dataclass
class AIResponse:
    text: str
    model: str
    provider: str


# ─── Provider configs ────────────────────────────────────────────

CLAUDE_MODELS = ["claude-sonnet-4-6", "claude-haiku-4-5"]
GEMINI_MODELS = ["gemini-2.0-flash", "gemini-1.5-pro"]
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini"]


# ─── Claude ──────────────────────────────────────────────────────

async def _try_claude(system: str, messages: list[dict]) -> AIResponse | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=AI_TIMEOUT)

    for model in CLAUDE_MODELS:
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=512,
                system=system,
                messages=messages,
            )
            text = response.content[0].text
            logger.info(f"[AI] Claude/{model} respondió")
            return AIResponse(text=text, model=model, provider="claude")
        except Exception as e:
            logger.warning(f"[AI] Claude/{model} falló: {e}")
            continue

    return None


# ─── Gemini ──────────────────────────────────────────────────────

async def _try_gemini(system: str, messages: list[dict]) -> AIResponse | None:
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        return None

    client = genai.Client(api_key=api_key)

    # Convert messages to Gemini format
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(genai.types.Content(
            role=role,
            parts=[genai.types.Part(text=msg["content"])],
        ))

    for model in GEMINI_MODELS:
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=512,
                ),
            )
            text = response.text
            if text:
                logger.info(f"[AI] Gemini/{model} respondió")
                return AIResponse(text=text, model=model, provider="gemini")
        except Exception as e:
            logger.warning(f"[AI] Gemini/{model} falló: {e}")
            continue

    return None


# ─── OpenAI ──────────────────────────────────────────────────────

async def _try_openai(system: str, messages: list[dict]) -> AIResponse | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    client = openai.AsyncOpenAI(api_key=api_key, timeout=AI_TIMEOUT)

    openai_messages = [{"role": "system", "content": system}]
    openai_messages.extend(messages)

    for model in OPENAI_MODELS:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=openai_messages,
                max_tokens=512,
            )
            text = response.choices[0].message.content
            if text:
                logger.info(f"[AI] OpenAI/{model} respondió")
                return AIResponse(text=text, model=model, provider="openai")
        except Exception as e:
            logger.warning(f"[AI] OpenAI/{model} falló: {e}")
            continue

    return None


# ─── Main router ─────────────────────────────────────────────────

async def get_ai_response(system: str, messages: list[dict]) -> AIResponse:
    """Try Claude → Gemini → OpenAI. Returns first successful response."""

    for provider_fn in [_try_claude, _try_gemini, _try_openai]:
        result = await provider_fn(system, messages)
        if result:
            return result

    logger.error("[AI] Todos los proveedores fallaron")
    return AIResponse(
        text="No pude conectar con ningún modelo. Intenta en un momento.",
        model="none",
        provider="fallback",
    )
