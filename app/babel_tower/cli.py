import asyncio
from pathlib import Path

import typer

app = typer.Typer(name="babel-tower", help="Voice input pipeline for Claude Code")


@app.command()
def listen(
    mode: str | None = typer.Option(
        None, help="Processing mode: strukturieren, bereinigen, durchreichen"
    ),
) -> None:
    """Record speech, transcribe, and process."""
    from babel_tower.pipeline import run_pipeline

    result = asyncio.run(run_pipeline(mode=mode))
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


if __name__ == "__main__":
    app()
