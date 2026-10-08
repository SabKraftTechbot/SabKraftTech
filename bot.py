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

app = Flask(__name__)

@app.route("/")
def health():
    return "SabKraftTech Premium AI Bot is Active!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

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
    [InlineKeyboardButton("📦 Download Overlays & Effects", url="https://t.me/SabKraftTech")],
    [InlineKeyboardButton("🎨 Download Presets, PNGs & Fonts", url="https://t.me/SabKraftTech")],
    [InlineKeyboardButton("🎵 Download BGM & SFX Packs", url="https://t.me/SabKraftTech")]
])

# ==========================================
# 💎 ULTIMATE SYSTEM PERSONA (Niche Focused)
# ==========================================
SYSTEM_PERSONA = (
    "You are SabKraftTech AI — an elite, premium, Gen-Z assistant created by Mohammad Sabit Javed. "
    "Your CORE EXPERTISE is: Video Editing Hacks, YouTube Growth Tips, 2026 YT Guidelines, Graphic & Thumbnail Designing, and distributing Premium Editing Materials.\n"
    "CRITICAL RULES:\n"
    "1. Keep responses ultra-aesthetic, professional, and short (2-3 lines max).\n"
    "2. Always use premium emojis (✨, 🚀, 💎, 🔥, 🎬, 🎨, 📈).\n"
    "3. Seamlessly match the user's language (English, Hindi, Roman Urdu/Hinglish).\n"
    "4. Whenever relevant, connect your advice to Video Editing, YouTube Guidelines, or Graphic Design.\n"
    "5. Be a highly motivating and expert thought-partner. Never sound robotic."
)

def get_ai_model():
    if not GEMINI_KEY:
        return None
    try:
        genai.configure(api_key=GEMINI_KEY)
        return genai.GenerativeModel(model_name="gemini-1.5-flash")
    except Exception:
        return None

ai_model = get_ai_model()

