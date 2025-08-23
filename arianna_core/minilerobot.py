"""Telegram bot interface for mini_LE responses."""

import os
import asyncio
from typing import Optional

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import mini_le

# Импортируем скриптпоэтри
# Импорт основной логики системы с безопасным фолбэком
try:
    from .skryptbridge import process_message
    SKRYPTBRIDGE_AVAILABLE = True
except ImportError:
    try:
        from arianna_core.skryptbridge import process_message
        SKRYPTBRIDGE_AVAILABLE = True
    except ImportError:
        # Полный фолбэк - используем только MiniLE
        SKRYPTBRIDGE_AVAILABLE = False
        process_message = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Respond to the /start command."""
    if update.message:
        await update.message.reply_text("Send messages with /chat <text>.")


async def _send_response(update: Update, text: str) -> None:
    """Send response using SkryptBridge or MiniLE fallback."""
    try:
        if SKRYPTBRIDGE_AVAILABLE and process_message:
            # Используем SkryptBridge для обработки сообщения
            response = await process_message(text)
        else:
            # Фолбэк - только MiniLE
            import logging
            logging.warning("SkryptBridge unavailable, using MiniLE fallback")
            response = mini_le.chat_response(text)
    except Exception as exc:  # pragma: no cover - unexpected failure
        import logging
        logging.exception("Response generation failed: %s", exc)
        # Последний фолбэк - только MiniLE
        try:
            response = mini_le.chat_response(text)
        except:
            response = "System temporarily unavailable."
    
    if update.message:
        await update.message.reply_text(response)


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /chat command and reply with mini_LE output."""
    if not update.message:
        return
    text = " ".join(context.args or [])
    if not text:
        await update.message.reply_text("Usage: /chat <message>")
        return
    await _send_response(update, text)


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to plain text messages with mini_LE output."""
    if update.message and update.message.text:
        await _send_response(update, update.message.text)


def build_application(token: Optional[str] = None):
    """Build the Telegram application with command handlers."""
    token = token or os.getenv("MINILE_TELEGRAM")
    if not token:
        raise RuntimeError("MINILE_TELEGRAM is not set")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chat", chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    return app


def run_bot(token: Optional[str] = None):
    """Run the Telegram bot until interrupted."""
    app = build_application(token)
    try:
        app.run_polling()
    except KeyboardInterrupt:
        pass
    return app


if __name__ == "__main__":
    run_bot()
