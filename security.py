"""
security.py — Security & Validation Layer
==========================================
This module is the SECURITY BACKBONE of the application.

WHY HASHING?
  Storing raw passwords is catastrophic. If the database is ever leaked, every
  user's password is exposed. Hashing converts a password into a fixed-length
  digest that is computationally infeasible to reverse.

WHY SALTING?
  Without a salt, two users with the same password produce the same hash.
  An attacker with a precomputed "rainbow table" can crack thousands of
  passwords instantly. A unique random salt forces the attacker to crack
  each hash individually — making bulk attacks impractical.

WHY PBKDF2?
  PBKDF2 (Password-Based Key Derivation Function 2) applies the hash function
  100,000 times (iterations). This makes a single guess take ~0.1s on modern
  hardware, turning a brute-force of a million guesses into 100,000 seconds.
"""

import hashlib
import secrets
import re
from typing import Tuple, List


# ─────────────────────────────────────────────────────────
# PASSWORD HASHING  (Data Layer ↔ Business Logic Interface)
# ─────────────────────────────────────────────────────────

def hash_password(password: str) -> Tuple[str, str]:
    """
    Generate a cryptographically secure salt and hash the password with PBKDF2-HMAC-SHA256.

    Returns:
        (salt_hex, hash_hex) — both stored in the database, never the raw password.

    Process:
        1. Generate 32 random bytes (256-bit salt) via the OS CSPRNG.
        2. Run PBKDF2-HMAC-SHA256 with 100,000 iterations.
        3. Return both as hexadecimal strings for safe JSON storage.
    """
    # secrets.token_hex uses os.urandom() — a cryptographically secure source
    salt: str = secrets.token_hex(32)  # 64-char hex string = 32 random bytes

    pwd_bytes: bytes = password.encode("utf-8")
    salt_bytes: bytes = salt.encode("utf-8")

    # PBKDF2 with 100,000 iterations — slows brute-force attacks dramatically
    pwd_hash: bytes = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=pwd_bytes,
        salt=salt_bytes,
        iterations=100_000,
        dklen=32,  # 256-bit output key
    )

    return salt, pwd_hash.hex()


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    """
    Recompute the hash from the provided password + stored salt and compare
    it against the stored hash using a CONSTANT-TIME comparison.

    WHY CONSTANT-TIME?
        Python's '==' short-circuits on the first mismatch, leaking timing
        information. An attacker measuring response time can determine how many
        bytes matched. hmac.compare_digest() always takes the same time.
    """
    import hmac  # imported here to keep the constant-time comparison explicit

    pwd_bytes: bytes = password.encode("utf-8")
    salt_bytes: bytes = salt.encode("utf-8")

    recomputed_hash: bytes = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=pwd_bytes,
        salt=salt_bytes,
        iterations=100_000,
        dklen=32,
    )

    # Constant-time comparison — prevents timing side-channel attacks
    return hmac.compare_digest(recomputed_hash.hex(), stored_hash)


# ─────────────────────────────────────────────────────────
# INPUT VALIDATION  (Business Logic Layer)
# ─────────────────────────────────────────────────────────

def validate_password(password: str) -> Tuple[bool, List[str]]:
    """
    Enforce a strong password policy and return a list of unmet criteria.

    A strong password significantly reduces the risk from credential stuffing
    and dictionary attacks. Each rule is checked independently so the user
    sees ALL failures at once — not one at a time.

    Returns:
        (is_valid: bool, error_messages: List[str])
    """
    errors: List[str] = []

    if len(password) < 8:
        errors.append("❌  Minimum 8 characters required")

    if not re.search(r"[A-Z]", password):
        errors.append("❌  At least one UPPERCASE letter (A–Z)")

    if not re.search(r"[a-z]", password):
        errors.append("❌  At least one lowercase letter (a–z)")

    if not re.search(r"\d", password):
        errors.append("❌  At least one digit (0–9)")

    # Common special characters that are always reachable on standard keyboards
    if not re.search(r"""[!@#$%^&*()\-_=+\[\]{};:'",.<>?/\\|`~]""", password):
        errors.append("❌  At least one special character (!@#$%^&* etc.)")

    return (len(errors) == 0, errors)


def validate_email(email: str) -> bool:
    """
    Validate e-mail format using a conservative RFC 5322-inspired regex.
    This catches obvious mistakes without rejecting valid edge-case addresses.
    """
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Username rules:
      • 3–20 characters
      • Only letters, digits, underscores, hyphens
      • Must start with a letter
    Returns (is_valid, error_message).
    """
    username = username.strip()

    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 20:
        return False, "Username must be at most 20 characters."
    if not re.match(r"^[a-zA-Z]", username):
        return False, "Username must start with a letter."
    if not re.match(r"^[a-zA-Z0-9_\-]+$", username):
        return False, "Only letters, digits, underscores, and hyphens allowed."

    return True, ""


def validate_full_name(name: str) -> Tuple[bool, str]:
    """Basic full-name validation: non-empty, letters and spaces only."""
    name = name.strip()
    if len(name) < 2:
        return False, "Full name must be at least 2 characters."
    if not re.match(r"^[a-zA-Z\s\-']+$", name):
        return False, "Full name may only contain letters, spaces, hyphens, or apostrophes."
    return True, ""
