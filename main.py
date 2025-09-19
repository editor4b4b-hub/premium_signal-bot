import os
import logging
import random
import openai
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

# /start কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is running!")

# /signal কমান্ড
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signals = ["🟢 BUY", "🔴 SELL", "🟡 WAIT"]
    chosen_signal = random.choice(signals)
    await update.message.reply_text(f"📡 Signal: {chosen_signal}")

# মেসেজ হ্যান্ডলার (ChatGPT Reply)
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
    app.add_handler(CommandHandler("signal", signal))  # ✅ নতুন কমান্ড যোগ হলো
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
