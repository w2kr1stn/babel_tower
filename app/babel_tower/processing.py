from pathlib import Path

import httpx

from babel_tower.config import Settings


class ProcessingError(Exception):
    pass


async def process_transcript(
    transcript: str,
    mode: str | None = None,
    settings: Settings | None = None,
) -> str:
    settings = settings or Settings()

    if mode is None:
        word_count = len(transcript.split())
        mode = (
            "durchreichen"
            if word_count <= settings.durchreichen_max_words
            else settings.default_mode
        )

    system_prompt = _load_prompt(mode, settings)
    return await _call_llm(transcript, system_prompt, settings)


def _resolve_prompts_dir(settings: Settings) -> Path:
    prompts_path = Path(settings.prompts_dir)
    if not prompts_path.is_absolute():
        prompts_path = Path(__file__).resolve().parent.parent.parent / settings.prompts_dir
    return prompts_path


def get_available_modes(settings: Settings | None = None) -> set[str]:
    settings = settings or Settings()
    return {p.stem for p in _resolve_prompts_dir(settings).glob("*.md")}


def _load_prompt(mode: str, settings: Settings) -> str:
    prompt_file = _resolve_prompts_dir(settings) / f"{mode}.md"
    if not prompt_file.exists():
        raise ProcessingError(f"Unknown mode: {mode}")
    return prompt_file.read_text()


async def _call_llm(transcript: str, system_prompt: str, settings: Settings) -> str:
    url = f"{settings.llm_url}/v1/chat/completions"
    payload: dict[str, object] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ],
    }

    headers: dict[str, str] = {}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
        except httpx.ConnectError as e:
            raise ProcessingError(f"LLM unreachable at {settings.llm_url}") from e
        except httpx.TimeoutException as e:
            raise ProcessingError("LLM request timed out") from e

    if response.status_code != 200:
        raise ProcessingError(f"LLM returned {response.status_code}: {response.text}")

    result: dict[str, object] = response.json()
    choices = result["choices"]
    assert isinstance(choices, list)
    first_choice: dict[str, object] = choices[0]  # pyright: ignore[reportUnknownVariableType]
    message = first_choice["message"]  # pyright: ignore[reportUnknownVariableType]
    assert isinstance(message, dict)
    content = message["content"]  # pyright: ignore[reportUnknownVariableType]
    assert isinstance(content, str)
    return content.strip()
