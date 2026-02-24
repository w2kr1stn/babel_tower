from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# sounddevice requires PortAudio at import time; stub it for CI/headless environments
if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = MagicMock()

from babel_tower.config import Settings  # noqa: E402
from babel_tower.tts import TTSError, synthesize  # noqa: E402


@pytest.fixture
def tts_settings(clean_env: pytest.MonkeyPatch) -> Settings:
    clean_env.setenv("BABEL_TTS_URL", "http://test-tts:8000")
    clean_env.setenv("BABEL_TTS_ENABLED", "true")
    return Settings()


class TestSynthesize:
    @pytest.mark.anyio
    async def test_returns_audio_bytes(
        self, tts_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(200, content=b"RIFF-fake-wav")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        result = await synthesize("Hallo Welt", tts_settings)
        assert result == b"RIFF-fake-wav"

    @pytest.mark.anyio
    async def test_sends_correct_payload(
        self, tts_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_kwargs: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            captured_kwargs.update(kwargs)
            return httpx.Response(200, content=b"audio")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await synthesize("Test text", tts_settings)
        assert captured_kwargs["json"] == {
            "model": "tts-1",
            "input": "Test text",
            "voice": "thorsten_emotional",
            "response_format": "wav",
        }

    @pytest.mark.anyio
    async def test_uses_correct_url(
        self, tts_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_url: str = ""

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            nonlocal captured_url
            captured_url = url
            return httpx.Response(200, content=b"audio")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await synthesize("Test", tts_settings)
        assert captured_url == "http://test-tts:8000/v1/audio/speech"

    @pytest.mark.anyio
    async def test_raises_on_connection_error(
        self, tts_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(TTSError, match="unreachable"):
            await synthesize("Test", tts_settings)

    @pytest.mark.anyio
    async def test_raises_on_timeout(
        self, tts_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ReadTimeout("timeout")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(TTSError, match="timed out"):
            await synthesize("Test", tts_settings)

    @pytest.mark.anyio
    async def test_raises_on_non_200(
        self, tts_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(TTSError, match="500"):
            await synthesize("Test", tts_settings)


class TestSpeak:
    @pytest.mark.anyio
    async def test_synthesizes_and_plays(self, tts_settings: Settings) -> None:
        from babel_tower.tts import speak

        with (
            patch(
                "babel_tower.tts.synthesize",
                new_callable=AsyncMock,
                return_value=b"fake-audio",
            ) as mock_synth,
            patch("babel_tower.tts._play_audio_blocking") as mock_play,
        ):
            await speak("Hallo", tts_settings)
            mock_synth.assert_called_once_with("Hallo", tts_settings)
            mock_play.assert_called_once_with(b"fake-audio")

    @pytest.mark.anyio
    async def test_propagates_tts_error(self, tts_settings: Settings) -> None:
        from babel_tower.tts import speak

        with (
            patch(
                "babel_tower.tts.synthesize",
                new_callable=AsyncMock,
                side_effect=TTSError("unreachable"),
            ),
            pytest.raises(TTSError, match="unreachable"),
        ):
            await speak("Test", tts_settings)


class TestPlayAudioBlocking:
    def test_plays_audio_via_sounddevice(self) -> None:
        from babel_tower.tts import _play_audio_blocking

        mock_data = MagicMock()
        mock_sr = 22050

        with (
            patch("babel_tower.tts.sf.read", return_value=(mock_data, mock_sr)) as mock_read,
            patch("babel_tower.tts.sd.play") as mock_play,
            patch("babel_tower.tts.sd.wait") as mock_wait,
        ):
            _play_audio_blocking(b"fake-wav-bytes")
            mock_read.assert_called_once()
            mock_play.assert_called_once_with(mock_data, mock_sr)
            mock_wait.assert_called_once()
