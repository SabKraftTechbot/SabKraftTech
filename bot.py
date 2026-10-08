import json
import os
import re
import asyncio
import logging
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==========================================
# 1. LOGGING & FLASK HEALTH CHECK
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

app = Flask(__name__)

@app.route("/")
def health():
    return "SabKraftTech Strict Filter Bot Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. BOT CONFIG & BUTTON LAYOUTS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

OFFICIAL_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📢 Telegram Channel", url="https://t.me/SabKraftTech"),
        InlineKeyboardButton("👥 Telegram Group", url="https://t.me/TeamSabKraftTech")
    ],
    [
        InlineKeyboardButton("▶️ YouTube Channel", url="https://youtube.com/@sabkrafttech?si=BvFSMTysyXScxEj2"),
        InlineKeyboardButton("📸 Instagram ID", url="https://instagram.com/sabkrafttech")
    ]
])

MATERIAL_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("📦 Explore Materials & APKs in Channel", url="https://t.me/SabKraftTech")]
])

# ==========================================
# 3. DYNAMIC JSON CONFIG READER (HOT-RELOAD)
# ==========================================
def load_filters():
    """Dynamically reloads filters.json on every hit without needing server restart."""
    if os.path.exists("filters.json"):
        try:
            with open("filters.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("filters", [])
        except Exception as e:
            logging.error(f"Error reading filters.json: {e}")
    return []

def find_matching_filter(text_lower: str):
    filters_list = load_filters()
    for item in filters_list:
        keywords = item.get("keywords", [])
        for kw in keywords:
            pattern = r'\b' + re.escape(kw.lower().strip()) + r'\b'
            if re.search(pattern, text_lower):
                return item
    return None

def extract_user_tag(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "User"
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

# ==========================================
# 4. AUTO-DELETE HELPER (5 MINUTES / 300 SECONDS)
# ==========================================
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    """Safe async delay auto-delete task."""
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.debug(f"Auto-delete failed or message already deleted: {e}")

# ==========================================
# 5. CORE MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat = update.message.chat
    chat_type = chat.type
    is_group_or_channel = chat_type in ["group", "supergroup", "channel"]
    bot_username = context.bot.username or ""

    user_text = update.message.text or update.message.caption or ""
    if not user_text.strip():
        return

    user_text_clean = user_text.strip()
    lower_text = user_text_clean.lower()
    user_tag = extract_user_tag(update)

    # ------------------------------------------
    # A. LINK BLOCKER FOR GROUPS (EXCEPT OWN LINKS)
    # ------------------------------------------
    if is_group_or_channel and re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
        if "t.me/sabkrafttech" not in lower_text and "t.me/teamsabkrafttech" not in lower_text:
            try:
                await update.message.delete()
                return
            except Exception:
                pass

    # ------------------------------------------
    # B. SPAM FILTER & MENTION CHECK FOR GROUPS
    # ------------------------------------------
    is_tagged = (bot_username and f"@{bot_username}".lower() in lower_text) or (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )

    matched_filter = find_matching_filter(lower_text)

    # If in Group: Ignore messages that are neither tagged nor match a filter
    if is_group_or_channel:
        is_forwarded = bool(update.message.forward_origin or update.message.forward_from_chat or update.message.forward_from)
        if is_forwarded and not is_tagged and not matched_filter:
            return
        if not is_tagged and not matched_filter:
            return

    # ------------------------------------------
    # C. RESPONSE GENERATION & BUTTON ATTACHMENT
    # ------------------------------------------
    reply_text = ""
    markup = None

    if matched_filter:
        raw_reply = matched_filter.get("reply", "")
        reply_text = raw_reply.replace("{user_tag}", user_tag)
        btn_type = matched_filter.get("button_type", "none")

        if btn_type == "official":
            markup = OFFICIAL_BUTTONS
        elif btn_type == "material":
            markup = MATERIAL_BUTTONS
        else:
            markup = None
    else:
        # Fallback when tagged in group or direct DM
        if not is_group_or_channel:
            reply_text = f"✨ Hey {user_tag}! Welcome to SabKraftTech. How can I help you today?"
        else:
            reply_text = f"✨ Yes {user_tag}! How can SabKraftTech assist you?"
        markup = None

    # Send Reply
    sent_message = None
    try:
        sent_message = await update.message.reply_text(reply_text, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        try:
            sent_message = await update.message.reply_text(reply_text, reply_markup=markup)
        except Exception:
            pass

    # ------------------------------------------
    # D. AUTO-DELETE IN 5 MINS (300 SECONDS)
    # ------------------------------------------
    if sent_message and is_group_or_channel:
        asyncio.create_task(
            delete_message_after_delay(context, update.message.chat_id, sent_message.message_id, 300)
        )

# ==========================================
# 6. APP STARTUP
# ==========================================
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_TOKEN environment variable missing!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    )

    logging.info("🚀 SabKraftTech Engine Started Successfully...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
