"""Telegram bot: voice messages → babel_tower pipeline → cleaned text reply."""

import html
from io import BytesIO

from loguru import logger
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from babel_tower.config import Settings
from babel_tower.processing import ProcessingError, process_transcript
from babel_tower.stt import STTError, transcribe

_TELEGRAM_MESSAGE_LIMIT = 4000


def parse_allowed_users(raw: str) -> set[int]:
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


def split_for_telegram(text: str, limit: int = _TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


async def handle_voice(
    audio_bytes: bytes,
    settings: Settings,
) -> str:
    """Run audio through the babel_tower pipeline. Returns reply text (cleaned or error message)."""
    try:
        transcript = await transcribe(audio_bytes, settings)
    except STTError as e:
        logger.error("STT failed: {}", e)
        return f"❌ STT: {e}"

    if not transcript:
        return "⚠️ Keine Sprache erkannt."

    try:
        return await process_transcript(transcript, mode=None, settings=settings)
    except ProcessingError as e:
        logger.warning("LLM postprocessing failed, returning raw transcript: {}", e)
        return transcript


def build_application(settings: Settings) -> Application:
    if not settings.telegram_bot_token:
        raise RuntimeError("BABEL_TELEGRAM_BOT_TOKEN is required")

    app = Application.builder().token(settings.telegram_bot_token).build()
    allowed = parse_allowed_users(settings.telegram_allowed_users)

    async def on_voice(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        if allowed and update.effective_user.id not in allowed:
            logger.warning(
                "Rejecting voice message from unauthorized user {}", update.effective_user.id
            )
            return

        media = update.message.voice or update.message.audio
        if not media:
            return

        try:
            file = await app.bot.get_file(media.file_id)
            buf = BytesIO()
            await file.download_to_memory(buf)
            audio_bytes = buf.getvalue()
        except Exception as e:
            logger.error("Telegram download failed: {}", e)
            await update.message.reply_text(f"❌ Download fehlgeschlagen: {e}")
            return

        await update.message.chat.send_action("typing")
        reply = await handle_voice(audio_bytes, settings)

        if reply.startswith(("❌", "⚠️")):
            await update.message.reply_text(reply)
            return

        for chunk in split_for_telegram(reply):
            await update.message.reply_text(
                f"<pre>{html.escape(chunk)}</pre>", parse_mode="HTML"
            )

    async def on_text(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        if allowed and update.effective_user.id not in allowed:
            return
        await update.message.reply_text("🗼 Schick mir eine Sprachnachricht.")

    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app


def run() -> None:
    settings = Settings()
    app = build_application(settings)
    allowed = parse_allowed_users(settings.telegram_allowed_users)
    logger.info(
        "Starting Babel Tower Telegram Bot (allowed users: {})",
        sorted(allowed) if allowed else "ALL (no ACL)",
    )
    app.run_polling(allowed_updates=["message"], drop_pending_updates=True)


if __name__ == "__main__":
    run()
