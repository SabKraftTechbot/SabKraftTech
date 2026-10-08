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
# 1. LOGGING & FLASK SERVER
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

app = Flask(__name__)

@app.route("/")
def health():
    return "SabKraftTech Ultimate Master AI is Active!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. CONFIG & BUTTONS
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
# 3. 💎 THE ULTIMATE SYSTEM PERSONA
# ==========================================
SYSTEM_PERSONA = (
    "You are SabKraftTech AI — an elite, ultra-smart, premium Gen-Z assistant created by Mohammad Sabit Javed. "
    "Your MAIN FOCUS: Providing Premium APKs (CapCut, KineMaster, Alight Motion, etc.), Video Editing Tips, "
    "Graphic Designing, YouTube Growth/Guidelines, and overall Content Creation.\n"
    "CRITICAL RULES (FOLLOW STRICTLY):\n"
    "1. NEVER REPEAT YOURSELF. Every single response must be 100% unique, even if they say 'hi' repeatedly.\n"
    "2. CONTEXT IS KING: If a user chats casually (hi/hello), give a unique creative welcome and smoothly offer help with Premium APKs, Editing, or YouTube.\n"
    "3. Keep it SHORT & PREMIUM: Maximum 2-3 lines. To the point. No fluff.\n"
    "4. Use aesthetic emojis (✨, 🚀, 💎, 🔥, 🎬, 🎨, 📈, 📱) to look professional.\n"
    "5. Language: Seamlessly blend Hindi, Hinglish, and English.\n"
    "6. If they ask for apps/APKs, guide them to check the Telegram channel/buttons while giving a premium reply.\n"
    "7. Handle all other topics (science, religion, politics, daily chat) smartly, briefly, and professionally, but try to bring the vibe back to creation and tech."
)

def get_ai_model():
    if not GEMINI_KEY:
        return None
    try:
        genai.configure(api_key=GEMINI_KEY)
        generation_config = genai.types.GenerationConfig(temperature=0.8)
        return genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
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

# ==========================================
# 4. JSON FILTER READER
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
# 5. 🚀 DYNAMIC MESSAGE HANDLER
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

    # Link & Spam Blocker in Groups
    if is_group and user_text_clean:
        if re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
            try:
                await update.message.delete()
                return
            except Exception:
                pass

    # Button Triggers
    apk_keywords = ["apk", "capcut", "alight motion", "kinemaster", "vn", "pixellab", "picsart", "download", "mod", "premium", "apps", "modes"]
    material_keywords = ["material", "materials", "overlay", "transition", "preset", "png", "bgm", "sfx", "font", "bundle", "package"]
    official_keywords = ["sabkraft", "sabkrafttech", "admin", "malik", "owner", "creator", "youtube", "instagram"]

    is_apk_query = any(kw in lower_text for kw in apk_keywords)
    is_material_query = any(kw in lower_text for kw in material_keywords)
    show_official = any(kw in lower_text for kw in official_keywords)

    reply_text = ""
    model = ai_model or get_ai_model()

    dynamic_prompt = (
        f"{SYSTEM_PERSONA}\n\n"
        f"User Tag: {user_tag}\n"
        f"Exact User Message: \"{user_text_clean}\"\n"
    )

    matched_rule = get_matched_rule(lower_text)

    # Logic 1: Image Processing
    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

            prompt = dynamic_prompt + "\nTask: Analyze this screenshot. Give a short, premium 2-line response related to Video Editing, APKs, or Graphics."
            if model:
                res = model.generate_content([prompt, image_part])
                reply_text = res.text if (res and hasattr(res, 'text')) else f"✨ Hey {user_tag}! Image processed. Design ya APK me kya help karoon? 📱"
        except Exception as e:
            logging.error(f"Vision Error: {e}")

    # Logic 2: Emoji Only
    elif is_only_emoji(user_text_clean) or update.message.sticker:
        reply_text = f"✨ Amazing vibe {user_tag}! 🔥 Aaj konsa premium APK chahiye ya video edit karni hai? 🎬"

    # Logic 3: JSON Filter Match
    elif matched_rule:
        category = matched_rule.get("category", "")
        base_reply = matched_rule.get("reply", "")
        
        if "WARNING" in category or "Hate Speech" in category:
            reply_text = base_reply.replace("{user_tag}", user_tag)
        else:
            dynamic_prompt += (
                f"\n[INTERNAL SYSTEM ALERT]: Matches '{category}' rule. "
                f"Base reply: '{base_reply}'.\n"
                f"TASK: Write a COMPLETELY NEW, fresh 2-line response. Connect subtly to Content Creation, YouTube, or Premium Editing tools."
            )
            try:
                if model:
                    res = model.generate_content(dynamic_prompt)
                    reply_text = res.text if (res and hasattr(res, 'text')) else base_reply.replace("{user_tag}", user_tag)
            except Exception:
                reply_text = base_reply.replace("{user_tag}", user_tag)

    # Logic 4: Direct Chat / Everyday Messages
    elif user_text_clean:
        dynamic_prompt += (
            "\nTASK: Generate an aesthetic, premium, 100% unique 2-line response. "
            "Smoothly offer help with Premium APKs, Video Editing, or YouTube Guidelines."
        )
        try:
            if model:
                res = model.generate_content(dynamic_prompt)
                reply_text = res.text if (res and hasattr(res, 'text')) else f"✨ Welcome {user_tag}! SabKraftTech AI haazir hai. Aaj konsi video editing ya YouTube query solve karein? 🚀"
        except Exception as e:
            logging.error(f"Gemini API Error: {e}")
            reply_text = f"✨ Hey {user_tag}! Main SabKraftTech AI hoon. Editing, Graphics ya Premium APK ke liye batayein! 📱🎬"

    # Send Final Output
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

    logging.info("🚀 SabKraftTech Ultimate Master AI Active...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
