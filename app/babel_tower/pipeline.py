import sys
import threading

from babel_tower.audio import NoSpeechError, record_speech
from babel_tower.config import Settings
from babel_tower.output import copy_to_clipboard, notify
from babel_tower.processing import ProcessingError, process_transcript
from babel_tower.stt import STTError, transcribe


async def run_pipeline(
    mode: str | None = None,
    settings: Settings | None = None,
    clipboard: bool = True,
    stop_event: threading.Event | None = None,
) -> str:
    """Record speech, transcribe, process, and output. Returns processed text."""
    settings = settings or Settings()

    notify("Babel Tower", "Aufnahme gestartet...")
    try:
        audio = await record_speech(settings, stop_event=stop_event)
    except NoSpeechError:
        notify("Babel Tower", "Keine Sprache erkannt", "low")
        return ""

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
    except ProcessingError as e:
        print(f"LLM-Fehler: {e}", file=sys.stderr)
        notify("Babel Tower", f"LLM-Fehler: {e}", "critical")
        result = transcript

    if settings.review_enabled:
        from babel_tower.review import review_text

        reviewed = review_text(result)
        if reviewed is None:
            notify("Babel Tower", "Verworfen", "low")
            return ""
        result = reviewed

    if clipboard:
        copy_to_clipboard(result)
        notify("Babel Tower", result[:100])

    return result


async def process_file(
    audio_path: str,
    mode: str | None = None,
    settings: Settings | None = None,
    clipboard: bool = True,
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
    except ProcessingError as e:
        print(f"LLM-Fehler: {e}", file=sys.stderr)
        notify("Babel Tower", f"LLM-Fehler: {e}", "critical")
        result = transcript

    if settings.review_enabled:
        from babel_tower.review import review_text

        reviewed = review_text(result)
        if reviewed is None:
            notify("Babel Tower", "Verworfen", "low")
            return ""
        result = reviewed

    if clipboard:
        copy_to_clipboard(result)
        notify("Babel Tower", result[:100])

    return result
