from pathlib import Path

import httpx
import pytest
from babel_tower.config import Settings
from babel_tower.processing import ProcessingError, get_available_modes, process_transcript


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    (tmp_path / "_formatting.md").write_text("Formatting rules.")
    (tmp_path / "durchreichen.md").write_text("Passthrough prompt.")
    (tmp_path / "clean.md").write_text("Cleanup prompt.")
    (tmp_path / "structure.md").write_text("Structuring prompt.")
    (tmp_path / "revise.md").write_text("Revise prompt.")
    return tmp_path


@pytest.fixture
def processing_settings(clean_env: pytest.MonkeyPatch, prompts_dir: Path) -> Settings:
    clean_env.setenv("BABEL_LLM_URL", "http://test-llm:4000")
    clean_env.setenv("BABEL_PROMPTS_DIR", str(prompts_dir))
    return Settings()


def _llm_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"content": content}},
            ],
        },
    )


class TestGetAvailableModes:
    def test_returns_modes_from_prompts_dir(self, processing_settings: Settings) -> None:
        modes = get_available_modes(processing_settings)
        assert modes == {"structure", "clean", "durchreichen", "revise"}

    def test_excludes_underscore_prefixed_files(self, processing_settings: Settings) -> None:
        modes = get_available_modes(processing_settings)
        assert "_formatting" not in modes

    def test_returns_empty_for_missing_dir(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_PROMPTS_DIR", "/nonexistent/path")
        modes = get_available_modes(Settings())
        assert modes == set()


class TestAutoModeSelection:
    @pytest.mark.anyio
    async def test_auto_mode_durchreichen_for_short_text(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_payload: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            captured_payload.update(kwargs.get("json", {}))  # type: ignore[union-attr]
            return _llm_response("Ja okay")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await process_transcript("Ja okay", settings=processing_settings)

        messages = captured_payload["messages"]
        assert isinstance(messages, list)
        system_msg: dict[str, object] = messages[0]
        assert system_msg["content"] == "Formatting rules.\n\nPassthrough prompt."

    @pytest.mark.anyio
    async def test_auto_mode_clean_for_normal_text(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_payload: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            captured_payload.update(kwargs.get("json", {}))  # type: ignore[union-attr]
            return _llm_response("Cleaned text")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await process_transcript(
            "Ich möchte ein neues Feature für den Plugin implementieren",
            settings=processing_settings,
        )

        messages = captured_payload["messages"]
        assert isinstance(messages, list)
        system_msg: dict[str, object] = messages[0]
        assert system_msg["content"] == "Formatting rules.\n\nCleanup prompt."


class TestExplicitMode:
    @pytest.mark.anyio
    async def test_explicit_mode_override(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_payload: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            captured_payload.update(kwargs.get("json", {}))  # type: ignore[union-attr]
            return _llm_response("Structured output")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await process_transcript(
            "Kurzer Text",
            mode="structure",
            settings=processing_settings,
        )

        messages = captured_payload["messages"]
        assert isinstance(messages, list)
        system_msg: dict[str, object] = messages[0]
        assert system_msg["content"] == "Formatting rules.\n\nStructuring prompt."


class TestErrorHandling:
    @pytest.mark.anyio
    async def test_raises_on_unknown_mode(self, processing_settings: Settings) -> None:
        with pytest.raises(ProcessingError, match="Unknown mode: nonexistent"):
            await process_transcript("Test", mode="nonexistent", settings=processing_settings)

    @pytest.mark.anyio
    async def test_raises_on_llm_connection_error(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(ProcessingError, match="unreachable"):
            await process_transcript(
                "Test text here", mode="clean", settings=processing_settings
            )

    @pytest.mark.anyio
    async def test_raises_on_llm_timeout(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ReadTimeout("timeout")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(ProcessingError, match="timed out"):
            await process_transcript(
                "Test text here", mode="clean", settings=processing_settings
            )

    @pytest.mark.anyio
    async def test_raises_on_non_200(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(ProcessingError, match="500"):
            await process_transcript(
                "Test text here", mode="clean", settings=processing_settings
            )


class TestLLMResponseParsing:
    @pytest.mark.anyio
    async def test_parses_llm_response_correctly(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return _llm_response("  Bereinigter Text mit Leerzeichen  ")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        result = await process_transcript(
            "Test text here", mode="clean", settings=processing_settings
        )
        assert result == "Bereinigter Text mit Leerzeichen"


class TestContextParameter:
    @pytest.mark.anyio
    async def test_context_prepended_to_user_message(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_payload: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            captured_payload.update(kwargs.get("json", {}))  # type: ignore[union-attr]
            return _llm_response("Revised text")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await process_transcript(
            "ändere X zu Y",
            mode="clean",
            settings=processing_settings,
            context="## Originaltext\n\nOriginal content\n\n## Änderungsanweisungen",
        )

        messages = captured_payload["messages"]
        assert isinstance(messages, list)
        user_msg: dict[str, object] = messages[1]
        content = user_msg["content"]
        assert isinstance(content, str)
        assert content.startswith("<<<TRANSKRIPT>>>")
        assert content.endswith("<<<ENDE>>>")
        assert "## Originaltext" in content
        assert "Original content" in content
        assert "ändere X zu Y" in content

    @pytest.mark.anyio
    async def test_no_context_sends_transcript_only(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_payload: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            captured_payload.update(kwargs.get("json", {}))  # type: ignore[union-attr]
            return _llm_response("Cleaned text")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await process_transcript(
            "plain transcript",
            mode="clean",
            settings=processing_settings,
        )

        messages = captured_payload["messages"]
        assert isinstance(messages, list)
        user_msg: dict[str, object] = messages[1]
        assert user_msg["content"] == "<<<TRANSKRIPT>>>\nplain transcript\n<<<ENDE>>>"


class TestFormattingFragment:
    @pytest.mark.anyio
    async def test_formatting_prepended_to_prompt(
        self, processing_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_payload: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            captured_payload.update(kwargs.get("json", {}))  # type: ignore[union-attr]
            return _llm_response("Cleaned text")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await process_transcript(
            "Ich möchte die File config punkt py anpassen",
            mode="clean",
            settings=processing_settings,
        )

        messages = captured_payload["messages"]
        assert isinstance(messages, list)
        system_msg: dict[str, object] = messages[0]
        content = system_msg["content"]
        assert isinstance(content, str)
        assert content.startswith("Formatting rules.")
        assert content.endswith("Cleanup prompt.")

    @pytest.mark.anyio
    async def test_no_formatting_file_falls_back(
        self, clean_env: pytest.MonkeyPatch, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "clean.md").write_text("Cleanup prompt.")
        clean_env.setenv("BABEL_LLM_URL", "http://test-llm:4000")
        clean_env.setenv("BABEL_PROMPTS_DIR", str(tmp_path))
        settings = Settings()

        captured_payload: dict[str, object] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            captured_payload.update(kwargs.get("json", {}))  # type: ignore[union-attr]
            return _llm_response("Cleaned text")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await process_transcript(
            "Ich möchte etwas implementieren", mode="clean", settings=settings
        )

        messages = captured_payload["messages"]
        assert isinstance(messages, list)
        system_msg: dict[str, object] = messages[0]
        assert system_msg["content"] == "Cleanup prompt."
