import json
import os
import re
import asyncio
import logging
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==========================================
# 1. GEMINI AI INTEGRATION
# ==========================================
try:
    import google.generativeai as genai
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
        ai_model = genai.GenerativeModel("gemini-1.5-flash")
    else:
        ai_model = None
except Exception as e:
    ai_model = None

# ==========================================
# 2. LOGGING & FLASK HEALTH CHECK
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

app = Flask(__name__)

@app.route("/")
def health():
    return "SabKraftTech Pro Editor AI Engine Online 24/7!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 3. BOT CONFIG & BUTTON LAYOUTS
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
    [InlineKeyboardButton("📦 Explore Materials & APKs in Channel", url="https://t.me/SabKraftTech")]
])

# ==========================================
# 4. DYNAMIC JSON FILTER READER
# ==========================================
_cached_filters = []

def load_filters():
    global _cached_filters
    if os.path.exists("filters.json"):
        try:
            with open("filters.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                _cached_filters = data.get("filters", [])
                return _cached_filters
        except Exception as e:
            logging.error(f"Error reading filters.json: {e}")
            return _cached_filters
    return []

def match_keyword_smart(kw: str, text: str) -> bool:
    kw = kw.lower().strip()
    if not kw:
        return False
    if " " in kw:
        return kw in text
    pattern = r'(?<!\w)' + re.escape(kw) + r'(?!\w)'
    return bool(re.search(pattern, text))

def find_matching_filter(text_lower: str):
    filters_list = load_filters()
    for item in filters_list:
        keywords = item.get("keywords", [])
        for kw in keywords:
            if match_keyword_smart(kw, text_lower):
                return item
    return None

def extract_user_tag(msg) -> str:
    user = msg.from_user if msg else None
    if not user:
        return "Member"
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

# ==========================================
# 5. CREATOR & EDITOR PERSONA GEMINI AI
# ==========================================
async def get_ai_response(user_text: str, user_name: str) -> str:
    if not ai_model:
        return f"✨ **Hey {user_name}!** SabKraftTech Editor Community me aapka swagat hai. Aaj konse project ya asset me help chahiye?"

    system_prompt = f"""
    You are 'SabKraftTech AI' — an expert Mobile Video Editor, Graphic Designer, Cinematic Documentary Creator, and Freelancer assistant for the SabKraftTech community (Founder: Sabit Ansari).

    CORE PERSONALITY & BEHAVIOR RULES:
    1. CONTEXT: The member speaking is '{user_name}'.
    2. VOICE & TONE: Speak like a real, experienced Video Editor & Freelance Creator. Be warm, supportive, friendly, highly practical, and knowledgeable about YouTube growth, CTR, CapCut, KineMaster, Alight Motion, Photoshop, and mobile editing tools.
    3. GREETINGS (Hi, Hlo, Good Morning, Good Night, Good Day, etc.): Respond warmly as a fellow creator! Wish them well, boost their creative energy, and casually ask what editing project or asset they are working on today.
    4. LANGUAGE: Match the user's language smoothly (Hinglish/Hindi/Urdu/English). Keep religious & respectful greetings authentic.
    5. STYLE: Clean Markdown, short & engaging (2-3 brief lines or clean bullet points). Avoid long boring lectures.

    Member Message: "{user_text}"
    Give a natural, aesthetic reply as a Pro Video Editor:
    """

    try:
        response = await asyncio.to_thread(ai_model.generate_content, system_prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini AI Error: {e}")
        return f"✨ **Hey {user_name}!**\n\nKaise hain aap? Aaj editing, graphic design, ya YouTube content ke silsile me kya update hai?"

# ==========================================
# 6. AUTO-DELETE HELPER (300 SECONDS)
# ==========================================
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# ==========================================
# 7. CORE MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    chat = msg.chat
    chat_type = chat.type
    is_group = chat_type in ["group", "supergroup"]

    # 🛑 1. IGNORE CHANNEL AUTOMATIC POSTS & FORWARDS
    if msg.is_automatic_forward or getattr(msg, "forward_origin", None) or getattr(msg, "forward_from_chat", None):
        return

    # 🛑 2. IGNORE SENDER CHAT / POSTS SENT AS CHANNEL
    if msg.sender_chat and msg.sender_chat.id != chat.id:
        return

    # 🛑 3. IGNORE BOT MESSAGES
    if msg.from_user and msg.from_user.is_bot:
        return

    user_text = msg.text or msg.caption or ""
    if not user_text.strip():
        return

    user_text_clean = user_text.strip()
    lower_text = user_text_clean.lower()
    user_tag = extract_user_tag(msg)
    user_name = msg.from_user.first_name if msg.from_user else "Creator"

    # 🛡️ 4. LINK BLOCKER FOR GROUPS
    if is_group and re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
        if "t.me/sabkrafttech" not in lower_text and "t.me/teamsabkrafttech" not in lower_text:
            try:
                await msg.delete()
                return
            except Exception:
                pass

    # 🟢 5. ALWAYS REPLY TO REAL MEMBERS IN GROUP & DM
    matched_filter = find_matching_filter(lower_text)
    reply_text = ""
    markup = None

    if matched_filter:
        raw_reply = matched_filter.get("reply", "")
        reply_text = raw_reply.replace("{user_tag}", user_tag)
        btn_type = matched_filter.get("button_type", "none")

        if btn_type == "official":
            markup = OFFICIAL_BUTTONS
        elif btn_type == "material":
            markup = MATERIAL_BUTTONS
        else:
            markup = None
    else:
        # Greetings / General Chat / Queries -> Pro Video Editor Gemini AI
        reply_text = await get_ai_response(user_text_clean, user_name)
        markup = None

    # Send Reply
    sent_message = None
    try:
        sent_message = await msg.reply_text(reply_text, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        try:
            sent_message = await msg.reply_text(reply_text, reply_markup=markup)
        except Exception:
            pass

    # Auto-delete in 5 mins (Groups only)
    if sent_message and is_group:
        asyncio.create_task(
            delete_message_after_delay(context, msg.chat_id, sent_message.message_id, 300)
        )

# ==========================================
# 8. APP STARTUP
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

    logging.info("🚀 SabKraftTech Editor AI Bot Running...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
