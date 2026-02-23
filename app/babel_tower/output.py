import subprocess


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
