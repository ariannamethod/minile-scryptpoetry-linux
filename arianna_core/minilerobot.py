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
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry'))
try:
    from symphony import Symphony
    from skryptmetrics import entropy, perplexity, resonance
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry', 'arianna_linux'))
    from letsgo import run_script
    SKRYPTPOETRY_AVAILABLE = True
except ImportError:
    SKRYPTPOETRY_AVAILABLE = False

# Ленивая инициализация Symphony
_symphony = None

def _get_symphony():
    """Ленивая инициализация Symphony только когда нужно."""
    global _symphony
    if _symphony is None and SKRYPTPOETRY_AVAILABLE:
        try:
            scripts_path = os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry', 'tongue', 'prelanguage.md')
            dataset_path = os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry', 'datasets', 'dataset01.md')
            _symphony = Symphony(dataset_path=dataset_path, scripts_path=scripts_path)
        except Exception:
            pass
    return _symphony


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Respond to the /start command."""
    if update.message:
        await update.message.reply_text("Send messages with /chat <text>.")


async def _send_response(update: Update, text: str) -> None:
    """Send mini_LE's response with skryptpoetry visualization."""
    try:
        # Получаем ответ от MiniLE
        if hasattr(asyncio, "to_thread"):
            minile_reply = await asyncio.to_thread(mini_le.chat_response, text)
        else:  # Python 3.8 fallback
            loop = asyncio.get_running_loop()
            minile_reply = await loop.run_in_executor(None, mini_le.chat_response, text)
        
        # Добавляем скриптпоэтри визуализацию
        symphony = _get_symphony()
        if SKRYPTPOETRY_AVAILABLE and symphony:
            try:
                # Получаем скрипт на основе ответа MiniLE
                if hasattr(asyncio, "to_thread"):
                    script_code = await asyncio.to_thread(symphony.respond, minile_reply)
                    # Выполняем скрипт
                    script_result = await asyncio.to_thread(run_script, script_code)
                else:
                    loop = asyncio.get_running_loop()
                    script_code = await loop.run_in_executor(None, symphony.respond, minile_reply)
                    # Выполняем скрипт
                    script_result = await loop.run_in_executor(None, run_script, script_code)
                
                # Комбинируем ответы
                combined_reply = f"{minile_reply}\n\n{script_result}"
            except Exception:
                combined_reply = minile_reply
        else:
            combined_reply = minile_reply
            
    except Exception as exc:  # pragma: no cover - unexpected failure
        import logging

        logging.exception("Response generation failed: %s", exc)
        if update.message:
            await update.message.reply_text("Error: failed to generate response.")
        return
    if update.message:
        await update.message.reply_text(combined_reply)


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
