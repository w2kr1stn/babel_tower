# Babel Tower

Voice input pipeline for Claude Code: spoken German/English input → STT → LLM postprocessing → high-quality text.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  LAPTOP HOST (Pop!_OS, PipeWire, RTX 3060)                    │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Dev Container (Djinn in a Box)                          │  │
│  │   └─ Claude Code → spawns babel-tower-app via Docker    │  │
│  └────────┬────────────────────────────────────────────────┘  │
│            │ docker run -i                                     │
│            ▼                                                   │
│  ┌──────────────────────┐    ┌──────────────────────────┐     │
│  │ babel-tower-app      │    │ babel-tower-stt          │     │
│  │ (MCP or Daemon)      │───▶│ (faster-whisper + CUDA)  │     │
│  │ PulseAudio + VAD     │    │ OpenAI API :29000        │     │
│  └──────────┬───────────┘    └──────────────────────────┘     │
│             │ Tailscale                                        │
└─────────────┼──────────────────────────────────────────────────┘
              ▼
┌──────────────────────────┐
│  M5 AI STATION           │
│  LiteLLM :4000           │
│    → model "babel"        │
└──────────────────────────┘
```

## Quick Start

### 1. Start STT Container

```bash
docker compose -f docker/docker-compose.yml up -d stt
```

Requires NVIDIA Container Toolkit. Downloads `Systran/faster-whisper-large-v3` on first run.

### 2. Build App Container

```bash
docker build -f docker/Dockerfile.app -t babel-tower-app ..
```

(Run from `docker/` directory, or use `-f docker/Dockerfile.app` with context `.`)

### 3a. MCP Mode (Claude Code)

```bash
claude mcp add babel-tower -- docker run -i --rm \
  --network host \
  -e PULSE_SERVER=unix:/tmp/pulse.socket \
  -e BABEL_STT_URL=http://localhost:29000 \
  -e BABEL_LLM_URL=http://ai-station:4000 \
  -v ${XDG_RUNTIME_DIR}/pulse/native:/tmp/pulse.socket \
  babel-tower-app python -m babel_tower.mcp_server
```

MCP tools: `converse` (optional speak-message + record + transcribe + process), `set_mode` (change processing mode).

### 3b. Daemon Mode (Continuous Listening)

```bash
docker compose -f docker/docker-compose.yml up daemon
```

Continuous VAD-based listening. Speech → STT → LLM → clipboard + notification.

### 3c. Telegram Bot Mode (Mobile Input)

```bash
docker compose -f docker/docker-compose.m5.yml up -d telegram-bot
```

Deploys a Telegram bot on M5 (24/7 availability, independent of laptop).
Send voice messages to the bot; it replies with the cleaned transcript
wrapped in a tap-to-copy HTML code block — designed for dictating prompts
to Claude Code from mobile.

Requires `BABEL_TELEGRAM_BOT_TOKEN` (from @BotFather) and
`BABEL_TELEGRAM_ALLOWED_USERS` (comma-separated Telegram user IDs) in
`docker/.env`. Unauthorized users are silently ignored.

### 3d. Desktop Hotkey Toggle (same key = start/stop)

On Wayland desktops, binding `babel clean` directly to a DE shortcut has two
problems: there is no Terminal to press Enter to stop the recording, and VAD-
based auto-stop ends recordings prematurely when you pause to think. The
`listen-toggle` subcommand solves this — it records until it receives
`SIGUSR1`, then runs the rest of the pipeline to completion.

Wrap it with a tiny PID-file script to get a true same-key toggle:

```bash
cat > ~/.local/bin/babel-toggle <<'EOF'
#!/usr/bin/env bash
PIDFILE="/tmp/babel-toggle.pid"
LOG="/tmp/babel-toggle.log"
MODE="${1:-clean}"

if [ -f "$PIDFILE" ]; then
  PID=$(cat "$PIDFILE")
  if kill -0 "$PID" 2>/dev/null; then
    kill -USR1 "$PID"
    exit 0
  fi
  rm -f "$PIDFILE"
fi

