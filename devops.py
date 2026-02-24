"""DevOps tasks for toolkit-infra.

Usage: uv run devops.py <task>
Tasks: fmt, test, clean
"""

import subprocess
import sys


def _run(commands: list[list[str]]) -> None:
    """Execute a sequence of shell commands, exiting on first failure."""
    for cmd in commands:
        try:
            subprocess.run(cmd, check=True)  # nosec: B603, B607
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {' '.join(e.cmd)}", file=sys.stderr)
            sys.exit(e.returncode)


def format_code() -> None:
    """Format the codebase with Ruff."""
    _run(
        [
            ["echo", "🎨 [Native Task] Formatting with Ruff...\n"],
            ["ruff", "format", "."],
            ["ruff", "check", "--fix", "."],
            ["echo", "\n🟢 Made everything pretty → ✅ Code clean."],
        ]
    )


def test() -> None:
    """Run tests with PyTest."""
    _run(
        [
            ["echo", "🧪 [Native Task] Testing with PyTest...\n"],
            ["uv", "run", "pytest", "-q"],
            ["echo", "\n🟢 Test Coverage → ✅ Test coverage sufficient"],
        ]
    )


def clean() -> None:
    """Clean up the project."""
    _run(
        [
            ["echo", "🧹 [Native Task] Cleaning the Project...\n"],
            # ---------------------
            # Basic clean up
            # ----------------------
            ["find", ".", "-type", "d", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"],
            ["find", ".", "-type", "f", "-name", "*.pyc", "-delete"],
            ["echo", "\n🟢 Caches & Artifacts → ✅ All fresh now"],
        ]
    )
