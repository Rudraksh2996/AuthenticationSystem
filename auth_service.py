"""
auth_service.py — Business Logic / Service Layer
==================================================
The AuthService class is the HEART of the backend.

It orchestrates everything:
  • Calls security.py  to hash/verify passwords and validate inputs
  • Calls database.py  to read and write user records
  • Returns clean (success, message, data) tuples to the UI layer

WHY THIS LAYER?
  The UI (ui.py / main.py) should NEVER touch the database directly, and the
  database should NEVER apply business rules. The service layer is the bridge:
  it knows the rules and delegates storage/hashing to the right specialists.

  This follows the classic three-tier architecture:
    Presentation → Business Logic → Data Access

RETURN CONVENTION:
  Every public method returns a tuple:  (success: bool, message: str, payload)
  This keeps error handling uniform — the UI always checks `success` first,
  then shows `message`, then uses `payload` if it exists.
"""

from typing import Optional, Tuple, Any
from datetime import datetime

from models import User
from database import Database
from security import (
    hash_password,
    verify_password,
    validate_password,
    validate_email,
    validate_username,
    validate_full_name,
)


# ─────────────────────────────────────────────────────────
# AUTH SERVICE  (Business Logic Layer)
# ─────────────────────────────────────────────────────────

class AuthService:
    """
    Handles all authentication and user-management business logic.

    Attributes:
        _db            — the Database (data layer) instance
        _current_user  — the logged-in User, or None if no session is active
    """

    def __init__(self, database: Optional[Database] = None) -> None:
        # Dependency injection — lets tests swap in a mock database
        self._db: Database = database or Database()
        self._current_user: Optional[User] = None

    # ── Session Management ───────────────────────────────

    @property
    def current_user(self) -> Optional[User]:
        """The currently authenticated user, or None."""
        return self._current_user

    @property
    def is_authenticated(self) -> bool:
        """True only when a user is actively logged in."""
        return self._current_user is not None

    def logout(self) -> Tuple[bool, str, None]:
        """Clear the active session. Safe to call even when not logged in."""
        name = self._current_user.full_name if self._current_user else "User"
        self._current_user = None
        return True, f"Goodbye, {name}! You have been logged out.", None

    # ── Registration ─────────────────────────────────────

    def register(
        self,
        username:  str,
        email:     str,
        password:  str,
        full_name: str,
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user after full validation.

        Validation order (fail fast with a clear message on each step):
          1. Username format & availability
          2. E-mail format & availability
          3. Full-name format
          4. Password strength

        On success:
          - Hash the password with a fresh random salt
          - Persist the new User record
          - Return the User object (caller may auto-login)
        """

        # ── Step 1: Validate username ──
        username = username.strip()
        ok, err = validate_username(username)
        if not ok:
            return False, f"Invalid username — {err}", None

        if self._db.username_exists(username):
            return False, f"Username '{username}' is already taken. Please choose another.", None

        # ── Step 2: Validate e-mail ──
        email = email.strip().lower()
        if not validate_email(email):
            return False, "Invalid e-mail address format. Please try again.", None

        if self._db.email_exists(email):
            return False, "An account with that e-mail already exists.", None

        # ── Step 3: Validate full name ──
        full_name = full_name.strip()
        ok, err = validate_full_name(full_name)
        if not ok:
            return False, f"Invalid full name — {err}", None

        # ── Step 4: Validate password strength ──
        ok, errors = validate_password(password)
        if not ok:
            # Return ALL failures so the user fixes everything at once
            error_block = "\n  ".join(errors)
            return False, f"Password does not meet requirements:\n  {error_block}", None

        # ── Step 5: Hash the password and persist ──
        salt, pwd_hash = hash_password(password)   # Never store `password` itself

        new_user = User(
            username=      username.lower(),
            email=         email,
            password_hash= pwd_hash,
            salt=          salt,
            full_name=     full_name,
        )

        self._db.save_user(new_user)

        return True, f"Account created successfully! Welcome, {full_name}!", new_user

    # ── Login ────────────────────────────────────────────

    def login(
        self,
        username: str,
        password: str,
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Authenticate a user by username + password.

        Security measures:
          • Account lockout after 5 consecutive failures (anti-brute-force)
          • Constant-time password comparison (in security.verify_password)
          • Failed-attempt counter persisted to disk (survives restarts)
          • Generic error messages — never reveal whether the username exists
            (prevents username enumeration attacks)
        """

        # ── Lookup user ──
        username = username.strip().lower()
        user = self._db.get_user_by_username(username)

        # Generic message prevents username enumeration
        generic_err = "Invalid username or password."

        if user is None:
            return False, generic_err, None

        # ── Check account status ──
        if not user.is_active:
            return False, "This account has been deactivated. Contact support.", None

        if user.is_locked:
            return (
                False,
                "Account locked due to too many failed attempts. "
                "Please reset your password to unlock it.",
                None,
            )

        # ── Verify password ──
        if not verify_password(password, user.salt, user.password_hash):
            user.record_failed_attempt()   # Increment the counter
            self._db.save_user(user)       # Persist the new counter value

            remaining = max(0, 5 - user.login_attempts)
            if remaining > 0:
                return (
                    False,
                    f"{generic_err}  ({remaining} attempt{'s' if remaining != 1 else ''} remaining before lockout)",
                    None,
                )
            else:
                return False, "Account is now locked due to too many failed attempts.", None

        # ── Success ──
        user.record_login()        # Update last_login + reset counter
        self._db.save_user(user)   # Persist the updated timestamps
        self._current_user = user  # Establish the session

        return True, f"Welcome back, {user.full_name}!", user

    # ── Change Password ──────────────────────────────────

    def change_password(
        self,
        old_password: str,
        new_password: str,
        confirm_password: str,
    ) -> Tuple[bool, str, None]:
        """
        Allow an authenticated user to change their own password.

        Requires the current password as proof of identity before accepting
        the new one. This prevents a session-hijack scenario where someone
        at an unlocked terminal changes the password without knowing the old one.
        """

        if not self.is_authenticated:
            return False, "You must be logged in to change your password.", None

        user = self._current_user

        # ── Confirm knowledge of old password ──
        if not verify_password(old_password, user.salt, user.password_hash):
            return False, "Current password is incorrect.", None

        # ── Confirm new passwords match ──
        if new_password != confirm_password:
            return False, "New passwords do not match.", None

        # ── Prevent reuse of the same password ──
        if verify_password(new_password, user.salt, user.password_hash):
            return False, "New password must be different from the current password.", None

        # ── Validate strength of new password ──
        ok, errors = validate_password(new_password)
        if not ok:
            error_block = "\n  ".join(errors)
            return False, f"New password does not meet requirements:\n  {error_block}", None

        # ── Hash the new password with a FRESH salt (rotate salt on change) ──
        new_salt, new_hash = hash_password(new_password)
        user.password_hash  = new_hash
        user.salt           = new_salt
        self._db.save_user(user)   # Persist the updated credentials

        return True, "Password changed successfully!", None

    # ── Profile ──────────────────────────────────────────

    def get_profile(self) -> Tuple[bool, str, Optional[User]]:
        """Return the current user's profile data."""
        if not self.is_authenticated:
            return False, "No active session.", None
        return True, "Profile loaded.", self._current_user

    def get_stats(self) -> dict:
        """Return aggregate stats for a potential admin view."""
        return {
            "total_users":  self._db.count_users(),
            "storage_path": self._db.filepath,
        }
