import os
import json
import logging
import asyncio
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Any, Dict, AsyncGenerator, List, Optional
from functools import lru_cache

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai._exceptions import APIError, APITimeoutError, RateLimitError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    import tiktoken
except ImportError:
    tiktoken = None

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------
# Config
# ------------------------------------------------------

@dataclass(frozen=True)
class ChatConfig:
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")
    fallback_model: str = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-3.5-turbo")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    max_output_tokens: int = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "600"))
    max_prompt_tokens: int = int(os.getenv("OPENAI_MAX_PROMPT_TOKENS", "6000"))
    request_timeout_s: float = float(os.getenv("OPENAI_REQUEST_TIMEOUT_S", "60"))
    system_prompt: str = os.getenv("OPENAI_SYSTEM_PROMPT", (
        "You are a precise document analysis assistant. Extract and present exact information from the context. "
        "Do NOT include page numbers or citations in the answer text. The app will show sources/pages separately."
    ))

_CFG = ChatConfig()

# ------------------------------------------------------
# Encoder
# ------------------------------------------------------

def _get_encoder():
    if not tiktoken:
        return None
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None

_ENCODER = _get_encoder()

def _count_tokens(text: str) -> int:
    if not text:
        return 0
    if _ENCODER:
        try:
            return len(_ENCODER.encode(text))
        except Exception:
            pass
    return len(text) // 4 

def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    if not text or max_tokens <= 0:
        return ""
    if _ENCODER:
        try:
            toks = _ENCODER.encode(text)
            if len(toks) <= max_tokens:
                return text
            return _ENCODER.decode(toks[:max_tokens])
        except Exception:
            pass
    return text[:max_tokens * 4]

# ------------------------------------------------------
# Prompt Construction
# ------------------------------------------------------

def _build_messages(context: str, question: str, hint: str = "") -> List[Dict[str, str]]:
    sys = _CFG.system_prompt
    if hint:
        sys = f"{sys}\n\nDomain hint: {hint}"

    user = f"""ANALYSIS TASK: Extract exact information to answer the question.

CRITICAL INSTRUCTIONS:
1. BE DIRECT: If information exists in the context, present it clearly.
2. NO PAGE NUMBERS: Never write page numbers/citations in the answer text.
3. PRESERVE FORMAT: Keep original formatting of numbers, dates, currencies.
4. BE COMPLETE: Include all relevant information found.
5. NO DISCLAIMERS: Present what exists without apologies.
6. MATHEMATICAL PRECISION: Ensure numerical accuracy in calculations.
7. LIST PROCESSING: When extracting from numbered lists or bullet points:
   - For summary requests, provide concise bullet points with key terms
   - Use asterisks (*) for bullet points in the response
   - Extract the most relevant 3-5 items if many exist
   - Preserve the original German terminology when appropriate


CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""

    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
    ]
    
# ------------------------------------------------------
# Rate Limiting
# ------------------------------------------------------

class RateLimiter:
    def __init__(self, rpm_limit=200):
        self.rpm_limit = rpm_limit
        self.timestamps = []

    async def wait(self):
        now = datetime.now()
        self.timestamps = [t for t in self.timestamps if t > now - timedelta(minutes=1)]
        if len(self.timestamps) >= self.rpm_limit:
            wait_time = (self.timestamps[0] + timedelta(minutes=1)) - now
            await asyncio.sleep(max(0, wait_time.total_seconds()))
        self.timestamps.append(datetime.now())

_limiter = RateLimiter()

# ------------------------------------------------------
# Client
# ------------------------------------------------------

_client: Optional[AsyncOpenAI] = None

def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not _CFG.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        _client = AsyncOpenAI(api_key=_CFG.api_key, timeout=_CFG.request_timeout_s)
        logger.info("AsyncOpenAI client initialized with model: %s", _CFG.model)
    return _client

# ------------------------------------------------------
# Main APIs
# ------------------------------------------------------

async def get_answer_stream_from_openai(context: str, question: str) -> AsyncGenerator[str, None]:
    """Stream answer tokens from OpenAI (WebSocket use)"""
    client = get_openai_client()

    safe_context = _truncate_to_tokens(context, _CFG.max_prompt_tokens - _CFG.max_output_tokens - 400)
    messages = _build_messages(safe_context, question)

    await _limiter.wait()

    try:
        stream = await client.chat.completions.create(
            model=_CFG.model,
            messages=messages,
            temperature=_CFG.temperature,
            max_tokens=_CFG.max_output_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None):
                    yield delta.content
    except Exception as e:
        logger.exception("Streaming failed: %s", e)
        yield "Error: Unable to generate response"

async def get_answer_from_openai(context: str, question: str) -> Dict[str, Any]:
    """Get answer as full string (REST use)"""
    client = get_openai_client()

    safe_context = _truncate_to_tokens(context, _CFG.max_prompt_tokens - _CFG.max_output_tokens - 400)
    messages = _build_messages(safe_context, question)

    for model in [_CFG.model, _CFG.fallback_model]:
        try:
            await _limiter.wait()
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=_CFG.temperature,
                max_tokens=_CFG.max_output_tokens,
            )
            return {
                "text": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "model": model,
            }
        except Exception as e:
            logger.warning("OpenAI call failed with model %s: %s", model, e)

    return {
        "text": "All models failed. Please try again later.",
        "tokens_used": 0,
        "model": None,
    }
