import sys
import threading

from babel_tower.audio import NoSpeechError, record_speech
from babel_tower.config import Settings
from babel_tower.output import copy_to_clipboard, notify, read_from_clipboard
from babel_tower.processing import ProcessingError, process_transcript
from babel_tower.stt import STTError, transcribe


async def run_pipeline(
    mode: str | None = None,
    settings: Settings | None = None,
    clipboard: bool = True,
    stop_event: threading.Event | None = None,
    strict: bool = False,
) -> str:
    """Record speech, transcribe, process, and output. Returns processed text.

    When strict=True, errors propagate as exceptions instead of degrading gracefully.
    """
    settings = settings or Settings()

    notify("Babel Tower", "Aufnahme gestartet...")
    try:
        audio = await record_speech(settings, stop_event=stop_event)
    except NoSpeechError:
        notify("Babel Tower", "Keine Sprache erkannt", "low")
        if strict:
            raise
        return ""

    notify("Babel Tower", "Transkribiere...")
    try:
        transcript = await transcribe(audio, settings)
    except STTError as e:
        notify("Babel Tower", f"STT-Fehler: {e}", "critical")
        if strict:
            raise
        return f"[STT-Fehler: {e}]"

    if not transcript:
        notify("Babel Tower", "Keine Sprache erkannt", "low")
        if strict:
            raise NoSpeechError("Empty transcript")
        return ""

    notify("Babel Tower", "Verarbeite...")
    try:
        result = await process_transcript(transcript, mode, settings)
    except ProcessingError as e:
        notify("Babel Tower", f"LLM-Fehler: {e}", "critical")
        if strict:
            raise
        print(f"LLM-Fehler: {e}", file=sys.stderr)
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


class ReviseError(Exception):
    pass


async def run_revise_pipeline(
    settings: Settings | None = None,
    stop_event: threading.Event | None = None,
    strict: bool = False,
) -> str:
    """Read clipboard, record change instructions, apply revision via LLM."""
    settings = settings or Settings()

    original = read_from_clipboard()
    if not original or not original.strip():
        msg = "Clipboard ist leer — nichts zum Überarbeiten"
        notify("Babel Tower", msg, "critical")
        if strict:
            raise ReviseError(msg)
        return ""

    notify("Babel Tower", "Aufnahme läuft — sprich die Änderungen")
    try:
        audio = await record_speech(settings, stop_event=stop_event)
    except NoSpeechError:
        notify("Babel Tower", "Keine Sprache erkannt", "low")
        if strict:
            raise
        return ""

    notify("Babel Tower", "Transkribiere...")
    try:
        transcript = await transcribe(audio, settings)
    except STTError as e:
        notify("Babel Tower", f"STT-Fehler: {e}", "critical")
        if strict:
            raise
        return f"[STT-Fehler: {e}]"

    if not transcript:
        notify("Babel Tower", "Keine Sprache erkannt", "low")
        if strict:
            raise NoSpeechError("Empty transcript")
        return ""

    context = f"## Originaltext\n\n{original.strip()}\n\n## Änderungsanweisungen"
    notify("Babel Tower", "Überarbeite...")
    try:
        result = await process_transcript(
            transcript, mode="revise", settings=settings, context=context
        )
    except ProcessingError as e:
        notify("Babel Tower", f"LLM-Fehler: {e}", "critical")
        if strict:
            raise
        print(f"LLM-Fehler: {e}", file=sys.stderr)
        return ""

    copy_to_clipboard(result)
    notify("Babel Tower", result[:100])

    return result


async def process_file(
    audio_path: str,
    mode: str | None = None,
    settings: Settings | None = None,
    clipboard: bool = True,
    strict: bool = False,
) -> str:
    """Process an existing audio file through the pipeline."""
    settings = settings or Settings()

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    try:
        transcript = await transcribe(audio_bytes, settings)
    except STTError as e:
        notify("Babel Tower", f"STT-Fehler: {e}", "critical")
        if strict:
            raise
        return f"[STT-Fehler: {e}]"

    if not transcript:
        notify("Babel Tower", "Keine Sprache erkannt", "low")
        if strict:
            raise NoSpeechError("Empty transcript")
        return ""

    try:
        result = await process_transcript(transcript, mode, settings)
    except ProcessingError as e:
        notify("Babel Tower", f"LLM-Fehler: {e}", "critical")
        if strict:
            raise
        print(f"LLM-Fehler: {e}", file=sys.stderr)
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
