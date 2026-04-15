import requests
import pandas as pd
import time
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== SETTINGS =====
TOKEN = "8718378709:AAFzoUzG3so7JF0SCpVN7qTdNHaZvBAn8QM"
API_KEY = "d5ae0f61032849f0bf0e943dbccb85a4"
CHAT _ID = "6181352243"
ALLOWED_IDS = ["129634078"]  # yahan apne trade IDs add karo

users = {}

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"] 
 PAIRS = ["EURUSD"OTC, "GBPUSD"OTC, "PAKUSD"OTC" ]

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Welcome!\nApna Trade ID enter karo:")

# ===== HANDLE LOGIN =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    trade_id = update.message.text

    if trade_id in ALLOWED_IDS:
        users[user_id] = True
        await update.message.reply_text("✅ Login Successful! Signals start honge.")
    else:
        await update.message.reply_text("❌ Invalid Trade ID")

# ===== DATA =====
def get_data(pair):
    url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval=1min&outputsize=100&apikey={API_KEY}"
    data = requests.get(url).json()

    df = pd.DataFrame(data["values"])
    df = df.iloc[::-1]

    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    return df

# ===== RSI =====
def rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ===== SUPPORT/RESISTANCE =====
def sr(df):
    support = df["low"].rolling(20).min().iloc[-1]
    resistance = df["high"].rolling(20).max().iloc[-1]
    return support, resistance

# ===== SIGNAL =====
def get_signal(pair):
    df = get_data(pair)

    df["rsi"] = rsi(df)
    ema = df["close"].ewm(span=50).mean()

    support, resistance = sr(df)

    last = df.iloc[-1]

    bullish = last["close"] > last["open"]
    bearish = last["close"] < last["open"]

    # fake breakout filter
    if last["high"] > resistance and last["close"] < resistance:
        return None
    if last["low"] < support and last["close"] > support:
        return None

    if last["close"] > ema.iloc[-1] and last["rsi"] < 60 and bullish:
        return "CALL 📈"
    elif last["close"] < ema.iloc[-1] and last["rsi"] > 40 and bearish:
        return "PUT 📉"

    return None

# ===== SMART ENTRY =====
def wait_for_entry():
    ist = pytz.timezone('Asia/Kolkata')

    while True:
        now = datetime.now(ist)
        if now.second <= 3:
            return now
        time.sleep(0.2)

# ===== SIGNAL LOOP =====
async def send_signals(app):
    while True:
        now = wait_for_entry()

        for pair in PAIRS:
            signal = get_signal(pair)

            if signal:
                msg = f"""🔥 PRO SIGNAL
Pair: {pair}
Signal: {signal}
Entry Time (IST): {now.strftime('%H:%M:%S')}
Entry: 0-3 sec window
Timeframe: 1M"""

                for user_id in users:
                    await app.bot.send_message(chat_id=user_id, text=msg)

        await asyncio.sleep(1)

# ===== MAIN =====
import asyncio

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.job_queue.run_once(lambda ctx: asyncio.create_task(send_signals(app)), 1)

print("Bot running...")
app.run_polling()