exec >> "$LOG" 2>&1
exec 0< /dev/null
export PATH="$HOME/.local/bin:$PATH"
"$HOME/.local/bin/babel" listen-toggle --mode "$MODE" &
echo $! > "$PIDFILE"
wait
rm -f "$PIDFILE"
EOF
chmod +x ~/.local/bin/babel-toggle
```

Bind `~/.local/bin/babel-toggle` to a DE shortcut (COSMIC: Settings → Input
Devices → Keyboard → Custom Shortcuts). First press starts recording, second
press ends it and triggers transcription + cleanup. Presses during processing
are swallowed until the pipeline finishes. Result lands in the clipboard
(`Ctrl+V` to paste). For the `structure` mode, use a second shortcut with the
command `~/.local/bin/babel-toggle structure`.

Requires `libnotify-bin` for desktop popups (`sudo apt install libnotify-bin`).

### 3e. HTTP Service Mode (for nanobot/Rupert)

```bash
docker compose -f docker/docker-compose.m5.yml up -d babel-service
```

Exposes `POST /process` on port 3001 (multipart `file` + optional `mode`,
returns `{text, transcript}`). Used by nanobot/Rupert as an STT+cleanup
front end for incoming Telegram voice messages.

## Configuration

All settings via `BABEL_` environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `BABEL_STT_URL` | `http://localhost:29000` | STT API endpoint |
| `BABEL_STT_MODEL` | `Systran/faster-whisper-large-v3` | Whisper model name |
| `BABEL_STT_LANGUAGE` | `de` | Transcription language |
| `BABEL_STT_TIMEOUT` | `600.0` | STT request timeout (seconds) |
| `BABEL_STT_HOTWORDS` | `""` | Comma-separated hotwords for faster-whisper biasing |
| `BABEL_STT_PROMPT` | `""` | Context prompt fed to Whisper |
| `BABEL_STT_CORRECTIONS` | `""` | Post-STT regex find:replace pairs (`wrong:right,…`) |
| `BABEL_LLM_URL` | `http://ai-station:4000` | LLM API endpoint (Tailscale) |
| `BABEL_LLM_MODEL` | `babel` | LiteLLM model alias |
| `BABEL_LLM_API_KEY` | `""` | Bearer token for LiteLLM (optional) |
| `BABEL_LLM_TIMEOUT` | `300.0` | LLM request timeout (seconds) |
| `BABEL_DEFAULT_MODE` | `clean` | Default processing mode |
| `BABEL_DURCHREICHEN_MAX_WORDS` | `5` | Word threshold for auto-`durchreichen` |
| `BABEL_REVIEW_ENABLED` | `false` | Show rofi edit popup before clipboard |
| `BABEL_VAD_THRESHOLD` | `0.5` | silero-vad confidence threshold |
| `BABEL_SILENCE_DURATION` | `2.0` | Seconds of silence to end recording |
| `BABEL_INTER_SEGMENT_TIMEOUT` | `30.0` | Seconds between multi-segment speech bursts |
| `BABEL_MAX_RECORD_SECONDS` | `600` | Hard cap on recording duration |
| `BABEL_TTS_ENABLED` | `false` | Enable spoken replies in `converse` |
| `BABEL_TTS_URL` | `http://m5:8000` | OpenedAI-Speech endpoint |
| `BABEL_TTS_VOICE` | `thorsten_emotional` | Piper TTS voice |
| `BABEL_TELEGRAM_BOT_TOKEN` | `""` | Telegram bot token (required for telegram-bot mode) |
| `BABEL_TELEGRAM_ALLOWED_USERS` | `""` | Comma-separated Telegram user IDs allowed to use the bot |

## Processing Modes

| Mode | Intensity | Use Case |
|------|-----------|----------|
| **structure** | High | Feature descriptions, bug reports — extracts goals, structures into Markdown |
| **clean** | Medium | Conversational input — removes fillers, fixes grammar, preserves tone |
| **durchreichen** | Minimal | Short confirmations — passthrough with typo fixes only |
| **revise** | Meta | Apply spoken change instructions to a previous result (used by `babel revise`) |

Auto-selection: transcripts with `BABEL_DURCHREICHEN_MAX_WORDS` (default 5) or fewer words use `durchreichen`, otherwise `default_mode`.

## Graceful Degradation

- **STT unreachable** → error message returned, critical notification
- **LLM unreachable** → raw transcript used as fallback, notification warns
- **No speech detected** → empty string returned, low notification

## Development

```bash
uv sync                           # Install dependencies
uv run pytest tests/              # Run all tests
uv run ruff check app/ tests/     # Lint
uv run ruff format app/ tests/    # Format
uv run pyright app/               # Type check
```

### STT Evaluation

```bash
# Record 10 test sentences (see tests/stt_evaluation/sentences.json)
python tests/stt_evaluation/evaluate.py --stt-url http://localhost:29000 --wav-dir ./wavs
```
