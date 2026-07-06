import os
import json
import logging
import httpx
from typing import Any

logger = logging.getLogger("sql_assistant.llm")

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_HEADERS: dict[str, str] = {}

_ngrok_header = os.getenv("OLLAMA_HEADER_NAME", "")
_ngrok_value = os.getenv("OLLAMA_HEADER_VALUE", "")
if _ngrok_header and _ngrok_value:
    OLLAMA_HEADERS[_ngrok_header] = _ngrok_value


async def generate(prompt: str, system: str | None = None, temperature: float = 0.1) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }

    logger.info(f"Sending prompt to {OLLAMA_BASE} ({OLLAMA_MODEL})")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE}/api/chat",
            json=payload,
            headers=OLLAMA_HEADERS,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")
        logger.info(f"LLM response: {len(content)} chars")
        return content.strip()


async def generate_json(prompt: str, system: str | None = None, temperature: float = 0.1) -> dict[str, Any]:
    content = await generate(prompt, system, temperature)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content.strip())


async def check_health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{OLLAMA_BASE}/api/tags",
                headers=OLLAMA_HEADERS,
            )
            return response.status_code == 200
    except Exception:
        return False
