"""Interactive CLI Model Selector for Neuromancer."""

import os
import sys
import select
import json
import urllib.request
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
    {
        "id": "ollama/qwen2.5:3b",
        "label": "ollama/qwen2.5:3b (Local Core - Fast CPU Tool Caller, Recommended for VMs)",
    },
    {
        "id": "ollama/llama3.2:3b",
        "label": "ollama/llama3.2:3b (Local Core - Fast 3B CPU Inference)",
    },
    {
        "id": "ollama/qwen2.5:7b",
        "label": "ollama/qwen2.5:7b (Local Core - High Precision Function Calling)",
    },
    {
        "id": "ollama/llama3.1:8b",
        "label": "ollama/llama3.1:8b (Local Core - Llama 3.1 Function Calling)",
    },
    {
        "id": "ollama/qwen2.5:14b",
        "label": "ollama/qwen2.5:14b (Local Core - 14B High Precision)",
    },
    {
        "id": "ollama/mistral:7b",
        "label": "ollama/mistral:7b (Local Core - Mistral 7B)",
    },
]


def discover_local_ollama_models(api_base: Optional[str] = None) -> List[Dict[str, str]]:
    """Auto-discover locally installed Ollama models and prepend to selector list."""
    base = api_base or os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    url = f"{base.rstrip('/')}/api/tags"
    discovered: List[Dict[str, str]] = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Neuromancer/1.0"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            if resp.status == 200:
                payload = json.loads(resp.read().decode("utf-8"))
                raw_models = payload.get("models", [])
                for item in raw_models:
                    raw_name = item.get("name") or item.get("model")
                    if not raw_name:
                        continue
                    model_id = raw_name if raw_name.startswith("ollama/") else f"ollama/{raw_name}"
                    discovered.append({
                        "id": model_id,
                        "label": f"{model_id} [Installed Ollama]"
                    })
    except Exception:
        return list(MODELS)

    if not discovered:
        return list(MODELS)

    discovered_ids = {m["id"] for m in discovered}
    remaining_static = [m for m in MODELS if m["id"] not in discovered_ids]
    return discovered + remaining_static


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


def get_current_model_index(default: int = 0, models: Optional[List[Dict[str, str]]] = None) -> int:
    """Return index of current model from .env or default."""
    model_list = models if models is not None else MODELS
    current = get_current_model()
    if current:
        for idx, m in enumerate(model_list):
            if m["id"] == current:
                return idx
    return default


def update_env_model(
    model_name: str,
    env_path: Optional[Path] = None,
    ollama_api_base: Optional[str] = None
) -> Path:
    """Update or create .env with LITELLM_MODEL_NAME and OLLAMA_API_BASE if appropriate."""
    if env_path is None:
        target_path = get_env_path()
    else:
        target_path = Path(env_path)

    is_ollama = model_name.startswith("ollama/") or model_name.startswith("ollama_chat/")
    base_val = ollama_api_base or (os.getenv("OLLAMA_API_BASE", "http://localhost:11434") if is_ollama else None)

    lines: List[str] = []
    if target_path.exists():
        try:
            lines = target_path.read_text().splitlines()
        except Exception:
            lines = []

    model_found = False
    ollama_found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("LITELLM_MODEL_NAME="):
            new_lines.append(f"LITELLM_MODEL_NAME={model_name}")
            model_found = True
        elif stripped.startswith("OLLAMA_API_BASE="):
            if is_ollama and base_val:
                new_lines.append(f"OLLAMA_API_BASE={base_val}")
                ollama_found = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if not model_found:
        new_lines.append(f"LITELLM_MODEL_NAME={model_name}")
    if is_ollama and base_val and not ollama_found:
        new_lines.append(f"OLLAMA_API_BASE={base_val}")

    target_path.write_text("\n".join(new_lines) + "\n")
    return target_path


def _non_tty_select(default_index: int = 0, models: Optional[List[Dict[str, str]]] = None) -> str:
    """Graceful fallback for non-TTY or piped environments."""
    model_list = models if models is not None else MODELS
    print("\nNeuromancer Neural Model Selection:")
    for idx, model in enumerate(model_list, start=1):
        marker = "*" if idx - 1 == default_index else " "
        print(f" {marker} {idx}) {model['label']}")

    default_model = model_list[default_index]["id"] if default_index < len(model_list) else model_list[0]["id"]
    try:
        prompt_text = f"\nSelect model [1-{len(model_list)}] (default: {default_index + 1}): "
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
            if 0 <= idx < len(model_list):
                return model_list[idx]["id"]
        for m in model_list:
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


def select_model_interactive(default_index: int = 0, models: Optional[List[Dict[str, str]]] = None) -> str:
    """Interactive CLI menu to select a model.

    Supports Up/Down arrow keys (and j/k), direct number keys (1..N),
    Enter to select, and graceful non-tty fallback.
    """
    model_list = models if models is not None else discover_local_ollama_models()

    # Sanitize default_index
    if isinstance(default_index, str):
        found = False
        for i, m in enumerate(model_list):
            if m["id"] == default_index or m["label"] == default_index:
                default_index = i
                found = True
                break
        if not found:
            default_index = 0
    elif not isinstance(default_index, int) or default_index < 0 or default_index >= len(model_list):
        default_index = 0

    # Non-TTY fallback check
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return _non_tty_select(default_index, models=model_list)

    try:
        import termios
        import tty
    except ImportError:
        return _non_tty_select(default_index, models=model_list)

    fd = sys.stdin.fileno()
    try:
        old_settings = termios.tcgetattr(fd)
    except Exception:
        return _non_tty_select(default_index, models=model_list)

    num_models = len(model_list)
    selected_index = default_index

    header = (
        "\r\n\033[1;35m--- NEUROMANCER NEURAL MODEL MENU ---\033[0m\r\n"
        f"\033[90m[↑/↓ / j/k: Navigate | 1-{min(num_models, 9)}: Direct Select | Enter: Confirm]\033[0m\r\n"
    )
    sys.stdout.write(header)
    sys.stdout.flush()

    def render_menu(current_idx: int) -> str:
        lines = []
        for idx, model in enumerate(model_list, start=1):
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
        selected_model = model_list[selected_index]["id"]
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
    available_models = discover_local_ollama_models()
    current_idx = get_current_model_index(default=0, models=available_models)
    try:
        chosen_model = select_model_interactive(default_index=current_idx, models=available_models)
        update_env_model(chosen_model)
        print(f"[+] Switched neural model to: {chosen_model}")
    except KeyboardInterrupt:
        print("\n[!] Model selection cancelled.")
        sys.exit(130)
