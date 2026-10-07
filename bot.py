import os
import re
import asyncio
from flask import Flask
from threading import Thread
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- 1. FLASK WEB SERVER (Render 24/7 Keep-Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "SabKraftTech Smart Bot Active 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. GEMINI AI SETUP (SUPER SMART SYSTEM PROMPT) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
        system_instruction = (
            "You are SabKraftTech AI, a highly intelligent, polite, and helpful assistant for the SabKraftTech channel community. "
            "Your main expertise is video editing (CapCut, KineMaster, Alight Motion, XML presets, color grading, VFX, overlays), YouTube growth, and tech tips. "
            "However, you can accurately answer ANY question asked by the user (General Knowledge, Science, Everyday Chat, Advice, Coding, Tech, etc.). "
            "Always respond in natural, easy-to-understand Hinglish (Hindi written in Roman script). "
            "Keep answers direct, short, crisp, informative, engaging, and polite. Never refuse a genuine question."
        )
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)
        print("Gemini AI Initialized Successfully!")
    except Exception as e:
        print(f"Gemini Init Error: {e}")

# --- 3. CUSTOM KEYWORD FILTERS (File Delivery & Redirect) ---
CUSTOM_FILTERS = {
    "capcut": {
        "text": "📱 **CapCut Pro Latest Version**\n\nNeeche button par click karke direct download karein:",
        "btn_text": "📥 Download CapCut Pro",
        "url": "https://t.me/SabKraftTech"
    },
    "kinemaster": {
        "text": "🎬 **KineMaster Pro (No Watermark)**\n\nLatest Mod Version direct download link:",
        "btn_text": "📥 Download KineMaster Pro",
        "url": "https://t.me/SabKraftTech"
    },
    "alight motion": {
        "text": "⚡ **Alight Motion MOD APK**\n\nFull unlocked mod version download karne ke liye click karein:",
        "btn_text": "📥 Download Alight Motion",
        "url": "https://t.me/SabKraftTech"
    },
    "preset": {
        "text": "🎨 **SabKraftTech Presets & XML Materials**\n\nSabhi trending presets aur editing materials yahan available hain:",
        "btn_text": "📂 Open Material Channel",
        "url": "https://t.me/SabKraftTech"
    }
}

# --- 4. INSTANT GREETINGS WITH USER TAGGING ---
GREETINGS_DATA = [
    (["hi", "hello", "hey", "hlo"], "Hello {user}! Welcome to **SabKraftTech** ⚡ Kaise hain aap? Bataiye kya help chahiye?"),
    (["good morning", "gm"], "Good morning {user} from **SabKraftTech**! 🌅 Apka din bohot accha rahe!"),
    (["good night", "gn"], "Good night {user} from **SabKraftTech**! 🌙 Shubh ratri!"),
    (["assalamu alaikum", "assalam", "salam"], "Walaikum Assalam {user}! Welcome to **SabKraftTech** ⚡ Bataiye kya sewa karein?"),
    (["namaste", "pranam"], "Namaste {user}! **SabKraftTech** mein aapka swagat hai 🙏"),
    (["kaise ho", "how are you"], "Main bilkul badhiya hoon {user}! Aap batao, aaj kya edit kar rahe ho?")
]

