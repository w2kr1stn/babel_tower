from __future__ import annotations

import sys
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# sounddevice requires PortAudio at import time; stub it for CI/headless environments
if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = MagicMock()

from babel_tower.config import Settings  # noqa: E402
from babel_tower.pipeline import process_file, run_pipeline  # noqa: E402


@pytest.fixture
def mock_settings(clean_env: pytest.MonkeyPatch) -> Settings:
    clean_env.setenv("BABEL_STT_URL", "http://test:9000")
    clean_env.setenv("BABEL_LLM_URL", "http://test:4000")
    return Settings()


class TestRunPipeline:
    @pytest.mark.anyio
    async def test_full_pipeline(self, mock_settings: Settings) -> None:
        with (
            patch(
                "babel_tower.pipeline.record_speech",
                new_callable=AsyncMock,
                return_value=BytesIO(b"fake"),
            ),
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="raw text",
            ),
            patch(
                "babel_tower.pipeline.process_transcript",
                new_callable=AsyncMock,
                return_value="processed text",
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True),
        ):
            result = await run_pipeline(settings=mock_settings)
            assert result == "processed text"

    @pytest.mark.anyio
    async def test_passes_mode_through(self, mock_settings: Settings) -> None:
        with (
            patch(
                "babel_tower.pipeline.record_speech",
                new_callable=AsyncMock,
                return_value=BytesIO(b"fake"),
            ),
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="text",
            ),
            patch(
                "babel_tower.pipeline.process_transcript",
                new_callable=AsyncMock,
                return_value="done",
            ) as mock_proc,
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True),
        ):
            await run_pipeline(mode="strukturieren", settings=mock_settings)
            mock_proc.assert_called_once_with("text", "strukturieren", mock_settings)

    @pytest.mark.anyio
    async def test_notifies_at_each_stage(self, mock_settings: Settings) -> None:
        with (
            patch(
                "babel_tower.pipeline.record_speech",
                new_callable=AsyncMock,
                return_value=BytesIO(b"fake"),
            ),
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="text",
            ),
            patch(
                "babel_tower.pipeline.process_transcript",
                new_callable=AsyncMock,
                return_value="result",
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
        ):
            await run_pipeline(settings=mock_settings)
            assert mock_notify.call_count == 4
            titles = [call.args[0] for call in mock_notify.call_args_list]
            assert all(t == "Babel Tower" for t in titles)


class TestProcessFile:
    @pytest.mark.anyio
    async def test_processes_existing_file(self, mock_settings: Settings, tmp_path: object) -> None:
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="from file",
            ) as mock_transcribe,
            patch(
                "babel_tower.pipeline.process_transcript",
                new_callable=AsyncMock,
                return_value="processed",
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True),
        ):
            result = await process_file(str(audio_file), settings=mock_settings)
            assert result == "processed"
            # Verify transcribe received the raw bytes from the file
            call_args = mock_transcribe.call_args
            assert call_args is not None
            assert call_args.args[0] == b"RIFF" + b"\x00" * 100

    @pytest.mark.anyio
    async def test_passes_mode_through(self, mock_settings: Settings, tmp_path: object) -> None:
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="text",
            ),
            patch(
                "babel_tower.pipeline.process_transcript",
                new_callable=AsyncMock,
                return_value="done",
            ) as mock_proc,
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True),
        ):
            await process_file(str(audio_file), mode="strukturieren", settings=mock_settings)
            mock_proc.assert_called_once_with("text", "strukturieren", mock_settings)
