"""Telegram bridge for executing visual scripts."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

try:
    from .letsgo import choose_script, run_script
except ImportError:  # pragma: no cover
    from letsgo import choose_script, run_script


load_dotenv()


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Select and run a script based on the incoming message."""
    text = update.message.text if update.message else ""
    code = choose_script(text)
    output = run_script(code)
    if update.message:
        await update.message.reply_text(output)


def decide_and_run(message: str) -> str:
    """Helper used in tests to run the script for a message."""
    code = choose_script(message)
    return run_script(code)


def main(token: Optional[str] = None) -> None:
    token = token or os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN is not set")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )
    app.run_polling()


if __name__ == "__main__":
    main()
