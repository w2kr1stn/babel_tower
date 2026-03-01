# Babel Tower — Implementierungsdokumentation

## Zweck

Babel Tower ist eine Voice-Input-Pipeline fuer Claude Code. Gesprochenes Deutsch/Englisch wird ueber eine Kette aus VAD-gesteuerter Audioaufnahme, GPU-beschleunigter Spracherkennung und LLM-Nachbearbeitung in hochwertigen Text umgewandelt. Die Anwendung laeuft vollstaendig containerisiert und integriert sich ueber MCP (Model Context Protocol) direkt in Claude Code.

---

## Architektur

### Systemuebersicht

```
┌──────────────────────────────────────────────────────────────────────┐
│  LAPTOP HOST (Pop!_OS, PipeWire, RTX 3060, Docker)                   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Dev Container (Djinn in a Box)                                  │  │
│  │   └─ Claude Code                                                │  │
│  │       └─ spawnt babel-tower-app via Docker Socket               │  │
│  └─────────┬───────────────────────────────────────────────────────┘  │
│             │ docker run -i (STDIO)                                   │
│             ▼                                                         │
│  ┌──────────────────────────┐    ┌───────────────────────────────┐   │
│  │ babel-tower-app           │    │ babel-tower-stt               │   │
│  │                           │    │                               │   │
│  │ Python 3.13               │    │ speaches (faster-whisper)     │   │
│  │ silero-vad (ONNX)         │    │ CUDA / RTX 3060               │   │
│  │ FastMCP (STDIO)           │───▶│ OpenAI-kompatible API         │   │
│  │ PulseAudio-Socket         │    │ :9000 → :8000 intern          │   │
│  │ wl-copy / notify-send     │    │ large-v3, int8                │   │
│  └──────────┬────────────────┘    └───────────────────────────────┘   │
│             │ HTTP via Tailscale                                      │
└─────────────┼────────────────────────────────────────────────────────┘
              ▼
┌───────────────────────────────┐
│  M5 AI Station                │
│  LiteLLM :4000                │
│    → Modell "babel"            │
│  AMD Radeon 8060S (RDNA 3.5)  │
└───────────────────────────────┘
```

### Signalketten

```
MCP-Pfad (primaer):
  Claude Code
    → docker run -i babel-tower-app python -m babel_tower.mcp_server
      → MCP Tool "listen"
        → Audio aufnehmen (VAD-gesteuert, PulseAudio)
        → STT (babel-tower-stt, localhost:9000)
        → LLM-Nachbearbeitung (M5, Tailscale/LiteLLM)
        → [optional: rofi Review-Popup]
        → Text als Tool-Response an Claude Code

Daemon-Pfad:
  docker compose up daemon
    → Endlosschleife: VAD lauscht auf PulseAudio-Stream
      → Sprache erkannt → Aufnahme → STT → LLM
      → [optional: rofi Review-Popup]
      → Clipboard (wl-copy) + Desktop-Benachrichtigung (notify-send)

CLI-Pfad:
  babel-tower listen [--mode MODE]
    → Einmalaufnahme → STT → LLM → Clipboard + Notification
  babel-tower process <audio.wav> [--mode MODE]
    → WAV-Datei → STT → LLM → Clipboard + Notification
```

### Modul-Abhaengigkeitsgraph

```
cli.py ─────────────────────────────────────────────────────────┐
  │ (lazy imports in jeder Subcommand)                          │
  ├──→ pipeline.py (listen, process)                            │
  ├──→ daemon.py (daemon)                                       │
  └──→ mcp_server.py (mcp)                                     │
                                                                 │
mcp_server.py ──→ pipeline.py (Modul-Level)                     │
               ──→ processing.py (get_available_modes)           │
               ──→ config.py (Settings)                         │
                                                                 │
daemon.py ──→ pipeline.py (Modul-Level)                         │
           ──→ audio.py (NoSpeechError)                         │
           ──→ output.py (notify)                               │
           ──→ config.py (Settings)                             │
                                                                 │
pipeline.py ──→ audio.py (record_speech, NoSpeechError)  ◄──────┘
             ──→ stt.py (transcribe, STTError)
             ──→ processing.py (process_transcript, ProcessingError)
             ──→ output.py (copy_to_clipboard, notify)
             ──→ review.py (lazy, nur wenn review_enabled=true)
             ──→ config.py (Settings)

audio.py ──→ sounddevice (nativ, PortAudio)
          ──→ soundfile
          ──→ silero_vad (ONNX Runtime)
          ──→ numpy
          ──→ config.py

stt.py ──→ httpx (async)
        ──→ config.py

processing.py ──→ httpx (async)
               ──→ pathlib (Prompt-Dateien)
               ──→ config.py

output.py ──→ subprocess (wl-copy, notify-send)

review.py ──→ subprocess (rofi)

config.py ──→ pydantic_settings
```

