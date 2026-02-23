import asyncio
import signal

from babel_tower.audio import NoSpeechError
from babel_tower.config import Settings
from babel_tower.output import notify
from babel_tower.pipeline import run_pipeline


class VoiceDaemon:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._running = False

    async def run(self) -> None:
        self._running = True
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._shutdown)

        notify("Babel Tower", "Daemon gestartet \u2014 warte auf Sprache...", "low")

        while self._running:
            try:
                await run_pipeline(settings=self.settings)
            except NoSpeechError:
                continue
            except Exception as e:
                notify("Babel Tower", f"Fehler: {e}", "critical")
                await asyncio.sleep(1)

        notify("Babel Tower", "Daemon gestoppt", "low")

    def _shutdown(self) -> None:
        self._running = False
