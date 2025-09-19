import os
import logging
import random
import openai
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ✅ Secrets থেকে Key পড়া
OPENAI_API_KEY = os.getenv("Premium_Signal")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# OpenAI কনফিগ
openai.api_key = OPENAI_API_KEY

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ✅ History কাউন্টার
history = {
    "big_small": {"win": 0, "loss": 0},
    "color": {"win": 0, "loss": 0},
    "number": {"win": 0, "loss": 0},
    "round": 0
}

# 🎯 Helper function (random signal generate)
def generate_signal():
    numbers = list(range(10))
    chosen_number = random.choice(numbers)

    # Determine color
    if chosen_number in [1, 3, 5, 7, 9]:
        color = "🟢 GREEN"
    elif chosen_number in [2, 4, 6, 8]:
        color = "🔴 RED"
    elif chosen_number == 0:
        color = "🔴 RED & 🟣 VIOLET"
    elif chosen_number == 5:
        color = "🟢 GREEN & 🟣 VIOLET"

    # Determine big/small
    size = "BIG" if chosen_number >= 5 else "SMALL"

    # Randomly mark win/loss for demo
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

# /start কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Premium Signal Bot!\n\n"
        "Use these commands:\n"
        "📡 /signal → Get a new signal\n"
        "📊 /history → See Win/Loss Summary\n"
        "📜 /live → Get Live Result from API"
    )

# /signal কমান্ড
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number, color, size, result = generate_signal()
    await update.message.reply_text(
        f"🎯 Round: {history['round']}\n"
        f"Signal: {size}\n"
        f"Color: {color}\n"
        f"Number: {number}\n"
        f"Result: ✅ {result}"
    )

# /history কমান্ড
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 Signal History (Summary)\n"
        f"━━━━━━━━━━━━━━━\n"
        f"BIG/SMALL ➜ ✅ {history['big_small']['win']} | ❌ {history['big_small']['loss']}\n"
        f"COLOR     ➜ ✅ {history['color']['win']} | ❌ {history['color']['loss']}\n"
        f"NUMBER    ➜ ✅ {history['number']['win']} | ❌ {history['number']['loss']}\n\n"
        f"📢 Last Round Checked: {history['round']}"
    )

# /live কমান্ড (API থেকে লাইভ ডেটা)
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistorylssuePage.json?ts=1758183840473"
        response = requests.get(url, timeout=10)
        data = response.json()
        await update.message.reply_text(f"📜 Live History:\n{data}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ লাইভ ডেটা আনতে সমস্যা: {e}")

# ChatGPT reply
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}]
        )
        reply = response.choices[0].message['content']
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"⚠️ কিছু ভুল হয়েছে: {e}")

# মেইন ফাংশন
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
