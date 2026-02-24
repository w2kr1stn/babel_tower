from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# sounddevice requires PortAudio at import time; stub it for CI/headless environments
if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = MagicMock()

from babel_tower.mcp_server import _settings, converse, mcp, set_mode  # noqa: E402


class TestMcpServerSetup:
    def test_mcp_server_name(self) -> None:
        assert mcp.name == "babel-tower"

    def test_settings_initialized(self) -> None:
        assert _settings is not None
        assert isinstance(_settings.default_mode, str)


class TestConverseTool:
    @pytest.mark.anyio
    async def test_calls_pipeline_with_default_mode(self) -> None:
        with patch(
            "babel_tower.mcp_server.run_pipeline",
            new_callable=AsyncMock,
            return_value="processed text",
        ) as mock_pipeline:
            result = await converse()
            assert result == "processed text"
            mock_pipeline.assert_called_once_with(
                mode=None, settings=_settings, clipboard=False
            )

    @pytest.mark.anyio
    async def test_calls_pipeline_with_explicit_mode(self) -> None:
        with patch(
            "babel_tower.mcp_server.run_pipeline",
            new_callable=AsyncMock,
            return_value="structured text",
        ) as mock_pipeline:
            result = await converse(mode="strukturieren")
            assert result == "structured text"
            mock_pipeline.assert_called_once_with(
                mode="strukturieren", settings=_settings, clipboard=False
            )

    @pytest.mark.anyio
    async def test_message_shows_notification(self) -> None:
        with (
            patch(
                "babel_tower.mcp_server.run_pipeline",
                new_callable=AsyncMock,
                return_value="response",
            ),
            patch("babel_tower.mcp_server.notify", return_value=True) as mock_notify,
        ):
            await converse(message="Hallo, was soll ich tun?")
            mock_notify.assert_called_once_with("Babel Tower", "Hallo, was soll ich tun?")

    @pytest.mark.anyio
    async def test_no_message_skips_notification(self) -> None:
        with (
            patch(
                "babel_tower.mcp_server.run_pipeline",
                new_callable=AsyncMock,
                return_value="response",
            ),
            patch("babel_tower.mcp_server.notify", return_value=True) as mock_notify,
        ):
            await converse()
            mock_notify.assert_not_called()

    @pytest.mark.anyio
    async def test_wait_for_response_false_returns_empty(self) -> None:
        with patch(
            "babel_tower.mcp_server.run_pipeline",
            new_callable=AsyncMock,
        ) as mock_pipeline:
            result = await converse(wait_for_response=False)
            assert result == ""
            mock_pipeline.assert_not_called()

    @pytest.mark.anyio
    async def test_wait_for_response_false_with_message(self) -> None:
        with (
            patch(
                "babel_tower.mcp_server.run_pipeline",
                new_callable=AsyncMock,
            ) as mock_pipeline,
            patch("babel_tower.mcp_server.notify", return_value=True) as mock_notify,
        ):
            result = await converse(message="Suche im Code...", wait_for_response=False)
            assert result == ""
            mock_notify.assert_called_once_with("Babel Tower", "Suche im Code...")
            mock_pipeline.assert_not_called()


class TestConverseToolTTS:
    @pytest.mark.anyio
    async def test_tts_enabled_speaks_instead_of_notify(self) -> None:
        original = _settings.tts_enabled
        _settings.tts_enabled = True
        try:
            with (
                patch(
                    "babel_tower.mcp_server.run_pipeline",
                    new_callable=AsyncMock,
                    return_value="response",
                ),
                patch("babel_tower.mcp_server.notify", return_value=True) as mock_notify,
                patch("babel_tower.tts.speak", new_callable=AsyncMock) as mock_speak,
            ):
                await converse(message="Hallo")
                mock_speak.assert_called_once_with("Hallo", _settings)
                mock_notify.assert_not_called()
        finally:
            _settings.tts_enabled = original

    @pytest.mark.anyio
    async def test_tts_error_falls_back_to_notify(self) -> None:
        original = _settings.tts_enabled
        _settings.tts_enabled = True
        try:
            with (
                patch(
                    "babel_tower.mcp_server.run_pipeline",
                    new_callable=AsyncMock,
                    return_value="response",
                ),
                patch("babel_tower.mcp_server.notify", return_value=True) as mock_notify,
                patch(
                    "babel_tower.tts.speak",
                    new_callable=AsyncMock,
                    side_effect=Exception("TTS down"),
                ),
            ):
                await converse(message="Hallo")
                mock_notify.assert_called_once_with("Babel Tower", "Hallo")
        finally:
            _settings.tts_enabled = original

    @pytest.mark.anyio
    async def test_tts_disabled_uses_notify(self) -> None:
        assert not _settings.tts_enabled
        with (
            patch(
                "babel_tower.mcp_server.run_pipeline",
                new_callable=AsyncMock,
                return_value="response",
            ),
            patch("babel_tower.mcp_server.notify", return_value=True) as mock_notify,
        ):
            await converse(message="Test")
            mock_notify.assert_called_once_with("Babel Tower", "Test")


class TestSetModeTool:
    @pytest.mark.anyio
    async def test_set_valid_mode_strukturieren(self) -> None:
        original = _settings.default_mode
        try:
            result = await set_mode(mode="strukturieren")
            assert result == "Default mode set to: strukturieren"
            assert _settings.default_mode == "strukturieren"
        finally:
            _settings.default_mode = original

    @pytest.mark.anyio
    async def test_set_valid_mode_bereinigen(self) -> None:
        original = _settings.default_mode
        try:
            result = await set_mode(mode="bereinigen")
            assert result == "Default mode set to: bereinigen"
            assert _settings.default_mode == "bereinigen"
        finally:
            _settings.default_mode = original

    @pytest.mark.anyio
    async def test_set_valid_mode_durchreichen(self) -> None:
        original = _settings.default_mode
        try:
            result = await set_mode(mode="durchreichen")
            assert result == "Default mode set to: durchreichen"
            assert _settings.default_mode == "durchreichen"
        finally:
            _settings.default_mode = original

    @pytest.mark.anyio
    async def test_set_invalid_mode(self) -> None:
        original = _settings.default_mode
        result = await set_mode(mode="invalid")
        assert "Unknown mode: invalid" in result
        assert "bereinigen" in result
        assert "durchreichen" in result
        assert "strukturieren" in result
        # Settings should not change
        assert _settings.default_mode == original

    @pytest.mark.anyio
    async def test_set_empty_mode(self) -> None:
        original = _settings.default_mode
        result = await set_mode(mode="")
        assert "Unknown mode: " in result
        assert _settings.default_mode == original
