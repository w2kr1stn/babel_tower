from unittest.mock import AsyncMock, patch

import pytest
from babel_tower.config import Settings
from babel_tower.processing import ProcessingError
from babel_tower.stt import STTError
from babel_tower.telegram_bot import (
    build_application,
    handle_voice,
    parse_allowed_users,
    split_for_telegram,
)


class TestParseAllowedUsers:
    def test_empty(self) -> None:
        assert parse_allowed_users("") == set()

    def test_single(self) -> None:
        assert parse_allowed_users("12345") == {12345}

    def test_multiple(self) -> None:
        assert parse_allowed_users("1, 2,3") == {1, 2, 3}

    def test_ignores_blanks(self) -> None:
        assert parse_allowed_users("1, ,2") == {1, 2}

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_allowed_users("abc")


class TestSplitForTelegram:
    def test_short(self) -> None:
        assert split_for_telegram("hello") == ["hello"]

    def test_at_limit(self) -> None:
        text = "x" * 4000
        assert split_for_telegram(text) == [text]

    def test_split(self) -> None:
        text = "x" * 9000
        chunks = split_for_telegram(text)
        assert len(chunks) == 3
        assert chunks[0] == "x" * 4000
        assert chunks[1] == "x" * 4000
        assert chunks[2] == "x" * 1000

    def test_custom_limit(self) -> None:
        assert split_for_telegram("abcde", limit=2) == ["ab", "cd", "e"]


class TestHandleVoice:
    @pytest.mark.asyncio
    async def test_success(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        with (
            patch(
                "babel_tower.telegram_bot.transcribe",
                new=AsyncMock(return_value="raw transcript"),
            ),
            patch(
                "babel_tower.telegram_bot.process_transcript",
                new=AsyncMock(return_value="cleaned text"),
            ),
        ):
            result = await handle_voice(b"audio", settings)
        assert result == "cleaned text"

    @pytest.mark.asyncio
    async def test_empty_transcript(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        with patch(
            "babel_tower.telegram_bot.transcribe", new=AsyncMock(return_value="")
        ):
            result = await handle_voice(b"audio", settings)
        assert "Keine Sprache" in result

    @pytest.mark.asyncio
    async def test_stt_error(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        with patch(
            "babel_tower.telegram_bot.transcribe",
            new=AsyncMock(side_effect=STTError("speaches down")),
        ):
            result = await handle_voice(b"audio", settings)
        assert "STT" in result
        assert "speaches down" in result

    @pytest.mark.asyncio
    async def test_processing_error_falls_back_to_raw(
        self, clean_env: pytest.MonkeyPatch
    ) -> None:
        settings = Settings()
        with (
            patch(
                "babel_tower.telegram_bot.transcribe",
                new=AsyncMock(return_value="raw fallback"),
            ),
            patch(
                "babel_tower.telegram_bot.process_transcript",
                new=AsyncMock(side_effect=ProcessingError("llm down")),
            ),
        ):
            result = await handle_voice(b"audio", settings)
        assert result == "raw fallback"


class TestBuildApplication:
    def test_missing_token_raises(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        with pytest.raises(RuntimeError, match="BABEL_TELEGRAM_BOT_TOKEN"):
            build_application(settings)
