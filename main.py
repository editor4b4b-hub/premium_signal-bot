import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import openai

# লগ সেটআপ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# OpenAI API Key সেট
openai.api_key = os.getenv("Premium_Signal")

# /start কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot চলছে! আমাকে কিছু জিজ্ঞাসা করো।")

# /ask কমান্ড
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ব্যবহার: /ask আপনার প্রশ্ন")
        return

    question = " ".join(context.args)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": question}]
        )
        answer = response["choices"][0]["message"]["content"]
        await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text(f"❌ কিছু ভুল হয়েছে: {e}")

# মেইন ফাংশন
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN পাওয়া যায়নি। প্রথমে সেট করো।")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))

    print("✅ Bot চালু হয়েছে!")
    app.run_polling()

if __name__ == "__main__":
    main()
