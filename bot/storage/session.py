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
    history: deque[dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=HISTORY_LIMIT)
    )

    def messages(self) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []
        if SYSTEM_PROMPT:
            msgs.append({"role": "system", "content": SYSTEM_PROMPT})
        msgs.extend(self.history)
        return msgs


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

    def reset(self, user_id: int) -> None:
        s = self._by_user.get(user_id)
        if s is not None:
            s.history.clear()
