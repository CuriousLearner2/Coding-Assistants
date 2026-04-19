#!/usr/bin/env python3
"""Replate CLI — food rescue volunteer driver app (Supabase Edition)."""

import os
import sys

# ── App ────────────────────────────────────────────────────────────────────────

def main() -> int:
    from client.auth import run_auth_menu, logout
    from client.onboarding import run_onboarding
    from client.available_tasks import run_available_tasks
    from client.my_tasks import run_my_tasks
    from client.account import run_account
    from client.session import load_session
    from client import display as d

    # Load or create session
    session = load_session()
    if not session:
        session = run_auth_menu()
        if not session:
            return 0

    # Onboarding gate
    if not session.get("partner_id"):
        session = run_onboarding(session)
        if not session:
            return 0

    # Main navigation loop
    while True:
        d.header("REPLATE — Main Menu")
        d.blank()
        d.info(f"Welcome, {session.get('first_name', 'Driver')}!")
        choice = d.menu(["Available Pick-ups", "My Tasks", "My Account"], back_label="Quit")

        if choice == "1":
            run_available_tasks(session)
        elif choice == "2":
            run_my_tasks(session)
        elif choice == "3":
            result = run_account(session)
            if result == "logout":
                break
        elif choice in ("b", "q", "quit"):
            break
        else:
            d.error("Invalid choice.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Goodbye.")
        sys.exit(0)
