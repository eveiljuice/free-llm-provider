from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from bot.config import HISTORY_LIMIT, SYSTEM_PROMPT
from bot.providers.registry import Model, Provider


@dataclass
class UserSession:
    provider_name: str
    model_id: str
    reasoning_enabled: bool = False
    show_reasoning: bool = False
    history: deque[dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=HISTORY_LIMIT)
    )

    def messages(self) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []
        if SYSTEM_PROMPT:
            msgs.append({"role": "system", "content": SYSTEM_PROMPT})
        msgs.append({"role": "system", "content": self._reasoning_instruction()})
        msgs.extend(self.history)
        return msgs

    def _reasoning_instruction(self) -> str:
        if self.reasoning_enabled and self.show_reasoning:
            return (
                "Reasoning mode is enabled. Think carefully when useful. "
                "If the model exposes visible reasoning, you may include it briefly "
                "using <think>...</think> before the final answer."
            )
        if self.reasoning_enabled:
            return (
                "Reasoning mode is enabled. Think carefully when useful, but do not "
                "reveal chain-of-thought, scratchpad text, or <think> blocks. "
                "Return only the final answer."
            )
        return (
            "Reasoning mode is disabled. Prefer direct answers with minimal visible "
            "deliberation. Do not reveal chain-of-thought, scratchpad text, or "
            "<think> blocks."
        )


class Sessions:
    def __init__(self, default_provider: Provider, default_model: Model) -> None:
        self._default_provider = default_provider.name
        self._default_model = default_model.id
        self._by_user: dict[int, UserSession] = {}

    def get(self, user_id: int) -> UserSession:
        s = self._by_user.get(user_id)
        if s is None:
            s = UserSession(
                provider_name=self._default_provider, model_id=self._default_model
            )
            self._by_user[user_id] = s
        return s

    def set_model(self, user_id: int, provider: Provider, model: Model) -> None:
        s = self.get(user_id)
        s.provider_name = provider.name
        s.model_id = model.id

    def set_reasoning(self, user_id: int, enabled: bool) -> None:
        self.get(user_id).reasoning_enabled = enabled

    def set_show_reasoning(self, user_id: int, enabled: bool) -> None:
        self.get(user_id).show_reasoning = enabled

    def reset(self, user_id: int) -> None:
        s = self._by_user.get(user_id)
        if s is not None:
            s.history.clear()
