from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Any

import httpx
import sounddevice as sd
import soundfile as sf  # pyright: ignore[reportUnknownVariableType]

from babel_tower.config import Settings


class TTSError(Exception):
    pass


async def synthesize(text: str, settings: Settings) -> bytes:
    url = f"{settings.tts_url}/v1/audio/speech"
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": settings.tts_voice,
        "response_format": "wav",
    }

    async with httpx.AsyncClient(timeout=settings.tts_timeout) as client:
        try:
            response = await client.post(url, json=payload)
        except httpx.ConnectError as e:
            raise TTSError(f"TTS service unreachable at {settings.tts_url}") from e
        except httpx.TimeoutException as e:
            raise TTSError("TTS request timed out") from e

    if response.status_code != 200:
        raise TTSError(f"TTS returned {response.status_code}: {response.text}")

    return response.content


def _play_audio_blocking(audio_bytes: bytes) -> None:
    data: Any
    sr: int
    data, sr = sf.read(BytesIO(audio_bytes))  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    sd.play(data, sr)  # pyright: ignore[reportUnknownMemberType]
    sd.wait()  # pyright: ignore[reportUnknownMemberType]


async def speak(text: str, settings: Settings) -> None:
    audio_bytes = await synthesize(text, settings)
    await asyncio.to_thread(_play_audio_blocking, audio_bytes)
