import json
import os
import re
import threading
import logging
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
    return "SabKraftTech Professional Aesthetic Bot Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. BOT CONFIG & BUTTONS
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
# 4. CORE MESSAGE HANDLER (AESTHETIC & TARGETED)
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat = update.message.chat
    chat_type = chat.type
    user_tag = extract_user_tag(update)
    is_group_or_channel = chat_type in ["group", "supergroup", "channel"]
    bot_username = context.bot.username or ""

    user_text = update.message.text or update.message.caption or ""
    if not user_text.strip():
        return

    user_text_clean = user_text.strip()
    lower_text = user_text_clean.lower()

    # Link Blocker for Groups/Channels (Except own branding)
    if is_group_or_channel and user_text_clean:
        if re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
            if "t.me/sabkrafttech" not in lower_text and "t.me/teamsabkrafttech" not in lower_text:
                try:
                    if chat_type in ["group", "supergroup"]:
                        await update.message.delete()
                        return
                except Exception:
                    pass

    # ==========================================
    # 🎯 SMART FILTER & SPAM PREVENTION LOGIC
    # ==========================================
    if is_group_or_channel:
        is_forwarded = bool(update.message.forward_origin or update.message.forward_from_chat or update.message.forward_from)
        
        is_tagged = (bot_username and f"@{bot_username}".lower() in lower_text) or (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
            and update.message.reply_to_message.from_user.id == context.bot.id
        )

        matched_rule = get_matched_rule(lower_text)

        # Ignore un-tagged channel forwards and random chatter
        if is_forwarded and not is_tagged and not matched_rule:
            return

        if not is_tagged and not matched_rule:
            return

    # ==========================================
    # 🔑 RESPONSE GENERATION (AESTHETIC & PROFESSIONAL)
    # ==========================================
    matched_rule = get_matched_rule(lower_text)

    if not matched_rule:
        if not is_group_or_channel:
            reply_text = f"✨ Hey {user_tag}! Welcome to SabKraftTech. Looking for CapCut/Alight Motion mods, editing resources, or YouTube growth tips? Drop your query below."
        else:
            reply_text = f"✨ Yes {user_tag}! SabKraftTech support is active. Let me know what material or app you need assistance with."
    else:
        base_reply = matched_rule.get("reply", "")
        reply_text = base_reply.replace("{user_tag}",
        
