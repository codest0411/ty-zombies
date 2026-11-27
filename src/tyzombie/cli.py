"""Command-line interface for ty-zombies (`tyzombie`)."""

import argparse
import curses
import os
import sys

from tyzombie import __version__
from tyzombie.app import App
from tyzombie.save import SaveManager


def setup_shell():
    """Configure or display shell alias/PATH instructions for `tyzombie`."""
    if sys.platform == "win32":
        profile = os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "PowerShell",
            "Microsoft.PowerShell_profile.ps1",
        )
        snippet = f'function tyzombie {{ & "{sys.executable}" -m tyzombie @args }}'
        try:
            os.makedirs(os.path.dirname(profile), exist_ok=True)
            existing = ""
            if os.path.isfile(profile):
                with open(profile, "r", encoding="utf-8") as f:
                    existing = f.read()
            if "tyzombie" not in existing:
                with open(profile, "a", encoding="utf-8") as f:
                    f.write(("\n" if existing and not existing.endswith("\n") else "") + snippet + "\n")
                print(f"Added `tyzombie` function to PowerShell profile: {profile}")
            else:
                print(f"`tyzombie` is already configured in {profile}")
        except OSError as exc:
            print(f"Could not update {profile}: {exc}", file=sys.stderr)
            print(f"Add this line manually:\n  {snippet}")
        return 0

    rc_name = ".zshrc" if "zsh" in os.environ.get("SHELL", "") else ".bashrc"
    rc_path = os.path.join(os.path.expanduser("~"), rc_name)
    snippet = f'alias tyzombie="{sys.executable} -m tyzombie"'
    try:
        existing = ""
        if os.path.isfile(rc_path):
            with open(rc_path, "r", encoding="utf-8") as f:
                existing = f.read()
        if "alias tyzombie=" not in existing:
            with open(rc_path, "a", encoding="utf-8") as f:
                f.write(("\n" if existing and not existing.endswith("\n") else "") + snippet + "\n")
            print(f"Added `tyzombie` alias to {rc_path}")
        else:
            print(f"`tyzombie` alias already present in {rc_path}")
    except OSError as exc:
        print(f"Could not update {rc_path}: {exc}", file=sys.stderr)
        print(f"Add this line manually:\n  {snippet}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tyzombie",
        description="TY-ZOMBIES: A fast, tactical terminal typing survival game.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--mode",
        choices=["campaign", "survival", "daily", "sandbox"],
        default=None,
        help="Jump directly into a specific game mode.",
    )
    parser.add_argument(
        "--seed",
        default=None,
        help="Custom seed for sandbox mode.",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Print your latest / personal-best shareable run card and exit.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("setup-shell", help="Add a `tyzombie` shell alias/function to your profile.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "setup-shell":
        return setup_shell()

    if args.record:
        mgr = SaveManager()
        card = mgr.data.get("last_run_card") or mgr.data.get("best_run_card")
        print(mgr.format_run_card(card))
        return 0

    os.environ.setdefault("ESCDELAY", "25")
    try:
        curses.wrapper(lambda stdscr: App(stdscr, start_mode=args.mode, start_seed=args.seed).main())
    except KeyboardInterrupt:
        pass
    except curses.error as exc:
        print(f"Terminal error: {exc}. Try resizing your terminal to at least 78x20.", file=sys.stderr)
        return 1
    print("The dead are still out there. See you next time.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
