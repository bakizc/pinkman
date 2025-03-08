import os
import logging
import sqlite3
import uuid
import base64
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))  # Only the owner can upload media
CHANNEL_LINK = os.getenv("CHANNEL_LINK")
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID"))  # Private storage channel

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
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def encode_payload(payload: str) -> str:
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

def decode_payload(encoded: str) -> str:
    padding = len(encoded) % 4
    if padding:
        encoded += "=" * (4 - padding)
    return base64.urlsafe_b64decode(encoded).decode()

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

⚠️ *WARNING: 18+ Content*

🔞 This bot provides *exclusive content for adults only*. By continuing, you confirm that you are *18 or older*.

📌 *Join now:* [Click Here]({CHANNEL_LINK})
"""

        await update.message.reply_text(welcome_message, parse_mode="Markdown", disable_web_page_preview=True)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != OWNER_ID:
        return  # Ignore media uploads from other users

    file_id = None
    thumb_id = None
    file_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
        if update.message.video.thumbnail:
            thumb_id = update.message.video.thumbnail.file_id

    if not file_id or not file_type:
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

        caption = f"🔥 Media Link:\n📌 {link}"
        
        await update.message.reply_text(caption)

    except Exception as e:
        logging.error(f"Error handling media: {e}")
        await update.message.reply_text("❌ Failed to process media!")

async def send_media(update: Update, context: ContextTypes.DEFAULT_TYPE, unique_id: str) -> None:
    try:
        cursor.execute("SELECT file_id, thumb_id, file_type FROM media WHERE unique_id = ?", (unique_id,))
        result = cursor.fetchone()

        if result:
            file_id, thumb_id, file_type = result

            warning_message = "⚠️ *This media will be deleted in 15 minutes!*"
            sent_message = None

            if file_type == "photo":
                sent_message = await update.message.reply_photo(photo=file_id, caption=warning_message, parse_mode="Markdown")
            elif file_type == "video":
                sent_message = await update.message.reply_video(video=file_id, caption=warning_message, parse_mode="Markdown")

            # Schedule deletion asynchronously
            if sent_message:
                message_id = sent_message.message_id
                chat_id = update.message.chat_id
                asyncio.create_task(delete_message_later(context, chat_id, message_id))

        else:
            await update.message.reply_text("❌ Invalid or expired link!")

    except Exception as e:
        logging.error(f"Error sending media: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def delete_message_later(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    """Deletes a message after 15 minutes without blocking the bot."""
    await asyncio.sleep(900)  # Wait 15 minutes
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.warning(f"Failed to delete message: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

    logging.info("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
