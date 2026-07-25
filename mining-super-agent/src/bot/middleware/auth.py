"""
Authentication Middleware
=========================
Tracks Telegram users, enforces rate limits, and provides admin access
for Valentine.

Security model:
- Every Telegram user is auto-registered on first message
- Rate limiting: 30 messages/minute per user (generous for conversation)
- Admin: Valentine's Telegram user ID gets elevated access
"""

import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Rate limiting constants
RATE_LIMIT_WINDOW = 60       # seconds
RATE_LIMIT_MAX_MESSAGES = 30  # messages per window
ADMIN_RATE_LIMIT = 100       # admin gets a higher limit


@dataclass
class UserProfile:
    """A registered Telegram user."""
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    language_code: str = "sw"
    is_admin: bool = False
    is_banned: bool = False
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    message_count: int = 0


class AuthMiddleware:
    """
    User tracking and rate limiting.

    Not true authentication (Telegram handles that), but provides:
    - User registration and profile tracking
    - Per-user rate limiting
    - Admin access control
    """

    def __init__(self, admin_user_id: int = 0):
        self._users: dict[int, UserProfile] = {}
        self._rate_limits: dict[int, list[float]] = defaultdict(list)
        self._admin_user_id = admin_user_id

        if admin_user_id:
            logger.info("Admin user ID set: %s", admin_user_id)

    def register_user(self, user) -> UserProfile:
        """Register or update a Telegram user."""
        user_id = user.id

        if user_id not in self._users:
            profile = UserProfile(
                user_id=user_id,
                username=user.username or "",
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                language_code=user.language_code or "sw",
                is_admin=(user_id == self._admin_user_id),
            )
            self._users[user_id] = profile
            logger.info(
                "New user registered: %s (%s) [%s]",
                profile.first_name, user_id, "ADMIN" if profile.is_admin else "USER",
            )
        else:
            profile = self._users[user_id]
            profile.last_seen = time.time()
            profile.message_count += 1
            # Update mutable fields
            profile.username = user.username or profile.username
            profile.first_name = user.first_name or profile.first_name

        return self._users[user_id]

    def get_user(self, user_id: int) -> Optional[UserProfile]:
        """Get a user profile by ID."""
        return self._users.get(user_id)

    def is_admin(self, user_id: int) -> bool:
        """Check if a user is the admin (Valentine)."""
        if user_id == self._admin_user_id:
            return True
        profile = self._users.get(user_id)
        return profile.is_admin if profile else False

    def is_banned(self, user_id: int) -> bool:
        """Check if a user is banned."""
        profile = self._users.get(user_id)
        return profile.is_banned if profile else False

    def ban_user(self, user_id: int) -> None:
        """Ban a user (admin action)."""
        profile = self._users.get(user_id)
        if profile:
            profile.is_banned = True
            logger.info("User %s banned by admin", user_id)

    def unban_user(self, user_id: int) -> None:
        """Unban a user (admin action)."""
        profile = self._users.get(user_id)
        if profile:
            profile.is_banned = False
            logger.info("User %s unbanned by admin", user_id)

    def get_stats(self) -> dict:
        """Get system statistics (for admin dashboard)."""
        active_threshold = time.time() - 3600  # 1 hour
        active_users = sum(
            1 for u in self._users.values()
            if u.last_seen > active_threshold
        )
        return {
            "total_users": len(self._users),
            "active_users": active_users,
            "total_messages": sum(u.message_count for u in self._users.values()),
        }


def rate_limit_check(user_id: int, middleware: Optional['AuthMiddleware'] = None) -> bool:
    """
    Check if a user has exceeded the rate limit.

    This is a module-level convenience function. In production,
    the AuthMiddleware instance would be used directly.

    Returns True if the request is allowed, False if rate-limited.
    """
    # For the module-level function, we use a module-level store
    if not hasattr(rate_limit_check, '_store'):
        rate_limit_check._store: dict[int, list[float]] = defaultdict(list)

    store = rate_limit_check._store
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries
    store[user_id] = [t for t in store[user_id] if t > window_start]

    # Check limit
    limit = ADMIN_RATE_LIMIT if (middleware and middleware.is_admin(user_id)) else RATE_LIMIT_MAX_MESSAGES

    if len(store[user_id]) >= limit:
        logger.warning("Rate limit hit for user %s (%d messages in %ds)", user_id, len(store[user_id]), RATE_LIMIT_WINDOW)
        return False

    store[user_id].append(now)
    return True
