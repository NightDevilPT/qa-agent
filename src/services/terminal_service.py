"""Interactive Terminal Service for Auto-Dubber.

Provides user input prompts, single/multi-option selection menus, file path
validation, confirmation dialogs, and styled CLI summary boxes.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# ANSI Color Constants for Terminal UI
class ANSI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"


class TerminalService:
    """Service class for wrapping interactive terminal prompts and UI elements."""

    def display_header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Display a styled banner box in the terminal.

        Args:
            title: Main header title string.
            subtitle: Optional subtitle or description string.
        """
        line_length = max(60, len(title) + 10)
        border = f"{ANSI.CYAN}{'=' * line_length}{ANSI.RESET}"
        
        print(f"\n{border}")
        print(f"{ANSI.BOLD}{ANSI.WHITE}  {title.upper()}{ANSI.RESET}")
        if subtitle:
            print(f"{ANSI.DIM}  {subtitle}{ANSI.RESET}")
        print(f"{border}\n")

    def prompt_file_path(
        self,
        prompt_msg: str = "Enter media file path (video/audio)",
        default: Optional[str] = None,
        must_exist: bool = True,
    ) -> Path:
        """Prompt user for a file path with auto-cleaning and existence validation.

        Args:
            prompt_msg: Prompt label message.
            default: Optional default file path string.
            must_exist: If True, loops until user enters an existing file path.

        Returns:
            Resolved Path object.
        """
        default_str = f" [{default}]" if default else ""

        while True:
            try:
                user_input = input(f"{ANSI.CYAN}?{ANSI.RESET} {ANSI.BOLD}{prompt_msg}{default_str}:{ANSI.RESET} ").strip()
                if not user_input and default:
                    user_input = default

                clean_path = user_input.strip('\'"')
                if not clean_path:
                    print(f"  {ANSI.RED}Path cannot be empty. Please enter a valid path.{ANSI.RESET}")
                    continue

                path_obj = Path(clean_path).resolve()

                if must_exist and not path_obj.exists():
                    print(f"  {ANSI.RED}File does not exist: '{path_obj}'. Please try again.{ANSI.RESET}")
                    continue

                return path_obj
            except KeyboardInterrupt:
                print(f"\n{ANSI.YELLOW}Operation cancelled by user.{ANSI.RESET}")
                sys.exit(0)

    def prompt_select(
        self,
        prompt_msg: str,
        options: List[Dict[str, str]],
        default_index: int = 0,
    ) -> Dict[str, str]:
        """Display a numbered single-selection menu and return selected option dictionary.

        Each option dictionary must contain:
            - 'name': Human-readable option label (e.g. 'Hindi')
            - 'code': Option value or ISO code (e.g. 'hi')

        Args:
            prompt_msg: Label description.
            options: List of option dictionaries.
            default_index: Index of default option (0-indexed).

        Returns:
            Selected option dictionary.
        """
        print(f"\n{ANSI.CYAN}?{ANSI.RESET} {ANSI.BOLD}{prompt_msg}:{ANSI.RESET}")
        for idx, opt in enumerate(options, 1):
            name = opt.get("name", "Unknown")
            code = opt.get("code", "")
            code_str = f" ({code})" if code else ""
            is_default = " (default)" if (idx - 1) == default_index else ""
            print(f"  {ANSI.GREEN}[{idx}]{ANSI.RESET} {name}{code_str}{ANSI.DIM}{is_default}{ANSI.RESET}")

        while True:
            try:
                choice = input(f"{ANSI.CYAN}Select option [1-{len(options)}] (default {default_index + 1}):{ANSI.RESET} ").strip()
                if not choice:
                    return options[default_index]

                if choice.isdigit():
                    num = int(choice)
                    if 1 <= num <= len(options):
                        return options[num - 1]

                print(f"  {ANSI.RED}Invalid selection. Please enter a number between 1 and {len(options)}.{ANSI.RESET}")
            except KeyboardInterrupt:
                print(f"\n{ANSI.YELLOW}Operation cancelled by user.{ANSI.RESET}")
                sys.exit(0)

    def prompt_multi_select(
        self,
        prompt_msg: str,
        options: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """Display a numbered menu allowing user to select multiple options (comma-separated or 'all').

        Args:
            prompt_msg: Label description.
            options: List of option dictionaries.

        Returns:
            List of selected option dictionaries.
        """
        print(f"\n{ANSI.CYAN}?{ANSI.RESET} {ANSI.BOLD}{prompt_msg} (e.g. 1,3 or 'all'):{ANSI.RESET}")
        for idx, opt in enumerate(options, 1):
            name = opt.get("name", "Unknown")
            code = opt.get("code", "")
            code_str = f" ({code})" if code else ""
            print(f"  {ANSI.GREEN}[{idx}]{ANSI.RESET} {name}{code_str}")

        while True:
            try:
                user_input = input(f"{ANSI.CYAN}Select option numbers (comma-separated):{ANSI.RESET} ").strip()
                if not user_input:
                    print(f"  {ANSI.RED}Please select at least one option.{ANSI.RESET}")
                    continue

                if user_input.lower() in ("all", "*"):
                    return options

                parts = [p.strip() for p in user_input.split(",") if p.strip()]
                selected = []
                valid = True

                for p in parts:
                    if p.isdigit():
                        num = int(p)
                        if 1 <= num <= len(options):
                            selected.append(options[num - 1])
                        else:
                            valid = False
                            break
                    else:
                        valid = False
                        break

                if valid and selected:
                    return selected

                print(f"  {ANSI.RED}Invalid entry. Enter comma-separated numbers (e.g. '1, 2') or 'all'.{ANSI.RESET}")
            except KeyboardInterrupt:
                print(f"\n{ANSI.YELLOW}Operation cancelled by user.{ANSI.RESET}")
                sys.exit(0)

    def prompt_text(self, prompt_msg: str, default: Optional[str] = None) -> str:
        """Prompt user for a text input string.

        Args:
            prompt_msg: Label description.
            default: Optional default text value.

        Returns:
            Entered or default text string.
        """
        default_str = f" [{default}]" if default else ""
        while True:
            try:
                user_input = input(f"{ANSI.CYAN}?{ANSI.RESET} {ANSI.BOLD}{prompt_msg}{default_str}:{ANSI.RESET} ").strip()
                if not user_input and default is not None:
                    return default
                if user_input:
                    return user_input
                print(f"  {ANSI.RED}Input cannot be empty. Please enter text.{ANSI.RESET}")
            except KeyboardInterrupt:
                print(f"\n{ANSI.YELLOW}Operation cancelled by user.{ANSI.RESET}")
                sys.exit(0)

    def prompt_confirm(self, prompt_msg: str, default: bool = True) -> bool:
        """Prompt user for a Yes/No confirmation.

        Args:
            prompt_msg: Label message.
            default: Default boolean choice if user presses Enter.

        Returns:
            Boolean True for Yes, False for No.
        """
        opts_str = " [Y/n]" if default else " [y/N]"
        while True:
            try:
                user_input = input(f"{ANSI.CYAN}?{ANSI.RESET} {ANSI.BOLD}{prompt_msg}{opts_str}:{ANSI.RESET} ").strip().lower()
                if not user_input:
                    return default
                if user_input in ("y", "yes", "true", "1"):
                    return True
                if user_input in ("n", "no", "false", "0"):
                    return False
                print(f"  {ANSI.RED}Please enter 'y' for yes or 'n' for no.{ANSI.RESET}")
            except KeyboardInterrupt:
                print(f"\n{ANSI.YELLOW}Operation cancelled by user.{ANSI.RESET}")
                sys.exit(0)

    def display_summary(self, title: str, items: Dict[str, Any]) -> None:
        """Display a formatted summary box with key-value pairs in the terminal.

        Args:
            title: Title string for the summary box.
            items: Dictionary of key-value pairs to render.
        """
        max_key_len = max((len(str(k)) for k in items.keys()), default=15)
        box_width = max(60, max_key_len + 30)

        print(f"\n{ANSI.BLUE}+{'=' * box_width}+{ANSI.RESET}")
        print(f"{ANSI.BLUE}|{ANSI.RESET} {ANSI.BOLD}{title.center(box_width - 2)}{ANSI.RESET} {ANSI.BLUE}|{ANSI.RESET}")
        print(f"{ANSI.BLUE}+{'=' * box_width}+{ANSI.RESET}")

        for key, value in items.items():
            k_str = f"{key}:".ljust(max_key_len + 2)
            v_str = str(value)
            print(f"{ANSI.BLUE}|{ANSI.RESET}   {ANSI.CYAN}{k_str}{ANSI.RESET} {ANSI.WHITE}{v_str}{ANSI.RESET}")

        print(f"{ANSI.BLUE}+{'=' * box_width}+{ANSI.RESET}\n")


# Singleton instance for convenient direct import
terminal_service = TerminalService()
