import os
import json
import re
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from flask import Flask

from telegram import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    Update, 
    ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
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
    logging.error(f"Gemini Config Error: {e}")
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
# 3. BOT CONFIG, MAINTENANCE & BUTTON LAYOUTS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1391169804"))
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"maintenance": False}
    return {"maintenance": False}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Config save error: {e}")

bot_config = load_config()

def is_maintenance():
    return bot_config.get("maintenance", False)

OFFICIAL_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("📢 Telegram Channel", url="https://t.me/SabKraftTech")],
    [InlineKeyboardButton("👥 Telegram Group", url="https://t.me/TeamSabKraftTech")],
    [InlineKeyboardButton("▶️ YouTube Channel", url="https://youtube.com/@sabkrafttech?si=BvFSMTysyXScxEj2")],
    [InlineKeyboardButton("📸 Instagram ID", url="https://instagram.com/sabkrafttech")]
])

MATERIAL_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("📦 Explore Materials & APKs in Channel", url="https://t.me/SabKraftTech")]
])

def parse_custom_buttons(button_type, button_text=None, button_url=None):
    keyboard = []
    if button_type == "official":
        return OFFICIAL_BUTTONS
    elif button_type == "material":
        return MATERIAL_BUTTONS
    elif button_type == "youtube":
        return InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Watch on YouTube", url="https://youtube.com/@sabkrafttech?si=BvFSMTysyXScxEj2")]])
    elif button_type == "instagram":
        return InlineKeyboardMarkup([[InlineKeyboardButton("📸 Instagram ID", url="https://instagram.com/sabkrafttech")]])
    elif button_type == "telegram":
        return InlineKeyboardMarkup([[InlineKeyboardButton("📢 Telegram Channel", url="https://t.me/SabKraftTech")]])
    elif button_type == "url" and button_text and button_url:
        keyboard.append([InlineKeyboardButton(button_text, url=button_url)])
    elif button_type == "custom" and button_text:
        keyboard.append([InlineKeyboardButton(button_text, callback_data="custom_btn")])
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

# ==========================================
# 4. TARGET RESOLVER (REPLY + USERNAME TAG)
# ==========================================
async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    
    args = context.args
    if args and args[0].startswith("@"):
        return args[0] # Returns @username string
    return None

def extract_user_tag(user) -> str:
    if not user:
        return "Creator"
    if isinstance(user, str):
        return user
    if hasattr(user, "username") and user.username:
        return f"@{user.username}"
    if hasattr(user, "first_name"):
        full_name = f"{user.first_name} {user.last_name}".strip() if getattr(user, "last_name", None) else user.first_name
        return f"[{full_name}](tg://user?id={user.id})"
    return str(user)

# ==========================================
# 5. DYNAMIC JSON FILTER MANAGEMENT
# ==========================================
FILTERS_FILE = "filters.json"

