import logging
import os

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не задан TG_BOT_TOKEN (ни в .env, ни в переменных окружения)")
if not WEBAPP_URL:
    raise RuntimeError("Не задан WEBAPP_URL (ни в .env, ни в переменных окружения)")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                text="Открыть приложение",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            "Мини-приложение для поиска компании. Нажмите, чтобы открыть.",
            reply_markup=reply_markup,
        )


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()


if __name__ == "__main__":
    main()