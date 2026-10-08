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

# --- GEMINI AI INTEGRATION ---
try:
    import google.generativeai as genai
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
        # Using Gemini 1.5 Flash for high-speed & highly aesthetic response
        ai_model = genai.GenerativeModel("gemini-1.5-flash")
    else:
        ai_model = None
except Exception as e:
    ai_model = None

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
    return "SabKraftTech Ultra Smart AI Bot Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. BOT CONFIG & BUTTON LAYOUTS
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
# 3. DYNAMIC JSON CONFIG READER
# ==========================================
def load_filters():
    if os.path.exists("filters.json"):
        try:
            with open("filters.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("filters", [])
        except Exception as e:
            logging.error(f"Error reading filters.json: {e}")
    return []

def find_matching_filter(text_lower: str):
    filters_list = load_filters()
    for item in filters_list:
        keywords = item.get("keywords", [])
        for kw in keywords:
            pattern = r'\b' + re.escape(kw.lower().strip()) + r'\b'
            if re.search(pattern, text_lower):
                return item
    return None

def extract_user_tag(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "User"
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

# ==========================================
# 4. GEMINI REPLIT-STYLE AI RESPONSE GENERATOR
# ==========================================
async def get_ai_response(user_text: str, user_name: str) -> str:
    if not ai_model:
        return f"✨ Hey {user_name}! SabKraftTech AI me aapka swagat hai. Main aapki kya help kar sakta hoon?"

    system_prompt = f"""
    You are SabKraftTech AI, an ultra-smart, aesthetic, emotionally connective, and respectful assistant created for SabKraftTech channel (Founder: Sabit Ansari).
    
    GUIDELINES FOR YOUR RESPONSE:
    1. USER CONTEXT: The user's name is '{user_name}'. Address them naturally.
    2. LANGUAGE & SENTIMENT: Match the exact language/dialect (Hinglish, Urdu, Hindi, English) and tone of the user. Respect their religious greetings, cultural context, and emotions deeply.
    3. TONE & STYLE: Short, premium, aesthetic, to-the-point, highly supportive, no spam, formatted with clean bullet points or bold text.
    4. GREETINGS (Hi/Hello/Salam/Namaste): Briefly mention what they can get here (Editing assets, Pro APKs, High CTR Thumbnails, Scripting tips) and how to search.
    5. EMOTIONS (Sad/Breakup/Focus/Distraction/Alone): Provide deeply moving, human-like emotional support. Encourage them to channel their pain into editing skills & YouTube creation.
    6. NO ROBOTIC REPETITION: Make every response feel fresh, human, and custom-crafted like Replit AI. Never sound like a rigid script.
    
    User Query: "{user_text}"
    Respond in 2-4 short, ultra-aesthetic paragraphs/bullets:
    """
    
    try:
        response = await asyncio.to_thread(ai_model.generate_content, system_prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini AI Error: {e}")
        return f"✨ **Hey {user_name}!**\n\nSabKraftTech community me aapka swagat hai. Batayein aaj kis topic ya video project me aapko assistance chahiye?"

# ==========================================
# 5. AUTO-DELETE HELPER (300 SECONDS)
# ==========================================
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# ==========================================
# 6. CORE MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat = update.message.chat
    chat_type = chat.type
    is_group_or_channel = chat_type in ["group", "supergroup", "channel"]
    bot_username = context.bot.username or ""

    user_text = update.message.text or update.message.caption or ""
    if not user_text.strip():
        return

    user_text_clean = user_text.strip()
    lower_text = user_text_clean.lower()
    user_tag = extract_user_tag(update)
    user_name = update.effective_user.first_name if update.effective_user else "Creator"

    # A. LINK BLOCKER FOR GROUPS
    if is_group_or_channel and re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
        if "t.me/sabkrafttech" not in lower_text and "t.me/teamsabkrafttech" not in lower_text:
            try:
                await update.message.delete()
                return
            except Exception:
                pass

    # B. SPAM FILTER & MENTION CHECK FOR GROUPS
    is_tagged = (bot_username and f"@{bot_username}".lower() in lower_text) or (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )

    matched_filter = find_matching_filter(lower_text)

    # In Groups: Only reply when tagged OR when keyword filter matches
    if is_group_or_channel:
        is_forwarded = bool(update.message.forward_origin or update.message.forward_from_chat or update.message.forward_from)
        if is_forwarded and not is_tagged and not matched_filter:
            return
        if not is_tagged and not matched_filter:
            return

    # C. RESPONSE GENERATION
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
        # Fallback to AI Engine (Replit Style) when tagged or in DMs
        reply_text = await get_ai_response(user_text_clean, user_name)
        markup = None

    # Send Reply
    sent_message = None
    try:
        sent_message = await update.message.reply_text(reply_text, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        try:
            sent_message = await update.message.reply_text(reply_text, reply_markup=markup)
        except Exception:
            pass

    # D. AUTO-DELETE IN 5 MINS
    if sent_message and is_group_or_channel:
        asyncio.create_task(
            delete_message_after_delay(context, update.message.chat_id, sent_message.message_id, 300)
        )

# ==========================================
# 7. APP STARTUP
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

    logging.info("🚀 SabKraftTech Replit-Killer AI Bot Started...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
