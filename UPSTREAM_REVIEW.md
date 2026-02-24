# Upstream Review — Claude Code VoiceMode

## What is VoiceMode?

Claude Code's built-in voice input feature. Currently in development as part of the Claude Code CLI.

- Reference: [VoiceMode MCP](https://github.com/mbailey/voicemode) (community implementation)
- Status: Not yet a first-party feature in Claude Code

## Babel Tower vs VoiceMode

| Feature | Babel Tower | VoiceMode (community) |
|---------|-------------|----------------------|
| STT Engine | faster-whisper (self-hosted, GPU) | Cloud-based (varies) |
| DE/EN Code-Switching | Optimized (large-v3) | Depends on provider |
| LLM Postprocessing | 3 modes (strukturieren/bereinigen/durchreichen) | None |
| Mode Selection | Auto + explicit | N/A |
| Review UI | rofi-based editing before output | None |
| Offline STT | Yes (local Docker) | No |
| Graceful Degradation | STT error + LLM fallback handled | Basic |
| MCP Integration | STDIO transport | STDIO transport |

## When Babel Tower Becomes Obsolete

Babel Tower can be retired when Claude Code VoiceMode natively supports:

1. **LLM Postprocessing** — Automatic cleanup/restructuring of spoken input before it reaches the conversation
2. **Mode Selection** — Different processing intensities (deep restructuring vs light cleanup vs passthrough)
3. **DE/EN Code-Switching** — Accurate recognition of German speech with English technical terms
4. **Local STT** — Self-hosted STT option for low-latency and privacy
5. **Review Step** — Editable preview before text is submitted

Until all 5 criteria are met, Babel Tower provides value that VoiceMode doesn't.

## Review Schedule

Check quarterly (or on major Claude Code releases) whether VoiceMode has closed the gap on any of these criteria.

Last reviewed: 2026-02-24
