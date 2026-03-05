from __future__ import annotations

import sys
import threading
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf
from numpy.typing import NDArray

# sounddevice requires PortAudio at import time; stub it for CI/headless environments
if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = MagicMock()

from babel_tower.audio import NoSpeechError, _record_speech_blocking  # noqa: E402
from babel_tower.config import Settings  # noqa: E402


def _make_chunk(value: float = 0.0, size: int = 512) -> NDArray[np.int16]:
    """Create a mono int16 audio chunk reshaped as (size, 1) like sounddevice returns."""
    amplitude = int(value * 32767)
    return np.full((size, 1), amplitude, dtype=np.int16)


class FakeStream:
    """Mock for sd.InputStream that yields pre-defined chunks."""

    def __init__(self, chunks: list[NDArray[np.int16]]) -> None:
        self._chunks = iter(chunks)

    def read(self, _frames: int) -> tuple[NDArray[np.int16], bool]:
        try:
            return next(self._chunks), False
        except StopIteration:
            return _make_chunk(0.0), False

    def __enter__(self) -> FakeStream:
        return self

    def __exit__(self, *_args: object) -> None:
        pass


class FakeVADIterator:
    """Mock VADIterator that returns start/end events at configurable positions.

    Supports multi-segment via events list: [(start1, end1), (start2, end2), ...].
    Default: single segment at calls 2-5 (backward compatible).
    """

    def __init__(
        self,
        _model: Any,
        threshold: float = 0.5,
        sampling_rate: int = 16000,
        min_silence_duration_ms: int = 1500,
    ) -> None:
        self._call_count = 0
        self._events: list[tuple[int, int]] = [(2, 5)]

    def configure(self, start_at: int, end_at: int) -> None:
        self._events = [(start_at, end_at)]

    def configure_multi(self, events: list[tuple[int, int]]) -> None:
        self._events = events

    def reset_states(self) -> None:
        pass

    def __call__(self, _x: Any, **_kwargs: Any) -> dict[str, int] | None:
        self._call_count += 1
        for start, end in self._events:
            if self._call_count == start:
                return {"start": 0}
            if self._call_count == end:
                return {"end": self._call_count * 512}
        return None


class FakeVADIteratorNoSpeech:
    """VADIterator mock that never detects speech."""

    def __init__(self, _model: Any, **_kwargs: Any) -> None:
        pass

    def __call__(self, _x: Any, **_kwargs: Any) -> None:
        return None


def _make_settings(inter_segment_timeout: float = 0.0) -> Settings:
    return Settings(
        audio_sample_rate=16000,
        audio_channels=1,
        vad_threshold=0.5,
        silence_duration=2.0,
        inter_segment_timeout=inter_segment_timeout,
    )


