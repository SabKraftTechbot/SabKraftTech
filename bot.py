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
# 3. ADVANCED CULTURAL & CONTEXTUAL AI ENGINE
# ==========================================
SYSTEM_PERSONA = (
    "You are SabKraftTech AI — an elite, highly intelligent, premium, and aesthetic Gen-Z assistant "
    "for Video Editors, Graphic Designers, YouTubers, Freelancers, and Creators.\n"
    "CRITICAL RULES:\n"
    "1. **Cultural & Respectful Greetings:** Match the user's greeting naturally and respectfully. If they greet with Islamic adab (e.g., 'Assalamu Alaikum', 'Jumma Mubarak'), reply warmly with Islamic grace (e.g., 'Walaikum Assalam wa Rahmatullahi wa Barakatuh', 🌙✨). If they greet with Hindu or other cultural respect (e.g., 'Namaste', 'Jai Shri Ram'), reply with equal warmth and positivity (🙏✨).\n"
    "2. **Unique & Contextual:** Read the query deeply. Never repeat the same response twice. Keep it short (2-3 lines max), professional, to-the-point, and styled with high-end aesthetic emojis.\n"
    "3. **Language Matching:** Match the user's exact language (English, Hindi, Roman Urdu/Hinglish) seamlessly.\n"
    "4. Always address or tag the user cleanly."
)

def get_ai_model():
    if not GEMINI_KEY:
        logging.error("❌ GEMINI_API_KEY is missing!")
        return None
    try:
        genai.configure(api_key=GEMINI_KEY)
        return genai.GenerativeModel(model_name="gemini-1.5-flash")
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
# 4. JSON CONFIG & BRAND OVERRIDES
# ==========================================
def load_json_config():
    if os.path.exists("filters.json"):
        try:
            with open("filters.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"JSON Load Error: {e}")
    return {"button_triggers": [], "custom_rules": []}

def get_brand_reply(lower_text: str, user_tag: str) -> str:
    config = load_json_config()
    rules = config.get("custom_rules", [])
    user_words = set(lower_text.split())
    
    for rule in rules:
        keywords = rule.get("keywords", [])
        for kw in keywords:
            kw_lower = kw.lower().strip()
            if kw_lower == lower_text or kw_lower in user_words or kw_lower in lower_text:
                reply = rule.get("reply", "")
                return reply.replace("{user_tag}", user_tag)
    return ""

def is_only_emoji(text: str) -> bool:
    emoji_pattern = re.compile(r"^[\s\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]+$")
    return bool(emoji_pattern.match(text))

# ==========================================
# 5. MAIN MESSAGE HANDLER (Safe & Robust)
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

    # 3. Dynamic Keyword Classification (Group vs Channel/Material context)
    apk_keywords = ["apk", "capcut", "alight motion", "kinemaster", "vn", "pixellab", "picsart", "app", "download mod"]
    material_keywords = ["material", "materials", "overlay", "transition", "preset", "png", "bgm", "sfx", "font", "bundle", "package", "tmkoc", "cid", "meme"]

    is_apk_query = any(kw in lower_text for kw in apk_keywords)
    is_material_query = any(kw in lower_text for kw in material_keywords)
    official_keywords = ["sabkraft", "sabkrafttech", "admin", "malik", "owner"]
    show_official = any(kw in lower_text for kw in official_keywords)

    reply_text = ""

    # Step A: Check Brand Override
    brand_reply = get_brand_reply(lower_text, user_tag)
    if brand_reply and ("sabkraft" in lower_text):
        reply_text = brand_reply

    # Step B: Emoji or Sticker Response
    elif is_only_emoji(user_text_clean) or update.message.sticker:
        reply_text = f"✨ Hey {user_tag}! 🔥 Great vibe! Aaj editing ya creative project me kya chal raha hai? 🎬"

    # Step C: Location & Context Aware Routing (Group vs Channel Search)
    elif is_apk_query or is_material_query:
        if is_group:
            if is_apk_query:
                reply_text = f"📱 **Group App Search**: Hey {user_tag}! Pro APKs aur latest updates ke liye hamare main channel files ko explore karein ya neeche diye buttons ka use karein! ⚡"
            else:
                reply_text = f"📦 **Group Material Hub**: Hey {user_tag}! Editing materials aur presets group me explore karne ke liye pinned messages ya channel links check karein! 🎨"
        else:
            if is_apk_query:
                reply_text = f"🚀 **Pro APK Hub**: Hey {user_tag}! Aapko unblocked pro apps chahiye? Channel ke downloads section ya button se direct access lein! 🔥"
            else:
                reply_text = f"✨ **Channel Material Exploration**: Hey {user_tag}! Premium overlays, transitions aur SFX packs load ho chuke hain. Neeche buttons se download karein! 💎"

    # Step D: Screenshot Vision AI Scan
    elif update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

            query_prompt = user_text_clean if user_text_clean else "Error Screenshot"
            full_prompt = f"{SYSTEM_PERSONA}\n\nUser Tag: {user_tag}\nQuery/Error: {query_prompt}\nAnalyze this image/error contextually and give a crisp, aesthetic 2-step fix."

            model = ai_model or get_ai_model()
            if model:
                res = model.generate_content([full_prompt, image_part])
                if res and hasattr(res, 'text') and res.text:
                    reply_text = res.text
                else:
                    reply_text = f"✨ Hey {user_tag}! Image processed successfully. App name mention karein! ⚡"
            else:
                reply_text = f"✨ Hey {user_tag}! AI engine offline hai. ⚠️"
        except Exception as e:
            logging.error(f"Vision Error: {e}")
            reply_text = f"✨ Hey {user_tag}! Image analysis complete, details share karein! 🛠️"

    # Step E: Fully Dynamic Contextual AI with Safe Response Extraction
    elif user_text_clean:
        try:
            model = ai_model or get_ai_model()
            if model:
                full_prompt = f"{SYSTEM_PERSONA}\n\nUser Tag: {user_tag}\nUser Message: {user_text_clean}\nContext: Craft a completely fresh, unique, respectful (applying proper cultural/religious greetings if triggered), and aesthetic response tailored directly to this input."
                res = model.generate_content(full_prompt)
                
                # Safe text extraction to prevent any crashes
                if res and hasattr(res, 'text') and res.text:
                    reply_text = res.text
                else:
                    reply_text = f"✨ Hey {user_tag}! Aaj ka session amazing rahega, apni next query poochhein! 🚀"
            else:
                reply_text = f"✨ Hey {user_tag}! AI engine configuration check karein. ⚠️"
        except Exception as e:
            logging.error(f"Gemini API Execution Error: {e}")
            reply_text = f"✨ Hey {user_tag}! Bilkul badhiya sawal hai! Ispar aur detail me bataiye taaki aur behtar guide kar sakuin! 💡"

    # Step F: Send Final Reply with Interactive Buttons
    if reply_text:
        markup = None
        if show_official or is_apk_query:
            markup = OFFICIAL_BUTTONS
        elif is_material_query:
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
        logging.error("❌ TELEGRAM_TOKEN missing!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    )

    logging.info("🚀 SabKraftTech Bot active and polling (drop_pending_updates=True)...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
