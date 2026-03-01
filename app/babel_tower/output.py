import subprocess


def read_from_clipboard() -> str | None:
    """Read text from clipboard via wl-paste. Returns None on failure."""
    try:
        result = subprocess.run(
            ["wl-paste", "--no-newline"],
            check=True,
            timeout=5,
            capture_output=True,
            text=True,
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard via wl-copy. Returns True on success."""
    try:
        subprocess.run(
            ["wl-copy", text],
            check=True,
            timeout=5,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def notify(title: str, body: str, urgency: str = "normal") -> bool:
    """Send desktop notification via notify-send. Returns True on success."""
    try:
        subprocess.run(
            ["notify-send", f"--urgency={urgency}", title, body[:200]],
            check=True,
            timeout=5,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False
