"""Interactive CLI Model Selector for Neuromancer."""

import os
import sys
import select
from pathlib import Path
from typing import List, Dict, Optional

MODELS: List[Dict[str, str]] = [
    {
        "id": "gemini/gemini-2.5-flash",
        "label": "gemini/gemini-2.5-flash (Free Tier Recommended)",
    },
    {
        "id": "gemini/gemini-flash-latest",
        "label": "gemini/gemini-flash-latest",
    },
    {
        "id": "gemini/gemini-3.1-pro-preview",
        "label": "gemini/gemini-3.1-pro-preview",
    },
    {
        "id": "gemini/gemini-3.5-flash-lite",
        "label": "gemini/gemini-3.5-flash-lite",
    },
    {
        "id": "vertex_ai/gemini-3.1-pro",
        "label": "vertex_ai/gemini-3.1-pro",
    },
    {
        "id": "gemini/antigravity-preview-09-2026",
        "label": "gemini/antigravity-preview-09-2026",
    },
]


def get_project_root() -> Path:
    """Resolve project root directory."""
    return Path(__file__).resolve().parent.parent


def get_env_path() -> Path:
    """Find the path to the .env file."""
    root = get_project_root()
    root_env = root / ".env"
    if root_env.exists():
        return root_env
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env
    return root_env


def get_current_model() -> Optional[str]:
    """Retrieve current LITELLM_MODEL_NAME from .env if present."""
    env_path = get_env_path()
    if env_path.exists():
        try:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("LITELLM_MODEL_NAME="):
                    return line.split("=", 1)[1].strip()
        except Exception:
            pass
    return None


def get_current_model_index(default: int = 0) -> int:
    """Return index of current model from .env or default."""
    current = get_current_model()
    if current:
        for idx, m in enumerate(MODELS):
            if m["id"] == current:
                return idx
    return default


