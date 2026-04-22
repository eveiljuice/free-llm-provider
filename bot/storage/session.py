from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bot.config import HISTORY_LIMIT, MEMORY_ROOT, SYSTEM_PROMPT
from bot.providers.registry import Model, Provider


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _now_human() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _short_text(value: Any, limit: int = 280) -> str:
    if isinstance(value, str):
        text = value.strip()
    else:
        text = json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text[: limit - 1] + "…" if len(text) > limit else text


@dataclass
class UserSession:
    user_id: int
    memory_dir: Path
    provider_name: str
    model_id: str
    reasoning_enabled: bool = False
    show_reasoning: bool = False
    history: deque[dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=HISTORY_LIMIT)
    )

    @property
    def prd_path(self) -> Path:
        return self.memory_dir / "prd.json"

    @property
    def progress_path(self) -> Path:
        return self.memory_dir / "progress.txt"

    @property
    def agents_path(self) -> Path:
        return self.memory_dir / "AGENTS.md"

    @property
    def history_path(self) -> Path:
        return self.memory_dir / "history.jsonl"

    def messages(self) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []
        if SYSTEM_PROMPT:
            msgs.append({"role": "system", "content": SYSTEM_PROMPT})
        msgs.append({"role": "system", "content": self._reasoning_instruction()})
        distilled = self.distilled_memory()
        if distilled:
            msgs.append(
                {
                    "role": "system",
                    "content": (
                        "Durable user memory from AGENTS.md. "
                        "Treat these as stable user preferences/instructions.\n\n"
                        f"{distilled}"
                    ),
                }
            )
        msgs.extend(self.history)
        return msgs

    def distilled_memory(self) -> str:
        if not self.agents_path.exists():
            return ""
        text = self.agents_path.read_text(encoding="utf-8").strip()
        lines = [
            line.rstrip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        useful = [
            line
            for line in lines
            if "Add stable user preferences" not in line
            and "Use /remember" not in line
        ]
        return "\n".join(useful).strip()

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
        self._base_dir = MEMORY_ROOT
        self._by_user: dict[int, UserSession] = {}

    def get(self, user_id: int) -> UserSession:
        s = self._by_user.get(user_id)
        if s is None:
            s = self._load(user_id)
            self._by_user[user_id] = s
        return s

    def add_user_turn(
        self, user_id: int, content: Any, *, persist_content: Any | None = None
    ) -> None:
        s = self.get(user_id)
        s.history.append({"role": "user", "content": content})
        stored = content if persist_content is None else persist_content
        self._append_history_record(s, role="user", content=stored)
        self._append_progress(
            s,
            "USER TURN",
            [
                f"Provider/model: {s.provider_name} / {s.model_id}",
                f"Summary: {_short_text(stored)}",
            ],
        )
        self._save_state(s)

    def add_assistant_turn(self, user_id: int, content: str) -> None:
        s = self.get(user_id)
        s.history.append({"role": "assistant", "content": content})
        self._append_history_record(s, role="assistant", content=content)
        self._append_progress(
            s,
            "ASSISTANT TURN",
            [
                f"Provider/model: {s.provider_name} / {s.model_id}",
                f"Summary: {_short_text(content)}",
            ],
        )
        self._save_state(s)

    def rollback_user_turn(self, user_id: int) -> None:
        s = self.get(user_id)
        try:
            if s.history and s.history[-1].get("role") == "user":
                s.history.pop()
        except IndexError:
            pass

    def set_model(self, user_id: int, provider: Provider, model: Model) -> None:
        s = self.get(user_id)
        s.provider_name = provider.name
        s.model_id = model.id
        self._save_state(s)
        self._append_progress(
            s,
            "MODEL SWITCH",
            [f"Selected: {provider.name} / {model.id}"],
        )

    def set_reasoning(self, user_id: int, enabled: bool) -> None:
        s = self.get(user_id)
        s.reasoning_enabled = enabled
        self._save_state(s)
        self._append_progress(
            s,
            "REASONING TOGGLE",
            [f"reasoning_enabled = {enabled}"],
        )

    def set_show_reasoning(self, user_id: int, enabled: bool) -> None:
        s = self.get(user_id)
        s.show_reasoning = enabled
        self._save_state(s)
        self._append_progress(
            s,
            "SHOW REASONING TOGGLE",
            [f"show_reasoning = {enabled}"],
        )

    def remember(self, user_id: int, note: str) -> bool:
        s = self.get(user_id)
        normalized = note.strip()
        if not normalized:
            return False

        existing = s.agents_path.read_text(encoding="utf-8")
        bullet = f"- {normalized}"
        if bullet in existing:
            return False

        with s.agents_path.open("a", encoding="utf-8") as f:
            if not existing.endswith("\n"):
                f.write("\n")
            f.write(f"{bullet}\n")

        self._append_progress(
            s,
            "DISTILLED MEMORY UPDATE",
            [f"Added to AGENTS.md: {normalized}"],
        )
        return True

    def memory_snapshot(self, user_id: int) -> str:
        s = self.get(user_id)
        distilled = s.distilled_memory() or "(empty)"
        return (
            f"🧠 Durable memory for user `{user_id}`\n\n"
            f"Provider/model: {s.provider_name} / {s.model_id}\n"
            f"Reasoning: {'ON' if s.reasoning_enabled else 'OFF'}\n"
            f"Show thoughts: {'ON' if s.show_reasoning else 'OFF'}\n"
            f"History in context: {len(s.history)} messages\n"
            f"Memory dir: `{s.memory_dir}`\n\n"
            f"AGENTS.md\n{distilled}"
        )

    def reset(self, user_id: int) -> None:
        s = self.get(user_id)
        s.history.clear()
        with s.history_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {"type": "reset", "ts": _now_iso(), "reason": "user_requested"},
                    ensure_ascii=False,
                )
                + "\n"
            )
        self._append_progress(
            s,
            "RESET",
            ["Conversation context cleared for future runs."],
        )
        self._save_state(s)

    def _load(self, user_id: int) -> UserSession:
        memory_dir = self._base_dir / str(user_id)
        memory_dir.mkdir(parents=True, exist_ok=True)

        if not (memory_dir / "AGENTS.md").exists():
            (memory_dir / "AGENTS.md").write_text(
                "# Durable User Memory\n\n"
                "Stable preferences and instructions for this user.\n"
                "Use /remember <note> to add distilled memory entries.\n",
                encoding="utf-8",
            )

        if not (memory_dir / "progress.txt").exists():
            (memory_dir / "progress.txt").write_text(
                "# Progress Log\n"
                f"Started: {_now_human()}\n"
                "---\n\n"
                "## User Patterns\n"
                "- Stable user preferences belong in AGENTS.md\n"
                "- This file is append-only raw memory\n"
                "---\n",
                encoding="utf-8",
            )

        if not (memory_dir / "history.jsonl").exists():
            (memory_dir / "history.jsonl").write_text("", encoding="utf-8")

        state = {
            "project": "freegpt-telegram-bot",
            "description": "Ralph-style durable session memory for one Telegram user",
            "userId": user_id,
            "sessionState": {
                "providerName": self._default_provider,
                "modelId": self._default_model,
                "reasoningEnabled": False,
                "showReasoning": False,
                "lastActiveAt": _now_iso(),
            },
        }
        prd_path = memory_dir / "prd.json"
        if prd_path.exists():
            try:
                state = json.loads(prd_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        else:
            prd_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        session_state = state.get("sessionState", {})
        session = UserSession(
            user_id=user_id,
            memory_dir=memory_dir,
            provider_name=session_state.get("providerName", self._default_provider),
            model_id=session_state.get("modelId", self._default_model),
            reasoning_enabled=bool(session_state.get("reasoningEnabled", False)),
            show_reasoning=bool(session_state.get("showReasoning", False)),
        )

        history = deque(maxlen=HISTORY_LIMIT)
        try:
            for line in session.history_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("type") == "reset":
                    history.clear()
                    continue
                if row.get("type") != "message":
                    continue
                role = row.get("role")
                if role not in {"user", "assistant"}:
                    continue
                history.append({"role": role, "content": row.get("content", "")})
        except json.JSONDecodeError:
            history.clear()
        session.history = history
        self._save_state(session)
        return session

    def _save_state(self, session: UserSession) -> None:
        data = {
            "project": "freegpt-telegram-bot",
            "description": "Ralph-style durable session memory for one Telegram user",
            "userId": session.user_id,
            "sessionState": {
                "providerName": session.provider_name,
                "modelId": session.model_id,
                "reasoningEnabled": session.reasoning_enabled,
                "showReasoning": session.show_reasoning,
                "historyLength": len(session.history),
                "lastActiveAt": _now_iso(),
            },
        }
        session.prd_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _append_history_record(self, session: UserSession, *, role: str, content: Any) -> None:
        payload = {
            "type": "message",
            "ts": _now_iso(),
            "role": role,
            "content": content,
        }
        with session.history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _append_progress(
        self, session: UserSession, title: str, details: list[str] | None = None
    ) -> None:
        lines = [f"## {_now_human()} - {title}"]
        for detail in details or []:
            lines.append(f"- {detail}")
        lines.append("---")
        with session.progress_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
