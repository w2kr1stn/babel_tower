import asyncio
import threading
from pathlib import Path

import typer

app = typer.Typer(name="babel-tower", help="Voice input pipeline for Claude Code")


def _wait_for_enter(stop_event: threading.Event) -> None:
    try:
        input()
    except EOFError:
        return
    stop_event.set()


@app.command()
def listen(
    mode: str | None = typer.Option(
        None, help="Processing mode: structure, clean, durchreichen"
    ),
) -> None:
    """Record speech, transcribe, and process."""
    from babel_tower.pipeline import run_pipeline

    stop_event = threading.Event()
    thread = threading.Thread(target=_wait_for_enter, args=(stop_event,), daemon=True)
    thread.start()
    typer.echo("Aufnahme läuft — Enter zum Beenden")
    result = asyncio.run(run_pipeline(mode=mode, stop_event=stop_event))
    typer.echo(result)


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


if __name__ == "__main__":
    app()
