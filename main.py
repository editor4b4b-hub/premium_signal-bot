from dotenv import load_dotenv
load_dotenv()

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

# CONFIG: environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("Premium_Signal")  # optional

# OpenAI client (new sdk style). If OPENAI_API_KEY not provided, client remains None.
client = None
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

STATE_FILE = "state.json"
API_BASE = "https://draw.ar-lottery01.com/WinGo/WinGo_30S"
API_PATH = "GetHistoryIssuePage.json"  # dynamic timestamp param added when requesting


# Utilities: state persistence
def load_state():
    default = {
        "history": {
            "big_small": {"win": 0, "loss": 0},
            "color": {"win": 0, "loss": 0},
            "number": {"win": 0, "loss": 0},
        },
        "round_checked": None,  # last issue number we've seen
        "last_prediction": None,  # {predicted_issue, predicted_number, predicted_color, predicted_size, status}
    }
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # ensure keys present
            for k in default:
                if k not in data:
                    data[k] = default[k]
            return data
    except Exception:
        pass
    return default


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.exception("Failed to save state")


# Mapping helpers
def num_to_color_map(n: int) -> str:
    # Based on your mapping: 1,3,5,7,9 = GREEN; 2,4,6,8 = RED; 0,5 = VIOLET (5 mixes too)
    if n == 0:
        return "RED & VIOLET"
    if n == 5:
        return "GREEN & VIOLET"
    if n in {1, 3, 7, 9}:
        return "GREEN"
    if n in {2, 4, 6, 8}:
        return "RED"
    # fallback
    return "UNKNOWN"


def num_to_size(n: int) -> str:
    return "BIG" if n >= 5 else "SMALL"


# Fetch latest results from API (runs in thread to avoid blocking)
async def fetch_latest_api():
    ts = int(time.time() * 1000)
    url = f"{API_BASE}/{API_PATH}?ts={ts}"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://dkwin9.com/",
        "Origin": "https://dkwin9.com",
        "User-Agent": "Mozilla/5.0 (compatible)",
    }
    try:
        # run requests.get in thread
        resp = await asyncio.to_thread(requests.get, url, {"timeout": 10, "headers": headers})
        # Note: requests.get signature when used via to_thread passes dict to second arg,
        # so better call as lambda for clarity:
    except Exception:
        # fallback correct call
        try:
            resp = await asyncio.to_thread(lambda: requests.get(url, timeout=10, headers=headers))
        except Exception as e:
            raise e

    if resp.status_code != 200:
        raise RuntimeError(f"API returned status {resp.status_code}")
    data = resp.json()
    return data


# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 স্বাগতম — Premium Signal Bot\n\n"
        "কমান্ডসমূহ:\n"
        "/signal — রিয়েল সিগন্যাল (API বেসড; পরবর্তী রাউন্ডের জন্য প্রেডিকশন)\n"
        "/live — টপ লেটেস্ট রেজাল্ট (API থেকে)\n"
        "/history — Win/Loss সারাংশ\n"
        "/help — নির্দেশ দেখাবে\n\n"
        "নোট: সেটআপের সময় BOT_TOKEN ও (ঐচ্ছিক) Premium_Signal (OpenAI) env সেট করো।"
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# /live shows latest and evaluates pending prediction if new round arrived
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    try:
        data = await fetch_latest_api()
    except Exception as e:
        await update.message.reply_text(f"⚠️ লাইভ ডেটা আনতে সমস্যা: {e}")
        return

    # extract latest
    try:
        latest = data.get("data", {}).get("list", [])[0]
    except Exception:
        await update.message.reply_text("⚠️ API Response unexpected format.")
        return

    issue = latest.get("issueNumber")
    number_raw = latest.get("number")
    try:
        number = int(number_raw)
    except Exception:
        # sometimes number might be string with commas; try int conversion safe way
        try:
            number = int(str(number_raw).strip())
        except Exception:
            await update.message.reply_text("⚠️ নম্বর পার্স করতে সমস্যা।")
            return

    api_color = str(latest.get("color", "")).upper()
    size = num_to_size(number)
    our_color_from_num = num_to_color_map(number)

    # Evaluate pending prediction if we haven't checked this issue yet
    last_checked = state.get("round_checked")
    last_pred = state.get("last_prediction")

    eval_msg = ""
    if last_checked is None or str(last_checked) != str(issue):
        # new round arrived => evaluate previous pending prediction (if any)
        if last_pred and last_pred.get("status") == "pending":
            predicted_number = int(last_pred.get("predicted_number"))
            predicted_color = last_pred.get("predicted_color", "").upper()
            predicted_size = last_pred.get("predicted_size", "").upper()

            # Determine wins/losses
            number_win = predicted_number == number
            color_win = (predicted_color in api_color) or (predicted_color == our_color_from_num.upper())
            size_win = predicted_size == size

            # update history counters
            if number_win:
                state["history"]["number"]["win"] += 1
            else:
                state["history"]["number"]["loss"] += 1

            if color_win:
                state["history"]["color"]["win"] += 1
            else:
                state["history"]["color"]["loss"] += 1

            if size_win:
                state["history"]["big_small"]["win"] += 1
            else:
                state["history"]["big_small"]["loss"] += 1

            # mark prediction resolved
            last_pred["status"] = "won" if (number_win and color_win and size_win) else "lost"
            last_pred["resolved_with"] = {
                "issue": issue,
                "actual_number": number,
                "actual_color": api_color,
                "actual_size": size,
                "number_win": number_win,
                "color_win": color_win,
                "size_win": size_win,
                "resolved_at": int(time.time() * 1000),
            }
            state["last_prediction"] = last_pred
            eval_msg = (
                f"🔔 পূর্ববর্তী প্রেডিকশন রেজল্ট হয়েছে: {last_pred['status'].upper()}\n"
                f"➡️ Predicted #{last_pred['predicted_number']} ({last_pred['predicted_color']}, {last_pred['predicted_size']})\n"
                f"✔️ Actual #{number} ({api_color}, {size})\n"
            )
        # update last checked
        state["round_checked"] = issue
        save_state(state)

    # Compose reply showing latest result
    reply = (
        f"📡 Live Result\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🆔 Issue: {issue}\n"
        f"🔢 Number: {number}\n"
        f"🎨 API Color: {api_color}\n"
        f"📏 Size: {size}\n"
    )
    if eval_msg:
        reply = eval_msg + "\n" + reply

    await update.message.reply_text(reply)


