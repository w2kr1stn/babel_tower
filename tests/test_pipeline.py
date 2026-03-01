from __future__ import annotations

import sys
import threading
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# sounddevice requires PortAudio at import time; stub it for CI/headless environments
if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = MagicMock()

from babel_tower.audio import NoSpeechError  # noqa: E402
from babel_tower.config import Settings  # noqa: E402
from babel_tower.pipeline import process_file, run_pipeline  # noqa: E402
from babel_tower.processing import ProcessingError  # noqa: E402
from babel_tower.stt import STTError  # noqa: E402


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
            await run_pipeline(mode="structure", settings=mock_settings)
            mock_proc.assert_called_once_with("text", "structure", mock_settings)

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

    @pytest.mark.anyio
    async def test_passes_stop_event_to_record_speech(self, mock_settings: Settings) -> None:
        stop = threading.Event()
        with (
            patch(
                "babel_tower.pipeline.record_speech",
                new_callable=AsyncMock,
                return_value=BytesIO(b"fake"),
            ) as mock_record,
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="text",
            ),
            patch(
                "babel_tower.pipeline.process_transcript",
                new_callable=AsyncMock,
                return_value="done",
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True),
        ):
            await run_pipeline(settings=mock_settings, stop_event=stop)
            mock_record.assert_called_once_with(mock_settings, stop_event=stop)


class TestRunPipelineClipboard:
    @pytest.mark.anyio
    async def test_clipboard_false_skips_copy(self, mock_settings: Settings) -> None:
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
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True) as mock_clip,
            patch("babel_tower.pipeline.notify", return_value=True),
        ):
            result = await run_pipeline(settings=mock_settings, clipboard=False)
            assert result == "processed text"
            mock_clip.assert_not_called()

    @pytest.mark.anyio
    async def test_clipboard_false_skips_final_notify(self, mock_settings: Settings) -> None:
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
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
        ):
            await run_pipeline(settings=mock_settings, clipboard=False)
            # Should have 3 intermediate notifications but NOT the final result notification
            assert mock_notify.call_count == 3
            bodies = [call.args[1] for call in mock_notify.call_args_list]
            assert "processed text" not in bodies


class TestRunPipelineReview:
    @pytest.mark.anyio
    async def test_review_enabled_passes_through_rofi(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_STT_URL", "http://test:9000")
        clean_env.setenv("BABEL_LLM_URL", "http://test:4000")
        clean_env.setenv("BABEL_REVIEW_ENABLED", "true")
        settings = Settings()

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
            patch("babel_tower.review.subprocess.run") as mock_rofi,
        ):
            from unittest.mock import MagicMock

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "reviewed\n"
            mock_rofi.return_value = mock_result

            result = await run_pipeline(settings=settings)
            assert result == "reviewed"

    @pytest.mark.anyio
    async def test_review_dismissed_returns_empty(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_STT_URL", "http://test:9000")
        clean_env.setenv("BABEL_LLM_URL", "http://test:4000")
        clean_env.setenv("BABEL_REVIEW_ENABLED", "true")
        settings = Settings()

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
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
            patch("babel_tower.review.subprocess.run") as mock_rofi,
        ):
            from unittest.mock import MagicMock

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_rofi.return_value = mock_result

            result = await run_pipeline(settings=settings)
            assert result == ""
            mock_notify.assert_any_call("Babel Tower", "Verworfen", "low")


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
            await process_file(str(audio_file), mode="structure", settings=mock_settings)
            mock_proc.assert_called_once_with("text", "structure", mock_settings)


class TestGracefulDegradation:
    @pytest.mark.anyio
    async def test_no_speech_returns_empty(self, mock_settings: Settings) -> None:
        with (
            patch(
                "babel_tower.pipeline.record_speech",
                new_callable=AsyncMock,
                side_effect=NoSpeechError("No speech detected"),
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
        ):
            result = await run_pipeline(settings=mock_settings)
            assert result == ""
            mock_notify.assert_any_call("Babel Tower", "Keine Sprache erkannt", "low")

    @pytest.mark.anyio
    async def test_stt_error_returns_error_message(self, mock_settings: Settings) -> None:
        with (
            patch(
                "babel_tower.pipeline.record_speech",
                new_callable=AsyncMock,
                return_value=BytesIO(b"fake"),
            ),
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                side_effect=STTError("service unreachable"),
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
        ):
            result = await run_pipeline(settings=mock_settings)
            assert result == "[STT-Fehler: service unreachable]"
            mock_notify.assert_any_call(
                "Babel Tower", "STT-Fehler: service unreachable", "critical"
            )

    @pytest.mark.anyio
    async def test_empty_transcript_returns_empty(self, mock_settings: Settings) -> None:
        with (
            patch(
                "babel_tower.pipeline.record_speech",
                new_callable=AsyncMock,
                return_value=BytesIO(b"fake"),
            ),
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
        ):
            result = await run_pipeline(settings=mock_settings)
            assert result == ""
            mock_notify.assert_any_call("Babel Tower", "Keine Sprache erkannt", "low")

    @pytest.mark.anyio
    async def test_processing_error_falls_back_to_raw_transcript(
        self, mock_settings: Settings
    ) -> None:
        with (
            patch(
                "babel_tower.pipeline.record_speech",
                new_callable=AsyncMock,
                return_value=BytesIO(b"fake"),
            ),
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="raw transcript text",
            ),
            patch(
                "babel_tower.pipeline.process_transcript",
                new_callable=AsyncMock,
                side_effect=ProcessingError("LLM unreachable"),
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True) as mock_clip,
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
        ):
            result = await run_pipeline(settings=mock_settings)
            assert result == "raw transcript text"
            mock_notify.assert_any_call(
                "Babel Tower", "LLM-Fehler: LLM unreachable", "critical"
            )
            mock_clip.assert_called_once_with("raw transcript text")


class TestProcessFileGracefulDegradation:
    @pytest.mark.anyio
    async def test_stt_error_returns_error_message(
        self, mock_settings: Settings, tmp_path: object
    ) -> None:
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                side_effect=STTError("timeout"),
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
        ):
            result = await process_file(str(audio_file), settings=mock_settings)
            assert result == "[STT-Fehler: timeout]"
            mock_notify.assert_any_call("Babel Tower", "STT-Fehler: timeout", "critical")

    @pytest.mark.anyio
    async def test_empty_transcript_returns_empty(
        self, mock_settings: Settings, tmp_path: object
    ) -> None:
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True),
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
        ):
            result = await process_file(str(audio_file), settings=mock_settings)
            assert result == ""
            mock_notify.assert_any_call("Babel Tower", "Keine Sprache erkannt", "low")

    @pytest.mark.anyio
    async def test_processing_error_falls_back_to_raw_transcript(
        self, mock_settings: Settings, tmp_path: object
    ) -> None:
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)

        with (
            patch(
                "babel_tower.pipeline.transcribe",
                new_callable=AsyncMock,
                return_value="raw from file",
            ),
            patch(
                "babel_tower.pipeline.process_transcript",
                new_callable=AsyncMock,
                side_effect=ProcessingError("LLM timeout"),
            ),
            patch("babel_tower.pipeline.copy_to_clipboard", return_value=True) as mock_clip,
            patch("babel_tower.pipeline.notify", return_value=True) as mock_notify,
        ):
            result = await process_file(str(audio_file), settings=mock_settings)
            assert result == "raw from file"
            mock_notify.assert_any_call(
                "Babel Tower", "LLM-Fehler: LLM timeout", "critical"
            )
            mock_clip.assert_called_once_with("raw from file")
