import json
import os
import re
import threading
import logging
from flask import Flask
import google.generativeai as genai
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==========================================
# 1. FLASK WEB SERVER (24/7 KEEP-ALIVE)
# ==========================================
app = Flask(__name__)

@app.route("/")
def health():
    return "SabKraftTech Ultimate AI Bot is Active & Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. ENVIRONMENT & BUTTONS CONFIG
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Official Social Buttons
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

# Editing Material Buttons
MATERIAL_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📦 Download Overlays & Effects", url="https://t.me/SabKraftTech")
    ],
    [
        InlineKeyboardButton("🎨 Download Presets, PNGs & Fonts", url="https://t.me/SabKraftTech")
    ],
    [
        InlineKeyboardButton("🎵 Download BGM & SFX Packs", url="https://t.me/SabKraftTech")
    ]
])

# ==========================================
# 3. GEMINI AI ENGINE SETUP
# ==========================================
SYSTEM_PERSONA = (
    "You are SabKraftTech AI — an elite, premium, and aesthetic Gen-Z assistant "
    "for Video Editors, Graphic Designers, YouTubers, Freelancers, and Creators. "
    "Rule: Every response must be completely unique, ultra-short (2-3 lines max), "
    "professional, trendy, to-the-point, and styled with high-end aesthetic emojis. Always tag the user cleanly."
)

def get_ai_model():
    if not GEMINI_KEY:
        logging.error("❌ GEMINI_API_KEY is missing!")
        return None
    try:
        genai.configure(api_key=GEMINI_KEY)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        logging.error(f"❌ AI Init Error: {e}")
        return None

ai_model = get_ai_model()

def extract_user_tag(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "Creator"
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

# ==========================================
# 4. SMART PHRASE MATCHING JSON FILTERS
# ==========================================
def load_json_config():
    if os.path.exists("filters.json"):
        try:
            with open("filters.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"JSON Load Error: {e}")
    return {"button_triggers": [], "custom_rules": []}

def get_filter_reply(lower_text: str, user_tag: str) -> str:
    config = load_json_config()
    rules = config.get("custom_rules", [])
    user_words = set(lower_text.split())
    
    for rule in rules:
        keywords = rule.get("keywords", [])
        for kw in keywords:
            kw_lower = kw.lower().strip()
            # If keyword has spaces (phrase), check as substring. If single word, match exact or in words.
            if " " in kw_lower:
                if kw_lower in lower_text:
                    reply = rule.get("reply", "")
                    return reply.replace("{user_tag}", user_tag)
            else:
                if kw_lower == lower_text or kw_lower in user_words:
                    reply = rule.get("reply", "")
                    return reply.replace("{user_tag}", user_tag)
    return ""

def is_only_emoji(text: str) -> bool:
    emoji_pattern = re.compile(r"^[\s\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]+$")
    return bool(emoji_pattern.match(text))

# ==========================================
# 5. MAIN MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_type = update.message.chat.type
    user_tag = extract_user_tag(update)
    bot_username = context.bot.username or ""
    is_group = chat_type in ["group", "supergroup"]

    user_text = update.message.text or update.message.caption or ""
    user_text_clean = user_text.strip()
    lower_text = user_text_clean.lower()

    # 1. Anti-Spam Link Blocker (Group chats)
    if is_group and user_text_clean:
        if re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
            try:
                await update.message.delete()
                return
            except Exception:
                pass

    # 2. Mention Check in Groups
    if is_group:
        is_tagged = (bot_username and f"@{bot_username}" in user_text_clean) or (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
            and update.message.reply_to_message.from_user.id == context.bot.id
        )
        if not is_tagged:
            return

    # 3. Dynamic Button Triggers
    material_keywords = [
        "material", "materials", "overlay", "transition",
        "preset", "png", "bgm", "sfx", "font", "apk", "download",
        "bundle", "package", "packege", "bundles", "packages"
    ]
    official_keywords = ["sabkraft", "sabkrafttech", "admin", "malik", "owner"]

    show_official = any(kw in lower_text for kw in official_keywords)
    show_material = any(kw in lower_text for kw in material_keywords)

    reply_text = ""

    # Step A: Check JSON Filters (With Smart Phrase Matching)
    matched_reply = get_filter_reply(lower_text, user_tag)
    if matched_reply:
        reply_text = matched_reply

    # Step B: Emoji or Sticker Response
    elif is_only_emoji(user_text_clean) or update.message.sticker:
        reply_text = f"✨ Hey {user_tag}! 🔥 Great vibe! Aaj editing ka kaunsa masterpiece chal raha hai? 🎬"

    # Step C: Screenshot Vision AI Scan
    elif update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

            query_prompt = user_text_clean if user_text_clean else "Error Screenshot"
            full_prompt = f"{SYSTEM_PERSONA}\n\nUser Tag: {user_tag}\nQuery/Error: {query_prompt}\nAnalyze this image error and give a quick 2-step fix."

            model = ai_model or get_ai_model()
            if model:
                res = model.generate_content([full_prompt, image_part])
                reply_text = res.text
            else:
                reply_text = f"✨ Hey {user_tag}! Screenshot received. Please mention your app name! ⚡"
        except Exception as e:
            logging.error(f"Vision Error: {e}")
            reply_text = f"✨ Hey {user_tag}! Screenshot processed, details share karo! 🛠️"

    # Step D: General Unique Contextual Query via Gemini AI
    elif user_text_clean:
        try:
            model = ai_model or get_ai_model()
            if model:
                full_prompt = f"{SYSTEM_PERSONA}\n\nUser Tag: {user_tag}\nQuery: {user_text_clean}"
                res = model.generate_content(full_prompt)
                reply_text = res.text
            else:
                reply_text = f"✨ Hey {user_tag}! AI not configured. Check Render API Key! ⚠️"
        except Exception as e:
            logging.error(f"Gemini API Execution Error: {e}")
            reply_text = f"✨ Hey {user_tag}! Apni query thoda aur detail me poochhein, main ready hoon! 💡"

    # Step E: Send Final Reply with Markup
    if reply_text:
        markup = None
        if show_official:
            markup = OFFICIAL_BUTTONS
        elif show_material:
            markup = MATERIAL_BUTTONS

        try:
            await update.message.reply_text(
                reply_text,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception:
            try:
                await update.message.reply_text(reply_text, reply_markup=markup)
            except Exception:
                pass

# ==========================================
# 6. APP LAUNCHER
# ==========================================
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_BOT_TOKEN missing!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    )

    logging.info("🚀 SabKraftTech Bot active and polling (drop_pending_updates=True)...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
