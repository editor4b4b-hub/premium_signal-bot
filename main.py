import os
import json
import time
import logging
import requests
import random
import asyncio
import openai
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ==============================
# ENVIRONMENT VARIABLES
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN পাওয়া যায়নি! GitHub Codespaces Secrets চেক করো।")

if not OPENAI_API_KEY:
    print("⚠️ সতর্কতা: OPENAI_API_KEY পাওয়া যায়নি। কিছু ফিচার কাজ নাও করতে পারে।")

# ==============================
# OPENAI CLIENT SETUP
# ==============================
client = None
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ==============================
# LOGGING CONFIGURATION
# ==============================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

STATE_FILE = "state.json"
API_BASE = "https://draw.ar-lottery01.com/WinGo/WinGo_30S"
API_PATH = "GetHistoryIssuePage.json"

# ==============================
# UTILITY FUNCTIONS
# ==============================
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

# ==============================
# TELEGRAM HANDLERS
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot চলছে! /live কমান্ড দিয়ে সিগন্যাল দেখো।")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    try:
        response = requests.post(f"{API_BASE}/{API_PATH}", json={"page": 1, "size": 1})
        data = response.json()

        if "data" in data and "list" in data["data"]:
            last_result = data["data"]["list"][0]

            issue = last_result.get("issue")
            number = last_result.get("number")
            api_color = last_result.get("color")
            size = last_result.get("size")

            # state update
            state["last_prediction"] = {
                "issue": issue,
                "number": number,
                "color": api_color,
                "size": size,
                "checked_at": str(datetime.now())
            }
            save_state(state)

            msg = (
                "📊 Live Result\n"
                f"🔢 Issue: {issue}\n"
                f"🎲 Number: {number}\n"
                f"🎨 API Color: {api_color}\n"
                f"📏 Size: {size}\n"
            )
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("⚠️ ডাটা আনতে সমস্যা হয়েছে। পরে চেষ্টা করো।")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ==============================
# MAIN FUNCTION
# ==============================
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("live", live))

    print("🤖 Bot চলছে... বন্ধ করতে Ctrl+C চাপুন।")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
