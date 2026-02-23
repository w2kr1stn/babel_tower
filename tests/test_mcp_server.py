from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# sounddevice requires PortAudio at import time; stub it for CI/headless environments
if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = MagicMock()

from babel_tower.mcp_server import _settings, listen, mcp, set_mode  # noqa: E402


class TestMcpServerSetup:
    def test_mcp_server_name(self) -> None:
        assert mcp.name == "babel-tower"

    def test_settings_initialized(self) -> None:
        assert _settings is not None
        assert _settings.default_mode == "bereinigen"


class TestListenTool:
    @pytest.mark.anyio
    async def test_calls_pipeline_with_default_mode(self) -> None:
        with patch(
            "babel_tower.mcp_server.run_pipeline",
            new_callable=AsyncMock,
            return_value="processed text",
        ) as mock_pipeline:
            result = await listen()
            assert result == "processed text"
            mock_pipeline.assert_called_once_with(mode=None, settings=_settings)

    @pytest.mark.anyio
    async def test_calls_pipeline_with_explicit_mode(self) -> None:
        with patch(
            "babel_tower.mcp_server.run_pipeline",
            new_callable=AsyncMock,
            return_value="structured text",
        ) as mock_pipeline:
            result = await listen(mode="strukturieren")
            assert result == "structured text"
            mock_pipeline.assert_called_once_with(mode="strukturieren", settings=_settings)

    @pytest.mark.anyio
    async def test_calls_pipeline_with_none_mode(self) -> None:
        with patch(
            "babel_tower.mcp_server.run_pipeline",
            new_callable=AsyncMock,
            return_value="auto text",
        ) as mock_pipeline:
            result = await listen(mode=None)
            assert result == "auto text"
            mock_pipeline.assert_called_once_with(mode=None, settings=_settings)


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