---

## Datenfluss

### Vollstaendiger Pipeline-Durchlauf

```
                            ┌─────────────────────────┐
                            │  PulseAudio-Mikrofon     │
                            │  16 kHz, mono, int16     │
                            └────────────┬─────────────┘
                                         │
                        ┌────────────────▼────────────────┐
                        │  audio.py: _record_speech_blocking │
                        │                                    │
                        │  silero-vad (ONNX)                 │
                        │  512-Sample-Chunks (32 ms)         │
                        │  Schwellwert: vad_threshold (0.5)  │
                        │                                    │
                        │  Sprache erkannt? ──nein──▶ NoSpeechError
                        │       │ ja                         │
                        │       ▼                            │
                        │  Aufnahme bis Stille               │
                        │  (silence_duration: 1.5s)          │
                        │  Max: 60 Sekunden                  │
                        │       │                            │
                        │       ▼                            │
                        │  WAV-Bytes (BytesIO, PCM_16)       │
                        └────────────────┬───────────────────┘
                                         │
                        ┌────────────────▼────────────────┐
                        │  stt.py: transcribe              │
                        │                                  │
                        │  POST /v1/audio/transcriptions   │
                        │  multipart/form-data:            │
                        │    file=audio.wav                 │
                        │    model=large-v3                 │
                        │    language=de                    │
                        │  Timeout: stt_timeout (30s)       │
                        │                                  │
                        │  Fehler? ──▶ STTError            │
                        │       │                          │
                        │       ▼                          │
                        │  Rohes Transkript (str)           │
                        └────────────────┬─────────────────┘
                                         │
                        ┌────────────────▼────────────────┐
                        │  processing.py: process_transcript│
                        │                                  │
                        │  Modus-Auswahl:                   │
                        │    Woerter <= 5? → durchreichen   │
                        │    Sonst → default_mode           │
                        │    Oder: expliziter mode-Parameter│
                        │                                  │
                        │  System-Prompt aus prompts/*.md    │
                        │                                  │
                        │  POST /v1/chat/completions        │
                        │  {"model":"babel",                 │
                        │   "messages":[system, user]}      │
                        │  Timeout: llm_timeout (15s)       │
                        │                                  │
                        │  Fehler? ──▶ ProcessingError     │
                        │       │                          │
                        │       ▼                          │
                        │  Nachbearbeiteter Text (str)      │
                        └────────────────┬─────────────────┘
                                         │
                    ┌────────────────────▼─────────────────────┐
                    │  review.py (optional, wenn review_enabled) │
                    │                                           │
                    │  rofi -dmenu -p "Babel Tower"             │
                    │    -filter <text> -l 0                    │
                    │  Timeout: 60s                             │
                    │                                           │
                    │  Escape/Timeout → None → Pipeline bricht ab│
                    │  Enter → bearbeiteter Text                │
                    └────────────────────┬──────────────────────┘
                                         │
                        ┌────────────────▼────────────────┐
                        │  output.py                       │
                        │                                  │
                        │  wl-copy <text>    → Clipboard   │
                        │  notify-send       → Notification│
                        │    --urgency=normal               │
                        │    Body: max 200 Zeichen          │
                        │  Beide: Timeout 5s, fail-safe     │
                        └──────────────────────────────────┘
```

### Graceful Degradation

```
Fehler in der Pipeline             │ Verhalten
───────────────────────────────────┼──────────────────────────────────────
NoSpeechError (VAD)                │ → "" (leerer String), Notification "low"
STTError (Netzwerk/Timeout)        │ → "[STT-Fehler: <details>]", Notification "critical"
Leeres Transkript                  │ → "" (leerer String), Notification "low"
ProcessingError (LLM offline)      │ → Rohes Transkript als Fallback, Notification "normal"
Review abgebrochen (Escape/Timeout)│ → "" (leerer String), Notification "low"
wl-copy/notify-send nicht verfuegbar│ → False (kein Crash), Pipeline laeuft weiter
```

---

## Module im Detail

### config.py — Konfiguration

