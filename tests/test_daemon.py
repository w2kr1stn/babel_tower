from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = MagicMock()

from babel_tower.audio import NoSpeechError  # noqa: E402
from babel_tower.config import Settings  # noqa: E402
from babel_tower.daemon import VoiceDaemon  # noqa: E402


@pytest.fixture
def mock_settings(clean_env: pytest.MonkeyPatch) -> Settings:
    clean_env.setenv("BABEL_STT_URL", "http://test:9000")
    clean_env.setenv("BABEL_LLM_URL", "http://test:4000")
    return Settings()


class TestVoiceDaemonInit:
    def test_creates_default_settings(self, clean_env: pytest.MonkeyPatch) -> None:
        d = VoiceDaemon()
        assert d.settings is not None
        assert d._running is False

    def test_accepts_custom_settings(self, mock_settings: Settings) -> None:
        d = VoiceDaemon(settings=mock_settings)
        assert d.settings is mock_settings


class TestVoiceDaemonRun:
    @pytest.mark.anyio
    async def test_notifies_on_start_and_stop(self, mock_settings: Settings) -> None:
        d = VoiceDaemon(settings=mock_settings)

        async def stop_after_start(settings: Settings) -> str:
            d._running = False
            return "result"

        with (
            patch(
                "babel_tower.daemon.run_pipeline",
                new_callable=AsyncMock,
                side_effect=stop_after_start,
            ),
            patch("babel_tower.daemon.notify", return_value=True) as mock_notify,
        ):
            await d.run()

            assert mock_notify.call_count == 2
            mock_notify.assert_any_call(
                "Babel Tower", "Daemon gestartet \u2014 warte auf Sprache...", "low"
            )
            mock_notify.assert_any_call("Babel Tower", "Daemon gestoppt", "low")

    @pytest.mark.anyio
    async def test_continues_on_no_speech(self, mock_settings: Settings) -> None:
        d = VoiceDaemon(settings=mock_settings)
        call_count = 0

        async def no_speech_then_stop(settings: Settings) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NoSpeechError("No speech detected")
            d._running = False
            return "result"

        with (
            patch(
                "babel_tower.daemon.run_pipeline",
                new_callable=AsyncMock,
                side_effect=no_speech_then_stop,
            ),
            patch("babel_tower.daemon.notify", return_value=True),
        ):
            await d.run()
            assert call_count == 2

    @pytest.mark.anyio
    async def test_notifies_on_error_and_continues(self, mock_settings: Settings) -> None:
        d = VoiceDaemon(settings=mock_settings)
        call_count = 0

        async def error_then_stop(settings: Settings) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("STT offline")
            d._running = False
            return "result"

        with (
            patch(
                "babel_tower.daemon.run_pipeline",
                new_callable=AsyncMock,
                side_effect=error_then_stop,
            ),
            patch("babel_tower.daemon.notify", return_value=True) as mock_notify,
            patch("babel_tower.daemon.asyncio.sleep", new_callable=AsyncMock),
        ):
            await d.run()
            assert call_count == 2
            mock_notify.assert_any_call("Babel Tower", "Fehler: STT offline", "critical")


class TestVoiceDaemonShutdown:
    def test_shutdown_sets_running_false(self, mock_settings: Settings) -> None:
        d = VoiceDaemon(settings=mock_settings)
        d._running = True
        d._shutdown()
        assert d._running is False
