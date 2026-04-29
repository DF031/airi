from typing import Dict, List

from backend.core.schemas import ChatMessage


def build_sliding_window_memory(chat_history: List[ChatMessage], max_turns: int = 3) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    recent = chat_history[-(max_turns * 2):]
    for item in recent:
        content = item.content.strip()
        if not content:
            continue
        role = "assistant" if item.role in {"ai", "assistant"} else "user"
        messages.append({"role": role, "content": content})
    return messages

