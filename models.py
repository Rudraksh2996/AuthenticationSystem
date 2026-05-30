q

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ─────────────────────────────────────────────────────────
# USER ENTITY  (Data / Model Layer)
# ─────────────────────────────────────────────────────────

@dataclass
class User:
    """
    Represents a single registered user in the system.

    Fields are kept as plain types (str, int, bool) so the object serialises
    cleanly to/from JSON without any custom encoder.

    Security fields:
        password_hash — the PBKDF2-SHA256 digest (never the raw password)
        salt          — the unique random salt used when hashing this user's password

    Audit fields:
        created_at    — ISO-8601 timestamp set once at registration
        last_login    — ISO-8601 timestamp updated on every successful login
        login_attempts— rolling count; resets to 0 on success
    """

    username:        str
    email:           str
    password_hash:   str                 # Never the raw password
    salt:            str                 # Unique per-user; stored alongside hash
    full_name:       str
    created_at:      str  = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    last_login:      Optional[str] = None
    is_active:       bool = True
    login_attempts:  int  = 0

    # ── Serialisation ────────────────────────────────────

    def to_dict(self) -> dict:
        """Convert the User to a JSON-serialisable dictionary."""
        return {
            "username":       self.username,
            "email":          self.email,
            "password_hash":  self.password_hash,
            "salt":           self.salt,
            "full_name":      self.full_name,
            "created_at":     self.created_at,
            "last_login":     self.last_login,
            "is_active":      self.is_active,
            "login_attempts": self.login_attempts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Reconstruct a User from a dictionary loaded from JSON storage."""
        return cls(
            username=       data["username"],
            email=          data["email"],
            password_hash=  data["password_hash"],
            salt=           data["salt"],
            full_name=      data["full_name"],
            created_at=     data.get("created_at", datetime.now().isoformat()),
            last_login=     data.get("last_login"),
            is_active=      data.get("is_active", True),
            login_attempts= data.get("login_attempts", 0),
        )

    # ── Behaviour ────────────────────────────────────────

    def record_login(self) -> None:
        """Called by AuthService after a successful login verification."""
        self.last_login      = datetime.now().isoformat()
        self.login_attempts  = 0   # Reset the failed-attempt counter

    def record_failed_attempt(self) -> None:
        """Increment the failed-login counter (used for account lockout)."""
        self.login_attempts += 1

    # ── Properties ───────────────────────────────────────

    @property
    def is_locked(self) -> bool:
        """
        An account is locked after 5 consecutive failed login attempts.
        This mitigates online brute-force / credential-stuffing attacks.
        The threshold is stored per-user so admins could adjust it later.
        """
        return self.login_attempts >= 5

    @property
    def formatted_created_at(self) -> str:
        """Human-readable registration timestamp for profile display."""
        try:
            dt = datetime.fromisoformat(self.created_at)
            return dt.strftime("%B %d, %Y  at  %I:%M %p")
        except ValueError:
            return self.created_at

    @property
    def formatted_last_login(self) -> str:
        """Human-readable last-login timestamp for profile display."""
        if not self.last_login:
            return "Never"
        try:
            dt = datetime.fromisoformat(self.last_login)
            return dt.strftime("%B %d, %Y  at  %I:%M %p")
        except ValueError:
            return self.last_login

    @property
    def initials(self) -> str:
        """Return up to two initials for avatar-style display."""
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.full_name[:2].upper()

    @property
    def status_label(self) -> str:
        if self.is_locked:
            return "🔒 Locked"
        return "✅ Active" if self.is_active else "⛔ Inactive"

    def __repr__(self) -> str:
        return (
            f"User(username={self.username!r}, email={self.email!r}, "
            f"active={self.is_active}, attempts={self.login_attempts})"
        )
