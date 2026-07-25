"""
Conversation Manager
====================
Tracks per-user conversation state:
- Session state (current topic, pending actions)
- Context memory (last N messages)
- Language preference
- Conversation history for report generation
"""

import time
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAX_HISTORY = 50       # Maximum messages stored per user
CONTEXT_WINDOW = 10    # Messages sent to the LLM for context
SESSION_TIMEOUT = 3600  # 1 hour — after this, session resets


@dataclass
class Message:
    """A single conversation message."""
    role: str               # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    lang: str = "sw"
    intent: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserSession:
    """Per-user conversation state."""
    user_id: int
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    state: str = "idle"         # idle, awaiting_photo, awaiting_location, etc.
    pending_action: str = ""     # What we're waiting for from the user
    current_topic: str = ""      # What we're currently discussing
    messages: deque[Message] = field(default_factory=lambda: deque(maxlen=MAX_HISTORY))
    analysis_results: list[dict] = field(default_factory=list)

    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > SESSION_TIMEOUT

    def touch(self) -> None:
        self.last_active = time.time()

    def add(self, message: Message) -> None:
        self.messages.append(message)
        self.touch()

    def get_context(self, n: int = CONTEXT_WINDOW) -> list[Message]:
        """Return the last N messages for LLM context."""
        return list(self.messages)[-n:]

    def get_context_as_dicts(self, n: int = CONTEXT_WINDOW) -> list[dict]:
        """Return context as serializable dicts (for API calls)."""
        return [
            {"role": m.role, "content": m.content}
            for m in self.get_context(n)
        ]


class ConversationManager:
    """
    Manages conversation sessions for all users.

    Thread-safe for the single-threaded async bot.
    Sessions are stored in memory; persist to Redis for production.
    """

    def __init__(self):
        self._sessions: dict[int, UserSession] = {}

    def _get_or_create(self, user_id: int) -> UserSession:
        """Get an existing session or create a new one."""
        session = self._sessions.get(user_id)
        if session is None or session.is_expired():
            if session and session.is_expired():
                logger.info("Session expired for user %s, creating new one", user_id)
            session = UserSession(user_id=user_id)
            self._sessions[user_id] = session
        return session

    def add_message(
        self,
        user_id: int,
        role: str,
        content: str,
        lang: str = "sw",
        intent: str = "general",
        metadata: Optional[dict] = None,
    ) -> None:
        """Add a message to the user's conversation history."""
        session = self._get_or_create(user_id)
        msg = Message(
            role=role,
            content=content,
            lang=lang,
            intent=intent,
            metadata=metadata or {},
        )
        session.add(msg)

    def get_history(self, user_id: int) -> list[dict]:
        """Get full conversation history for a user."""
        session = self._sessions.get(user_id)
        if not session:
            return []
        return [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp,
                "lang": m.lang,
                "intent": m.intent,
                "analysis": m.metadata.get("analysis"),
            }
            for m in session.messages
        ]

    def get_context(self, user_id: int) -> list[dict]:
        """Get recent context for LLM calls."""
        session = self._get_or_create(user_id)
        return session.get_context_as_dicts()

    def set_state(self, user_id: int, state: str, pending: str = "") -> None:
        """Set the session state (e.g., 'awaiting_photo')."""
        session = self._get_or_create(user_id)
        session.state = state
        session.pending_action = pending

    def get_state(self, user_id: int) -> tuple[str, str]:
        """Get (state, pending_action) for a user."""
        session = self._get_or_create(user_id)
        return session.state, session.pending_action

    def set_topic(self, user_id: int, topic: str) -> None:
        """Set the current conversation topic."""
        session = self._get_or_create(user_id)
        session.current_topic = topic

    def get_topic(self, user_id: int) -> str:
        """Get the current conversation topic."""
        session = self._get_or_create(user_id)
        return session.current_topic

    def add_analysis_result(self, user_id: int, result: dict) -> None:
        """Store an analysis result for report generation."""
        session = self._get_or_create(user_id)
        session.analysis_results.append(result)

    def get_analysis_results(self, user_id: int) -> list[dict]:
        """Get all analysis results for a user (for reports)."""
        session = self._sessions.get(user_id)
        if not session:
            return []
        return session.analysis_results

    def clear_session(self, user_id: int) -> None:
        """Clear a user's session (fresh start)."""
        if user_id in self._sessions:
            del self._sessions[user_id]

    def get_active_user_count(self) -> int:
        """Count of non-expired sessions."""
        return sum(
            1 for s in self._sessions.values() if not s.is_expired()
        )

    def get_total_messages(self) -> int:
        """Total messages across all sessions."""
        return sum(len(s.messages) for s in self._sessions.values())

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count removed."""
        expired = [
            uid for uid, session in self._sessions.items()
            if session.is_expired()
        ]
        for uid in expired:
            del self._sessions[uid]
        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))
        return len(expired)
