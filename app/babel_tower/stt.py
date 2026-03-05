import re
from io import BytesIO

import httpx

from babel_tower.config import Settings


class STTError(Exception):
    pass


def _parse_corrections(raw: str) -> list[tuple[re.Pattern[str], str]]:
    pairs: list[tuple[re.Pattern[str], str]] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" not in entry:
            continue
        wrong, right = entry.split(":", 1)
        if wrong.strip() and right.strip():
            pairs.append((re.compile(re.escape(wrong.strip()), re.IGNORECASE), right.strip()))
    return pairs


def apply_corrections(text: str, settings: Settings) -> str:
    if not settings.stt_corrections:
        return text
    for pattern, replacement in _parse_corrections(settings.stt_corrections):
        text = pattern.sub(replacement, text)
    return text


async def transcribe(audio: bytes | BytesIO, settings: Settings | None = None) -> str:
    settings = settings or Settings()
    url = f"{settings.stt_url}/v1/audio/transcriptions"

    if isinstance(audio, BytesIO):
        audio = audio.getvalue()

    files = {"file": ("audio.wav", audio, "audio/wav")}
    data: dict[str, str] = {"model": settings.stt_model, "language": settings.stt_language}
    if settings.stt_hotwords:
        data["hotwords"] = settings.stt_hotwords
    if settings.stt_prompt:
        data["prompt"] = settings.stt_prompt

    async with httpx.AsyncClient(timeout=settings.stt_timeout) as client:
        try:
            response = await client.post(url, files=files, data=data)
        except httpx.ConnectError as e:
            raise STTError(f"STT service unreachable at {settings.stt_url}") from e
        except httpx.TimeoutException as e:
            raise STTError("STT request timed out") from e

    if response.status_code != 200:
        raise STTError(f"STT returned {response.status_code}: {response.text}")

    result = response.json()
    text = result.get("text", "").strip()
    return apply_corrections(text, settings)
