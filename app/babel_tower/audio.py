from __future__ import annotations

import asyncio
import threading
from io import BytesIO
from typing import Any

import numpy as np
import sounddevice as sd
import soundfile as sf  # pyright: ignore[reportUnknownVariableType]
from numpy.typing import NDArray
from silero_vad import VADIterator, load_silero_vad

from babel_tower.config import Settings

VAD_CHUNK_SIZE = 512
MAX_RECORD_SECONDS = 60


class NoSpeechError(Exception):
    pass


def _record_speech_blocking(
    settings: Settings, stop_event: threading.Event | None = None
) -> BytesIO:
    model: Any = load_silero_vad(onnx=True)  # pyright: ignore[reportUnknownVariableType]
    vad = VADIterator(
        model,
        threshold=settings.vad_threshold,
        sampling_rate=settings.audio_sample_rate,
        min_silence_duration_ms=int(settings.silence_duration * 1000),
    )

    frames: list[NDArray[np.int16]] = []
    speech_started = False
    speech_ended = False
    max_chunks = int(MAX_RECORD_SECONDS * settings.audio_sample_rate / VAD_CHUNK_SIZE)

    with sd.InputStream(
        samplerate=settings.audio_sample_rate,
        channels=settings.audio_channels,
        dtype="int16",
        blocksize=VAD_CHUNK_SIZE,
    ) as stream:
        for _ in range(max_chunks):
            if stop_event and stop_event.is_set():
                break

            raw, _overflowed = stream.read(VAD_CHUNK_SIZE)  # pyright: ignore[reportUnknownMemberType]
            chunk_int16: NDArray[np.int16] = np.asarray(raw, dtype=np.int16)
            mono = chunk_int16[:, 0]

            chunk_float = mono.astype(np.float32) / 32768.0
            vad_result = vad(chunk_float)

            if vad_result is not None and "start" in vad_result:
                speech_started = True

            if speech_started:
                frames.append(np.array(mono, dtype=np.int16, copy=True))

            if vad_result is not None and "end" in vad_result:
                speech_ended = True
                break

    if not speech_started or not frames:
        raise NoSpeechError("No speech detected")

    audio_data = np.concatenate(frames)

    if not speech_ended:
        # Max duration reached without silence detection -- still return what we have
        pass

    buf = BytesIO()
    sf.write(buf, audio_data, settings.audio_sample_rate, format="WAV", subtype="PCM_16")  # pyright: ignore[reportUnknownMemberType]
    buf.seek(0)
    return buf


async def record_speech(
    settings: Settings | None = None, stop_event: threading.Event | None = None
) -> BytesIO:
    settings = settings or Settings()
    return await asyncio.to_thread(_record_speech_blocking, settings, stop_event)