class TestRecordSpeechBlocking:
    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.VADIterator", FakeVADIterator)
    @patch("babel_tower.audio.sd.InputStream")
    def test_returns_valid_wav(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        chunks = [_make_chunk(0.0)] * 2 + [_make_chunk(0.5)] * 3 + [_make_chunk(0.0)] * 2
        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        result = _record_speech_blocking(_make_settings())

        assert isinstance(result, BytesIO)
        result.seek(0)
        data, samplerate = sf.read(result)
        assert samplerate == 16000
        assert len(data) > 0

    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.VADIterator", FakeVADIterator)
    @patch("babel_tower.audio.sd.InputStream")
    def test_captures_frames_between_start_and_end(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        chunks = [_make_chunk(0.0)] * 10
        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        result = _record_speech_blocking(_make_settings())

        result.seek(0)
        data, _ = sf.read(result)
        # FakeVADIterator fires start on call 2, end on call 5.
        # Frames captured at calls 2, 3, 4, 5 (inclusive) = 4 frames.
        expected_samples = 4 * 512
        assert len(data) == expected_samples

    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.VADIterator", FakeVADIteratorNoSpeech)
    @patch("babel_tower.audio.sd.InputStream")
    def test_raises_no_speech_error(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        chunks = [_make_chunk(0.0)] * 10
        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        with pytest.raises(NoSpeechError, match="No speech detected"):
            _record_speech_blocking(_make_settings())

    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.VADIterator", FakeVADIterator)
    @patch("babel_tower.audio.sd.InputStream")
    def test_loads_vad_with_onnx(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        chunks = [_make_chunk(0.0)] * 10
        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        _record_speech_blocking(_make_settings())

        mock_load_vad.assert_called_once_with(onnx=True)

    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.VADIterator", FakeVADIterator)
    @patch("babel_tower.audio.sd.InputStream")
    def test_opens_stream_with_correct_params(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        chunks = [_make_chunk(0.0)] * 10
        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        settings = _make_settings()
        _record_speech_blocking(settings)

        mock_input_stream.assert_called_once_with(
            samplerate=16000,
            channels=1,
            dtype="int16",
            blocksize=512,
        )


    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.VADIterator", FakeVADIterator)
    @patch("babel_tower.audio.sd.InputStream")
    def test_stop_event_breaks_recording(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        chunks = [_make_chunk(0.0)] * 100
        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        stop = threading.Event()
        stop.set()

        with pytest.raises(NoSpeechError):
            _record_speech_blocking(_make_settings(), stop_event=stop)


class TestMultiSegmentRecording:
    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.sd.InputStream")
    def test_two_segments_concatenated(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        # Segment 1: start@2, end@4. Gap@5-6. Segment 2: start@7, end@9.
        # inter_segment_timeout covers chunks 5-106 (enough for gap at 5-6).
        vad = FakeVADIterator(None)
        vad.configure_multi([(2, 4), (7, 9)])
        chunks = [_make_chunk(0.0)] * 20

        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        with patch("babel_tower.audio.VADIterator", return_value=vad):
            settings = _make_settings(inter_segment_timeout=3.2)
            result = _record_speech_blocking(settings)

        result.seek(0)
        data, _ = sf.read(result)
        # Segment 1 frames: calls 2,3,4 = 3 chunks. Segment 2 frames: calls 7,8,9 = 3 chunks.
        assert len(data) == 6 * 512

    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.sd.InputStream")
    def test_inter_segment_timeout_expires(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        # Single segment, then timeout expires (no second segment).
        vad = FakeVADIterator(None)
        vad.configure_multi([(2, 4)])
        # Use very short timeout: 1 chunk = 512/16000 = 0.032s
        chunks = [_make_chunk(0.0)] * 20

        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        with patch("babel_tower.audio.VADIterator", return_value=vad):
            # 0.032s timeout = 1 chunk → expires at chunk_index 4+1=5
            settings = _make_settings(inter_segment_timeout=0.032)
            result = _record_speech_blocking(settings)

        result.seek(0)
        data, _ = sf.read(result)
        # Only segment 1: calls 2,3,4 = 3 chunks
        assert len(data) == 3 * 512

    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.sd.InputStream")
    def test_legacy_single_segment_with_zero_timeout(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        vad = FakeVADIterator(None)
        vad.configure_multi([(2, 5), (8, 10)])
        chunks = [_make_chunk(0.0)] * 20

        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        with patch("babel_tower.audio.VADIterator", return_value=vad):
            settings = _make_settings(inter_segment_timeout=0.0)
            result = _record_speech_blocking(settings)

        result.seek(0)
        data, _ = sf.read(result)
        # Only first segment: calls 2,3,4,5 = 4 chunks (breaks at first end)
        assert len(data) == 4 * 512


class TestRecordSpeechAsync:
    @pytest.mark.anyio
    @patch("babel_tower.audio.load_silero_vad")
    @patch("babel_tower.audio.VADIterator", FakeVADIterator)
    @patch("babel_tower.audio.sd.InputStream")
    async def test_async_wrapper_returns_wav(
        self,
        mock_input_stream: MagicMock,
        mock_load_vad: MagicMock,
    ) -> None:
        from babel_tower.audio import record_speech

        chunks = [_make_chunk(0.0)] * 10
        mock_input_stream.return_value = FakeStream(chunks)
        mock_load_vad.return_value = MagicMock()

        result = await record_speech(_make_settings())

        assert isinstance(result, BytesIO)
        result.seek(0)
        data, samplerate = sf.read(result)
        assert samplerate == 16000
        assert len(data) > 0