Zentrale Konfigurationsklasse auf Basis von Pydantic Settings. Alle Werte ueberschreibbar via `BABEL_<FELDNAME>` Umgebungsvariablen.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BABEL_")

    # STT (Speech-to-Text)
    stt_url: str = "http://localhost:9000"       # speaches API-Endpunkt
    stt_model: str = "large-v3"                  # Whisper-Modell
    stt_language: str = "de"                     # Transkriptionssprache
    stt_timeout: float = 30.0                    # HTTP-Timeout in Sekunden

    # LLM (Nachbearbeitung)
    llm_url: str = "http://m5:4000"              # LiteLLM-Endpunkt (Tailscale)
    llm_model: str = "babel"                      # Modell-Alias in LiteLLM
    llm_timeout: float = 15.0                    # HTTP-Timeout in Sekunden

    # Audio-Aufnahme
    audio_sample_rate: int = 16000               # Hz (Pflicht fuer silero-vad)
    audio_channels: int = 1                      # Mono
    vad_threshold: float = 0.5                   # silero-vad Konfidenz-Schwelle
    silence_duration: float = 1.5                # Sekunden Stille bis Aufnahme-Ende

    # Verarbeitung
    default_mode: str = "bereinigen"             # Standard-Verarbeitungsmodus
    durchreichen_max_words: int = 5              # Auto-Durchreichen-Schwelle
    review_enabled: bool = False                 # rofi-Review vor Clipboard (opt-in)
    prompts_dir: str = "prompts"                 # Pfad zu System-Prompt-Dateien
