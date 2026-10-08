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
# 1. LOGGING & FLASK SERVER (KEEP-ALIVE)
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

app = Flask(__name__)

@app.route("/")
def health():
    return "SabKraftTech Dynamic AI Engine is Active!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. CONFIG & AI SETUP
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMBilkul! Yeh ekdum next-level idea hai. Ek hi fixed reply baar-baar bhejne se bot boring (robotic) lagne lagta hai. 

Is problem ko solve karne ke liye maine **`bot.py` me ek "Dynamic AI Router"** banaya hai. Ab bot kya karega:
1. Sabse pehle `filters.json` me keyword match karega (taaki context pata chale ki user kya chahta hai).
2. Fir us category ka context aur user ka exact message **Gemini AI** ko bhejega.
3. Gemini us context ko samajh kar **har baar ek naya, fresh, aur aesthetic response** banayega!
4. **Hate Speech & Politics** ko strictly "Static" rakha gaya hai taaki wahan AI koi galti na kare aur direct warning de.

Yahan aapka **Ultimate `bot.py`** code hai jo is dynamic behavior ko handle karega:

### 🐍 The Advanced Context-Aware `bot.py`

```python
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

OFFICIAL_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📢 Telegram Channel", url="[https://t.me/SabKraftTech](https://t.me/SabKraftTech)"),
        InlineKeyboardButton("👥 Telegram Group", url="[https://t.me/TeamSabKraftTech](https://t.me/TeamSabKraftTech)")
    ],
    [
        InlineKeyboardButton("▶️ YouTube Channel", url="[https://youtube.com/@sabkrafttech?si=BvFSMTysyXScxEj2](https://youtube.com/@sabkrafttech?si=BvFSMTysyXScxEj2)"),
        InlineKeyboardButton("📸 Instagram ID", url="[https://instagram.com/sabkrafttech](https://instagram.com/sabkrafttech)")
    ]
])

MATERIAL_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("📦 Download Overlays & Effects", url="[https://t.me/SabKraftTech](https://t.me/SabKraftTech)")],
    [InlineKeyboardButton("🎨 Download Presets, PNGs & Fonts", url="[https://t.me/SabKraftTech](https://t.me/SabKraftTech)")],
    [InlineKeyboardButton("🎵 Download BGM & SFX Packs", url="[https://t.me/SabKraftTech](https://t.me/SabKraftTech)")]
])

# ==========================================
# 3. ADVANCED AI SYSTEM PERSONA
# ==========================================
SYSTEM_PERSONA = (
    "You are SabKraftTech AI — an elite, premium, Gen-Z assistant created for the SabKraft Tech platform. "
    "You assist Video Editors, Graphic Designers, YouTubers, and Creators.\n"
    "CRITICAL RULES:\n"
    "1. Keep responses ultra-aesthetic, professional, respectful, and concise (2-3 lines max).\n"
    "2. Use high-end emojis (✨, 🚀, 💎, 🔥, 🎬).\n"
    "3. Match the user's language smoothly (English, Hindi, Roman Urdu/Hinglish).\n"
    "4. Always greet or tag the user cleanly using their provided tag.\n"
    "5. Do NOT sound robotic. Be a natural, motivating, and helpful thought-partner."
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
# 4. JSON FILTER READER (RETURNS FULL RULE)
# ==========================================
def load_json_config():
    if os.path.exists("filters.json"):
        try:
            with open("filters.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"JSON Load Error: {e}")
    return {"button_triggers": [], "custom_rules": []}

def get_matched_rule(lower_text: str):
    """Returns the matched rule dictionary instead of just the string."""
    config = load_json_config()
    rules = config.get("custom_rules", [])
    
    for rule in rules:
        keywords = rule.get("keywords", [])
        for kw in keywords:
            if kw.lower().strip() in lower_text:
                return rule
    return None

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

    # Button Triggers Check
    apk_keywords = ["apk", "capcut", "alight motion", "kinemaster", "vn", "pixellab", "picsart", "download", "mod"]
    material_keywords = ["material", "materials", "overlay", "transition", "preset", "png", "bgm", "sfx", "font", "bundle"]
    official_keywords = ["sabkraft", "sabkrafttech", "admin", "malik", "owner", "creator", "youtube", "instagram"]

    is_apk_query = any(kw in lower_text for kw in apk_keywords)
    is_material_query = any(kw in lower_text for kw in material_keywords)
    show_official = any(kw in lower_text for kw in official_keywords)

    reply_text = ""
    model = ai_model or get_ai_model()

    # Step A: Check Custom Filters First
    matched_rule = get_matched_rule(lower_text)

    if matched_rule:
        category = matched_rule.get("category", "")
        base_reply = matched_rule.get("reply", "")

        # Strict Static Reply for Warnings (No AI alteration allowed)
        if "Hate Speech" in category or "WARNING" in category:
            reply_text = base_reply.replace("{user_tag}", user_tag)
        else:
            # Dynamic AI Generation based on Filter Context
            if model:
                try:
                    dynamic_prompt = (
                        f"{SYSTEM_PERSONA}\n\n"
                        f"User Tag: {user_tag}\n"
                        f"User Exact Message: \"{user_text_clean}\"\n\n"
                        f"Context/Category Match: {category}\n"
                        f"Core Vibe/Instruction: {base_reply}\n\n"
                        f"Task: Do not just copy the instruction. Write a COMPLETELY FRESH, unique, and dynamic 2-3 line response "
                        f"that directly answers the user's message while maintaining the '{category}' vibe. "
                        f"Keep it extremely aesthetic."
                    )
                    res = model.generate_content(dynamic_prompt)
                    reply_text = res.text if (res and hasattr(res, 'text') and res.text) else base_reply.replace("{user_tag}", user_tag)
                except Exception as e:
                    logging.error(f"Dynamic Gemini Error: {e}")
                    reply_text = base_reply.replace("{user_tag}", user_tag)
            else:
                # Fallback if Gemini is down
                reply_text = base_reply.replace("{user_tag}", user_tag)

    # Step B: Emoji / Sticker
    elif is_only_emoji(user_text_clean) or update.message.sticker:
        reply_text = f"✨ Hey {user_tag}! 🔥 Great vibe! Aaj editing ya creative project me kya chal raha hai? 🎬"

    # Step C: Screenshot Vision Scan
    elif update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

            query_prompt = user_text_clean if user_text_clean else "Analyze this screenshot contextually."
            full_prompt = f"{SYSTEM_PERSONA}\n\nUser Tag: {user_tag}\nQuery: {query_prompt}\nGive a crisp, 2-step solution or observation regarding this image."

            if model:
                res = model.generate_content([full_prompt, image_part])
                reply_text = res.text if (res and hasattr(res, 'text')) else f"✨ Hey {user_tag}! Image processed. Details share karein! ⚡"
            else:
                reply_text = f"✨ Hey {user_tag}! AI engine offline hai. ⚠️"
        except Exception as e:
            logging.error(f"Vision Error: {e}")
            reply_text = f"✨ Hey {user_tag}! Image analysis done, apni dikkat likh kar batayein! 🛠️"

    # Step D: Unfiltered Dynamic Chat (Standard AI)
    elif user_text_clean:
        try:
            if model:
                full_prompt = (
                    f"{SYSTEM_PERSONA}\n\nUser Tag: {user_tag}\nUser Message: {user_text_clean}\n"
                    "Craft a fresh, unique, aesthetic response strictly tailored to this input."
                )
                res = model.generate_content(full_prompt)
                reply_text = res.text if (res and hasattr(res, 'text')) else f"✨ Hey {user_tag}! Amazing, ispar aur detail me batayein! 🚀"
            else:
                reply_text = f"✨ Hey {user_tag}! AI backend error. ⚠️"
        except Exception as e:
            logging.error(f"Gemini API Execution Error: {e}")
            reply_text = f"✨ Hey {user_tag}! Sahi sawal hai! Thoda aur detail dejiye taaki exact solution de saku. 💡"

    # Step E: Send Reply with Buttons (If required)
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

    logging.info("🚀 SabKraftTech Bot active with Dynamic AI Mode...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