def extract_user_tag(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "Creator"
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

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
            # \b ensures Exact Word Match (e.g. 'hi' match karega, par 'this' me 'hi' ko ignore karega)
            pattern = r'\b' + re.escape(kw.lower().strip()) + r'\b'
            if re.search(pattern, lower_text):
                return rule
    return None

def is_only_emoji(text: str) -> bool:
    emoji_pattern = re.compile(r"^[\s\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]+$")
    return bool(emoji_pattern.match(text))

# ==========================================
# 🚀 MAIN MESSAGE HANDLER
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

    if is_group and user_text_clean:
        if re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
            try:
                await update.message.delete()
                return
            except Exception:
                pass

    if is_group:
        is_tagged = (bot_username and f"@{bot_username}" in user_text_clean) or (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
            and update.message.reply_to_message.from_user.id == context.bot.id
        )
        if not is_tagged:
            return

    apk_keywords = ["apk", "capcut", "alight motion", "kinemaster", "vn", "pixellab", "picsart", "download", "mod"]
    material_keywords = ["material", "materials", "overlay", "transition", "preset", "png", "bgm", "sfx", "font", "bundle"]
    official_keywords = ["sabkraft", "sabkrafttech", "admin", "malik", "owner", "creator", "youtube", "instagram"]

    is_apk_query = any(kw in lower_text for kw in apk_keywords)
    is_material_query = any(kw in lower_text for kw in material_keywords)
    show_official = any(kw in lower_text for kw in official_keywords)

    reply_text = ""
    model = ai_model or get_ai_model()

    # ==========================================
    # FIX: Smart Handler for Short/Meaningless Greetings
    # ==========================================
    short_greetings = ["hi", "hii", "hlo", "hello", "hey", "kya", "hy", "kya hai", "hyy"]
    is_short_greeting = lower_text in short_greetings

    matched_rule = get_matched_rule(lower_text)

    # Logic 1: Filter Matching (if not a short greeting)
    if matched_rule and not is_short_greeting:
        category = matched_rule.get("category", "")
        base_reply = matched_rule.get("reply", "")

        if "WARNING" in category or "Hate Speech" in category:
            reply_text = base_reply.replace("{user_tag}", user_tag)
        else:
            if model:
                try:
                    dynamic_prompt = (
                        f"{SYSTEM_PERSONA}\n\n"
                        f"User Tag: {user_tag}\n"
                        f"User Message: \"{user_text_clean}\"\n"
                        f"Category: {category}\n\n"
                        f"Task: Write a fresh, highly aesthetic 2-3 line response based on this category. "
                        f"Link it smartly to Editing, YT Growth, or Graphics if possible."
                    )
                    res = model.generate_content(dynamic_prompt)
                    reply_text = res.text if (res and hasattr(res, 'text') and res.text) else base_reply.replace("{user_tag}", user_tag)
                except Exception as e:
                    logging.error(f"Dynamic Gemini Error: {e}")
                    reply_text = base_reply.replace("{user_tag}", user_tag)
            else:
                reply_text = base_reply.replace("{user_tag}", user_tag)

    # Logic 2: Directly Handling Hii / Hlo (The Glitch Fix)
    elif is_short_greeting:
        reply_text = (
            f"✨ Welcome to SabKraftTech, {user_tag}! 🚀\n\n"
            f"Aapko **Video Editing Hacks, Graphic Design, ya YouTube 2026 Guidelines** se related kya madad chahiye? "
            f"Apna sawal thoda detail me likhein, ya neeche se resources explore karein! 🎬🎨"
        )
        show_official = True # Show buttons so they know what to do

    # Logic 3: Emojis
    elif is_only_emoji(user_text_clean) or update.message.sticker:
        reply_text = f"✨ Hey {user_tag}! 🔥 Great vibe! Video Editing, AI tools ya YouTube growth par kya seekhna hai aaj? 🎬"

    # Logic 4: Photos/Screenshots
    elif update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

            query_prompt = user_text_clean if user_text_clean else "Analyze this screenshot."
            full_prompt = f"{SYSTEM_PERSONA}\n\nUser Tag: {user_tag}\nQuery: {query_prompt}\nGive a crisp, 2-step premium solution related to Video Editing, Thumbnail Design, or YouTube."

            if model:
                res = model.generate_content([full_prompt, image_part])
                reply_text = res.text if (res and hasattr(res, 'text')) else f"✨ Hey {user_tag}! Image processed. Design ya editing ki dikkat likh kar batayein! ⚡"
            else:
                reply_text = f"✨ Hey {user_tag}! AI engine offline hai. ⚠️"
        except Exception as e:
            logging.error(f"Vision Error: {e}")
            reply_text = f"✨ Hey {user_tag}! Screenshot dekha maine. Apni editing/YT problem detail me likhein! 🛠️"

    # Logic 5: Normal Chats
    elif user_text_clean:
        try:
            if model:
                full_prompt = (
                    f"{SYSTEM_PERSONA}\n\nUser Tag: {user_tag}\nUser Message: {user_text_clean}\n"
                    "Task: Craft an aesthetic, premium 2-3 line response. Strictly connect your advice/reply to Video Editing hacks, YouTube 2026 Guidelines, or Graphic Design where appropriate."
                )
                res = model.generate_content(full_prompt)
                reply_text = res.text if (res and hasattr(res, 'text')) else f"✨ Hey {user_tag}! Apni video editing ya YouTube query detail me poochein. 🚀"
            else:
                reply_text = f"✨ Hey {user_tag}! AI backend error. ⚠️"
        except Exception as e:
            logging.error(f"Gemini API Error: {e}")
            # Updated Fallback (instead of "sahi sawal hai")
            reply_text = f"✨ Hey {user_tag}! Main SabKraftTech AI hoon. Video editing, YouTube growth ya graphic designing me kya help karoon? Detail me batayein! 🚀🎬"

    # Send Final Reply
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

def main():
    threading.Thread(target=run_flask, daemon=True).start()

    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_TOKEN missing!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    )

    logging.info("🚀 SabKraftTech Premium Bot Active...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
                
