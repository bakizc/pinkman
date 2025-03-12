import os
import logging
import sqlite3
import uuid
import base64
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK")
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8080))

# Initialize database
conn = sqlite3.connect("mediadatabase.db", check_same_thread=False)
cursor = conn.cursor()

# Ensure database schema is correct
cursor.execute("""
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT UNIQUE,
        thumb_id TEXT,
        file_type TEXT,
        unique_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# Logging
logging.basicConfig(filename="bot.log", format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Webhook Flask App
app = Flask(__name__)

# Telegram Bot Application
telegram_app = Application.builder().token(BOT_TOKEN).build()

def encode_payload(payload: str) -> str:
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

def decode_payload(encoded: str) -> str:
    padding = len(encoded) % 4
    if padding:
        encoded += "=" * (4 - padding)
    return base64.urlsafe_b64decode(encoded).decode()

async def send_media(update: Update, context: ContextTypes.DEFAULT_TYPE, unique_id: str):
    cursor.execute("SELECT file_id, thumb_id, file_type FROM media WHERE unique_id = ?", (unique_id,))
    media_entry = cursor.fetchone()

    if media_entry:
        file_id, thumb_id, file_type = media_entry
        
        if file_type == "photo":
            await update.message.reply_photo(photo=file_id)
        elif file_type == "video":
            await update.message.reply_video(video=file_id, thumb=thumb_id)
        
        logging.info(f"✅ Sent media: {unique_id}")
    else:
        await update.message.reply_text("❌ Media not found!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text.strip()
    if message_text.startswith("/start ") and len(message_text) > 7:
        encoded_payload = message_text.split(" ", 1)[1]
        try:
            decoded_payload = decode_payload(encoded_payload)
            if decoded_payload.startswith("get-media-"):
                unique_id = decoded_payload.replace("get-media-", "")
                await send_media(update, context, unique_id)
        except Exception as e:
            logging.error(f"Decoding error: {e}")
            await update.message.reply_text("❌ Invalid link format!")
    else:
        welcome_message = f"""🚀 *Welcome to the Bot!*
        \n⚠️ *WARNING: 18+ Content*\n\n🔞 This bot provides *exclusive content for adults only*.\n\n📌 *Join now:* [Click Here]({CHANNEL_LINK})"""
        await update.message.reply_text(welcome_message, parse_mode="Markdown", disable_web_page_preview=True)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != OWNER_ID:
        return

    file_id, thumb_id, file_type = None, None, None
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
        if update.message.video.thumbnail:
            thumb_id = update.message.video.thumbnail.file_id
    
    if not file_id or not file_type:
        await update.message.reply_text("❌ No valid media detected!")
        return
    
    try:
        cursor.execute("SELECT unique_id FROM media WHERE file_id = ?", (file_id,))
        existing_entry = cursor.fetchone()
        unique_id = existing_entry[0] if existing_entry else str(uuid.uuid4())[:8]
        
        if not existing_entry:
            with conn:
                cursor.execute("INSERT INTO media (file_id, thumb_id, file_type, unique_id) VALUES (?, ?, ?, ?)",
                               (file_id, thumb_id, file_type, unique_id))
            await context.bot.forward_message(chat_id=STORAGE_CHANNEL_ID, from_chat_id=update.message.chat_id,
                                              message_id=update.message.message_id)
        
        bot_user = await context.bot.get_me()
        encoded_link = encode_payload(f"get-media-{unique_id}")
        link = f"https://t.me/{bot_user.username}?start={encoded_link}"
        
        cooked_message = f"🔥 Cooked meth:\n\n📸 pic {unique_id if file_type == 'photo' else '🎥 mms ' + unique_id}\n\n🔗 LINK: {link}"
        sent_message = await update.message.reply_text(cooked_message)
        await context.bot.forward_message(chat_id=STORAGE_CHANNEL_ID, from_chat_id=update.message.chat_id,
                                          message_id=sent_message.message_id)
        logging.info(f"✅ Media saved: {file_id}, {unique_id}")
    except Exception as e:
        logging.error(f"Error handling media: {e}")
        await update.message.reply_text(f"❌ Failed to process media! Error: {str(e)}")

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), telegram_app.bot)
    telegram_app.process_update(update)
    return "OK", 200

async def set_webhook():
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

if __name__ == "__main__":
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    
    app.run(host="0.0.0.0", port=PORT)
