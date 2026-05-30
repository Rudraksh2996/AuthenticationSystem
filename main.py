"""
main.py — Application Entry Point & Controller
================================================
The App class is the CONTROLLER — it wires together the UI (presentation
layer) and AuthService (business logic layer) into a cohesive application.

It contains:
  • The main event loop (run)
  • Thin handler methods for each menu action
  • ZERO business logic (that belongs in auth_service.py)
  • ZERO direct DB access (that belongs in database.py)

This separation means you could, in theory, swap the CLI UI for a web
framework like Flask and reuse auth_service.py unchanged.

INSTALLATION (run once before first use):
  pip install rich

USAGE:
  python main.py
"""

import sys
from auth_service import AuthService
from ui import UI, console


# ─────────────────────────────────────────────────────────
# APPLICATION CONTROLLER
# ─────────────────────────────────────────────────────────

class App:
    """
    Top-level controller that drives the application loop.

    Responsibilities:
      • Maintain the running/stopped state
      • Route menu choices to the correct handler
      • Delegate all logic to AuthService
      • Delegate all display to UI
    """

    def __init__(self) -> None:
        self._auth    = AuthService()   # Business logic layer
        self._running = True            # Loop-control flag

    # ─────────────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────────────

    def run(self) -> None:
        """Application entry point — shows banner then starts the menu loop."""
        UI.show_banner()
        UI.pause(0.5)

        while self._running:
            if self._auth.is_authenticated:
                self._user_session_loop()
            else:
                self._main_menu_loop()

    # ─────────────────────────────────────────────────────
    # UNAUTHENTICATED MENU
    # ─────────────────────────────────────────────────────

    def _main_menu_loop(self) -> None:
        """Loop for users who are not yet logged in."""
        UI.show_banner()
        UI.show_main_menu()

        choice = UI.get_choice("Enter your choice", choices=["1", "2", "3"], default="")

        handlers = {
            "1": self._handle_register,
            "2": self._handle_login,
            "3": self._handle_exit,
        }
        handler = handlers.get(choice)
        if handler:
            handler()

    # ─────────────────────────────────────────────────────
    # AUTHENTICATED USER MENU
    # ─────────────────────────────────────────────────────

    def _user_session_loop(self) -> None:
        """Loop for authenticated users."""
        user = self._auth.current_user
        UI.show_dashboard(user)
        UI.show_user_menu(user)

        choice = UI.get_choice("Enter your choice", choices=["1", "2", "3"], default="")

        handlers = {
            "1": self._handle_view_profile,
            "2": self._handle_change_password,
            "3": self._handle_logout,
        }
        handler = handlers.get(choice)
        if handler:
            handler()

    # ─────────────────────────────────────────────────────
    # HANDLER: REGISTER
    # ─────────────────────────────────────────────────────

    def _handle_register(self) -> None:
        """
        Multi-step registration flow.

        The UI collects each field, then AuthService validates and stores.
        We loop on the overall form if registration fails (e.g., duplicate
        username) so the user can correct without restarting.
        """
        UI.show_register_header()

        # ── Collect inputs ──
        full_name = UI.get_input("Full Name")
        username  = UI.get_input("Username  (3–20 chars, letters/digits/_/-)")
        email     = UI.get_input("E-mail Address")

        # Show password rules before asking
        UI.blank()
        UI.show_password_rules()
        password  = UI.get_password("Create Password")
        confirm   = UI.get_password("Confirm Password")

        # Quick client-side confirmation check before hitting the service
        if password != confirm:
            UI.error("Passwords do not match. Please try again.")
            UI.press_enter()
            return

        # ── Call the business logic layer ──
        UI.blank()
        UI.loading("Creating your account", duration=1.8)

        success, message, user = self._auth.register(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
        )

        if success:
            UI.show_register_success(full_name)
            UI.pause(1.0)
        else:
            # AuthService returns all validation errors in `message`
            UI.error(message)
            UI.press_enter()

    # ─────────────────────────────────────────────────────
    # HANDLER: LOGIN
    # ─────────────────────────────────────────────────────

    def _handle_login(self) -> None:
        """
        Login flow.

        The service handles all security: account lockout, wrong password,
        non-existent user. The UI just shows what the service returns.
        """
        UI.show_login_header()

        username = UI.get_input("Username")
        password = UI.get_password("Password")

        UI.blank()
        UI.loading("Verifying your credentials", duration=1.5)

        success, message, user = self._auth.login(
            username=username,
            password=password,
        )

        if success:
            UI.success(message)
            UI.pause(0.8)
            # The loop will now detect is_authenticated=True
            # and switch to the user dashboard automatically
        else:
            UI.error(message)
            UI.press_enter()

    # ─────────────────────────────────────────────────────
    # HANDLER: VIEW PROFILE
    # ─────────────────────────────────────────────────────

    def _handle_view_profile(self) -> None:
        """Display the logged-in user's full profile."""
        success, message, user = self._auth.get_profile()

        if success and user:
            UI.show_profile(user)
        else:
            UI.error(message)

        UI.press_enter()

    # ─────────────────────────────────────────────────────
    # HANDLER: CHANGE PASSWORD
    # ─────────────────────────────────────────────────────

    def _handle_change_password(self) -> None:
        """
        Password-change flow.

        Requires the user to provide their CURRENT password first — this is a
        standard security measure to prevent session-hijacking scenarios.
        """
        UI.show_change_password_header()

        old_password = UI.get_password("Current Password")

        UI.blank()
        UI.show_password_rules()
        new_password     = UI.get_password("New Password")
        confirm_password = UI.get_password("Confirm New Password")

        UI.blank()
        UI.loading("Updating your password", duration=1.8)

        success, message, _ = self._auth.change_password(
            old_password=old_password,
            new_password=new_password,
            confirm_password=confirm_password,
        )

        if success:
            UI.success(message)
        else:
            UI.error(message)

        UI.press_enter()

    # ─────────────────────────────────────────────────────
    # HANDLER: LOGOUT
    # ─────────────────────────────────────────────────────

    def _handle_logout(self) -> None:
        """End the current session and return to the main menu."""
        if UI.confirm("Are you sure you want to logout?"):
            UI.loading("Ending session", duration=0.8)
            _, message, _ = self._auth.logout()
            UI.clear()
            UI.success(message)
            UI.pause(1.0)
        # Whether confirmed or not, the loop will re-check is_authenticated

    # ─────────────────────────────────────────────────────
    # HANDLER: EXIT
    # ─────────────────────────────────────────────────────

    def _handle_exit(self) -> None:
        """Graceful shutdown."""
        if UI.confirm("Are you sure you want to exit?"):
            UI.show_exit()
            UI.pause(1.5)
            self._running = False


# ─────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────

def main() -> None:
    """
    Bootstrap the application.

    The try/except KeyboardInterrupt ensures that pressing Ctrl+C (^C)
    exits cleanly instead of dumping a traceback — professional CLI behaviour.
    """
    try:
        app = App()
        app.run()
    except KeyboardInterrupt:
        UI.clear()
        console.print("\n\n  [bold yellow]⚡  Interrupted. Goodbye![/bold yellow]\n")
        sys.exit(0)
    except Exception as exc:
        console.print_exception(show_locals=False)
        console.print(f"\n  [bold red]Fatal error:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
