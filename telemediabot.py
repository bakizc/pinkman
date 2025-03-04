import os
import logging
import sqlite3
import uuid
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ContextTypes

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# Initialize database
conn = sqlite3.connect("mediadatabase.db", check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT UNIQUE,
        file_type TEXT,
        unique_id TEXT UNIQUE
    )
""")
conn.commit()

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command (without arguments)"""
    message_text = update.message.text.strip()
    
    if message_text.startswith("/start ") and len(message_text) > 7:  # Check if argument exists
        unique_id = message_text.split(" ", 1)[1]  # Extract unique ID
        await handle_start_with_id(update, context, unique_id)
    else:
        await update.message.reply_text("Send me a video or photo, and I'll store it!")

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

            bot_user = await context.bot.get_me()  # Get bot's username dynamically
            bot_username = bot_user.username
            link = f"https://t.me/{bot_username}?start={unique_id}"  # Shareable link

            await update.message.reply_text(f"✅ Media stored successfully!\nShare this link: {link}")
        except sqlite3.IntegrityError:
            await update.message.reply_text("⚠️ This media is already stored.")

async def handle_start_with_id(update: Update, context: CallbackContext, unique_id: str) -> None:
    """Fetch media when user clicks a stored link"""
    cursor.execute("SELECT file_id, file_type FROM media WHERE unique_id = ?", (unique_id,))
    result = cursor.fetchone()

    if result:
        file_id, file_type = result
        if file_type == "photo":
            await update.message.reply_photo(photo=file_id, caption="📸 Here’s your photo!")
        elif file_type == "video":
            await update.message.reply_video(video=file_id, caption="🎥 Here’s your video!")
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
