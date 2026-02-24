from io import BytesIO

import httpx

from babel_tower.config import Settings


class STTError(Exception):
    pass


async def transcribe(audio: bytes | BytesIO, settings: Settings | None = None) -> str:
    settings = settings or Settings()
    url = f"{settings.stt_url}/v1/audio/transcriptions"

    if isinstance(audio, BytesIO):
        audio = audio.getvalue()

    files = {"file": ("audio.wav", audio, "audio/wav")}
    data = {"model": settings.stt_model, "language": settings.stt_language}

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
    return result.get("text", "").strip()
