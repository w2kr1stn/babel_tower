from fastmcp import FastMCP

from babel_tower.config import Settings
from babel_tower.pipeline import run_pipeline

mcp = FastMCP("babel-tower")

_settings = Settings()


@mcp.tool(annotations={"title": "Listen", "readOnlyHint": False, "destructiveHint": False})
async def listen(
    mode: str | None = None,
) -> str:
    """Record speech via microphone, transcribe with STT, and post-process with LLM.

    Returns the processed text. Uses VAD for automatic speech boundary detection.
    Available modes: strukturieren (deep restructuring), bereinigen (light cleanup),
    durchreichen (passthrough).
    If no mode specified, auto-selects based on transcript length.
    """
    return await run_pipeline(mode=mode, settings=_settings)


@mcp.tool(annotations={"title": "Set Mode", "readOnlyHint": False, "destructiveHint": False})
async def set_mode(
    mode: str,
) -> str:
    """Change the default processing mode for this session.

    Available modes: strukturieren, bereinigen, durchreichen.
    """
    valid_modes = {"strukturieren", "bereinigen", "durchreichen"}
    if mode not in valid_modes:
        return f"Unknown mode: {mode}. Valid: {', '.join(sorted(valid_modes))}"
    _settings.default_mode = mode
    return f"Default mode set to: {mode}"


if __name__ == "__main__":
    mcp.run()