```

Pydantic uebernimmt automatisch die Typkonvertierung aus Umgebungsvariablen-Strings (z.B. `"44100"` → `int`, `"true"` → `bool`).

### audio.py — Audioaufnahme mit VAD

**Zentrale Aufgabe:** Mikrofon-Audio aufnehmen, per Voice Activity Detection (VAD) Sprachgrenzen erkennen, WAV-Bytes liefern.

**Technologie-Stack:**
- `sounddevice` (PortAudio-Binding) fuer Mikrofon-Zugriff
- `silero-vad` (ONNX Runtime, kein PyTorch) fuer Spracherkennung
- `soundfile` fuer WAV-Encoding
- `numpy` fuer Audio-Datenverarbeitung

**Konstanten:**
- `VAD_CHUNK_SIZE = 512` — Samples pro VAD-Verarbeitungsschritt (32 ms bei 16 kHz, Pflicht fuer silero-vad)
- `MAX_RECORD_SECONDS = 60` — Harte Obergrenze fuer Aufnahmedauer

**Aufnahmealgorithmus** (`_record_speech_blocking`):

1. silero-vad Modell laden (`onnx=True` — vermeidet PyTorch-Abhaengigkeit)
2. `VADIterator` erstellen mit konfigurierbarer Schwelle und Stille-Dauer
3. `sd.InputStream` oeffnen (16 kHz, mono, int16, blocksize=512)
4. Schleife ueber max. 1875 Chunks (= 60 Sekunden):
   - 512 Samples lesen → int16 → float32 normalisieren (`/ 32768.0`)
   - VAD aufrufen:
     - `{"start": sample}` → Sprachbeginn, ab jetzt Frames sammeln
     - `{"end": sample}` → Sprachende nach Stille, Schleife beenden
     - `None` → kein Ereignis
5. Keine Sprache erkannt → `NoSpeechError`
6. Frames zu einem `numpy`-Array konkatenieren
7. Als WAV (PCM_16) in `BytesIO` schreiben

**Async-Wrapper:** `record_speech()` nutzt `asyncio.to_thread()` um den blockierenden `InputStream`-Loop in einem separaten Thread auszufuehren.

**Fehlerklasse:** `NoSpeechError(Exception)` — wird geworfen wenn die VAD innerhalb von 60 Sekunden keinen Sprachbeginn erkennt.

### stt.py — STT-Client

**Zentrale Aufgabe:** WAV-Audio an den STT-Service senden, Transkript-Text zurueckbekommen.

**API-Vertrag:** OpenAI-kompatible `/v1/audio/transcriptions` Schnittstelle (multipart/form-data).

**Ablauf** (`transcribe`):
1. Audio als `bytes` oder `BytesIO` akzeptieren (BytesIO wird zu bytes konvertiert)
2. HTTP POST mit:
   - `file`: `("audio.wav", bytes, "audio/wav")`
   - `data`: `{"model": "large-v3", "language": "de"}`
3. Timeout: konfigurierbar via `BABEL_STT_TIMEOUT` (Standard: 30s)
4. Response parsen: `response.json()["text"]`

**Fehlerbehandlung:**
- `httpx.ConnectError` → `STTError("STT service unreachable at ...")`
- `httpx.TimeoutException` → `STTError("STT request timed out")`
- HTTP-Status != 200 → `STTError("STT returned <status>: <body>")`

### processing.py — LLM-Nachbearbeitung

**Zentrale Aufgabe:** Rohes Transkript durch ein LLM veredeln lassen. Modus bestimmt Intensitaet der Bearbeitung.

**Verarbeitungsmodi:**

| Modus | Intensitaet | Einsatzzweck |
|-------|-------------|--------------|
| `strukturieren` | Hoch | Feature-Beschreibungen, Aufgabenplanung — extrahiert Ziele, strukturiert in Markdown |
| `bereinigen` | Mittel | Normaler Gespraechsinput — entfernt Fuellwoerter, korrigiert Grammatik, bewahrt Ton |
| `durchreichen` | Minimal | Kurze Bestaetigung — nur offensichtliche Tippfehler korrigieren |

**Automatische Modus-Auswahl:**
- `mode`-Parameter explizit gesetzt → diesen verwenden
- Transkript hat <= 5 Woerter (`durchreichen_max_words`) → `durchreichen`
- Sonst → `default_mode` (Standard: `bereinigen`)

**Prompt-Aufloesung** (`_resolve_prompts_dir`):
- Relativer Pfad (Standard `"prompts"`) wird relativ zum Projekt-Root aufgeloest
- Berechnung: `Path(__file__).resolve().parent.parent.parent / prompts_dir`
- Absoluter Pfad wird direkt verwendet

**Dynamische Modus-Erkennung** (`get_available_modes`):
- Liest alle `*.md`-Dateien aus dem Prompts-Verzeichnis
- Gibt `{p.stem for p in ...glob("*.md")}` zurueck (z.B. `{"strukturieren", "bereinigen", "durchreichen"}`)
- Wird von `mcp_server.py` fuer die Validierung in `set_mode` verwendet

**LLM-Aufruf** (`_call_llm`):
- API: OpenAI-kompatible `/v1/chat/completions` (LiteLLM auf M5)
- Payload: `{"model": "babel", "messages": [{"role": "system", ...}, {"role": "user", ...}]}`
- Timeout: konfigurierbar via `BABEL_LLM_TIMEOUT` (Standard: 15s)
- Response-Parsing mit Runtime-`assert isinstance()` fuer strikte pyright-Kompatibilitaet

**Fehlerklasse:** `ProcessingError(Exception)` — LLM nicht erreichbar, Timeout, oder ungueltiger HTTP-Status.

### output.py — Clipboard und Benachrichtigungen

**Zentrale Aufgabe:** Text in die Zwischenablage kopieren und Desktop-Benachrichtigungen anzeigen.

**`copy_to_clipboard(text: str) -> bool`:**
- Fuehrt `wl-copy <text>` als Subprocess aus (Wayland-only)
- Timeout: 5 Sekunden
- Gibt `True` bei Erfolg zurueck, `False` bei `FileNotFoundError`, `CalledProcessError`, `TimeoutExpired`

**`notify(title: str, body: str, urgency: str = "normal") -> bool`:**
- Fuehrt `notify-send --urgency=<urgency> <title> <body[:200]>` als Subprocess aus
- Body wird auf 200 Zeichen abgeschnitten
- Urgency-Level: `"low"`, `"normal"`, `"critical"`
- Gleiche Fehlerbehandlung wie `copy_to_clipboard`

Beide Funktionen sind fail-safe: ein Fehler fuehrt nie zu einem Crash der Pipeline.

### review.py — Optionale Textueberarbeitung

**Zentrale Aufgabe:** Dem Nutzer den verarbeiteten Text vor dem Clipboard-Einfuegen zum Bearbeiten anzeigen (opt-in).

**`review_text(text: str) -> str | None`:**
- Zeigt rofi im dmenu-Modus mit dem Text als vorausgefuelltem Filter:
  ```
  rofi -dmenu -p "Babel Tower" -filter <text> -l 0
  ```
- `-l 0`: Keine Listeneintraege, reines Textfeld
- `-filter`: Vorbelegung des Eingabefelds
- Timeout: 60 Sekunden
- Rueckgabe:
  - Bearbeiteter Text (Enter gedrueckt)
  - `None` bei Escape, Timeout, oder fehlendem rofi

**Integration:** Lazy-Import in `pipeline.py` (nur wenn `settings.review_enabled == True`). Wird nach der LLM-Verarbeitung, vor dem Clipboard-Kopieren ausgefuehrt.

### pipeline.py — Orchestrierung

**Zentrale Aufgabe:** Die gesamte Verarbeitungskette verdrahten und Fehler abfangen.

**`run_pipeline(mode, settings) -> str`** — Vollstaendiger Durchlauf mit Audioaufnahme:

```
1. notify("Aufnahme gestartet...")
2. record_speech()          ──▶ NoSpeechError? → "" + Notification
3. notify("Transkribiere...")
4. transcribe()             ──▶ STTError? → "[STT-Fehler: ...]" + Notification
5. Leeres Transkript?       ──▶ "" + Notification
6. notify("Verarbeite...")
7. process_transcript()     ──▶ ProcessingError? → Rohtranskript als Fallback
8. review_text()            ──▶ None? → "" (verworfen) + Notification
   (nur wenn review_enabled)
