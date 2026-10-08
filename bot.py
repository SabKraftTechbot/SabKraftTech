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
    return "SabKraftTech Filter-Based Bot Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. BOT CONFIG & BUTTONS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

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
    [InlineKeyboardButton("📱 Download Premium APKs & Mods", url="https://t.me/SabKraftTech")],
    [InlineKeyboardButton("📦 Overlays, Presets & Fonts", url="https://t.me/SabKraftTech")],
    [InlineKeyboardButton("🎵 BGM & SFX Packs", url="https://t.me/SabKraftTech")]
])

# ==========================================
# 3. JSON CONFIG LOADER
# ==========================================
def load_json_config():
    if os.path.exists("filters.json"):
        try:
            with open("filters.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"button_triggers": [], "custom_rules": []}

def get_matched_rule(lower_text: str):
    config = load_json_config()
    rules = config.get("custom_rules", [])
    for rule in rules:
        keywords = rule.get("keywords", [])
        for kw in keywords:
            pattern = r'\b' + re.escape(kw.lower().strip()) + r'\b'
            if re.search(pattern, lower_text):
                return rule
    return None

def extract_user_tag(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "Creator"
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

# ==========================================
# 4. CORE MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_type = update.message.chat.type
    user_tag = extract_user_tag(update)
    is_group = chat_type in ["group", "supergroup"]

    user_text = update.message.text or update.message.caption or ""
    user_text_clean = user_text.strip()
    lower_text = user_text_clean.lower()
    bot_username = context.bot.username or ""

    # Group Link Blocker
    if is_group and user_text_clean:
        if re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
            try:
                await update.message.delete()
                return
            except Exception:
                pass

    # Button Keywords Check
    apk_keywords = ["apk", "capcut", "alight motion", "kinemaster", "vn", "pixellab", "picsart", "download", "mod", "premium", "apps", "modes"]
    material_keywords = ["material", "materials", "overlay", "transition", "preset", "png", "bgm", "sfx", "font", "bundle", "package"]
    official_keywords = ["sabkraft", "sabkrafttech", "admin", "malik", "owner", "creator", "youtube", "instagram"]

    is_apk_query = any(kw in lower_text for kw in apk_keywords)
    is_material_query = any(kw in lower_text for kw in material_keywords)
    show_official = any(kw in lower_text for kw in official_keywords)

    reply_text = ""

    # Match Rule from filters.json
    matched_rule = get_matched_rule(lower_text)

    if matched_rule:
        base_reply = matched_rule.get("reply", "")
        reply_text = base_reply.replace("{user_tag}", user_tag)
    else:
        # Agar koi aisi baat likhe jo json me nahi hai, toh ek default aesthetic creator reply dega
        reply_text = f"✨ Hey {user_tag}! SabKraftTech platform par aapka swagat hai. Video editing, apps ya YouTube tips ke liye batayein! 🚀"

    # Send Response with Buttons
    if reply_text:
        markup = None
        if is_apk_query or is_material_query:
            markup = MATERIAL_BUTTONS
        elif show_official:
            markup = OFFICIAL_BUTTONS

        try:
            await update.message.reply_text(reply_text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            try:
                await update.message.reply_text(reply_text, reply_markup=markup)
            except Exception:
                pass

# ==========================================
# 5. APP STARTUP
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

    logging.info("🚀 SabKraftTech Filter-Based Bot Starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
