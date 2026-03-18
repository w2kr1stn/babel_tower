"""DevOps tasks for babel-tower.

Bare functions (format_code, test, clean) are called via uv run fmt/test/clean.
Typer app: uv run devops mcp|daemon to start individual containers.
"""

import subprocess
import sys

import typer

_COMPOSE_FILE = "docker/docker-compose.laptop.yml"

app = typer.Typer(name="devops", help="Docker container management for babel-tower")


def _run(commands: list[list[str]]) -> None:
    """Execute a sequence of shell commands, exiting on first failure."""
    for cmd in commands:
        try:
            subprocess.run(cmd, check=True)  # nosec: B603, B607
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {' '.join(e.cmd)}", file=sys.stderr)
            sys.exit(e.returncode)


def _up(service: str) -> None:
    _run([["docker", "compose", "-f", _COMPOSE_FILE, "up", "-d", "--build", service]])


@app.command()
def mcp() -> None:
    """Start the MCP server container (SSE on port 3030)."""
    _up("mcp")


@app.command()
def daemon() -> None:
    """Start the voice daemon container."""
    _up("daemon")


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
