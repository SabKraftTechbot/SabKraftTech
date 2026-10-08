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
    return "SabKraftTech Auto-Delete Bot Online!", 200

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
# 4. AUTO-DELETE HELPER FUNCTION (5 MINUTES)
# ==========================================
def schedule_message_deletion(context, chat_id, message_id):
    def delete_msg():
        try:
            # Bot ki apni async loop me message delete karne ke liye run_coroutine_threadsafe use hota hai
            import asyncio
            async def do_delete():
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                except Exception:
                    pass
            
            # Application loop me task daalna
            loop = context.application.create_task(do_delete())
        except Exception:
            pass

    # 5 minutes = 300 seconds
    timer = threading.Timer(300.0, delete_msg)
    timer.daemon = True
    timer.start()

# ==========================================
# 5. CORE MESSAGE HANDLER
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

        if is_forwarded and not is_tagged and not matched_rule:
            return

        if not is_tagged and not matched_rule:
            return

    # ==========================================
    # 🔑 RESPONSE GENERATION
    # ==========================================
    matched_rule = get_matched_rule(lower_text)

    if not matched_rule:
        if not is_group_or_channel:
            reply_text = f"✨ Hey {user_tag}! Welcome to SabKraftTech. Looking for CapCut/Alight Motion mods, editing resources, or YouTube growth tips? Drop your query below."
        else:
            reply_text = f"✨ Yes {user_tag}! SabKraftTech support is active. Let me know what material or app you need assistance with."
    else:
        base_reply = matched_rule.get("reply", "")
        reply_text = base_reply.replace("{user_tag}", user_tag)

    # ==========================================
    # 🔘 BUTTON LOGIC: ONLY WHEN TAGGED
    # ==========================================
    markup = None
    is_explicitly_tagged = (bot_username and f"@{bot_username}".lower() in lower_text) or (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )

    if not is_group_or_channel or is_explicitly_tagged:
        apk_keywords = ["apk", "capcut", "alight motion", "kinemaster", "vn", "pixellab", "picsart", "download", "mod", "premium", "apps", "modes"]
        material_keywords = ["material", "materials", "overlay", "transition", "preset", "png", "bgm", "sfx", "font", "bundle", "package"]
        official_keywords = ["sabkraft", "sabkrafttech", "admin", "malik", "owner", "creator", "youtube", "instagram"]

        is_apk_query = any(kw in lower_text for kw in apk_keywords)
        is_material_query = any(kw in lower_text for kw in material_keywords)
        show_official = any(kw in lower_text for kw in official_keywords)

        if is_apk_query or is_material_query:
            markup = MATERIAL_BUTTONS
        elif show_official or matched_rule:
            markup = OFFICIAL_BUTTONS

    # Send Response
    try:
        sent_message = await update.message.reply_text(reply_text, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        try:
            sent_message = await update.message.reply_text(reply_text, reply_markup=markup)
        except Exception:
            sent_message = None

    # ⏱️ Agar message group ya supergroup me bheja gaya hai, toh 5 minute baad automatic delete karne ka timer lagayein
    if sent_message and is_group_or_channel:
        schedule_message_deletion(context, update.message.chat_id, sent_message.message_id)

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

    logging.info("🚀 SabKraftTech Auto-Delete Bot Starting Successfully...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
