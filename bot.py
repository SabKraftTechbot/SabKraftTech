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
    return "SabKraftTech Core Focus Bot Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. BOT CONFIG & OFFICIAL BUTTONS
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
# 4. CORE MESSAGE HANDLER (FINAL LOGIC)
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat = update.message.chat
    chat_type = chat.type
    user_tag = extract_user_tag(update)
    is_group_or_channel = chat_type in ["group", "supergroup", "channel"]
    bot_username = context.bot.username or ""

    # Agar message me text ya caption hi nahi hai (jaise sirf photo/video bina text ke), toh ignore karo
    user_text = update.message.text or update.message.caption or ""
    if not user_text.strip():
        return

    user_text_clean = user_text.strip()
    lower_text = user_text_clean.lower()

    # Group/Channel me link blocker (agar koi unauthorized link bhejta hai)
    if is_group_or_channel and user_text_clean:
        if re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
            # Agar message me official channel link khud ka hai toh allow karein, warna block/delete
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
        # 1. Agar message channel se forward hoke aaya hai, aur usme koi tag nahi hai, toh bot chup rahega!
        is_forwarded = bool(update.message.forward_origin or update.message.forward_from_chat or update.message.forward_from)
        
        # 2. Check karo ki kya bot ko tag kiya gaya hai ya bot ke message par reply hai?
        is_tagged = (bot_username and f"@{bot_username}".lower() in lower_text) or (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
            and update.message.reply_to_message.from_user.id == context.bot.id
        )

        # 3. Check karo ki kya message me koi valid trigger keyword (filters.json wala) maujood hai?
        matched_rule = get_matched_rule(lower_text)

        # 🚀 MAIN CONDITION:
        # Agar message forwarded hai AUR na toh bot ko tag kiya gaya hai, na hi koi trigger keyword match hua hai -> TAB BOT BILKUL RESPOND NAHI KAREGA.
        if is_forwarded and not is_tagged and not matched_rule:
            return

        # Agar normal group chat hai aur na toh tag kiya, na keyword match hua, toh bhi ignore (spam bachane ke liye)
        if not is_tagged and not matched_rule:
            return

    # ==========================================
    # 🔑 RULE MATCHING & RESPONSE GENERATION
    # ==========================================
    matched_rule = get_matched_rule(lower_text)

    if not matched_rule:
        # Agar tag kiya tha par koi specific keyword nahi mila, toh SabKraftTech core focus wala professional reply do
        if not is_group_or_channel:
            reply_text = f"✨ Hey {user_tag}! SabKraftTech AI haazir hai. Premium Apps (CapCut/Alight Motion), Editing Materials, ya YouTube/Social Media tips ke liye batayein! 🚀"
        else:
            reply_text = f"✨ Yes {user_tag}! SabKraftTech hub me batayein—CapCut/Alight Motion APK chahiye ya Editing Materials? 🎬🔥"
    else:
        base_reply = matched_rule.get("reply", "")
        reply_text = base_reply.replace("{user_tag}", user_tag)

    # Core Focus Buttons Logic (APKs & Materials & Official Links)
    apk_keywords = ["apk", "capcut", "alight motion", "kinemaster", "vn", "pixellab", "picsart", "download", "mod", "premium", "apps", "modes"]
    material_keywords = ["material", "materials", "overlay", "transition", "preset", "png", "bgm", "sfx", "font", "bundle", "package"]
    official_keywords = ["sabkraft", "sabkrafttech", "admin", "malik", "owner", "creator", "youtube", "instagram"]

    is_apk_query = any(kw in lower_text for kw in apk_keywords)
    is_material_query = any(kw in lower_text for kw in material_keywords)
    show_official = any(kw in lower_text for kw in official_keywords)

    markup = None
    if is_apk_query or is_material_query:
        markup = MATERIAL_BUTTONS
    elif show_official or matched_rule:
        markup = OFFICIAL_BUTTONS

    # Send Response
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

    logging.info("🚀 SabKraftTech Core Focus Bot Starting Successfully...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
