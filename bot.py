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
    return "SabKraftTech Master AI Engine Online!", 200

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
# 3. AI SYSTEM PROMPT
# ==========================================
SYSTEM_PERSONA = (
    "You are SabKraftTech AI — an official AI assistant created by Mohammad Sabit Javed for SabKraftTech.\n"
    "YOUR PRIMARY ROLE:\n"
    "- Help creators with Video Editing (CapCut, Alight Motion, KineMaster, Premiere Pro, VN).\n"
    "- Provide tips on Graphic Design, Thumbnails, Pixellab, Canva.\n"
    "- Guide on YouTube Growth, Algorithms, CTR, and Content Creation.\n"
    "- Share information about Premium Pro APKs, No-Watermark Apps, and Asset Bundles.\n\n"
    "STRICT OUTPUT RULES:\n"
    "1. ABSOLUTELY NEVER REPEAT PREVIOUS REPLIES. Every response MUST be unique, creative, and fresh.\n"
    "2. Language: Natural mix of Hinglish and English with a professional, friendly Gen-Z creator tone.\n"
    "3. Format: Keep it short (2 to 3 lines max). Use clean bullet points or bold text where necessary.\n"
    "4. Aesthetic Emojis: Use relevant emojis (✨, 🚀, 🎬, 🎨, 📈, 📱) to look high-quality.\n"
    "5. If the user asks general everyday questions, respond politely and connect it back to video editing or tech."
)

def get_ai_model():
    if not GEMINI_KEY:
        return None
    try:
        genai.configure(api_key=GEMINI_KEY)
        generation_config = genai.types.GenerationConfig(
            temperature=0.9,
            top_p=0.95,
            top_k=40
        )
        return genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
    except Exception as e:
        logging.error(f"AI Init Error: {e}")
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
# 4. JSON CONFIG LOADER
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

def is_only_emoji(text: str) -> bool:
    emoji_pattern = re.compile(r"^[\s\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]+$")
    return bool(emoji_pattern.match(text))

# ==========================================
# 5. CORE MESSAGE HANDLER
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

    # ==========================================
    # SMART GROUP FILTER (Common vs Tagged)
    # ==========================================
    if is_group:
        common_triggers = [
            "hi", "hii", "hlo", "hlw", "hello", "hey", "hy", "hyy", "salam", "assalamu", "assalam", 
            "aslm", "walekum", "namaste", "good morning", "good evening", "good night", "bye", 
            "kya haal", "kaise ho", "wassup", "sab thik", "inshaallah", "mashallah", "subhanallah",
            "apk", "capcut", "alight", "kinemaster", "vn", "pixellab", "picsart", "app", "apps", 
            "mod", "modes", "download", "editing", "video editing", "youtube", "yt", "ctr", 
            "views", "growth", "thumbnail", "font", "bgm", "sfx", "preset", "overlay", "png", 
            "material", "materials", "bundle", "earning", "paisa", "money", "help", "madad", 
            "error", "not working", "glitch", "problem", "issue", "sabkraft", "sabkrafttech"
        ]

        has_common_keyword = any(re.search(r'\b' + re.escape(kw) + r'\b', lower_text) for kw in common_triggers)
        is_tagged = (bot_username and f"@{bot_username}" in user_text_clean) or (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
            and update.message.reply_to_message.from_user.id == context.bot.id
        )

        if not has_common_keyword and not is_tagged:
            return

    # Button Keywords
    apk_keywords = ["apk", "capcut", "alight motion", "kinemaster", "vn", "pixellab", "picsart", "download", "mod", "premium", "apps", "modes"]
    material_keywords = ["material", "materials", "overlay", "transition", "preset", "png", "bgm", "sfx", "font", "bundle", "package"]
    official_keywords = ["sabkraft", "sabkrafttech", "admin", "malik", "owner", "creator", "youtube", "instagram"]

    is_apk_query = any(kw in lower_text for kw in apk_keywords)
    is_material_query = any(kw in lower_text for kw in material_keywords)
    show_official = any(kw in lower_text for kw in official_keywords)

    reply_text = ""
    model = ai_model or get_ai_model()

    matched_rule = get_matched_rule(lower_text)

    # ------------------------------------------
    # CASE 1: IMAGE ATTACHMENT
    # ------------------------------------------
    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

            prompt = (
                f"{SYSTEM_PERSONA}\nUser Tag: {user_tag}\n"
                f"Task: Analyze this image. Provide a unique 2-line response regarding Video Editing, Graphic Design, or App issues."
            )
            if model:
                res = model.generate_content([prompt, image_part])
                reply_text = res.text if (res and hasattr(res, 'text')) else f"✨ Screenshot dekha {user_tag}! Batayein is me kya editing ya app help chahiye? 📱"
        except Exception as e:
            logging.error(f"Image Error: {e}")

    # ------------------------------------------
    # CASE 2: EMOJI / STICKER ONLY
    # ------------------------------------------
    elif is_only_emoji(user_text_clean) or update.message.sticker:
        dynamic_prompt = (
            f"{SYSTEM_PERSONA}\nUser Tag: {user_tag}\n"
            f"User sent an emoji/sticker: '{user_text_clean}'.\n"
            f"Task: Write a fresh 1-line creative reaction and offer editing/tech help."
        )
        try:
            if model:
                res = model.generate_content(dynamic_prompt)
                reply_text = res.text
        except Exception:
            reply_text = f"🔥 Op vibe {user_tag}! Aaj kya naya edit kar rahe ho? 🎬"

    # ------------------------------------------
    # CASE 3: JSON FILTER MATCH
    # ------------------------------------------
    elif matched_rule:
        category = matched_rule.get("category", "")
        base_reply = matched_rule.get("reply", "")

        if "WARNING" in category or "Hate" in category:
            reply_text = base_reply.replace("{user_tag}", user_tag)
        else:
            dynamic_prompt = (
                f"{SYSTEM_PERSONA}\nUser Tag: {user_tag}\n"
                f"User Message: '{user_text_clean}'\n"
                f"Category Context: '{category}'\n"
                f"Reference Idea: '{base_reply}'\n"
                f"Task: Write a UNIQUE, FRESH 2-line response. DO NOT copy reference idea word-for-word. Keep it creative."
            )
            try:
                if model:
                    res = model.generate_content(dynamic_prompt)
                    reply_text = res.text if (res and hasattr(res, 'text')) else base_reply.replace("{user_tag}", user_tag)
            except Exception:
                reply_text = base_reply.replace("{user_tag}", user_tag)

    # ------------------------------------------
    # CASE 4: GENERAL CHAT & CREATOR QUESTIONS
    # ------------------------------------------
    elif user_text_clean:
        dynamic_prompt = (
            f"{SYSTEM_PERSONA}\nUser Tag: {user_tag}\n"
            f"User Input: '{user_text_clean}'\n"
            f"Task: Generate a smart, professional, highly relevant 2-line answer. Offer help with Editing, Apps, or YouTube."
        )
        try:
            if model:
                res = model.generate_content(dynamic_prompt)
                reply_text = res.text
        except Exception as e:
            logging.error(f"AI Generation Error: {e}")
            reply_text = f"✨ Hey {user_tag}! Main SabKraftTech AI hoon. Editing, Apps ya Youtube Growth me kya madad chahiye? 🚀"

    # ------------------------------------------
    # SEND RESPONSE WITH INLINE BUTTONS
    # ------------------------------------------
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
# 6. APP STARTUP
# ==========================================
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_BOT_TOKEN environment variable missing!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    )

    logging.info("🚀 SabKraftTech Master AI Bot Starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