9. copy_to_clipboard()
10. notify(result[:100])
11. return result
```

**`process_file(audio_path, mode, settings) -> str`** — Gleiche Kette, aber mit WAV-Datei statt Mikrofonaufnahme. Kein initialer Aufnahme-Schritt, liest stattdessen `audio_path` als Bytes ein.

**Benachrichtigungen** im Normalbetrieb: 4 Stueck (Aufnahme, Transkription, Verarbeitung, Ergebnis).

### daemon.py — Endlosschleife

**Zentrale Aufgabe:** Kontinuierlich auf Sprache lauschen und bei Erkennung die Pipeline triggern.

**`class VoiceDaemon`:**

```python
async def run(self):
    # Signal-Handler fuer graceful Shutdown
    for sig in (SIGINT, SIGTERM):
        loop.add_signal_handler(sig, self._shutdown)

    notify("Daemon gestartet — warte auf Sprache...")

    while self._running:
        try:
            await run_pipeline(settings=self.settings)
        except NoSpeechError:
            continue                     # Stille → naechster Durchlauf
        except Exception as e:
            notify(f"Fehler: {e}", urgency="critical")
            await asyncio.sleep(1)       # Backoff bei Fehler

    notify("Daemon gestoppt")
```

**Shutdown:** `SIGINT` oder `SIGTERM` setzen `self._running = False`. Die aktuelle Aufnahme wird beendet (VAD-Timeout oder naechster Chunk), dann bricht die Schleife ab.

### mcp_server.py — MCP-Integration

**Zentrale Aufgabe:** Claude Code zwei Tools bereitstellen: `listen` (Sprachaufnahme + Verarbeitung) und `set_mode` (Modus wechseln).

**Framework:** FastMCP 3.0.2, STDIO-Transport (Standard).

**Shared State:** Modul-Level `_settings = Settings()` — wird von `set_mode` mutiert und von `listen` gelesen. Lebt fuer die Dauer der MCP-Session.

**Tool `listen(mode: str | None = None) -> str`:**
- Delegiert vollstaendig an `run_pipeline(mode=mode, settings=_settings)`
- Optionaler `mode`-Parameter ueberschreibt den Session-Default

**Tool `set_mode(mode: str) -> str`:**
- Validiert gegen `get_available_modes(_settings)` (dynamisch vom Dateisystem)
- Mutiert `_settings.default_mode` bei Erfolg
- Gibt Bestaetigungs- oder Fehlermeldung als String zurueck

**Annotations:** `readOnlyHint=False`, `destructiveHint=False` auf beiden Tools.

### cli.py — Kommandozeile

**Zentrale Aufgabe:** Einstiegspunkt fuer alle Betriebsmodi. Entry-Point: `babel-tower` (registriert in `pyproject.toml`).

**Subcommands:**

| Command | Beschreibung |
|---------|-------------|
| `babel-tower listen [--mode MODE]` | Einmalaufnahme → Pipeline → Ergebnis auf stdout |
| `babel-tower process <audio.wav> [--mode MODE]` | WAV-Datei → Pipeline → Ergebnis auf stdout |
| `babel-tower daemon [--mode MODE]` | Endlosschleife (VAD-gesteuert) |
| `babel-tower mcp` | FastMCP-Server starten (STDIO-Transport) |

**Lazy Imports:** Alle schweren Module (`pipeline`, `daemon`, `mcp_server`) werden erst innerhalb der jeweiligen Subcommand-Funktion importiert. Dies vermeidet PortAudio-Import-Fehler beim bloessen Laden des CLI-Moduls.

---

## Docker-Infrastruktur

### Container-Topologie

```
┌──────────────────────────────────────────────────────────┐
│  docker-compose.yml                                       │
│                                                           │
│  ┌─────────────────────┐    ┌──────────────────────────┐ │
│  │ stt                  │    │ daemon                   │ │
│  │                      │    │                          │ │
│  │ speaches:latest-cuda │    │ Dockerfile.app           │ │
│  │ Healthcheck :8000    │    │ Python 3.13-slim         │ │
│  │ Port 9000→8000       │    │                          │ │
│  │ GPU (nvidia, 1x)     │◄───│ BABEL_STT_URL=           │ │
│  │ Model-Cache Volume   │    │   http://stt:9000        │ │
│  └─────────────────────┘    │                          │ │
│                              │ PulseAudio-Socket ◄──────┼─── Host-Mikrofon
│                              │ Wayland-Socket ◄─────────┼─── wl-copy, notify-send
│                              └──────────────────────────┘ │
│                                                           │
│  Volume: stt-models (HuggingFace Model-Cache)             │
└──────────────────────────────────────────────────────────┘
```

### STT-Container (`babel-tower-stt`)

- **Image:** `ghcr.io/speaches-ai/speaches:latest-cuda` (vorgefertigtes Image, kein eigenes Dockerfile)
- **Modell:** `Systran/faster-whisper-large-v3` mit `int8`-Quantisierung
- **GPU:** NVIDIA, 1 GPU reserviert (`deploy.resources.reservations.devices`)
- **Port-Mapping:** Host `9000` → Container `8000`
- **Model-Cache:** Named Volume `stt-models` unter `/home/ubuntu/.cache/huggingface/hub`
- **Healthcheck:** `curl -f http://localhost:8000/health` (30s Intervall, 60s Start-Grace-Period)
- **Konfiguration via Umgebungsvariablen:**
  - `WHISPER__MODEL=Systran/faster-whisper-large-v3`
  - `WHISPER__COMPUTE_TYPE=int8`

