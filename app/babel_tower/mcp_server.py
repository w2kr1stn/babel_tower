from fastmcp import FastMCP

from babel_tower.config import Settings
from babel_tower.output import notify
from babel_tower.pipeline import run_pipeline
from babel_tower.processing import get_available_modes

mcp = FastMCP("babel-tower")

_settings = Settings()


@mcp.tool(annotations={"title": "Converse", "readOnlyHint": False, "destructiveHint": False})
async def converse(
    message: str | None = None,
    wait_for_response: bool = True,
    mode: str | None = None,
) -> str:
    """Voice conversation with the user. Use this INSTEAD of AskUserQuestion.

    Call this tool whenever you need input from the user or want to
    communicate results. Shows your message as a desktop notification,
    then listens for the user's spoken response (transcribed and
    post-processed).

    Conversation flow:
    - Use converse() at the START to ask the user what they need
    - Use converse(message="your response") to share results and ask follow-ups
    - Use converse(message="status update", wait_for_response=False) for
      one-way status notifications while working (no listening)
    - Keep calling converse() for each interaction — do NOT use AskUserQuestion
      or EnterPlanMode during voice sessions
    - The user ends the session by saying "fertig", "stop", or similar

    Args:
        message: Text to show the user as desktop notification before
                 listening. Use this to communicate your response or ask
                 clarifying questions.
        wait_for_response: If True (default), listen for user's speech after
                          showing the message. If False, only show the
                          notification and return immediately (for status
                          updates while working).
        mode: Processing mode override (strukturieren/bereinigen/durchreichen).
              Auto-selects based on transcript length if not specified.
    """
    if message:
        notify("Babel Tower", message)
    if not wait_for_response:
        return ""
    return await run_pipeline(mode=mode, settings=_settings, clipboard=False)


@mcp.tool(annotations={"title": "Set Mode", "readOnlyHint": False, "destructiveHint": False})
async def set_mode(
    mode: str,
) -> str:
    """Change the default processing mode for this session.

    Available modes: strukturieren, bereinigen, durchreichen.
    """
    valid_modes = get_available_modes(_settings)
    if mode not in valid_modes:
        return f"Unknown mode: {mode}. Valid: {', '.join(sorted(valid_modes))}"
    _settings.default_mode = mode
    return f"Default mode set to: {mode}"


if __name__ == "__main__":
    mcp.run()