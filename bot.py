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

# --- 2. GEMINI AI SETUP WITH SYSTEM INSTRUCTION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # AI Context: SabKraftTech Community Purpose & Short Professional Answers
    system_instruction = (
        "You are the official AI Assistant of SabKraftTech. "
        "SabKraftTech is a premium community/channel for video editing, tech tips, software assets, presets, and mobile editing tutorials. "
        "Always reply in short, crisp, highly professional Hinglish/Hindi. "
        "Never write extremely long paragraphs. Keep answers direct and helpful."
    )
    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)
else:
    model = None

# --- 3. CUSTOM KEYWORD FILTERS (Assets & Material Delivery) ---
CUSTOM_FILTERS = {
    "capcut": {
        "text": "📱 **CapCut Pro Latest Version**\n\nNeeche button par click karke direct download karein:",
        "btn_text": "📥 Download CapCut Pro",
        "url": "https://t.me/SabKraftTech"
    },
    "kinemaster": {
        "text": "🎬 **KineMaster Pro (No Watermark)**\n\nDownload link yahan available hai:",
        "btn_text": "📥 Download KineMaster",
        "url": "https://t.me/SabKraftTech"
    },
    "alight motion": {
        "text": "⚡ **Alight Motion MOD APK**\n\nLatest Mod Version yahan se download karein:",
        "btn_text": "📥 Download Alight Motion",
        "url": "https://t.me/SabKraftTech"
    },
    "preset": {
        "text": "🎨 **SabKraftTech Trending Presets & Assets**\n\nSare editing materials hamare official channel par milenge:",
        "btn_text": "📂 Open Material Channel",
        "url": "https://t.me/SabKraftTech"
    }
}

GREETINGS = ["hi", "hello", "hey", "good morning", "good night", "good evening", "gm", "gn", "hlo", "ram ram", "assalamu alaikum"]

# --- 4. AUTO-DELETE HELPER (Clean Group Logic - 10 Mins) ---
async def delete_msg_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 600):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# --- 5. TELEGRAM HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **Welcome to SabKraftTech AI & Automation Bot!**\n\n"
        "• Editing material chahiye toh naam type karein (e.g., *CapCut*, *Preset*).\n"
        "• SabKraftTech ya tech assistance ke liye koi bhi sawaal poochhein!"
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

    # --- FEATURE A: ANTI-SPAM (External Link Protection) ---
    if re.search(r'(https?://|t\.me/|telegram\.me/)', user_text_lower):
        try:
            await update.message.delete()
            warn_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ {user_mention}, Group mein external links strictly prohibited hain!"
            )
            asyncio.create_task(delete_msg_after_delay(context, chat_id, warn_msg.message_id, 30))
            return
        except Exception:
            pass

    # --- FEATURE B: KEYWORD FILTER (Software & Materials) ---
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

    # --- FEATURE C: SMART GREETINGS WITH USER TAG ---
    is_greeting = any(re.search(rf'\b{g}\b', user_text_lower) for g in GREETINGS)
    if is_greeting and len(user_text.split()) <= 4:
        if "morning" in user_text_lower or "gm" in user_text_lower:
            greet_reply = f"Good morning {user_mention} from **SabKraftTech**! 🌅 Have a productive day!"
        elif "night" in user_text_lower or "gn" in user_text_lower:
            greet_reply = f"Good night {user_mention} from **SabKraftTech**! 🌙 Sweet dreams!"
        else:
            greet_reply = f"Hello {user_mention}! Welcome from **SabKraftTech** ⚡ Aapki kya help kar sakta hoon?"

        reply_msg = await update.message.reply_text(greet_reply, parse_mode='Markdown')
        if is_group:
            asyncio.create_task(delete_msg_after_delay(context, chat_id, update.message.message_id, 600))
            asyncio.create_task(delete_msg_after_delay(context, chat_id, reply_msg.message_id, 600))
        return

    # --- FEATURE D: GROUP INTELLIGENCE (Smart Selective Response) ---
    # Group me bot TABHI reply karega jab SabKraftTech ka zikr ho ya Bot ko message target kiya jaye
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    is_targeted = (bot_username and f"@{bot_username}" in user_text_lower) or ("sabkraft" in user_text_lower) or ("bot" in user_text_lower)

    if is_group and not (is_targeted or is_reply_to_bot):
        # Members aapas me baat kar rahe hain -> Bot silent rahega
        return

    # --- FEATURE E: GEMINI AI SHORT PROFESSIONAL REPLY ---
    await update.message.chat.send_action(action="typing")

    prompt = f"User name: {user_name}. Question/Message: {user_text}"
    if model:
        try:
            response = model.generate_content(prompt)
            reply_text = response.text
        except Exception:
            reply_text = "Maaf kijiyega, filhal AI assist karne mein samarth nahi hai."
    else:
        reply_text = "GEMINI_API_KEY is missing."

    ai_reply_msg = await update.message.reply_text(reply_text, parse_mode='Markdown')

    if is_group:
        asyncio.create_task(delete_msg_after_delay(context, chat_id, update.message.message_id, 600))
        asyncio.create_task(delete_msg_after_delay(context, chat_id, ai_reply_msg.message_id, 600))

# --- 6. MAIN RUNNER ---
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
          
