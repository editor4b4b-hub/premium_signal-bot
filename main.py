import os
import logging
import random
import requests
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ✅ Secrets থেকে Key পড়া
OPENAI_API_KEY = os.getenv("Premium_Signal")
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = OpenAI(api_key=OPENAI_API_KEY)

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# গ্লোবাল হিস্টোরি
stats = {
    "big_small": {"win": 0, "loss": 0},
    "color": {"win": 0, "loss": 0},
    "number": {"win": 0, "loss": 0},
    "round": 1
}

# 🔥 নাম্বার থেকে কালার বের করা
def get_color(number):
    if number in [1, 3, 5, 7, 9]:
        return "🟢 GREEN"
    elif number in [2, 4, 6, 8]:
        return "🔴 RED"
    elif number == 0:
        return "🔴 RED & 🟣 VIOLET"
    elif number == 5:
        return "🟢 GREEN & 🟣 VIOLET"

# 🔥 Big/Small বের করা
def get_big_small(number):
    return "BIG" if number >= 5 else "SMALL"

# 🔥 লাইভ হিস্টোরি আনা (API থেকে)
def fetch_live_history():
    try:
        # 🟢 এখানে তোমার আসল API URL বসাবে
        url = "https://example.com/api/live-results"  
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # এখানে ধরে নিলাম data = [{"round":1,"number":3,"color":"GREEN"}]
            last_5 = data[-5:]  # শেষ ৫টা রাউন্ড দেখাবে
            history_text = "\n".join(
                [f"Round {item['round']} → {item['color']} ({item['number']})" for item in last_5]
            )
            return history_text
        else:
            return "⚠️ API থেকে ডাটা আনা গেলো না!"
    except Exception as e:
        return f"⚠️ লাইভ ডেটা এরর: {e}"

# /start কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is running!")

# /signal কমান্ড
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = random.randint(0, 9)
    color = get_color(number)
    big_small = get_big_small(number)

    # র‍্যান্ডম Win/Loss
    win_or_loss = random.choice(["✅ Win", "❌ Loss"])

    # হিস্টোরি আপডেট
    if win_or_loss == "✅ Win":
        stats["big_small"]["win"] += 1
        stats["color"]["win"] += 1
        stats["number"]["win"] += 1
    else:
        stats["big_small"]["loss"] += 1
        stats["color"]["loss"] += 1
        stats["number"]["loss"] += 1

    live_history = fetch_live_history()

    text = f"""
📢 **Round {stats['round']}**

📡 **Signal:** {big_small}
🎨 **Color:** {color}
🔢 **Number:** {number}

📊 **Result:** {win_or_loss}

📈 **Win & Loss History**
BIG/SMALL → ✅ {stats['big_small']['win']} | ❌ {stats['big_small']['loss']}
COLOR → ✅ {stats['color']['win']} | ❌ {stats['color']['loss']}
NUMBER → ✅ {stats['number']['win']} | ❌ {stats['number']['loss']}

📡 **Live History**
{live_history}
"""
    stats["round"] += 1
    await update.message.reply_text(text, parse_mode="Markdown")

# মেসেজ হ্যান্ডলার (ChatGPT Reply)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_message}]
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"⚠️ কিছু ভুল হয়েছে: {e}")

# মেইন ফাংশন
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
