import os

import requests

from ollama.builder import build_chat_payload


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "seamon67/Ministral-3-Reasoning:14b")


def call_ollama(user_message: str, history: list[dict] | None = None) -> dict:
    payload = build_chat_payload(
        model=OLLAMA_MODEL,
        user_message=user_message,
        history=history,
    )

    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=300,
    )

    if not r.ok:
        print("OLLAMA STATUS:", r.status_code, flush=True)
        print("OLLAMA BODY:", r.text, flush=True)
        r.raise_for_status()

    return r.json()


def parse_model_output(data: dict) -> dict:
    message = data.get("message", {}) or {}

    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        tool_call = tool_calls[0] or {}
        function_data = tool_call.get("function", {}) or {}

        return {
            "action": "tool",
            "tool_name": function_data.get("name", ""),
            "arguments": function_data.get("arguments", {}) or {},
            "raw_message": message,
            "thinking": message.get("thinking", ""),
        }

    return {
        "action": "final",
        "answer": message.get("content", "") or "",
        "raw_message": message,
        "thinking": message.get("thinking", ""),
    }