Das Modell wird beim ersten Container-Start automatisch von HuggingFace heruntergeladen und im Volume persistiert.

### App-Container (`babel-tower-daemon` / MCP)

**Dockerfile.app:**

```dockerfile
FROM python:3.13-slim

# Audio-Abhaengigkeiten und System-Tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpulse0 \           # PulseAudio-Client-Bibliothek
    libportaudio2 \       # PortAudio (fuer sounddevice)
    portaudio19-dev \     # PortAudio-Header
    wl-clipboard \        # wl-copy (Wayland Clipboard)
    libnotify-bin \       # notify-send (Desktop-Benachrichtigungen)
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# uv Paketmanager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_LINK_MODE=copy UV_CACHE_DIR=/tmp/uv-cache

# Anwendung installieren
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY app/ app/
COPY prompts/ prompts/
RUN uv sync --frozen

ENTRYPOINT ["uv", "run"]
CMD ["python", "-m", "babel_tower.cli", "daemon"]
```

**Daemon-Modus** (docker-compose):
- PulseAudio-Socket vom Host gemountet → Mikrofon-Zugriff
- Wayland-Socket vom Host gemountet → wl-copy und notify-send funktionieren
- Laeuft als Host-User (`UID:GID`)
- Wartet auf STT-Healthcheck (`depends_on: stt: condition: service_healthy`)

**MCP-Modus** (manueller `docker run`):
```bash
docker run -i --rm \
  --network host \
  -e PULSE_SERVER=unix:/tmp/pulse.socket \
  -e BABEL_STT_URL=http://localhost:9000 \
  -e BABEL_LLM_URL=http://m5:4000 \
  -v ${XDG_RUNTIME_DIR}/pulse/native:/tmp/pulse.socket \
  babel-tower-app python -m babel_tower.mcp_server
```

---

## Konfiguration

### Vollstaendige Variablentabelle

| Variable | Typ | Standard | Beschreibung |
|----------|-----|----------|-------------|
| `BABEL_STT_URL` | `str` | `http://localhost:9000` | STT-API-Endpunkt |
| `BABEL_STT_MODEL` | `str` | `large-v3` | Whisper-Modellname |
| `BABEL_STT_LANGUAGE` | `str` | `de` | Transkriptionssprache |
| `BABEL_STT_TIMEOUT` | `float` | `30.0` | STT-Request-Timeout (Sekunden) |
| `BABEL_LLM_URL` | `str` | `http://m5:4000` | LLM-API-Endpunkt (Tailscale) |
| `BABEL_LLM_MODEL` | `str` | `rupt` | LiteLLM-Modell-Alias |
| `BABEL_LLM_TIMEOUT` | `float` | `15.0` | LLM-Request-Timeout (Sekunden) |
| `BABEL_AUDIO_SAMPLE_RATE` | `int` | `16000` | Abtastrate in Hz |
| `BABEL_AUDIO_CHANNELS` | `int` | `1` | Audiokanaele (mono) |
| `BABEL_VAD_THRESHOLD` | `float` | `0.5` | silero-vad Konfidenz-Schwelle |
| `BABEL_SILENCE_DURATION` | `float` | `1.5` | Stille-Dauer bis Aufnahme-Ende (Sekunden) |
| `BABEL_DEFAULT_MODE` | `str` | `bereinigen` | Standard-Verarbeitungsmodus |
| `BABEL_DURCHREICHEN_MAX_WORDS` | `int` | `5` | Schwelle fuer Auto-Durchreichen |
| `BABEL_REVIEW_ENABLED` | `bool` | `false` | rofi-Review-Popup aktivieren |
| `BABEL_PROMPTS_DIR` | `str` | `prompts` | Pfad zu System-Prompt-Dateien |

