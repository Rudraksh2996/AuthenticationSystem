"""
ui.py — Presentation / UI Layer
=================================
All visual output lives HERE and ONLY here.

The UI layer depends on the business layer (auth_service.py) but NEVER on
the data layer (database.py / models.py internals). This ensures that changing
the visual design never accidentally breaks authentication logic.

LIBRARIES USED:
  rich.console  — smart terminal output with markup
  rich.panel    — bordered boxes
  rich.table    — data tables
  rich.progress — loading spinners
  rich.prompt   — styled user input
  rich.align    — centering
  rich.rule     — horizontal dividers
  rich.text     — programmatic markup
"""

import os
import time
from typing import Optional, Callable, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.align import Align
from rich.rule import Rule
from rich.text import Text
from rich.columns import Columns
from rich import box

from models import User


# ─────────────────────────────────────────────────────────
# GLOBAL CONSOLE INSTANCE
# ─────────────────────────────────────────────────────────

console = Console()


# ─────────────────────────────────────────────────────────
# UI CLASS  (Presentation Layer)
# ─────────────────────────────────────────────────────────

class UI:
    """
    Encapsulates every terminal interaction — drawing panels, prompting for
    input, showing feedback messages, and simulating loading delays.

    Keeps the main app logic in main.py clean and readable.
    """

    # ── Colour Palette ───────────────────────────────────
    C_SUCCESS  = "bold green"
    C_ERROR    = "bold red"
    C_WARNING  = "bold yellow"
    C_INFO     = "bold cyan"
    C_ACCENT   = "bold magenta"
    C_DIM      = "dim white"
    C_TITLE    = "bold bright_white"
    C_MENU     = "bright_cyan"
    C_LABEL    = "bold bright_yellow"

    # ── Utility Methods ──────────────────────────────────

    @staticmethod
    def clear() -> None:
        """Clear the terminal screen cross-platform."""
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def pause(seconds: float = 0.6) -> None:
        """Brief pause for visual breathing room."""
        time.sleep(seconds)

    @staticmethod
    def press_enter() -> None:
        """Wait for the user to hit Enter before continuing."""
        console.print()
        console.input("[dim]  Press [bold]ENTER[/bold] to continue…[/dim]")

    # ── Feedback Messages ─────────────────────────────────

    @classmethod
    def success(cls, message: str) -> None:
        console.print(f"\n  [bold green]✔  {message}[/bold green]")

    @classmethod
    def error(cls, message: str) -> None:
        console.print(f"\n  [bold red]✘  {message}[/bold red]")

    @classmethod
    def warning(cls, message: str) -> None:
        console.print(f"\n  [bold yellow]⚠  {message}[/bold yellow]")

    @classmethod
    def info(cls, message: str) -> None:
        console.print(f"\n  [bold cyan]ℹ  {message}[/bold cyan]")

    # ── Loading Spinner ──────────────────────────────────

    @staticmethod
    def loading(message: str = "Processing", duration: float = 1.5) -> None:
        """
        Show an animated spinner for `duration` seconds.

        WHY?
          Mimics real-world async/network operations (e.g., password hashing on
          a remote server, DB roundtrip). PBKDF2 with 100k iterations actually
          takes ~0.1-0.3 s on most hardware — the extra delay makes it feel real.
        """
        with Progress(
            SpinnerColumn(spinner_name="dots", style="bold cyan"),
            TextColumn(f"  [bold cyan]{message}…[/bold cyan]"),
            transient=True,   # Clears itself when done
            console=console,
        ) as progress:
            task = progress.add_task("", total=100)
            steps = int(duration / 0.03)
            for _ in range(steps):
                progress.advance(task, 100 / steps)
                time.sleep(0.03)

    # ── Input Helpers ─────────────────────────────────────

    @staticmethod
    def get_input(prompt_text: str, default: str = "") -> str:
        """Styled text input. Returns stripped string."""
        console.print()
        return Prompt.ask(f"  [bold cyan]{prompt_text}[/bold cyan]", default=default).strip()

    @staticmethod
    def get_password(prompt_text: str = "Password") -> str:
        """Password input — characters are hidden."""
        console.print()
        return Prompt.ask(
            f"  [bold cyan]{prompt_text}[/bold cyan]",
            password=True,
        )

    @staticmethod
    def get_choice(prompt_text: str, choices: list, default: str = "") -> str:
        """Styled choice prompt with validation."""
        console.print()
        return Prompt.ask(
            f"  [bold cyan]{prompt_text}[/bold cyan]",
            choices=choices,
            default=default,
        ).strip()

    @staticmethod
    def confirm(prompt_text: str) -> bool:
        """Yes/no confirmation prompt."""
        console.print()
        return Confirm.ask(f"  [bold yellow]{prompt_text}[/bold yellow]")

    # ── Screens ──────────────────────────────────────────

    @classmethod
    def show_banner(cls) -> None:
        """
        Full-width welcome banner displayed on startup.
        Uses ASCII art + Rich markup for a polished first impression.
        """
        cls.clear()

        banner_art = Text(justify="center")
        banner_art.append("\n")
        banner_art.append("   ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗     \n", style="bold bright_cyan")
        banner_art.append("  ██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗    \n", style="bold cyan")
        banner_art.append("  ██║  ███╗██║   ██║███████║██████╔╝██║  ██║    \n", style="bold blue")
        banner_art.append("  ██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║    \n", style="bold bright_blue")
        banner_art.append("  ╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝    \n", style="bold magenta")
        banner_art.append("   ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝    \n", style="bold bright_magenta")
        banner_art.append("\n")
        banner_art.append("        🔐  Secure User Authentication System  🔐\n", style="bold bright_white")
        banner_art.append("    PBKDF2-SHA256 · Salted Hashing · JSON Persistence\n\n", style="dim white")

        console.print(
            Panel(
                Align(banner_art, align="center"),
                border_style="bright_cyan",
                padding=(0, 4),
            )
        )

    @classmethod
    def show_main_menu(cls) -> None:
        """Render the unauthenticated main menu."""
        menu = Table.grid(padding=(0, 2))
        menu.add_column(justify="center", style="bold bright_white", min_width=4)
        menu.add_column(style="bold bright_cyan")
        menu.add_column(style="dim white")

        menu.add_row("  [1]", "📝  Register",    "Create a new account")
        menu.add_row("  [2]", "🔑  Login",       "Sign in to your account")
        menu.add_row("  [3]", "❌  Exit",         "Quit the application")

        console.print(
            Panel(
                Align(menu, align="center"),
                title="[bold bright_white]  MAIN MENU  [/bold bright_white]",
                border_style="cyan",
                padding=(1, 6),
            )
        )

    @classmethod
    def show_user_menu(cls, user: User) -> None:
        """Render the authenticated user's action menu."""
        cls.clear()

        # ── Mini header ──
        header = Text(justify="center")
        header.append(f"\n  👤  {user.full_name}", style="bold bright_white")
        header.append(f"  (@{user.username})\n", style="dim white")

        menu = Table.grid(padding=(0, 2))
        menu.add_column(justify="center", style="bold bright_white", min_width=4)
        menu.add_column(style="bold bright_cyan")
        menu.add_column(style="dim white")

        menu.add_row("  [1]", "🧾  View Profile",    "See your account details")
        menu.add_row("  [2]", "🔒  Change Password",  "Update your password")
        menu.add_row("  [3]", "🚪  Logout",           "End this session")

        console.print(
            Panel(
                Align(
                    Text.assemble(header, "\n") if True else menu,
                    align="center",
                ),
                border_style="bright_green",
                padding=(0, 0),
            )
        )
        console.print(
            Panel(
                Align(menu, align="center"),
                title="[bold bright_green]  USER MENU  [/bold bright_green]",
                border_style="green",
                padding=(1, 6),
            )
        )

    @classmethod
    def show_dashboard(cls, user: User) -> None:
        """
        Post-login welcome screen — animated reveal of a personalised dashboard.
        """
        cls.clear()
        cls.loading("Initialising your dashboard", duration=1.2)
        cls.clear()

        # ── Avatar circle ──
        avatar_text = Text(justify="center")
        avatar_text.append(f"\n        ╔══════╗\n", style="bold bright_cyan")
        avatar_text.append(f"        ║  {user.initials:<4}║\n", style="bold bright_white")
        avatar_text.append(f"        ╚══════╝\n", style="bold bright_cyan")

        # ── Greeting ──
        greeting = Text(justify="center")
        greeting.append(f"\n  🎉  Welcome back, ", style="bold bright_yellow")
        greeting.append(f"{user.full_name}!", style="bold bright_white")
        greeting.append(f"\n  Last login: {user.formatted_last_login}\n", style="dim white")

        # ── Stats grid ──
        stats = Table.grid(padding=(0, 3), expand=False)
        stats.add_column(justify="right",  style="dim white")
        stats.add_column(justify="left",   style="bold bright_white")

        stats.add_row("Username",    f"@{user.username}")
        stats.add_row("E-mail",      user.email)
        stats.add_row("Member Since", user.formatted_created_at)
        stats.add_row("Status",      user.status_label)

        console.print(
            Panel(
                Align(
                    Text.assemble(avatar_text, greeting),
                    align="center",
                ),
                border_style="bright_green",
                padding=(1, 4),
            )
        )
        console.print(
            Panel(
                Align(stats, align="center"),
                title="[bold bright_green]  ACCOUNT OVERVIEW  [/bold bright_green]",
                border_style="green",
                padding=(1, 6),
            )
        )

    @classmethod
    def show_profile(cls, user: User) -> None:
        """Full profile view with a detailed table layout."""
        cls.clear()

        table = Table(
            title=f"[bold bright_white]👤  Profile — @{user.username}[/bold bright_white]",
            box=box.DOUBLE_EDGE,
            border_style="bright_cyan",
            header_style="bold bright_cyan",
            show_header=False,
            padding=(0, 2),
            expand=False,
        )

        table.add_column("Field",  style="bold bright_yellow", min_width=20)
        table.add_column("Value",  style="bright_white",       min_width=36)

        table.add_row("👤  Full Name",      user.full_name)
        table.add_row("🏷️  Username",       f"@{user.username}")
        table.add_row("📧  E-mail Address", user.email)
        table.add_row("📅  Member Since",   user.formatted_created_at)
        table.add_row("🕐  Last Login",     user.formatted_last_login)
        table.add_row("🔐  Account Status", user.status_label)
        table.add_row(
            "🛡️  Password Hash",
            f"[dim]{user.password_hash[:24]}…[/dim]  [dim](PBKDF2-SHA256)[/dim]",
        )

        console.print()
        console.print(Align(table, align="center"))
        console.print()

        # Security tip panel
        tip = Text(justify="center")
        tip.append("💡  Your password is stored as a PBKDF2-SHA256 hash — ", style="dim")
        tip.append("never in plain text.\n", style="bold dim")
        tip.append("    Even the system administrators cannot see your actual password.", style="dim")
        console.print(
            Panel(tip, border_style="dim", padding=(0, 2))
        )

    # ── Registration Flow ─────────────────────────────────

    @classmethod
    def show_register_header(cls) -> None:
        cls.clear()
        console.print(
            Panel(
                Align(
                    Text("📝  Create Your Account", style="bold bright_white", justify="center"),
                    align="center",
                ),
                subtitle="[dim]All fields are required[/dim]",
                border_style="bright_cyan",
                padding=(1, 4),
            )
        )
        console.print()

    @classmethod
    def show_register_success(cls, full_name: str) -> None:
        msg = Text(justify="center")
        msg.append(f"\n  🎉  Account created for ", style="bold bright_green")
        msg.append(f"{full_name}!\n\n", style="bold bright_white")
        msg.append("  You can now login with your new credentials.\n", style="dim")
        console.print(Panel(Align(msg, align="center"), border_style="bright_green", padding=(1, 4)))

    # ── Login Flow ────────────────────────────────────────

    @classmethod
    def show_login_header(cls) -> None:
        cls.clear()
        console.print(
            Panel(
                Align(
                    Text("🔑  Login to Your Account", style="bold bright_white", justify="center"),
                    align="center",
                ),
                border_style="bright_cyan",
                padding=(1, 4),
            )
        )
        console.print()

    # ── Password Rules Hint ───────────────────────────────

    @classmethod
    def show_password_rules(cls) -> None:
        """Show password requirements before the user types."""
        rules = Table.grid(padding=(0, 2))
        rules.add_column(justify="left", style="dim")
        rules.add_row("✔  Minimum 8 characters")
        rules.add_row("✔  At least one UPPERCASE letter")
        rules.add_row("✔  At least one lowercase letter")
        rules.add_row("✔  At least one digit  (0–9)")
        rules.add_row("✔  At least one special character  (!@#$%…)")
        console.print(
            Panel(rules, title="[bold yellow]  Password Requirements  [/bold yellow]",
                  border_style="yellow", padding=(0, 3))
        )

    # ── Change Password Flow ──────────────────────────────

    @classmethod
    def show_change_password_header(cls) -> None:
        cls.clear()
        console.print(
            Panel(
                Align(
                    Text("🔒  Change Your Password", style="bold bright_white", justify="center"),
                    align="center",
                ),
                border_style="yellow",
                padding=(1, 4),
            )
        )
        console.print()

    # ── Exit Screen ───────────────────────────────────────

    @classmethod
    def show_exit(cls) -> None:
        cls.clear()
        msg = Text(justify="center")
        msg.append("\n  👋  Thank you for using GuardAuth!\n\n", style="bold bright_cyan")
        msg.append("  Your data is safely persisted in  ", style="dim")
        msg.append("users.json\n\n", style="bold dim white")
        msg.append("         Stay secure. Stay protected. 🔐\n", style="bold bright_magenta")
        console.print(Panel(Align(msg, align="center"), border_style="bright_cyan", padding=(1, 4)))
        console.print()

    # ── Dividers ──────────────────────────────────────────

    @classmethod
    def divider(cls, title: str = "", style: str = "dim") -> None:
        console.print(Rule(title, style=style))

    @classmethod
    def blank(cls, n: int = 1) -> None:
        for _ in range(n):
            console.print()
