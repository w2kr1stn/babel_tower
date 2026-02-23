from babel_tower.audio import record_speech
from babel_tower.config import Settings
from babel_tower.output import copy_to_clipboard, notify
from babel_tower.processing import ProcessingError, process_transcript
from babel_tower.stt import STTError, transcribe


async def run_pipeline(
    mode: str | None = None,
    settings: Settings | None = None,
) -> str:
    """Record speech, transcribe, process, and output. Returns processed text."""
    settings = settings or Settings()

    notify("Babel Tower", "Aufnahme gestartet...")
    audio = await record_speech(settings)

    notify("Babel Tower", "Transkribiere...")
    try:
        transcript = await transcribe(audio, settings)
    except STTError as e:
        notify("Babel Tower", f"STT-Fehler: {e}", "critical")
        return f"[STT-Fehler: {e}]"

    if not transcript:
        notify("Babel Tower", "Keine Sprache erkannt", "low")
        return ""

    notify("Babel Tower", "Verarbeite...")
    try:
        result = await process_transcript(transcript, mode, settings)
    except ProcessingError:
        notify("Babel Tower", "M5 offline — Roh-Transkript verwendet", "normal")
        result = transcript

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

    try:
        transcript = await transcribe(audio_bytes, settings)
    except STTError as e:
        notify("Babel Tower", f"STT-Fehler: {e}", "critical")
        return f"[STT-Fehler: {e}]"

    if not transcript:
        notify("Babel Tower", "Keine Sprache erkannt", "low")
        return ""

    try:
        result = await process_transcript(transcript, mode, settings)
    except ProcessingError:
        notify("Babel Tower", "M5 offline — Roh-Transkript verwendet", "normal")
        result = transcript

    copy_to_clipboard(result)
    notify("Babel Tower", result[:100])

    return result