---

## Fehlerbehandlung

### Fehlerklassen-Hierarchie

```
Exception
├── NoSpeechError      (audio.py)    — VAD erkennt keine Sprache
├── STTError           (stt.py)      — STT-Service nicht erreichbar/fehlerhaft
├── ProcessingError    (processing.py) — LLM nicht erreichbar/fehlerhaft
├── FileNotFoundError  (output.py)   — wl-copy/notify-send/rofi nicht installiert
└── TimeoutExpired     (output.py)   — Subprocess-Timeout (5s output, 60s review)
```

Jede Fehlerklasse kapselt die zugrundeliegende httpx-Exception (`ConnectError`, `TimeoutException`) via `raise ... from e`.

### Fehlerbehandlungsstrategie nach Schicht

**audio.py:** Wirft `NoSpeechError` — kein Fallback moeglich, da es keinen sinnvollen Default gibt.

**stt.py:** Wirft `STTError` — Retry-Logik oder Fallback liegt bei der aufrufenden Schicht.

**processing.py:** Wirft `ProcessingError` — bewusst kein interner Fallback; die Pipeline entscheidet ueber Degradation.

**pipeline.py:** Faengt alle Fehler ab und degradiert intelligent:
- `NoSpeechError` → leerer String, niedrige Benachrichtigung
- `STTError` → Fehlermeldung als Ergebnis, kritische Benachrichtigung
- `ProcessingError` → rohes Transkript als Fallback, normale Benachrichtigung

**output.py / review.py:** Alle Subprocess-Fehler werden gefangen und geben `False` bzw. `None` zurueck — kein Crash.

**daemon.py:** Zweistufig:
- `NoSpeechError` → `continue` (naechster Durchlauf, keine Benachrichtigung)
- Jede andere Exception → Benachrichtigung + 1 Sekunde Backoff

---

## Externe Abhaengigkeiten

### Runtime

| Paket | Version | Zweck |
|-------|---------|-------|
| `fastmcp` | >=3.0.0 | MCP-Server (STDIO-Transport) |
| `httpx` | >=0.28.0 | Async HTTP-Client (STT, LLM) |
| `pydantic-settings` | >=2.7.0 | Konfiguration via Umgebungsvariablen |
| `silero-vad` | >=5.1 | Voice Activity Detection (ONNX, kein PyTorch) |
| `sounddevice` | >=0.5.0 | Mikrofon-Zugriff (PortAudio-Binding) |
| `soundfile` | >=0.13.0 | WAV-Encoding/Decoding |
| `numpy` | >=2.0.0 | Audio-Datenverarbeitung |
| `typer` | >=0.15.0 | CLI-Framework |

### System (in Dockerfile.app)

| Paket | Zweck |
|-------|-------|
| `libpulse0` | PulseAudio-Client-Bibliothek |
| `libportaudio2` + `portaudio19-dev` | PortAudio (sounddevice-Backend) |
| `wl-clipboard` | `wl-copy` fuer Wayland-Clipboard |
| `libnotify-bin` | `notify-send` fuer Desktop-Benachrichtigungen |

### Externe Services

| Service | Zugang | Zweck |
|---------|--------|-------|
| speaches (faster-whisper) | `localhost:9000` (Docker) | GPU-beschleunigte Spracherkennung |
| LiteLLM auf M5 | `m5:4000` (Tailscale) | LLM-Nachbearbeitung |

---

## Test-Architektur

### Teststruktur

