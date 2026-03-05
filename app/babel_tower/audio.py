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
    ever_had_speech = False
    max_chunks = int(settings.max_record_seconds * settings.audio_sample_rate / VAD_CHUNK_SIZE)
    timeout_chunks = int(
        settings.inter_segment_timeout * settings.audio_sample_rate / VAD_CHUNK_SIZE
    )
    inter_segment_deadline: int | None = None
    chunk_index = 0

    with sd.InputStream(
        samplerate=settings.audio_sample_rate,
        channels=settings.audio_channels,
        dtype="int16",
        blocksize=VAD_CHUNK_SIZE,
    ) as stream:
        for chunk_index in range(max_chunks):
            if stop_event and stop_event.is_set():
                break

            # Inter-segment timeout expired — done recording
            if inter_segment_deadline is not None and chunk_index >= inter_segment_deadline:
                break

            raw, _overflowed = stream.read(VAD_CHUNK_SIZE)  # pyright: ignore[reportUnknownMemberType]
            chunk_int16: NDArray[np.int16] = np.asarray(raw, dtype=np.int16)
            mono = chunk_int16[:, 0]

            chunk_float = mono.astype(np.float32) / 32768.0
            vad_result = vad(chunk_float)

            if vad_result is not None and "start" in vad_result:
                speech_started = True
                ever_had_speech = True
                inter_segment_deadline = None

            if speech_started:
                frames.append(np.array(mono, dtype=np.int16, copy=True))

            if vad_result is not None and "end" in vad_result:
                speech_started = False
                if timeout_chunks > 0:
                    # Multi-segment: wait for more speech
                    vad.reset_states()  # pyright: ignore[reportUnknownMemberType]
                    inter_segment_deadline = chunk_index + timeout_chunks
                else:
                    # Legacy single-segment: stop immediately
                    break

    if not ever_had_speech or not frames:
        raise NoSpeechError("No speech detected")

    audio_data = np.concatenate(frames)
    buf = BytesIO()
    sf.write(buf, audio_data, settings.audio_sample_rate, format="WAV", subtype="PCM_16")  # pyright: ignore[reportUnknownMemberType]
    buf.seek(0)
    return buf


async def record_speech(
    settings: Settings | None = None, stop_event: threading.Event | None = None
) -> BytesIO:
    settings = settings or Settings()
    return await asyncio.to_thread(_record_speech_blocking, settings, stop_event)
