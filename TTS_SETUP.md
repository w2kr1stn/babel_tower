# TTS Setup — Piper via OpenedAI-Speech auf M5

Deployment-Anleitung fuer den TTS-Service auf M5 (AMD Radeon 8060S, CPU-only).

## Ueberblick

```
Laptop (RTX 3060)              M5 (AMD 8060S)
┌──────────────────┐           ┌───────────────────────┐
│ Babel Tower      │           │ LiteLLM        :4000  │
│ STT (speaches)   │──Tailscale──│ OpenedAI-Speech :8000  │
│ Audio/VAD        │           │   └─ Piper TTS (CPU)  │
└──────────────────┘           └───────────────────────┘
```

- **Engine:** Piper TTS (ONNX, CPU-optimiert, sub-second Latenz)
- **Wrapper:** OpenedAI-Speech (OpenAI-kompatible API `/v1/audio/speech`)
- **Image:** `ghcr.io/matatonic/openedai-speech-min` (~860MB, Piper-only, kein CUDA)
- **Stimme:** `thorsten_emotional` (deutsch, medium quality)
- **Port:** 8000

## Verzeichnisstruktur

```
~/tts/
├── docker-compose.yml
├── speech.env
├── config/
│   └── voice_to_speaker.yaml
└── voices/          # wird beim Erststart automatisch befuellt
```

## Setup

### 1. Verzeichnisse anlegen

```bash
mkdir -p ~/tts/config ~/tts/voices
cd ~/tts
```

### 2. docker-compose.yml

```yaml
services:
  tts:
    image: ghcr.io/matatonic/openedai-speech-min
    container_name: openedai-speech
    env_file: speech.env
    ports:
      - "8000:8000"
    volumes:
      - ./voices:/app/voices
      - ./config:/app/config
    restart: unless-stopped
```

### 3. speech.env

```env
TTS_HOME=voices
HF_HOME=voices
```

### 4. config/voice_to_speaker.yaml

```yaml
tts-1:
  thorsten_emotional:
    model: voices/de_DE-thorsten_emotional-medium.onnx
    speaker:
  thorsten:
    model: voices/de_DE-thorsten-medium.onnx
    speaker:

tts-1-hd:
  thorsten_emotional:
    model: voices/de_DE-thorsten_emotional-medium.onnx
    speaker:
  thorsten:
    model: voices/de_DE-thorsten-medium.onnx
    speaker:
```

### 5. Starten

```bash
docker compose up -d
```

Beim ersten Start werden die Piper-Modelle automatisch von Hugging Face heruntergeladen (~50MB pro Stimme). Das kann 1-2 Minuten dauern.

```bash
# Logs pruefen
docker compose logs -f tts
```

## API testen

```bash
# Einfacher TTS-Test
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hallo, ich bin bereit fuer die Voice-Session.",
    "voice": "thorsten_emotional",
    "response_format": "wav"
  }' \
  -o test.wav

# Abspielen
aplay test.wav
# oder: mpv test.wav
# oder: paplay test.wav
```

### Von Laptop via Tailscale testen

```bash
curl -X POST http://m5:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Test ueber Tailscale.",
    "voice": "thorsten_emotional",
    "response_format": "wav"
  }' \
  -o test.wav && aplay test.wav
```

## Babel Tower Konfiguration

Auf dem Laptop (in `.env` oder als Env-Variablen):

```bash
BABEL_TTS_ENABLED=true
BABEL_TTS_URL=http://m5:8000
BABEL_TTS_VOICE=thorsten_emotional
```

## Verfuegbare deutsche Stimmen

| Voice | Beschreibung | Qualitaet |
|---|---|---|
| `thorsten_emotional` | Expressiv, natuerlich | Medium |
| `thorsten` | Neutral, klar | Low/Medium/High |
| `eva_k` | Weiblich | Medium |
| `karlsson` | Maennlich | Low |
| `kerstin` | Weiblich | Low |
| `ramona` | Weiblich | Low/Medium |

Weitere Stimmen hinzufuegen: Eintrag in `voice_to_speaker.yaml` ergaenzen, Modell wird beim ersten Aufruf automatisch heruntergeladen.

Piper Stimmen-Katalog: https://rhasspy.github.io/piper-samples/

## Troubleshooting

**Container startet nicht:**
```bash
docker compose logs tts
```

**Modell-Download haengt:**
Die ONNX-Modelle werden von Hugging Face geladen. Bei Netzwerkproblemen: manuell herunterladen und in `voices/` ablegen.

**Kein Audio / Stimme klingt falsch:**
- `voice` Parameter muss exakt einem Key in `voice_to_speaker.yaml` entsprechen
- `response_format: "wav"` verwenden (mp3 braucht ggf. Extra-Codec)

**Latenz zu hoch:**
- Piper auf CPU sollte <1s fuer kurze Saetze sein
- Tailscale-Latenz pruefen: `ping m5`
- Container-Ressourcen pruefen: `docker stats openedai-speech`

## Hinweise

- openedai-speech ist seit Jan 2026 archiviert (read-only). Das Image funktioniert weiterhin, Piper selbst wird aktiv gepflegt.
- Kein GPU noetig — Piper laeuft vollstaendig auf CPU mit ONNX Runtime.
- Kein Auth — der Service ist nur via Tailscale erreichbar, kein Reverse-Proxy noetig.
