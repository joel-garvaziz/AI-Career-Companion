
"""Shared M3 LLM helpers using the project's existing OpenRouter configuration."""
from __future__ import annotations
import json, logging, os, re, time
from typing import Any, Dict
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

def llm_config():
    """Return (api_key, base_url, model) for the configured provider, or (None, None, None).

    Gemini (GEMINI_API_KEY) is used when set, otherwise OpenRouter (OPENROUTER_API_KEY).
    Both are reached through the OpenAI-compatible SDK.
    """
    gem=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gem:
        return gem, "https://generativelanguage.googleapis.com/v1beta/openai/", os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    key=os.getenv("OPENROUTER_API_KEY")
    if key:
        return key, "https://openrouter.ai/api/v1", os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    return None, None, None

_blocked_until = 0.0

def llm_available() -> bool:
    """False while the provider is rate-limited/failing, so callers fall back instantly."""
    return time.time() >= _blocked_until

def note_llm_failure(exc: Exception) -> None:
    """Open a short circuit breaker on quota / auth / connectivity errors."""
    global _blocked_until
    text=str(exc)
    if any(t in text for t in ("429", "402", "401", "403", "RESOURCE_EXHAUSTED", "quota", "Connection", "timed out")):
        cooldown=int(os.getenv("LLM_COOLDOWN_SECONDS", "120"))
        _blocked_until=time.time()+cooldown
        logger.warning("LLM provider unavailable; using deterministic fallbacks for %ss", cooldown)

def make_client(key, base):
    return OpenAI(api_key=key, base_url=base, max_retries=0, timeout=float(os.getenv("LLM_TIMEOUT", "25")))

def llm_models():
    """Primary model first, then a backup on the same provider."""
    _, base, model = llm_config()
    if not model:
        return []
    if base and "generativelanguage" in base:
        backup = os.getenv("GEMINI_BACKUP_MODEL", "gemini-flash-latest")
        return [model] + ([backup] if backup != model else [])
    return [model]

def _client():
    key, base, _ = llm_config()
    if not key or not llm_available():
        return None
    return make_client(key, base)

def parse_json(content: Any) -> Dict[str, Any]:
    if isinstance(content, dict):
        return content
    text=str(content or "").strip()
    text=re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text=re.sub(r"\s*```$", "", text)
    start=text.find("{"); end=text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("LLM did not return a JSON object.")
    return json.loads(text[start:end+1])

def call_json(system_prompt: str, user_prompt: str, fallback: Dict[str, Any], temperature: float=0.2) -> Dict[str, Any]:
    client=_client()
    if not client:
        return fallback
    last=None
    for model in llm_models():
        try:
            response=client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "3000")),
                messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
                response_format={"type":"json_object"},
            )
            return parse_json(response.choices[0].message.content)
        except Exception as exc:
            last=exc
            logger.warning("LLM call failed on %s: %s", model, str(exc)[:160])
            if any(t in str(exc) for t in ("429", "401", "402", "403", "quota")):
                break  # backup model would fail the same way
    note_llm_failure(last)
    return fallback
