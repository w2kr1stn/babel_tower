import asyncio
import threading
from pathlib import Path

import typer

app = typer.Typer(name="babel", help="Voice input pipeline for Claude Code")


def _wait_for_enter(stop_event: threading.Event) -> None:
    try:
        input()
    except EOFError:
        return
    stop_event.set()


def _listen(mode: str | None = None) -> None:
    from babel_tower.pipeline import run_pipeline

    stop_event = threading.Event()
    thread = threading.Thread(target=_wait_for_enter, args=(stop_event,), daemon=True)
    thread.start()
    typer.echo("Aufnahme läuft — Enter zum Beenden")
    result = asyncio.run(run_pipeline(mode=mode, stop_event=stop_event))
    typer.echo(result)


@app.command()
def clean() -> None:
    """Record speech → clean transcript (Fließtext)."""
    _listen("clean")


@app.command()
def structure() -> None:
    """Record speech → structured Markdown output."""
    _listen("structure")


@app.command()
def listen(
    mode: str | None = typer.Option(
        None, help="Processing mode: structure, clean, durchreichen"
    ),
) -> None:
    """Record speech with explicit mode (default from config)."""
    _listen(mode)


@app.command()
def process(
    audio_file: Path = typer.Argument(..., help="Path to WAV file"),
    mode: str | None = typer.Option(None, help="Processing mode"),
) -> None:
    """Process an existing audio file."""
    from babel_tower.pipeline import process_file

    if not audio_file.exists():
        typer.echo(f"File not found: {audio_file}", err=True)
        raise typer.Exit(1)
    result = asyncio.run(process_file(str(audio_file), mode=mode))
    typer.echo(result)


@app.command()
def daemon(
    mode: str | None = typer.Option(
        None, help="Default processing mode for this session"
    ),
) -> None:
    """Start continuous voice listening daemon."""
    from babel_tower.config import Settings
    from babel_tower.daemon import VoiceDaemon

    settings = Settings()
    if mode:
        settings.default_mode = mode
    d = VoiceDaemon(settings=settings)
    asyncio.run(d.run())


@app.command()
def mcp() -> None:
    """Start MCP server (STDIO transport for Claude Code)."""
    from babel_tower.mcp_server import mcp as mcp_server

    mcp_server.run()


@app.command()
def debug() -> None:
    """Show resolved settings and test connectivity."""
    from babel_tower.config import Settings
    from babel_tower.processing import get_available_modes, resolve_prompts_dir

    settings = Settings()
    key = settings.llm_api_key
    masked_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else ("(set)" if key else "(empty)")

    typer.echo("=== Settings ===")
    typer.echo(f"llm_url:      {settings.llm_url}")
    typer.echo(f"llm_model:    {settings.llm_model}")
    typer.echo(f"llm_api_key:  {masked_key}")
    typer.echo(f"llm_timeout:  {settings.llm_timeout}s")
    typer.echo(f"stt_url:      {settings.stt_url}")
    typer.echo(f"default_mode: {settings.default_mode}")

    prompts_dir = resolve_prompts_dir(settings)
    typer.echo("\n=== Prompts ===")
    typer.echo(f"prompts_dir:  {prompts_dir}")
    typer.echo(f"exists:       {prompts_dir.exists()}")
    formatting = prompts_dir / "_formatting.md"
    typer.echo(f"_formatting:  {formatting.exists()}")
    typer.echo(f"modes:        {sorted(get_available_modes(settings))}")

    import httpx

    typer.echo("\n=== Connectivity ===")
    headers: dict[str, str] = {}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    try:
        r = httpx.get(f"{settings.llm_url}/v1/models", headers=headers, timeout=5)
        typer.echo(f"LLM ({settings.llm_url}): {r.status_code}")
    except httpx.ConnectError:
        typer.echo(f"LLM ({settings.llm_url}): UNREACHABLE", err=True)
    try:
        r = httpx.get(f"{settings.stt_url}/v1/models", timeout=5)
        typer.echo(f"STT ({settings.stt_url}): {r.status_code}")
    except httpx.ConnectError:
        typer.echo(f"STT ({settings.stt_url}): UNREACHABLE", err=True)


if __name__ == "__main__":
    app()
