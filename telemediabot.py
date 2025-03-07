import os
import logging
import sqlite3
import uuid
import base64
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ContextTypes

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_LINK = os.getenv("CHANNEL_LINK")  # Add your channel link in .env

# Initialize database
conn = sqlite3.connect("mediadatabase.db", check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT UNIQUE,
        file_type TEXT,
        unique_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def encode_payload(payload: str) -> str:
    """Encodes a payload into Base64."""
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

def decode_payload(encoded: str) -> str:
    """Decodes a Base64 payload."""
    padding = len(encoded) % 4
    if padding:
        encoded += "=" * (4 - padding)
    return base64.urlsafe_b64decode(encoded).decode()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command (with or without arguments)"""
    message_text = update.message.text.strip()
    
    # Send welcome message with channel link
    welcome_message = (
        "🚀 *Welcome to [Bot Name]!*\n"
        "🎉 Enjoy exclusive content — totally FREE!\n\n"
        "🔑 *How it works?*\n"
        "1️⃣ Click the link below to *join our channel*.\n"
        "2️⃣ Inside the channel, you'll find a *special return link* to access the content.\n"
        "3️⃣ Come back and enjoy — no charges, no limits!\n\n"
        f"📌 *Join now:* [Click Here]({CHANNEL_LINK})\n\n"
        "💡 *This service is 100% free! Just join & enjoy unlimited access!*"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown", disable_web_page_preview=True)
    
    if message_text.startswith("/start ") and len(message_text) > 7:
        encoded_payload = message_text.split(" ", 1)[1]
        try:
            decoded_payload = decode_payload(encoded_payload)
            if decoded_payload.startswith("get-media-"):
                unique_id = decoded_payload.replace("get-media-", "")
                await handle_start_with_id(update, context, unique_id)
        except Exception:
            await update.message.reply_text("❌ Invalid link format!")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles video/photo uploads and saves them with a unique ID"""
    file_id = None
    file_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"

    if file_id and file_type:
        unique_id = str(uuid.uuid4())[:8]  # Generate a short unique ID
        try:
            cursor.execute("INSERT INTO media (file_id, file_type, unique_id) VALUES (?, ?, ?)", (file_id, file_type, unique_id))
            conn.commit()

            bot_user = await context.bot.get_me()
            bot_username = bot_user.username
            encoded_link = encode_payload(f"get-media-{unique_id}")
            link = f"https://t.me/{bot_username}?start={encoded_link}"

            await update.message.reply_text(f"✅ Media stored successfully!\nShare this link: {link}")
        except sqlite3.IntegrityError:
            await update.message.reply_text("⚠️ This media is already stored.")

async def handle_start_with_id(update: Update, context: CallbackContext, unique_id: str) -> None:
    """Fetch media when user clicks a stored link and delete it after 15 minutes"""
    cursor.execute("SELECT file_id, file_type FROM media WHERE unique_id = ?", (unique_id,))
    result = cursor.fetchone()

    if result:
        file_id, file_type = result
        message = "⚠️ *Attention! This media will be deleted in 15 minutes.*"

        if file_type == "photo":
            await update.message.reply_photo(photo=file_id, caption=message, parse_mode="Markdown")
        elif file_type == "video":
            await update.message.reply_video(video=file_id, caption=message, parse_mode="Markdown")
        
        # Schedule file deletion after 15 minutes
        await asyncio.sleep(900)  # 900 seconds = 15 minutes
        cursor.execute("DELETE FROM media WHERE unique_id = ?", (unique_id,))
        conn.commit()
        logging.info(f"Media with ID {unique_id} deleted after 15 minutes.")
    else:
        await update.message.reply_text("❌ Invalid or expired link!")

def main():
    """Start the bot"""
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