# --- 5. AUTO-DELETE HELPER (10 Mins Clean Group) ---
async def delete_msg_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 600):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# --- 6. TELEGRAM MESSAGE HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **Welcome to SabKraftTech AI & Automation Bot!**\n\n"
        "• Editing Apps & Presets ke liye unka naam type karein (*CapCut*, *Preset*, *KineMaster*).\n"
        "• Koi bhi sawal ho — main har cheez ka smart response dunga!"
    )
    sent_msg = await update.message.reply_text(welcome_text, parse_mode='Markdown')
    if update.effective_chat.type != 'private':
        asyncio.create_task(delete_msg_after_delay(context, update.effective_chat.id, sent_msg.message_id, 600))
        asyncio.create_task(delete_msg_after_delay(context, update.effective_chat.id, update.message.message_id, 600))

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text
    user_text_lower = user_text.lower().strip()
    is_group = update.effective_chat.type != 'private'
    
    user_name = update.effective_user.first_name or "Friend"
    user_mention = f"@{update.effective_user.username}" if update.effective_user.username else f"[{user_name}](tg://user?id={update.effective_user.id})"
    bot_username = context.bot.username.lower() if context.bot.username else ""

    # --- FEATURE A: ANTI-SPAM LINK BLOCKER ---
    if is_group and re.search(r'(https?://|t\.me/|telegram\.me/)', user_text_lower):
        try:
            await update.message.delete()
            warn_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ {user_mention}, Group mein external links strictly allowed nahi hain!"
            )
            asyncio.create_task(delete_msg_after_delay(context, chat_id, warn_msg.message_id, 30))
            return
        except Exception:
            pass

    # --- FEATURE B: KEYWORD FILTERS (Download & Redirect Links) ---
    matched_key = None
    for key in CUSTOM_FILTERS:
        if key in user_text_lower:
            matched_key = key
            break

    if matched_key:
        filter_data = CUSTOM_FILTERS[matched_key]
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(text=filter_data["btn_text"], url=filter_data["url"])
        ]])
        reply_msg = await update.message.reply_text(
            text=filter_data["text"],
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        if is_group:
            asyncio.create_task(delete_msg_after_delay(context, chat_id, update.message.message_id, 600))
            asyncio.create_task(delete_msg_after_delay(context, chat_id, reply_msg.message_id, 600))
        return

    # --- FEATURE C: INSTANT GREETINGS WITH USER TAG ---
    for keywords, response_template in GREETINGS_DATA:
        if any(re.search(rf'\b{re.escape(k)}\b', user_text_lower) for k in keywords):
            greet_reply = response_template.format(user=user_mention)
            reply_msg = await update.message.reply_text(greet_reply, parse_mode='Markdown')
            if is_group:
                asyncio.create_task(delete_msg_after_delay(context, chat_id, update.message.message_id, 600))
                asyncio.create_task(delete_msg_after_delay(context, chat_id, reply_msg.message_id, 600))
            return

    # --- FEATURE D: GROUP SILENCE (Respond only when tagged/replied) ---
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    is_targeted = (bot_username and f"@{bot_username}" in user_text_lower) or ("sabkraft" in user_text_lower) or ("bot" in user_text_lower)

    if is_group and not (is_targeted or is_reply_to_bot):
        return

    # --- FEATURE E: GEMINI AI SMART ANSWER FOR ALL QUESTIONS ---
    await update.message.chat.send_action(action="typing")

    if model:
        try:
            prompt = f"User Name: {user_name}. Question: {user_text}"
            response = model.generate_content(prompt)
            
            if response and response.text:
                reply_text = response.text
            else:
                reply_text = f"Haan {user_mention}, main aapka sawaal samajh gaya. Bataiye main aapki kya help kar sakta hoon?"
        except Exception as err:
            print(f"Gemini API Execution Error: {err}")
            reply_text = f"Haan {user_mention}! Main aapki baat samajh gaya. Editing materials ke liye CapCut ya Preset write karein!"
    else:
        reply_text = "AI System configure nahi hua hai. Render Dashboard par GEMINI_API_KEY verify karein."

    ai_reply_msg = await update.message.reply_text(reply_text, parse_mode='Markdown')

    if is_group:
        asyncio.create_task(delete_msg_after_delay(context, chat_id, update.message.message_id, 600))
        asyncio.create_task(delete_msg_after_delay(context, chat_id, ai_reply_msg.message_id, 600))

# --- 7. MAIN RUNNER ---
if __name__ == '__main__':
    keep_alive()

    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN missing!")
        exit(1)

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))

    print("SabKraftTech Smart Bot Active...")
    application.run_polling()
