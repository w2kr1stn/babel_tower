from babel_tower.audio import record_speech
from babel_tower.config import Settings
from babel_tower.output import copy_to_clipboard, notify
from babel_tower.processing import process_transcript
from babel_tower.stt import transcribe


async def run_pipeline(
    mode: str | None = None,
    settings: Settings | None = None,
) -> str:
    """Record speech, transcribe, process, and output. Returns processed text."""
    settings = settings or Settings()

    notify("Babel Tower", "Aufnahme gestartet...")
    audio = await record_speech(settings)

    notify("Babel Tower", "Transkribiere...")
    transcript = await transcribe(audio, settings)

    notify("Babel Tower", "Verarbeite...")
    result = await process_transcript(transcript, mode, settings)

    copy_to_clipboard(result)
    notify("Babel Tower", result[:100])

    return result


async def process_file(
    audio_path: str,
    mode: str | None = None,
    settings: Settings | None = None,
) -> str:
    """Process an existing audio file through the pipeline."""
    settings = settings or Settings()

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    transcript = await transcribe(audio_bytes, settings)
    result = await process_transcript(transcript, mode, settings)

    copy_to_clipboard(result)
    notify("Babel Tower", result[:100])

    return result
