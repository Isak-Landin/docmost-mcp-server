from pathlib import Path

from ollama.envelope.defaults import get_defaults
from ollama.envelope.tools import get_tools


BASE_DIR = Path(__file__).resolve().parent
SYSTEM_PROMPT_PATH = BASE_DIR / "system" / "system.txt"


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_messages(user_message: str, history: list[dict] | None = None) -> list[dict]:
    messages = [
        {
            "role": "system",
            "content": load_system_prompt(),
        }
    ]

    if history:
        messages.extend(history)

    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    return messages


def build_chat_payload(model: str, user_message: str, history: list[dict] | None = None) -> dict:
    payload = {
        "model": model,
        "messages": build_messages(user_message, history),
        "tools": get_tools(),
    }

    payload.update(get_defaults())
    return payload