# /signal uses latest API result to create a deterministic prediction for the next round
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    try:
        data = await fetch_latest_api()
    except Exception as e:
        await update.message.reply_text(f"⚠️ লাইভ ডেটা আনতে সমস্যা: {e}")
        return

    try:
        latest = data.get("data", {}).get("list", [])[0]
    except Exception:
        await update.message.reply_text("⚠️ API Response unexpected format.")
        return

    issue = latest.get("issueNumber")
    number_raw = latest.get("number")
    try:
        last_number = int(number_raw)
    except Exception:
        try:
            last_number = int(str(number_raw).strip())
        except Exception:
            await update.message.reply_text("⚠️ নম্বর পার্স করতে সমস্যা।")
            return

    # Deterministic prediction logic (simple, repeatable): next_number = (last_number + 1) % 10
    predicted_number = (last_number + 1) % 10
    predicted_size = num_to_size(predicted_number)
    predicted_color = num_to_color_map(predicted_number)

    # Next issue guess (try incrementing numeric issueNumber if possible)
    predicted_issue = None
    try:
        predicted_issue = str(int(issue) + 1)
    except Exception:
        predicted_issue = f"{issue}_next"

    # store prediction as pending
    new_pred = {
        "predicted_issue": predicted_issue,
        "predicted_number": predicted_number,
        "predicted_color": predicted_color,
        "predicted_size": predicted_size,
        "timestamp": int(time.time() * 1000),
        "status": "pending",
    }
    state["last_prediction"] = new_pred
    save_state(state)

    reply = (
        f"🎯 Signal (Predicted for next issue)\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔁 Based on last Issue: {issue} → last number {last_number}\n"
        f"🆔 Predicted Issue: {predicted_issue}\n"
        f"🔢 Predicted Number: {predicted_number}\n"
        f"🎨 Predicted Color: {predicted_color}\n"
        f"📏 Predicted Size: {predicted_size}\n\n"
        f"⚠️ Prediction saved. Use /live later to get actual result and evaluation."
    )
    await update.message.reply_text(reply)


# /history prints the saved win/loss counters and last prediction details
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    h = state.get("history", {})
    last_pred = state.get("last_prediction")
    reply = (
        f"📊 Signal History Summary\n"
        f"━━━━━━━━━━━━━━━\n"
        f"BIG/SMALL → ✅ {h['big_small']['win']} | ❌ {h['big_small']['loss']}\n"
        f"COLOR     → ✅ {h['color']['win']} | ❌ {h['color']['loss']}\n"
        f"NUMBER    → ✅ {h['number']['win']} | ❌ {h['number']['loss']}\n\n"
    )
    if last_pred:
        reply += (
            "📌 Last Prediction:\n"
            f"  Issue: {last_pred.get('predicted_issue')}\n"
            f"  Number: {last_pred.get('predicted_number')}\n"
            f"  Color: {last_pred.get('predicted_color')}\n"
            f"  Size: {last_pred.get('predicted_size')}\n"
            f"  Status: {last_pred.get('status')}\n"
        )
        if last_pred.get("status") in ("won", "lost") and last_pred.get("resolved_with"):
            r = last_pred["resolved_with"]
            reply += (
                f"  Resolved Issue: {r.get('issue')}\n"
                f"  Actual Number: {r.get('actual_number')}\n"
                f"  Wins: number={r.get('number_win')}, color={r.get('color_win')}, size={r.get('size_win')}\n"
            )
    await update.message.reply_text(reply)


# ChatGPT handler (uses new OpenAI SDK if available, otherwise replies fallback)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if client is None:
        await update.message.reply_text("⚠️ OpenAI API key missing — Chat replies not available.")
        return
    user_message = update.message.text
    try:
        resp = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_message}],
            )
        )
        reply = resp.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"⚠️ OpenAI error: {e}")


# Main
def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN environment variable not set. Exiting.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
```0
