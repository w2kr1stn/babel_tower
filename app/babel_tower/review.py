import subprocess


def review_text(text: str) -> str | None:
    """Show text in rofi for editing. Returns edited text or None if dismissed."""
    try:
        result = subprocess.run(
            ["rofi", "-dmenu", "-p", "Babel Tower", "-filter", text, "-l", "0"],
            input="",
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if result.returncode != 0:
        return None

    return result.stdout.strip()
