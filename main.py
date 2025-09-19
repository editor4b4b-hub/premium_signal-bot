import os
import logging
import random
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# ✅ Load .env file
load_dotenv()

# 🔑 Read secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("Premium_Signal")

# 🛡️ Basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ✅ History counter
history = {
    "big_small": {"win": 0, "loss": 0},
    "color": {"win": 0, "loss": 0},
    "number": {"win": 0, "loss": 0},
    "round": 0
}

# 🎯 Helper: Random Signal
def generate_signal():
    numbers = list(range(10))
    chosen_number = random.choice(numbers)

    # Color
    if chosen_number in [1, 3, 5, 7, 9]:
        color = "🟢 GREEN"
    elif chosen_number in [2, 4, 6, 8]:
        color = "🔴 RED"
    elif chosen_number == 0:
        color = "🔴 RED & 🟣 VIOLET"
    elif chosen_number == 5:
        color = "🟢 GREEN & 🟣 VIOLET"

    # Size
    size = "BIG" if chosen_number >= 5 else "SMALL"

    # Win/Loss (Demo)
    result = random.choice(["WIN", "LOSS"])
    if result == "WIN":
        history["big_small"]["win"] += 1
        history["color"]["win"] += 1
        history["number"]["win"] += 1
    else:
        history["big_small"]["loss"] += 1
        history["color"]["loss"] += 1
        history["number"]["loss"] += 1

    history["round"] += 1

    return chosen_number, color, size, result


# 🟢 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Premium Signal Bot!\n\n"
        "📡 /signal → Get new signal\n"
        "📊 /history → Win/Loss summary\n"
        "📜 /live → Live result from API"
    )


# 🟢 /signal
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number, color, size, result = generate_signal()
    await update.message.reply_text(
        f"🎯 Round: {history['round']}\n"
        f"Size: {size}\n"
        f"Color: {color}\n"
        f"Number: {number}\n"
        f"Result: ✅ {result}"
    )


# 🟢 /history
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 Signal History\n"
        f"━━━━━━━━━━━━━━━\n"
        f"BIG/SMALL ➜ ✅ {history['big_small']['win']} | ❌ {history['big_small']['loss']}\n"
        f"COLOR     ➜ ✅ {history['color']['win']} | ❌ {history['color']['loss']}\n"
        f"NUMBER    ➜ ✅ {history['number']['win']} | ❌ {history['number']['loss']}\n"
        f"📢 Last Round: {history['round']}"
    )


# 🟢 /live → Real API
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistorylssuePage.json"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "data" in data and "list" in data["data"]:
            last_result = data["data"]["list"][0]
            await update.message.reply_text(
                f"📡 Live Result\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Round: {last_result['issue']}\n"
                f"Number: {last_result['number']}\n"
                f"Open Time: {last_result['openTime']}"
            )
        else:
            await update.message.reply_text("⚠️ লাইভ ডেটা পাওয়া যায়নি।")

    except Exception as e:
        await update.message.reply_text(f"⚠️ API Error: {e}")


# মেইন ফাংশন
def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN .env ফাইলে পাওয়া যায়নি!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("live", live))

    app.run_polling()


if __name__ == "__main__":
    main()
