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
│  │ PulseAudio + VAD     │    │ OpenAI API :9000         │     │
│  └──────────┬───────────┘    └──────────────────────────┘     │
│             │ Tailscale                                        │
└─────────────┼──────────────────────────────────────────────────┘
              ▼
┌──────────────────────────┐
│  M5 AI STATION           │
│  LiteLLM :4000           │
│    → model "rupt"        │
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
  -e BABEL_STT_URL=http://localhost:9000 \
  -e BABEL_LLM_URL=http://m5:4000 \
  -v ${XDG_RUNTIME_DIR}/pulse/native:/tmp/pulse.socket \
  babel-tower-app python -m babel_tower.mcp_server
```

MCP tools: `listen` (record + transcribe + process), `set_mode` (change processing mode).

### 3b. Daemon Mode (Continuous Listening)

```bash
docker compose -f docker/docker-compose.yml up daemon
```

Continuous VAD-based listening. Speech → STT → LLM → clipboard + notification.

## Configuration

All settings via `BABEL_` environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `BABEL_STT_URL` | `http://localhost:9000` | STT API endpoint |
| `BABEL_STT_MODEL` | `large-v3` | Whisper model name |
| `BABEL_STT_LANGUAGE` | `de` | Transcription language |
| `BABEL_STT_TIMEOUT` | `30.0` | STT request timeout (seconds) |
| `BABEL_LLM_URL` | `http://m5:4000` | LLM API endpoint (Tailscale) |
| `BABEL_LLM_MODEL` | `rupt` | LiteLLM model alias |
| `BABEL_LLM_TIMEOUT` | `15.0` | LLM request timeout (seconds) |
| `BABEL_DEFAULT_MODE` | `bereinigen` | Default processing mode |
| `BABEL_REVIEW_ENABLED` | `false` | Show rofi edit popup before clipboard |
| `BABEL_VAD_THRESHOLD` | `0.5` | silero-vad confidence threshold |
| `BABEL_SILENCE_DURATION` | `1.5` | Seconds of silence to end recording |

## Processing Modes

| Mode | Intensity | Use Case |
|------|-----------|----------|
| **strukturieren** | High | Feature descriptions, bug reports — extracts goals, structures into Markdown |
| **bereinigen** | Medium | Conversational input — removes fillers, fixes grammar, preserves tone |
| **durchreichen** | Minimal | Short confirmations — passthrough with typo fixes only |

Auto-selection: transcripts with 5 or fewer words use `durchreichen`, otherwise `default_mode`.

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
python tests/stt_evaluation/evaluate.py --stt-url http://localhost:9000 --wav-dir ./wavs
```
