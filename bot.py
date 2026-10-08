import os
import logging
import threading
import re
from flask import Flask
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==========================================
# 1. LOGGING & SERVER SETUP
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

app = Flask(__name__)

@app.route("/")
def health():
    return "SabKraftTech Pure AI Bot is Running smoothly!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. API KEYS & GEMINI SETUP
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

def get_ai_model():
    if not GEMINI_KEY:
        logging.error("GEMINI_API_KEY missing!")
        return None
    try:
        genai.configure(api_key=GEMINI_KEY)
        generation_config = genai.types.GenerationConfig(
            temperature=0.9,
            top_p=0.95,
        )
        return genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
    except Exception as e:
        logging.error(f"Gemini Init Error: {e}")
        return None

ai_model = get_ai_model()

# ==========================================
# 3. ADVANCED AI PERSONA (DIMAAG)
# ==========================================
SYSTEM_PERSONA = (
    "You are SabKraftTech AI — an elite, smart, and friendly assistant created by Mohammad Sabit Javed for SabKraftTech.\n"
    "YOUR ROLE & BEHAVIOR:\n"
    "1. Respond to EVERY message in chats and groups naturally and smartly (no tagging required).\n"
    "2. Understand user moods, language (Hinglish/Hindi/English), and demands instantly.\n"
    "3. Handle all greetings gracefully: Assalamualaikum, Good Morning, Good Evening, Good Night, Good Day, Hi, Hello, etc.\n"
    "4. For editing queries, apps/APKs (CapCut, Alight Motion, KineMaster, VN, Pixellab), video editing tips, YouTube growth, or materials, guide them warmly and point them to the SabKraftTech Telegram channel (t.me/SabKraftTech).\n"
    "5. Keep responses short, punchy (1-2 lines), aesthetic, and filled with cool emojis (✨, 🚀, 💡, 🎬, 📱, 🤲, ❤️).\n"
    "6. NEVER repeat the exact same response. Make every reply fresh, dynamic, and human-like."
)

def extract_user_tag(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "Creator"
    return f"@{user.username}" if user.username else user.first_name

# ==========================================
# 4. MAIN MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_tag = extract_user_tag(update)
    user_text = update.message.text or update.message.caption or ""
    user_text_clean = user_text.strip()

    # Agar sirf image aayi hai bina text ke
    if not user_text_clean and update.message.photo:
        user_text_clean = "User shared an image. Acknowledge it nicely."

    if not user_text_clean and not update.message.photo:
        return

    # Prepare Dynamic AI Prompt
    dynamic_prompt = (
        f"{SYSTEM_PERSONA}\n\n"
        f"User Tag: {user_tag}\n"
        f"User Message: \"{user_text_clean}\"\n"
        f"SabKraftTech AI Response:"
    )

    reply_text = ""
    model = ai_model or get_ai_model()

    # AI Request
    try:
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}
            res = model.generate_content([dynamic_prompt, image_part])
        else:
            res = model.generate_content(dynamic_prompt)
            
        reply_text = res.text.strip()
    except Exception as e:
        logging.error(f"AI Generation Error: {e}")
        reply_text = f"✨ Hey {user_tag}! Sab kuch set hai, batayein kya help chahiye? 🚀"

    # Send Output with Official SabKraftTech Channel Button
    if reply_text:
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Telegram Channel", url="https://t.me/SabKraftTech"),
                InlineKeyboardButton("👥 Telegram Group", url="https://t.me/TeamSabKraftTech")
            ]
        ])
        
        try:
            await update.message.reply_text(reply_text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            try:
                await update.message.reply_text(reply_text, reply_markup=markup)
            except Exception:
                pass

# ==========================================
# 5. START APP
# ==========================================
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_TOKEN is missing!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Catch all messages (Text, Photos, etc.)
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    logging.info("🚀 SabKraftTech Pure AI Bot Started Successfully!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
