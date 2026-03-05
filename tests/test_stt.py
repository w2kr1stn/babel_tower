from io import BytesIO

import httpx
import pytest
from babel_tower.config import Settings
from babel_tower.stt import STTError, apply_corrections, transcribe


@pytest.fixture
def stt_settings(clean_env: pytest.MonkeyPatch) -> Settings:
    clean_env.setenv("BABEL_STT_URL", "http://test-stt:9000")
    return Settings()


def _wav_bytes() -> bytes:
    return b"RIFF" + b"\x00" * 100


class TestTranscribe:
    @pytest.mark.anyio
    async def test_returns_transcript_text(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(200, json={"text": " Hallo Welt "})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        result = await transcribe(_wav_bytes(), stt_settings)
        assert result == "Hallo Welt"

    @pytest.mark.anyio
    async def test_accepts_bytesio(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(200, json={"text": "test"})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        result = await transcribe(BytesIO(_wav_bytes()), stt_settings)
        assert result == "test"

    @pytest.mark.anyio
    async def test_raises_on_connection_error(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(STTError, match="unreachable"):
            await transcribe(_wav_bytes(), stt_settings)

    @pytest.mark.anyio
    async def test_raises_on_timeout(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            raise httpx.ReadTimeout("timeout")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(STTError, match="timed out"):
            await transcribe(_wav_bytes(), stt_settings)

    @pytest.mark.anyio
    async def test_raises_on_non_200(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(STTError, match="500"):
            await transcribe(_wav_bytes(), stt_settings)

    @pytest.mark.anyio
    async def test_handles_empty_text(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(200, json={"text": ""})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        result = await transcribe(_wav_bytes(), stt_settings)
        assert result == ""


class TestSTTHotwords:
    @pytest.mark.anyio
    async def test_sends_hotwords_when_configured(
        self, clean_env: pytest.MonkeyPatch, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        clean_env.setenv("BABEL_STT_URL", "http://test-stt:9000")
        clean_env.setenv("BABEL_STT_HOTWORDS", "Claude Code Tailscale")
        settings = Settings()
        captured_data: dict[str, str] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            data = kwargs.get("data")
            assert isinstance(data, dict)
            captured_data.update(data)
            return httpx.Response(200, json={"text": "test"})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await transcribe(_wav_bytes(), settings)
        assert captured_data["hotwords"] == "Claude Code Tailscale"

    @pytest.mark.anyio
    async def test_omits_hotwords_when_empty(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_data: dict[str, str] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            data = kwargs.get("data")
            assert isinstance(data, dict)
            captured_data.update(data)
            return httpx.Response(200, json={"text": "test"})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await transcribe(_wav_bytes(), stt_settings)
        assert "hotwords" not in captured_data

    @pytest.mark.anyio
    async def test_sends_prompt_when_configured(
        self, clean_env: pytest.MonkeyPatch, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        clean_env.setenv("BABEL_STT_URL", "http://test-stt:9000")
        clean_env.setenv("BABEL_STT_PROMPT", "Software-Entwicklung mit Claude Code")
        settings = Settings()
        captured_data: dict[str, str] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            data = kwargs.get("data")
            assert isinstance(data, dict)
            captured_data.update(data)
            return httpx.Response(200, json={"text": "test"})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await transcribe(_wav_bytes(), settings)
        assert captured_data["prompt"] == "Software-Entwicklung mit Claude Code"

    @pytest.mark.anyio
    async def test_omits_prompt_when_empty(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured_data: dict[str, str] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            data = kwargs.get("data")
            assert isinstance(data, dict)
            captured_data.update(data)
            return httpx.Response(200, json={"text": "test"})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        await transcribe(_wav_bytes(), stt_settings)
        assert "prompt" not in captured_data


class TestApplyCorrections:
    def test_replaces_cloud_with_claude(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_STT_CORRECTIONS", "Cloud Code:Claude Code,Cloud:Claude")
        settings = Settings()
        assert apply_corrections("Ich nutze Cloud Code", settings) == "Ich nutze Claude Code"

    def test_replaces_gin_with_djinn(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_STT_CORRECTIONS", "Gin in a Box:Djinn in a Box")
        settings = Settings()
        assert apply_corrections("Meine Gin in a Box Anwendung", settings) == (
            "Meine Djinn in a Box Anwendung"
        )

    def test_case_insensitive(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_STT_CORRECTIONS", "todai:todAi")
        settings = Settings()
        assert apply_corrections("Ich arbeite an TODAI", settings) == "Ich arbeite an todAi"

    def test_no_corrections_returns_unchanged(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        assert apply_corrections("Hello World", settings) == "Hello World"

    def test_order_matters_longer_first(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_STT_CORRECTIONS", "Cloud Code:Claude Code,Cloud:Claude")
        settings = Settings()
        result = apply_corrections("Cloud Code und Cloud Computing", settings)
        assert result == "Claude Code und Claude Computing"

    def test_multiple_occurrences(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_STT_CORRECTIONS", "Cloud:Claude")
        settings = Settings()
        assert apply_corrections("Cloud und Cloud", settings) == "Claude und Claude"

    @pytest.mark.anyio
    async def test_corrections_applied_after_transcription(
        self, clean_env: pytest.MonkeyPatch, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        clean_env.setenv("BABEL_STT_URL", "http://test-stt:9000")
        clean_env.setenv("BABEL_STT_CORRECTIONS", "Cloud:Claude")
        settings = Settings()

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(200, json={"text": "Ich nutze Cloud"})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        result = await transcribe(_wav_bytes(), settings)
        assert result == "Ich nutze Claude"
