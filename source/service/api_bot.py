import os
import sys
import asyncio
from loguru import logger
from datetime import datetime
from configparser import ConfigParser
from langchain_openai.chat_models import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

path_this = os.path.dirname(os.path.abspath(__file__))
path_project = os.path.dirname(os.path.join(path_this, ".."))
path_root = os.path.dirname(os.path.join(path_this, "../.."))
sys.path.extend([path_root, path_project, path_this])

from tools import (
    AgentTaskManagement,
    SpreadsheetTool
)

config = ConfigParser()
config.read(os.path.join(path_root, "config.conf"))

llm = ChatOpenAI(
    api_key=config["llm"]["OPENAI_KEY"],
    temperature=0.1,
    model=config["llm"]["model_gpt"],
    max_tokens=4000,
    presence_penalty=0.8
)
memory = InMemorySaver()
agent = AgentTaskManagement(
    llm=llm,
    checkpoint=memory
)
st = SpreadsheetTool()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Halo! Saya bot task management.\n\n"
        "Silakan ketik task Anda dengan format berikut:\n"
        "📌 Project Name | Task | Assignor\n\n"
        "Contoh:\n"
        "Fusion | Adjust Network Cognitive Warfare | Fakhri\n\n"
        "Task Anda akan otomatis saya simpan ke spreadsheet. 🚀"
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Info Bot Task Management\n\n"
        "Cara menggunakan bot ini:\n"
        "1. Ketikkan task dalam format berikut:\n\n"
        "   Project Name | Task | Assignor\n\n"
        "   Contoh:\n"
        "   Fusion | Adjust Network Cognitive Warfare | Fakhri\n\n"
        "2. Bot akan menyimpan task tersebut ke spreadsheet.\n\n"
        "Daftar command:\n"
        "- /start → Memulai percakapan dengan bot\n"
        "- /info → Melihat informasi & panduan penggunaan\n"
        "- /chat → Chat langsung dengan bot\n"
        "- /check_task → Mengecek apakah masih ada task yang belum selesai\n\n"
        "Bot ini terhubung dengan Google Spreadsheet untuk menyimpan semua task.\n"
        "Apabila ada kendala hubungi admin: @FakhriMN25"
    )

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.first_name
    task_text = update.message.text
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # --- OpenAI untuk analisis task ---
    try:
        response = await agent._run(f"{user}: {task_text}")
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        response = "Maaf Saat ini saya sedang terkendala sesuatu, mohon coba sesaat lagi. apabila ini terus berlangsung tolong hubungi @FakhriMN25"

    await update.message.reply_text(
        response
    )

async def check_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.first_name
    try:
        result = await st.get_undone_task(user)
    except Exception as e:
        logger.error(f"Spreadsheet error: {e}")
        result = (
            "❌ Maaf, terjadi kesalahan saat mengambil data task.\n"
            "Silakan coba lagi nanti atau hubungi admin: @FakhriMN25"
        )

    await update.message.reply_text(result)

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.first_name
    chat_text = update.message.text.replace("/chat", "", 1).strip()

    if not chat_text:
        await update.message.reply_text("❌ Tolong masukkan pesan setelah /chat.")
        return

    try:
        response = await agent._run(f"{user}: {chat_text}")
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        response = (
            "Maaf, saya sedang mengalami kendala. "
            "Coba lagi nanti atau hubungi admin: @FakhriMN25"
        )

    await update.message.reply_text(response)    

async def set_commands(app):
    commands = [
        BotCommand("start", "add task"),
        BotCommand("info", "info"),
        BotCommand("check_task", "check task"),
        BotCommand("chat", "chat with bot")
    ]
    await app.bot.set_my_commands(commands)

def main():
    token = config["default"]["TELEGRAM_TOKEN"]
    app = ApplicationBuilder().token(token).post_init(set_commands).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("check_task", check_task))
    app.add_handler(CommandHandler("chat", chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_task))

    logger.info("🤖 Bot task management sudah berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()