def update_env_model(model_name: str, env_path: Optional[Path] = None) -> Path:
    """Update or create .env with LITELLM_MODEL_NAME."""
    if env_path is None:
        target_path = get_env_path()
    else:
        target_path = Path(env_path)

    if target_path.exists():
        try:
            lines = target_path.read_text().splitlines()
        except Exception:
            lines = []
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("LITELLM_MODEL_NAME="):
                new_lines.append(f"LITELLM_MODEL_NAME={model_name}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"LITELLM_MODEL_NAME={model_name}")
        target_path.write_text("\n".join(new_lines) + "\n")
    else:
        target_path.write_text(f"LITELLM_MODEL_NAME={model_name}\n")

    return target_path


def _non_tty_select(default_index: int = 0) -> str:
    """Graceful fallback for non-TTY or piped environments."""
    print("\nNeuromancer Neural Model Selection:")
    for idx, model in enumerate(MODELS, start=1):
        marker = "*" if idx - 1 == default_index else " "
        print(f" {marker} {idx}) {model['label']}")

    default_model = MODELS[default_index]["id"]
    try:
        prompt_text = f"\nSelect model [1-{len(MODELS)}] (default: {default_index + 1}): "
        sys.stdout.write(prompt_text)
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            return default_model
        choice = line.strip()
        if not choice:
            return default_model
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(MODELS):
                return MODELS[idx]["id"]
        for m in MODELS:
            if choice.lower() in (m["id"].lower(), m["label"].lower()):
                return m["id"]
        return default_model
    except (EOFError, KeyboardInterrupt):
        return default_model


def _read_key(fd: int) -> str:
    """Read a single keypress or escape sequence from file descriptor."""
    b = os.read(fd, 1)
    if b == b"\x1b":
        # Check if more bytes are waiting (ANSI escape sequence)
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            b2 = os.read(fd, 1)
            if b2 in (b"[", b"O"):
                r, _, _ = select.select([fd], [], [], 0.05)
                if r:
                    b3 = os.read(fd, 1)
                    if b3 == b"A":
                        return "UP"
                    elif b3 == b"B":
                        return "DOWN"
                    elif b3 == b"C":
                        return "RIGHT"
                    elif b3 == b"D":
                        return "LEFT"
        return "ESC"
    elif b in (b"\r", b"\n"):
        return "ENTER"
    elif b == b" ":
        return "SPACE"
    elif b == b"\x03":
        return "CTRL_C"
    elif b == b"\x04":
        return "CTRL_D"
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def select_model_interactive(default_index: int = 0) -> str:
    """Interactive CLI menu to select a model.

    Supports Up/Down arrow keys (and j/k), direct number keys (1..N),
    Enter to select, and graceful non-tty fallback.
    """
    # Sanitize default_index
    if isinstance(default_index, str):
        found = False
        for i, m in enumerate(MODELS):
            if m["id"] == default_index or m["label"] == default_index:
                default_index = i
                found = True
                break
        if not found:
            default_index = 0
    elif not isinstance(default_index, int) or default_index < 0 or default_index >= len(MODELS):
        default_index = 0

    # Non-TTY fallback check
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return _non_tty_select(default_index)

    try:
        import termios
        import tty
    except ImportError:
        return _non_tty_select(default_index)

    fd = sys.stdin.fileno()
    try:
        old_settings = termios.tcgetattr(fd)
    except Exception:
        return _non_tty_select(default_index)

    num_models = len(MODELS)
    selected_index = default_index

    header = (
        "\r\n\033[1;35m--- NEUROMANCER NEURAL MODEL MENU ---\033[0m\r\n"
        "\033[90m[↑/↓ / j/k: Navigate | 1-6: Direct Select | Enter: Confirm]\033[0m\r\n"
    )
    sys.stdout.write(header)
    sys.stdout.flush()

    def render_menu(current_idx: int) -> str:
        lines = []
        for idx, model in enumerate(MODELS, start=1):
            if idx - 1 == current_idx:
                lines.append(f"\033[K\033[1;36m > {idx}) {model['label']}\033[0m\r\n")
            else:
                lines.append(f"\033[K   {idx}) {model['label']}\r\n")
        return "".join(lines)

    # First render
    sys.stdout.write("\033[?25l")  # Hide cursor
    sys.stdout.write(render_menu(selected_index))
    sys.stdout.flush()

    try:
        tty.setraw(fd)
        while True:
            key = _read_key(fd)

            if key == "CTRL_C":
                raise KeyboardInterrupt
            elif key in ("ENTER", "SPACE"):
                break
            elif key in ("UP", "k", "K"):
                selected_index = (selected_index - 1) % num_models
                # Move cursor back up and re-render
                sys.stdout.write(f"\033[{num_models}A\r")
                sys.stdout.write(render_menu(selected_index))
                sys.stdout.flush()
            elif key in ("DOWN", "j", "J"):
                selected_index = (selected_index + 1) % num_models
                # Move cursor back up and re-render
                sys.stdout.write(f"\033[{num_models}A\r")
                sys.stdout.write(render_menu(selected_index))
                sys.stdout.flush()
            elif key.isdigit():
                num = int(key)
                if 1 <= num <= num_models:
                    selected_index = num - 1
                    # Direct selection via number key
                    break

        # Flush any remaining unread input
        try:
            termios.tcflush(fd, termios.TCIFLUSH)
        except Exception:
            pass

        # Clear menu lines and print selected model
        sys.stdout.write(f"\033[{num_models}A\r\033[J")
        selected_model = MODELS[selected_index]["id"]
        sys.stdout.write(f"\033[1;32m[+] Selected model: {selected_model}\033[0m\r\n")
        sys.stdout.flush()
        return selected_model

    finally:
        # Restore terminal settings and show cursor
        try:
            termios.tcsetattr(fd, termios.TCSANOW, old_settings)
        except Exception:
            pass
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


if __name__ == "__main__":
    current_idx = get_current_model_index(default=0)
    try:
        chosen_model = select_model_interactive(default_index=current_idx)
        update_env_model(chosen_model)
        print(f"[+] Switched neural model to: {chosen_model}")
    except KeyboardInterrupt:
        print("\n[!] Model selection cancelled.")
        sys.exit(130)