```
tests/
├── conftest.py            # Shared Fixtures (clean_env, env_overrides)
├── test_config.py         # Settings: Defaults, Env-Overrides
├── test_stt.py            # STT-Client: HTTP-Mocking
├── test_audio.py          # Audio: sounddevice-Stub, VAD-Mocking
├── test_processing.py     # LLM: HTTP-Mocking, Modus-Auswahl, Prompt-Loading
├── test_pipeline.py       # Pipeline: Alle Sub-Module gemockt
├── test_output.py         # Output: Subprocess-Mocking
├── test_review.py         # Review: rofi Subprocess-Mocking
├── test_daemon.py         # Daemon: Loop-Kontrolle via side_effect
├── test_mcp_server.py     # MCP: Tool-Funktionen direkt aufrufen
└── stt_evaluation/
    ├── evaluate.py        # WER-Evaluierungsskript (standalone)
    └── sentences.json     # 10 Referenzsaetze (DE/EN Code-Switching)
```

### Test-Patterns

**sounddevice-Stub:** `sys.modules["sounddevice"] = MagicMock()` muss vor dem Import jedes Moduls gesetzt werden, das `audio.py` direkt oder transitiv importiert (`pipeline.py`, `daemon.py`, `mcp_server.py`).

**Async-Tests:** Alle async Tests verwenden `@pytest.mark.anyio` (nicht `asyncio`).

**HTTP-Mocking:** `monkeypatch.setattr(httpx.AsyncClient, "post", mock_fn)` — mockt auf Client-Ebene, nicht auf Modul-Ebene.

**Pipeline-Mocking:** `unittest.mock.patch("babel_tower.pipeline.<function>")` — mockt die Referenz im Namespace der Pipeline, nicht im Quell-Modul.

**Daemon-Loop-Kontrolle:** `side_effect`-Callbacks setzen `daemon._running = False` um die Endlosschleife nach kontrollierter Iteration zu beenden.

**Environment-Isolation:** `clean_env`-Fixture loescht alle `BABEL_*`-Variablen; `env_overrides` setzt definierte Testwerte.

### STT-Evaluierung

Eigenstaendiges Skript (nicht Teil der pytest-Suite) zur Messung der Transkriptionsqualitaet:

- 10 Referenzsaetze mit DE/EN Code-Switching (z.B. *"Der API Endpoint braucht ein Rate Limiting"*)
- WER-Berechnung via `jiwer` gegen manuell aufgenommene WAV-Dateien
- Markdown-Report mit Per-Satz und Durchschnitts-WER
- WAV-Dateien muessen manuell aufgenommen werden (nicht im Repository)

```bash
python tests/stt_evaluation/evaluate.py --stt-url http://localhost:9000 --wav-dir ./wavs
```

---

## Projekt-Layout

```
babel_tower/
├── pyproject.toml                    # Build, Dependencies, Tool-Konfiguration
├── uv.lock                          # Deterministische Dependency-Locks
├── devops.py                        # fmt, test, clean Skripte
├── docker/
│   ├── Dockerfile.app               # App-Container (Python + Audio-Deps)
│   └── docker-compose.yml           # STT + Daemon Services
├── app/babel_tower/                  # Python-Package (via hatch → babel_tower)
│   ├── __init__.py
│   ├── config.py                    # Pydantic Settings
│   ├── audio.py                     # Audioaufnahme + VAD
│   ├── stt.py                       # STT-Client
│   ├── processing.py                # LLM-Nachbearbeitung
│   ├── output.py                    # Clipboard + Notification
│   ├── review.py                    # rofi Review-UI
│   ├── pipeline.py                  # Orchestrierung
│   ├── daemon.py                    # Endlosschleife
│   ├── mcp_server.py                # FastMCP-Server
│   └── cli.py                       # Typer CLI
├── prompts/
│   ├── strukturieren.md             # System-Prompt: tiefe Restrukturierung
│   ├── bereinigen.md                # System-Prompt: leichte Bereinigung
│   └── durchreichen.md              # System-Prompt: minimaler Durchlauf
└── tests/
    ├── conftest.py                  # Shared Fixtures
    ├── test_config.py
    ├── test_audio.py
    ├── test_stt.py
    ├── test_processing.py
    ├── test_pipeline.py
    ├── test_output.py
    ├── test_review.py
    ├── test_daemon.py
    ├── test_mcp_server.py
    └── stt_evaluation/
        ├── evaluate.py              # WER-Evaluierungsskript
        └── sentences.json           # 10 Referenzsaetze
```

### Package-Mapping

`pyproject.toml` nutzt hatch Build-Targets um `app/babel_tower/` auf `babel_tower` abzubilden:

```toml
[tool.hatch.build.targets.wheel.sources]
"app" = ""
```

Pyright und pytest erhalten `extraPaths = ["app"]` bzw. `pythonpath = ["app"]`, damit `import babel_tower` in beiden Kontexten funktioniert.