def load_filters_db():
    if os.path.exists(FILTERS_FILE):
        try:
            with open(FILTERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_filters_db(filters_dict):
    try:
        with open(FILTERS_FILE, "w", encoding="utf-8") as f:
            json.dump(filters_dict, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logging.error(f"Filter save error: {e}")
        return False

db_filters = load_filters_db()
# ==========================================
# 6. SELECTIVE TRANSLATION & AI FALLBACK
# ==========================================
async def get_ai_response(user_text: str, user_name: str) -> str:
    if not ai_model:
        return f"✨ **Hey {user_name}!** SabKraftTech Editor Community mein aapka swagat hai. Aaj konse project ya editing asset mein support chahiye?"

    system_prompt = f"""
    You are 'SabKraftTech AI' — an expert Mobile Video Editor, Graphic Designer, Cinematic Documentary Creator, and Freelance Creator Assistant.

    CORE BEHAVIOR RULES:
    1. USER CONTEXT: Speaking with '{user_name}'.
    2. VOICE & TONE: Professional, warm, highly encouraging, and helpful.
    3. LANGUAGE & TRANSLATION:
       - Respond directly and concisely to the query.
       - IF the user asks in English, Urdu, or Devnagri Hindi with a multi-word or complex query, generate the main response AND append a distinct line at the bottom with premium emojis containing the Hinglish (Roman Hindi) translation/summary:
         "✨ **Hinglish:** <translation in Roman Hindi>"
       - If the user uses standard greetings (Hi, Hello, Jumma Mubarak, Assalamu Alaikum), reply with authentic respectful greetings directly.
    4. FORMATTING: Clean line breaks, bullet points, short (2-3 lines max).

    Member Message: "{user_text}"
    Give a natural, aesthetic reply:
    """

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: ai_model.generate_content(system_prompt))
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini AI Exception: {e}")
        return f"✨ **Hey {user_name}!**\n\nSabKraftTech community mein aapka swagat hai! Bataiye aaj konse editing asset ya query mein help chahiye?"

# ==========================================
# 7. UTILITY & MAINTENANCE COMMANDS
# ==========================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📖 **SabKraftTech Bot Help Menu:**\n\n• `¥addfilter` - Naya filter add karein\n• `¥delfilter` - Filter delete karein\n• `¥filters` - Sabhi filters ki list dekhein\n• `¥maintenance on/off` - Maintenance mode switch\n• Moderation: `¥warn`, `¥mute`, `¥unmute`, `¥ban`, `¥kick`, `¥tban`, `¥unban` (Reply ya @tag karke)", parse_mode="Markdown")

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛠️ Support ke liye channel ya admin se sampark karein: @Sabkrafttechh")

async def welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 SabKraftTech mein aapka khairmakhdam hai! 🌙")

async def problem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ Agar aapko koi bhi problem aa rahi hai, toh turant detail mein group mein message drop karein.")

async def maintenance_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "on" in text:
        bot_config["maintenance"] = True
        save_config(bot_config)
        await update.message.reply_text("🛠️ Maintenance Mode **ON** kar diya gaya hai. Abhi bot limited commands process karega.")
    elif "off" in text:
        bot_config["maintenance"] = False
        save_config(bot_config)
        await update.message.reply_text("🟢 Maintenance Mode **OFF** kar diya gaya hai. Bot normal mode par hai.")
    else:
        status = "ON" if is_maintenance() else "OFF"
        await update.message.reply_text(f"⚙️ Current Maintenance Mode status: **{status}**\nUse: `¥maintenance on` ya `¥maintenance off`", parse_mode="Markdown")

# ==========================================
# 8. ADVANCED ADMIN MODERATION SUITE (REPLY + TAG)
# ==========================================
async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❌ Kripya user ke message par reply karein ya @username likhein.")
        return
    target_tag = extract_user_tag(target)
    await update.message.reply_text(f"⚠️ Warning: {target_tag} ko warning di gayi hai! Rules break mat karein.")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_maintenance(): 
        await update.message.reply_text("🛠️ Bot abhi Maintenance Mode mein hai.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❌ Kripya user ke message par reply karein.")
        return
    await update.message.reply_text("🔇 User ko mute kar diya gaya hai.")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❌ Kripya user ke message par reply karein.")
        return
    await update.message.reply_text("🔊 User ka mute hata diya gaya hai.")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❌ Kripya user ke message par reply karein.")
        return
    try:
        if hasattr(target, "id"):
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)
            await update.message.reply_text(f"🦶 {target.first_name} ko group se kick kar diya gaya hai.")
        else:
            await update.message.reply_text(f"🦶 User {target} ko kick kiya gaya.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❌ Kripya user ke message par reply karein.")
        return
    try:
        if hasattr(target, "id"):
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await update.message.reply_text(f"🚫 {target.first_name} ko permanent ban kar diya gaya hai.")
        else:
            await update.message.reply_text(f"🚫 User {target} ko ban kiya gaya.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def tban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❌ Kripya user ke message par reply karein.")
        return
    await update.message.reply_text("⏳ User ko temporary ban kar diya gaya hai.")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("❌ Kripya user ke message par reply karein.")
        return
    try:
        if hasattr(target, "id"):
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)
            await update.message.reply_text("✅ User ka ban hata diya gaya hai.")
        else:
            await update.message.reply_text("✅ User ka ban hata diya gaya hai.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    # ==========================================
# 9. DYNAMIC FILTER MANAGEMENT COMMANDS
# ==========================================
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text[len("¥addfilter"):].strip()
    if "|" not in text:
        await update.message.reply_text("❌ Galat format! Use karein:\n¥addfilter keyword1, keyword2 | Line 1\nLine 2 text | Button Name - https://link.com ya material/youtube")
        return

    parts = text.split("|", 2)
    keywords = [k.strip().lower() for k in parts[0].split(",")]
    reply_text = parts[1] # Exact line breaks aur spacing preserve karega
    
    button_type = "none"
    button_text = None
    button_url = None

    if len(parts) > 2:
        btn_info = parts[2].strip()
        btn_info_lower = btn_info.lower()
        if btn_info_lower in ["material", "official", "youtube", "instagram", "telegram"]:
            button_type = btn_info_lower
        elif "-" in btn_info:
            b_name, b_url = btn_info.split("-", 1)
            button_type = "url"
            button_text = b_name.strip()
            button_url = b_url.strip()
        else:
            button_type = "custom"
            button_text = btn_info

    for kw in keywords:
        if kw:
            db_filters[kw] = {
                "reply": reply_text,
                "button_type": button_type,
                "button_text": button_text,
                "button_url": button_url
            }
    
    save_filters_db(db_filters)
    await update.message.reply_text(f"✅ Filter Successfully Add Ho Gaya!\n🔑 Keywords: {', '.join(keywords)}")

async def del_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text[len("¥delfilter"):].strip().lower()
    if not keyword:
        await update.message.reply_text("❌ Kripya delete karne ke liye keyword likhein. Jaise: ¥delfilter capcut")
        return

    if keyword in db_filters:
        del db_filters[keyword]
        save_filters_db(db_filters)
        await update.message.reply_text(f"🗑️ Filter '{keyword}' ko successfully delete kar diya gaya hai!")
    else:
        await update.message.reply_text(f"⚠️ '{keyword}' naam ka koi filter database mein nahi mila.")

async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db_filters:
        await update.message.reply_text("📂 Filhal group mein koi custom filter saved nahi hai.")
        return
    
    msg = "📋 **Active Filters List:**\n\n"
    for kw in db_filters.keys():
        msg += f"• `{kw}`\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ==========================================
# 10. AUTO-DELETE HELPER (300 SECONDS / 5 MINS)
# ==========================================
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# ==========================================
# 11. MESSAGE CHECKER & KEYWORD PARSER
# ==========================================
async def check_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if is_maintenance():
        return # Maintenance on hone par auto-filters pause rahenge

    msg_text = update.message.text.lower()
    user = update.message.from_user
    user_tag = f"@{user.username}" if user and user.username else (user.first_name if user else "Creator")

    for kw, data in db_filters.items():
        if kw in msg_text:
            formatted_reply = data["reply"].replace("{user_tag}", user_tag).replace("{username}", user_tag)
            
            b_type = data.get("button_type", "none")
            b_text = data.get("button_text")
            b_url = data.get("button_url")
            
            reply_markup = parse_custom_buttons(b_type, b_text, b_url)
            
            sent_message = await update.message.reply_text(formatted_reply, reply_markup=reply_markup, parse_mode="Markdown")
            
            if update.effective_chat.type in ["group", "supergroup"] and sent_message:
                asyncio.create_task(delete_message_after_delay(context, update.effective_chat.id, sent_message.message_id, 300))
            break
    else:
        # Fallback to AI if no filter matches
        if not update.message.text.startswith("¥") and not update.message.text.startswith("/"):
            ai_reply = await get_ai_response(update.message.text, user.first_name if user else "Creator")
            await update.message.reply_text(ai_reply, parse_mode="Markdown")

# ==========================================
# 12. APP STARTUP & HANDLER REGISTRATION
# ==========================================
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_TOKEN environment variable missing!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Filter Handlers
    application.add_handler(CommandHandler("addfilter", add_filter))
    application.add_handler(MessageHandler(filters.Regex(r"^¥addfilter"), add_filter))
    application.add_handler(MessageHandler(filters.Regex(r"^¥delfilter"), del_filter))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)filters"), list_filters))

    # Maintenance Handler
    application.add_handler(MessageHandler(filters.Regex(r"^¥maintenance"), maintenance_toggle))

    # Utility Commands
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)help"), help_command))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)support"), support_command))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)welcome"), welcome_command))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)problem"), problem_command))

    # Moderation Handlers (Reply & Tag)
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)warn"), warn_user))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)mute"), mute_user))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)unmute"), unmute_user))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)kick"), kick_user))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)ban"), ban_user))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)tban"), tban_user))
    application.add_handler(MessageHandler(filters.Regex(r"^(?:¥|/)unban"), unban_user))

    # Message Filter Checker & AI Fallback
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), check_filters))

    logging.info("🚀 SabKraftTech Pro AI Bot Running Successfully with All Features & Maintenance Mode...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
