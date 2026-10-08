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
# 3. BOT CONFIG & BUTTON LAYOUTS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Set ADMIN_ID in your environment variables or paste your Telegram User ID here
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

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
# 4. DYNAMIC JSON FILTER MANAGEMENT
# ==========================================
FILTERS_FILE = "filters.json"

def load_filters():
    if os.path.exists(FILTERS_FILE):
        try:
            with open(FILTERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("filters", [])
        except Exception as e:
            logging.error(f"Error reading {FILTERS_FILE}: {e}")
            return []
    return []

def save_filters(filters_list):
    try:
        data = {"filters": filters_list}
        with open(FILTERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving {FILTERS_FILE}: {e}")
        return False

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
        # Check if filter is active (default is True)
        if not item.get("active", True):
            continue

        keywords = item.get("keywords", [])
        for kw in keywords:
            if match_keyword_smart(kw, text_lower):
                return item
    return None

def extract_user_tag(msg) -> str:
    user = msg.from_user if msg else None
    if not user:
        return "Creator"
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

# ==========================================
# 5. CREATOR & EDITOR PERSONA GEMINI AI
# ==========================================
async def get_ai_response(user_text: str, user_name: str) -> str:
    if not ai_model:
        return f"✨ **Hey {user_name}!** SabKraftTech Editor Community me aapka swagat hai. Aaj konse project ya editing asset me support chahiye?"

    system_prompt = f"""
    You are 'SabKraftTech AI' — an expert Mobile Video Editor, Graphic Designer, Cinematic Documentary Creator, and Freelance Creator Assistant for the SabKraftTech community.

    CORE BEHAVIOR & PERSONALITY RULES:
    1. USER CONTEXT: The member speaking is '{user_name}'.
    2. VOICE & TONE: Speak like an experienced, helpful Video Editor & Freelance Creator. Be warm, friendly, respectful, practical, and knowledgeable about YouTube growth, CTR, CapCut, KineMaster, Alight Motion, Photoshop, PixelLab, and mobile editing workflows.
    3. GREETINGS & RESPECT: 
       - If the user uses Islamic greetings (Assalamu Alaikum, Salam, Jumma Mubarak, Ramadan Mubarak, etc.), ALWAYS respond respectfully with authentic warm greetings like "Walaikum Assalam Warahmatullahi Wabarakatuh" or relevant blessings before addressing their query.
       - Keep traditional, festive, and everyday greetings authentic, polite, and welcoming.
    4. LANGUAGE: Match the user's language smoothly (Hinglish/Hindi/Urdu/English).
    5. FORMATTING: Clean formatting, aesthetic bullet points, short & engaging (2-3 brief lines or clean points). Avoid long lectures.

    Member Message: "{user_text}"
    Give a natural, aesthetic reply as a Pro Video Editor:
    """

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: ai_model.generate_content(system_prompt))
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini AI Exception: {e}")
        return f"✨ **Hey {user_name}!**\n\nSabKraftTech community me aapka swagat hai! Bataiye aaj konse editing asset ya query me help chahiye?"

# ==========================================
# 6. ADMIN COMMAND HANDLERS
# ==========================================
def is_admin(user_id: int) -> bool:
    if ADMIN_ID == 0:
        return True  # If ADMIN_ID is not configured, allows commands or logging alert
    return user_id == ADMIN_ID

async def add_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_id = update.effective_user.id if update.effective_user else 0

    if not is_admin(user_id):
        await msg.reply_text("⛔ **Access Denied:** Sirf Admin hi filters modify kar sakta hai!")
        return

    text = " ".join(context.args)
    if "|" not in text:
        help_text = (
            "❌ **Invalid Format!**\n\n"
            "**Usage:**\n"
            "`/addfilter keyword1, keyword2 | Reply text here | button_type`\n\n"
            "**Button Types:** `official`, `material`, `none`\n\n"
            "**Example:**\n"
            "`/addfilter capcut apk, capcut mod | 🎬 CapCut Pro APK Link: https://t.me/SabKraftTech/123 | material`"
        )
        await msg.reply_text(help_text, parse_mode="Markdown")
        return

    parts = text.split("|")
    raw_keywords = parts[0].strip().lower().split(",")
    keywords = [k.strip() for k in raw_keywords if k.strip()]
    reply_content = parts[1].strip()
    button_type = parts[2].strip().lower() if len(parts) > 2 else "none"

    if button_type not in ["official", "material", "none"]:
        button_type = "none"

    filters_list = load_filters()
    
    # Check if keyword group already exists to update it
    updated = False
    for f_item in filters_list:
        existing_kws = [k.lower() for k in f_item.get("keywords", [])]
        if any(k in existing_kws for k in keywords):
            f_item["reply"] = reply_content
            f_item["button_type"] = button_type
            f_item["active"] = True
            updated = True
            break

    if not updated:
        filters_list.append({
            "keywords": keywords,
            "reply": reply_content,
            "button_type": button_type,
            "active": True
        })

    if save_filters(filters_list):
        await msg.reply_text(
            f"✅ **Filter Saved Successfully!**\n\n"
            f"🔑 **Keywords:** `{', '.join(keywords)}`\n"
            f"💬 **Reply:** {reply_content}\n"
            f"🔘 **Button:** `{button_type}`",
            parse_mode="Markdown"
        )
    else:
        await msg.reply_text("❌ Filter save karne me error aaya.")

async def remove_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_id = update.effective_user.id if update.effective_user else 0

    if not is_admin(user_id):
        await msg.reply_text("⛔ **Access Denied!**")
        return

    target_kw = " ".join(context.args).strip().lower()
    if not target_kw:
        await msg.reply_text("❌ Usage: `/removefilter <keyword>`", parse_mode="Markdown")
        return

    filters_list = load_filters()
    initial_len = len(filters_list)

    new_list = [
        f for f in filters_list
        if target_kw not in [k.lower() for k in f.get("keywords", [])]
    ]

    if len(new_list) < initial_len:
        save_filters(new_list)
        await msg.reply_text(f"🗑️ Filter matching `{target_kw}` permanently deleted!", parse_mode="Markdown")
    else:
        await msg.reply_text(f"⚠️ `{target_kw}` keyword se juda koi filter nahi mila.", parse_mode="Markdown")

async def toggle_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_id = update.effective_user.id if update.effective_user else 0

    if not is_admin(user_id):
        await msg.reply_text("⛔ **Access Denied!**")
        return

    target_kw = " ".join(context.args).strip().lower()
    if not target_kw:
        await msg.reply_text("❌ Usage: `/togglefilter <keyword>`", parse_mode="Markdown")
        return

    filters_list = load_filters()
    found = False
    new_status_str = ""

    for f_item in filters_list:
        kws = [k.lower() for k in f_item.get("keywords", [])]
        if target_kw in kws:
            current_active = f_item.get("active", True)
            f_item["active"] = not current_active
            found = True
            new_status_str = "🟢 Active (Resumed)" if f_item["active"] else "🔴 Paused (Disabled)"
            break

    if found:
        save_filters(filters_list)
        await msg.reply_text(f"⚙️ Filter `{target_kw}` status updated: **{new_status_str}**", parse_mode="Markdown")
    else:
        await msg.reply_text(f"⚠️ `{target_kw}` keyword se koi filter nahi mil paaya.", parse_mode="Markdown")

async def list_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_id = update.effective_user.id if update.effective_user else 0

    if not is_admin(user_id):
        await msg.reply_text("⛔ **Access Denied!**")
        return

    filters_list = load_filters()
    if not filters_list:
        await msg.reply_text("📁 Currently koi filter configured nahi hai.")
        return

    out = "📋 **SabKraftTech Configured Filters:**\n\n"
    for idx, f_item in enumerate(filters_list, 1):
        status = "🟢" if f_item.get("active", True) else "🔴"
        kws = ", ".join(f_item.get("keywords", []))
        btn = f_item.get("button_type", "none")
        out += f"{idx}. {status} `{kws}` | Button: `{btn}`\n"

    await msg.reply_text(out, parse_mode="Markdown")

async def clear_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_id = update.effective_user.id if update.effective_user else 0

    if not is_admin(user_id):
        await msg.reply_text("⛔ **Access Denied!**")
        return

    if save_filters([]):
        await msg.reply_text("🗑️ Saare custom filters successfully clear kar diye gaye!")

# ==========================================
# 7. AUTO-DELETE HELPER (300 SECONDS)
# ==========================================
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# ==========================================
# 8. CORE MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    chat = msg.chat
    chat_type = chat.type
    is_group = chat_type in ["group", "supergroup"]

    # 🛑 1. IGNORE CHANNEL AUTOMATIC POSTS & FORWARDS
    if getattr(msg, "is_automatic_forward", False) or getattr(msg, "forward_origin", None) or getattr(msg, "forward_from_chat", None):
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

    # 🟢 5. RESPONSE GENERATION FOR REAL MEMBERS
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
        # Greetings / Complex Queries -> Pro Video Editor Gemini AI
        reply_text = await get_ai_response(user_text_clean, user_name)
        markup = None

    # Send Reply safely without crashing on Markdown parse errors
    sent_message = None
    try:
        sent_message = await msg.reply_text(reply_text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        logging.warning(f"Markdown failed, falling back to plain text: {e}")
        try:
            sent_message = await msg.reply_text(reply_text, reply_markup=markup)
        except Exception as err:
            logging.error(f"Failed to send message: {err}")

    # Auto-delete in 5 mins (Groups only)
    if sent_message and is_group:
        asyncio.create_task(
            delete_message_after_delay(context, msg.chat_id, sent_message.message_id, 300)
        )

# ==========================================
# 9. APP STARTUP
# ==========================================
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_TOKEN environment variable missing!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Register Admin Commands
    application.add_handler(CommandHandler("addfilter", add_filter_cmd))
    application.add_handler(CommandHandler("removefilter", remove_filter_cmd))
    application.add_handler(CommandHandler("togglefilter", toggle_filter_cmd))
    application.add_handler(CommandHandler("listfilters", list_filters_cmd))
    application.add_handler(CommandHandler("clearfilters", clear_filters_cmd))

    # Catch ALL non-command group events (Text, Photos, Captions, Documents)
    all_group_messages_filter = ~filters.COMMAND & ~filters.StatusUpdate.ALL
    application.add_handler(MessageHandler(all_group_messages_filter, handle_message))

    logging.info("🚀 SabKraftTech Permanent AI Bot Running with Admin Controls...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
