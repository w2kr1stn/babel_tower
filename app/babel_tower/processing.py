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


def _load_prompt(mode: str, settings: Settings) -> str:
    prompt_file = Path(settings.prompts_dir) / f"{mode}.md"
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

    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        try:
            response = await client.post(url, json=payload)
        except httpx.ConnectError as e:
            raise ProcessingError(f"LLM unreachable at {settings.llm_url}") from e
        except httpx.TimeoutException as e:
            raise ProcessingError("LLM request timed out") from e

    if response.status_code != 200:
        raise ProcessingError(f"LLM returned {response.status_code}: {response.text}")

    result: dict[str, object] = response.json()
    choices = result["choices"]
    assert isinstance(choices, list)
    first_choice: dict[str, object] = choices[0]
    message = first_choice["message"]
    assert isinstance(message, dict)
    content = message["content"]
    assert isinstance(content, str)
    return content.strip()