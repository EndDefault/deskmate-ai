from __future__ import annotations

import json
from urllib import error, request

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig


SYSTEM_PROMPT = (
    "You are DeskMate AI, a concise Korean desktop assistant. "
    "Answer in Korean unless the user asks for another language."
)


def ask_local_model(prompt: str, *, config: AppConfig = DEFAULT_CONFIG) -> str | None:
    payload = {
        "model": config.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "keep_alive": config.ollama_keep_alive,
        "options": {
            "num_predict": config.ollama_max_tokens,
            "temperature": 0.4,
        },
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{config.ollama_base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=config.ollama_timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, error.URLError, json.JSONDecodeError):
        return None

    message = body.get("message", {})
    content = message.get("content")
    if not isinstance(content, str):
        return None

    return content.strip() or None
