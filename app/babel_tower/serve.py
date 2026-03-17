"""HTTP service endpoint: audio file → clean transcript."""

import tempfile
from pathlib import Path

from loguru import logger
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from babel_tower.config import Settings
from babel_tower.processing import ProcessingError, process_transcript
from babel_tower.stt import STTError, transcribe


async def process_endpoint(request: Request) -> JSONResponse:
    """
    POST /process

    Accepts: multipart/form-data with:
      - file: audio file (required)
      - mode: processing mode string (optional, defaults to settings.default_mode)

    Returns: {"text": "<cleaned>", "transcript": "<raw>"}
    """
    try:
        form = await request.form()
    except Exception as e:
        return JSONResponse({"error": f"Invalid form data: {e}"}, status_code=400)

    audio_file = form.get("file")
    if audio_file is None:
        return JSONResponse({"error": "Missing 'file' field"}, status_code=422)

    mode = form.get("mode") or None

    audio_bytes = await audio_file.read()
    if not audio_bytes:
        return JSONResponse({"error": "Empty audio file"}, status_code=422)

    # Write to temp file — process_file expects a path
    suffix = Path(getattr(audio_file, "filename", "audio.wav")).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        settings = Settings()

        with open(tmp_path, "rb") as f:
            raw_audio = f.read()

        transcript = await transcribe(raw_audio, settings)

        if not transcript:
            return JSONResponse({"text": "", "transcript": ""})

        try:
            cleaned = await process_transcript(transcript, mode, settings)
        except ProcessingError as e:
            logger.warning("LLM postprocessing failed, returning raw transcript: {}", e)
            cleaned = transcript

        return JSONResponse({"text": cleaned, "transcript": transcript})

    except STTError as e:
        logger.error("STT error in serve endpoint: {}", e)
        return JSONResponse({"error": f"STT error: {e}"}, status_code=502)
    except Exception as e:
        logger.error("Unexpected error in serve endpoint: {}", e)
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def create_app() -> Starlette:
    """Create the Starlette ASGI application."""
    return Starlette(
        routes=[
            Route("/process", process_endpoint, methods=["POST"]),
        ],
    )
