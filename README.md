# CLI User Authentication System

A production-quality, colourful, interactive **Command-Line User Authentication System** built in Python — demonstrating real backend thinking through clean architecture, secure password handling, and a rich terminal UI.

---

## ⚡ Quick Start

```bash
# 1. Install the only external dependency
pip install rich

# 2. Run the application (Python 3.10+ required)
python main.py
```

The app creates a `users.json` file in the same directory on first run to persist all user data.

---

## 🏗️ Architecture — Three-Tier Separation

```
┌─────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                        │
│   main.py  (App controller / menu routing)                  │
│   ui.py    (Rich panels, tables, spinners, prompts)         │
└──────────────────────┬──────────────────────────────────────┘
                       │  calls
┌──────────────────────▼──────────────────────────────────────┐
│                 BUSINESS LOGIC LAYER                        │
│   auth_service.py  (AuthService — register, login,          │
│                     change_password, session management)    │
│   security.py      (hashing, salting, validation rules)     │
└──────────────────┬──────────────────────────────────────────┘
                   │  calls
┌──────────────────▼──────────────────────────────────────────┐
│                   DATA ACCESS LAYER                         │
│   database.py  (Database — JSON read/write, CRUD ops)       │
│   models.py    (User dataclass — pure data entity)          │
│   users.json   (Persistent storage file)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

| File | Layer | Purpose |
|------|-------|---------|
| `main.py` | Controller | App loop, menu routing, handler methods |
| `ui.py` | Presentation | All terminal visuals (Rich library) |
| `auth_service.py` | Business Logic | Register, login, change-password logic |
| `security.py` | Business Logic | PBKDF2 hashing, salting, validation |
| `database.py` | Data Access | JSON file read/write, CRUD operations |
| `models.py` | Data Model | `User` dataclass and its properties |
| `users.json` | Storage | Auto-created on first run |

---

## 🔒 Security Features

### Password Hashing (PBKDF2-HMAC-SHA256)
Passwords are **never stored in plain text**. Instead:
1. A **32-byte cryptographically random salt** is generated via `secrets.token_hex(32)`.
2. The password + salt are fed through **PBKDF2-HMAC-SHA256 with 100,000 iterations**.
3. Only the `(salt, hash)` pair is stored — never the raw password.

```python
# What's stored in users.json:
"password_hash": "a3f8c2d1...",   # 256-bit digest
"salt":          "9e4b71a2...",   # unique per user
```

### Why Salting?
Without salts, two users with the same password produce identical hashes, making precomputed *rainbow table* attacks trivial. Unique salts force per-hash cracking.

### Constant-Time Comparison
Password verification uses `hmac.compare_digest()` — always takes the same time regardless of how many bytes match. This prevents *timing side-channel attacks*.

### Account Lockout
After **5 consecutive failed login attempts**, the account is locked and the counter is persisted to disk. This mitigates online brute-force attacks that survive application restarts.

### Salt Rotation on Password Change
When a password is changed, a **fresh salt is generated**. This invalidates any previously stolen hash material.

---

## 🛡️ Password Policy

| Rule | Requirement |
|------|-------------|
| Length | Minimum 8 characters |
| Uppercase | At least one A–Z |
| Lowercase | At least one a–z |
| Digit | At least one 0–9 |
| Special | At least one `!@#$%^&*` etc. |

All unmet rules are displayed simultaneously so the user fixes everything at once.

---

## 🎨 UI Features (Rich Library)

- **ASCII art banner** on startup
- **Coloured panels** with borders for every screen
- **Animated spinner** mimics real server response time
- **Hidden password input** — characters are masked
- **Colour-coded feedback**: 🟢 green (success), 🔴 red (error), 🟡 yellow (warning), 🔵 cyan (info)
- **Profile table** with formatted timestamps
- **Post-login dashboard** with avatar initials and account overview

---

## 📋 Features

| Feature | Details |
|---------|---------|
| Register | Full name, username, email, password with full validation |
| Login | Username + password, lockout after 5 failures |
| View Profile | Formatted table with all account fields |
| Change Password | Requires current password; validates new password strength |
| Logout | Clears session, returns to main menu |
| Persistence | Data survives app restarts via `users.json` |
| Duplicate detection | Blocks reuse of existing username or email |

---

## 🧠 Backend Principles Demonstrated

| Principle | Where |
|-----------|-------|
| Single Responsibility | Each file has one clear job |
| Dependency Injection | `AuthService(database=...)` — testable without a real file |
| Repository Pattern | `Database` hides storage implementation from business logic |
| Service Layer Pattern | `AuthService` orchestrates without knowing DB details |
| Data Transfer Objects | `User.to_dict()` / `from_dict()` for serialisation |
| Fail-Fast Validation | All input validated before any DB/crypto work |
| Generic Error Messages | Login never reveals whether username exists |

---

## 📦 Dependencies

| Package | Version | Why |
|---------|---------|-----|
| `rich` | latest | Terminal UI (panels, tables, spinners) |
| `hashlib` | stdlib | PBKDF2-HMAC-SHA256 hashing |
| `secrets` | stdlib | Cryptographically secure salt generation |
| `json` | stdlib | Data persistence |
| `re` | stdlib | Validation regexes |
| `dataclasses` | stdlib | Clean User model |

```bash
pip install rich
```

---

## 🧪 Testing Scenarios

```
# Happy path
Register with: Full Name, unique username, valid email, strong password
Login with correct credentials → see dashboard
View profile → see all account fields
Change password → provide old + new strong password
Logout → back to main menu

# Error paths
Register with duplicate username/email → clear error
Login with wrong password (5 times) → account locks
Change password with wrong current password → error
Change password to same password → error
Weak password (e.g. "abc") → shows all unmet rules
