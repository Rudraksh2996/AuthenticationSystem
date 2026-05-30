"""
database.py — Data Persistence Layer
======================================
Handles ALL read/write operations against the local JSON file.

WHY ABSTRACT THIS INTO ITS OWN CLASS?
  The rest of the application doesn't care whether data is stored in JSON,
  SQLite, or PostgreSQL. By hiding that detail behind a clean interface
  (get_user_by_username, save_user, etc.), we can swap the storage backend
  later without touching AuthService or the UI.

  This is the REPOSITORY PATTERN — a classic backend design principle.

THREAD SAFETY NOTE:
  This implementation is single-process / single-threaded (typical for a CLI).
  For a web API, you would use a proper database with connection pooling and
  transactions. The write-then-read pattern here (write full dict, read full dict)
  is atomic enough for a local CLI scenario.
"""

import json
import os
from typing import Dict, Optional, List

from models import User


# ─────────────────────────────────────────────────────────
# DATABASE CLASS  (Data / Persistence Layer)
# ─────────────────────────────────────────────────────────

class Database:
    """
    JSON-backed key-value store for User objects.

    Storage format inside users.json:
    {
        "users": {
            "<username>": { ...user fields... },
            ...
        }
    }

    Using username as the primary key gives O(1) lookup by username.
    The email-uniqueness check is O(n) but acceptable at this scale.
    """

    DEFAULT_PATH: str = "users.json"

    def __init__(self, filepath: str = DEFAULT_PATH) -> None:
        """
        Initialise the database.

        Args:
            filepath: Path to the JSON file. Stored relative to the CWD so the
                      file is always created next to wherever the script runs.
        """
        self._filepath: str = filepath
        self._ensure_file_exists()

    # ── Private Helpers ──────────────────────────────────

    def _ensure_file_exists(self) -> None:
        """Create an empty database file if one doesn't exist yet."""
        if not os.path.exists(self._filepath):
            self._write({"users": {}})

    def _read(self) -> dict:
        """
        Load the entire JSON file into memory.

        WHY LOAD THE WHOLE FILE?
          At CLI-app scale (tens to hundreds of users) this is perfectly fine
          and far simpler than partial reads. For millions of records you would
          use a real database with indexed queries.
        """
        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Guard against a corrupted/empty file
                if "users" not in data:
                    data["users"] = {}
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            # File corrupted or deleted mid-session — recover gracefully
            return {"users": {}}

    def _write(self, data: dict) -> None:
        """
        Persist the full data dictionary back to disk.

        indent=2 keeps the file human-readable — useful for debugging.
        Writing to a temp file then renaming is the safest atomic write pattern,
        but for a single-user CLI os.open is sufficient here.
        """
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_users(self) -> Dict[str, dict]:
        """Return the raw users dictionary from storage."""
        return self._read().get("users", {})

    # ── Public Interface ─────────────────────────────────

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Fetch a User by username (case-insensitive lookup).
        Returns None if the user doesn't exist — caller must handle this.
        """
        users = self._load_users()
        # Normalise to lowercase for case-insensitive matching
        user_data = users.get(username.lower())
        if user_data is None:
            return None
        return User.from_dict(user_data)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Fetch a User by e-mail address (case-insensitive).
        Used during registration to prevent duplicate e-mails.
        O(n) scan — acceptable at CLI scale.
        """
        users = self._load_users()
        email_lower = email.lower().strip()
        for user_data in users.values():
            if user_data.get("email", "").lower() == email_lower:
                return User.from_dict(user_data)
        return None

    def username_exists(self, username: str) -> bool:
        """Quick existence check — avoids constructing a full User object."""
        return username.lower() in self._load_users()

    def email_exists(self, email: str) -> bool:
        """Quick e-mail existence check."""
        return self.get_user_by_email(email) is not None

    def save_user(self, user: User) -> None:
        """
        Insert OR update a User record.
        The username (lowercased) is the primary key.

        This upsert pattern means we use the same method for both
        registration and profile updates — simpler API for AuthService.
        """
        data = self._read()
        data["users"][user.username.lower()] = user.to_dict()
        self._write(data)

    def delete_user(self, username: str) -> bool:
        """
        Remove a user record. Returns True if found and deleted, False otherwise.
        Included for completeness — could power an admin 'delete account' feature.
        """
        data = self._read()
        key = username.lower()
        if key in data["users"]:
            del data["users"][key]
            self._write(data)
            return True
        return False

    def get_all_users(self) -> List[User]:
        """Return every user — useful for admin dashboards or exports."""
        users = self._load_users()
        return [User.from_dict(u) for u in users.values()]

    def count_users(self) -> int:
        """Return total number of registered users."""
        return len(self._load_users())

    @property
    def filepath(self) -> str:
        """Expose the storage path for display in the UI."""
        return os.path.abspath(self._filepath)
