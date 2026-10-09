import json
import os
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
# 3. BOT CONFIG & DEFAULT BUTTON LAYOUTS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1391169804"))

OFFICIAL_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("📢 Telegram Channel", url="https://t.me/SabKraftTech")],
    [InlineKeyboardButton("👥 Telegram Group", url="https://t.me/TeamSabKraftTech")],
    [InlineKeyboardButton("▶️ YouTube Channel", url="https://youtube.com/@sabkrafttech?si=BvFSMTysyXScxEj2")],
    [InlineKeyboardButton("📸 Instagram ID", url="https://instagram.com/sabkrafttech")]
])

MATERIAL_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("📦 Explore Materials & APKs in Channel", url="https://t.me/SabKraftTech")]
])

def parse_custom_buttons(button_data_list):
    if not button_data_list:
        return None
    keyboard = []
    for btn in button_data_list:
        if isinstance(btn, dict) and "text" in btn and "url" in btn:
            keyboard.append([InlineKeyboardButton(btn["text"], url=btn["url"])])
    return InlineKeyboardMarkup(keyboard) if keyboard else None

# ==========================================
# 4. SMART USER TAGGING HELPER
# ==========================================
def extract_user_tag(user) -> str:
    if not user:
        return "Creator"
    if user.username:
        return f"@{user.username}"
    full_name = f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name
    return f"[{full_name}](tg://user?id={user.id})"

# ==========================================
# 5. DYNAMIC JSON FILTER MANAGEMENT
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
        if not item.get("active", True):
            continue
        keywords = item.get("keywords", [])
        for kw in keywords:
            if match_keyword_smart(kw, text_lower):
                return item
    return None

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
# 7. VAULT & MASTER COMMAND HANDLERS
# ==========================================
PREFIXES = ["/", "¥"]

async def master_menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_tag = extract_user_tag(msg.from_user)
    
    menu_text = (
        f"⚡ **SabKraftTech Master Vault & Menu**\n"
        f"Suno {user_tag}, niche di gayi commands ka upyog karein:\n\n"
        f"¥welcome - Welcome greeting\n"
        f"¥help - Help & Support Center\n"
        f"¥support - Direct Support Desk\n"
        f"¥material - Editing Assets Vault\n"
        f"¥warn - Warn user (Admin Only)\n"
        f"¥mute / ¥unmute - Mute controls (Admin Only)\n"
        f"¥kick / ¥ban / ¥unban - Moderation actions (Admin Only)"
    )
    await msg.reply_text(menu_text, parse_mode="Markdown")

async def welcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_tag = extract_user_tag(msg.from_user)
    text = f"✨ Welcome {user_tag}! SabKraftTech mein swagat hai. Aaj Editing, Design, Apps ya YouTube Growth mein kis par discussion karein? 🚀"
    await msg.reply_text(text, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_tag = extract_user_tag(msg.from_user)
    text = f"🤝 Help & Support Desk: Pareshan mat ho {user_tag}, main yahan aapki har problem solve karne ke liye hoon! Apni query ya issue yahan drop karein, turant madad milegi. ⚡"
    await msg.reply_text(text, parse_mode="Markdown")

async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_tag = extract_user_tag(msg.from_user)
    text = f"🤝 Support Desk: {user_tag}, apni query ya technical problem yahan drop karein, humari team turant assist karegi! ⚡"
    await msg.reply_text(text, parse_mode="Markdown")

async def material_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_tag = extract_user_tag(msg.from_user)
    text = f"🎬 Material Vault: {user_tag}, in keywords ka use karein: `overlays`, `effects`, `transition`, `background`, `sfx`, `bgm`, `green screen`, `png`, `apng`. ⚡"
    await msg.reply_text(text, reply_markup=MATERIAL_BUTTONS, parse_mode="Markdown")

# ==========================================
# 8. ADVANCED ADMIN MODERATION SUITE
# ==========================================
async def check_admin_privileges(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private":
        return True
    if user.id == ADMIN_ID:
        return True
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in ["creator", "administrator"]

async def notify_user_punishment(context: ContextTypes.DEFAULT_TYPE, target_user, action_name: str, duration_str: str, reason: str, chat_title: str):
    dm_text = (
        f"⚠️ **SabKraftTech Security Alert:**\n\n"
        f"Aapko **{chat_title}** mein **{action_name}** kiya gaya hai.\n"
        f"⏱️ **Duration:** {duration_str}\n"
        f"📝 **Reason:** {reason}\n\n"
        f"Time period khatam hone par aap dubara group join kar sakte hain."
    )
    try:
        await context.bot.send_message(chat_id=target_user.id, text=dm_text, parse_mode="Markdown")
        return True
    except Exception:
        return False

async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    reply = msg.reply_to_message
    if not reply or not reply.from_user:
        await msg.reply_text("❌ Target user ke message par reply karke `¥warn` type karein.")
        return
    
    target = reply.from_user
    target_tag = extract_user_tag(target)
    reason = " ".join(context.args) if context.args else "Group rules violation"
    
    await msg.reply_text(
        f"⚠️ **Warning Issued!**\n\n"
        f"👤 **User:** {target_tag}\n"
        f"📝 **Reason:** {reason}\n"
        f"🚨 Kripya rules follow karein, otherwise strict action (Kick/Ban) liya jayega!",
        parse_mode="Markdown"
    )

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    reply = msg.reply_to_message
    if not reply or not reply.from_user:
        await msg.reply_text("❌ Target user ke message par reply karein.")
        return

    target = reply.from_user
    target_tag = extract_user_tag(target)
    reason = " ".join(context.args) if context.args else "Spamming / Rules violation"
    
    until_date = datetime.now() + timedelta(hours=24)
    permissions = ChatPermissions(can_send_messages=False)
    
    try:
        await context.bot.restrict_chat_member(msg.chat_id, target.id, permissions=permissions, until_date=until_date)
        await notify_user_punishment(context, target, "Mute 🔕", "24 Hours", reason, msg.chat.title)
        await msg.reply_text(f"🔕 {target_tag} ko **24 Hours** ke liye mute kar diya gaya hai.\n📝 **Reason:** {reason}", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    reply = msg.reply_to_message
    if not reply or not reply.from_user:
        await msg.reply_text("❌ Target user ke message par reply karein.")
        return

    target = reply.from_user
    target_tag = extract_user_tag(target)
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )
    try:
        await context.bot.restrict_chat_member(msg.chat_id, target.id, permissions=permissions)
        await msg.reply_text(f"🔔 {target_tag} ko unmute kar diya gaya hai!", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    reply = msg.reply_to_message
    if not reply or not reply.from_user:
        await msg.reply_text("❌ Target user ke message par reply karein.")
        return

    target = reply.from_user
    target_tag = extract_user_tag(target)
    reason = " ".join(context.args) if context.args else "Strict violation"
    until_date = datetime.now() + timedelta(days=7)

    try:
        await context.bot.ban_chat_member(msg.chat_id, target.id, until_date=until_date)
        await notify_user_punishment(context, target, "Ban 🚫", "1 Week (7 Days)", reason, msg.chat.title)
        await msg.reply_text(f"🚫 {target_tag} ko **1 Week (7 Days)** ke liye ban kar diya gaya hai.\n📝 **Reason:** {reason}", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    reply = msg.reply_to_message
    if not reply or not reply.from_user:
        await msg.reply_text("❌ Target user ke message par reply karein.")
        return

    target = reply.from_user
    target_tag = extract_user_tag(target)
    try:
        await context.bot.unban_chat_member(msg.chat_id, target.id, only_if_banned=True)
        await msg.reply_text(f"✅ {target_tag} ko unban kar diya gaya hai!", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    reply = msg.reply_to_message
    if not reply or not reply.from_user:
        await msg.reply_text("❌ Target user ke message par reply karein.")
        return

    target = reply.from_user
    target_tag = extract_user_tag(target)
    reason = " ".join(context.args) if context.args else "Kicked by Admin"

    try:
        await context.bot.ban_chat_member(msg.chat_id, target.id, until_date=datetime.now() + timedelta(days=7))
        await context.bot.unban_chat_member(msg.chat_id, target.id, only_if_banned=True)
        await notify_user_punishment(context, target, "Kick 🦶", "1 Week", reason, msg.chat.title)
        await msg.reply_text(f"🦶 {target_tag} ko group se kick kar diya gaya hai.\n📝 **Reason:** {reason}", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")
    # ==========================================
# 9. DYNAMIC FILTER ADMIN MANAGEMENT
# ==========================================
def is_admin(user_id: int) -> bool:
    if ADMIN_ID == 0:
        return True
    return user_id == ADMIN_ID

async def add_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_id = update.effective_user.id if update.effective_user else 0

    if not is_admin(user_id):
        await msg.reply_text("⛔ **Access Denied:** Sirf Admin hi filters modify kar sakta hai!")
        return

    reply_to = msg.reply_to_message
    file_id = None
    file_type = None

    if reply_to:
        if reply_to.document:
            file_id = reply_to.document.file_id
            file_type = "document"
        elif reply_to.photo:
            file_id = reply_to.photo[-1].file_id
            file_type = "photo"
        elif reply_to.video:
            file_id = reply_to.video.file_id
            file_type = "video"
        elif reply_to.audio:
            file_id = reply_to.audio.file_id
            file_type = "audio"

    text = " ".join(context.args)
    if "|" not in text and not file_id:
        help_text = (
            "❌ **Invalid Format!**\n\n"
            "**Text Filter Usage:**\n"
            "`/addfilter keyword1, keyword2 | Reply text here | button_type`\n\n"
            "**APK/File Filter Usage (Reply to any File/APK):**\n"
            "`/addfilter keyword1, keyword2 | Caption text here | material`"
        )
        await msg.reply_text(help_text, parse_mode="Markdown")
        return

    parts = text.split("|")
    raw_keywords = parts[0].strip().lower().split(",")
    keywords = [k.strip() for k in raw_keywords if k.strip()]
    
    reply_content = parts[1].strip() if len(parts) > 1 else (reply_to.caption if reply_to and reply_to.caption else "")
    button_type = parts[2].strip().lower() if len(parts) > 2 else "none"

    if button_type not in ["official", "material", "none"]:
        button_type = "none"

    filters_list = load_filters()
    
    updated = False
    for f_item in filters_list:
        existing_kws = [k.lower() for k in f_item.get("keywords", [])]
        if any(k in existing_kws for k in keywords):
            f_item["reply"] = reply_content
            f_item["button_type"] = button_type
            f_item["file_id"] = file_id
            f_item["file_type"] = file_type
            f_item["active"] = True
            for k in keywords:
                if k not in existing_kws:
                    f_item["keywords"].append(k)
            updated = True
            break

    if not updated:
        filters_list.append({
            "keywords": keywords,
            "reply": reply_content,
            "button_type": button_type,
            "file_id": file_id,
            "file_type": file_type,
            "active": True
        })

    if save_filters(filters_list):
        media_str = f" 📦 ({file_type.upper()} Attached)" if file_id else ""
        await msg.reply_text(
            f"✅ **Filter Saved/Modified Successfully!**{media_str}\n\n"
            f"🔑 **Keywords:** `{', '.join(keywords)}`\n"
            f"💬 **Reply:**\n{reply_content}\n\n"
            f"🔘 **Button:** `{button_type}`",
            parse_mode="Markdown"
        )
    else:
        await msg.reply_text("❌ Filter save karne mein error aaya.")

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
        has_file = "📦 FILE" if f_item.get("file_id") else "📝 TEXT"
        out += f"{idx}. {status} [{has_file}] `{kws}` | Button: `{btn}`\n"

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
# 10. AUTO-DELETE HELPER (300 SECONDS / 5 MINS)
# ==========================================
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# ==========================================
# 11. CORE MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    chat = msg.chat
    chat_type = chat.type
    is_group = chat_type in ["group", "supergroup"]

    if getattr(msg, "is_automatic_forward", False) or getattr(msg, "forward_origin", None) or getattr(msg, "forward_from_chat", None):
        return

    if msg.sender_chat and msg.sender_chat.id != chat.id:
        return

    if msg.from_user and msg.from_user.is_bot:
        return

    user_text = msg.text or msg.caption or ""
    if not user_text.strip():
        return

    user_text_clean = user_text.strip()
    lower_text = user_text_clean.lower()
    user_tag = extract_user_tag(msg.from_user)
    user_name = msg.from_user.first_name if msg.from_user else "Creator"

    if is_group and re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
        if "t.me/sabkrafttech" not in lower_text and "t.me/teamsabkrafttech" not in lower_text:
            try:
                await msg.delete()
                return
            except Exception:
                pass

    matched_filter = find_matching_filter(lower_text)
    sent_message = None

    if matched_filter:
        raw_reply = matched_filter.get("reply", "")
        reply_text = raw_reply.replace("{user_tag}", user_tag).replace("{username}", user_tag)
        btn_type = matched_filter.get("button_type", "none")
        
        file_id = matched_filter.get("file_id")
        file_type = matched_filter.get("file_type")

        markup = None
        if btn_type == "official":
            markup = OFFICIAL_BUTTONS
        elif btn_type == "material":
            markup = MATERIAL_BUTTONS
        elif isinstance(matched_filter.get("custom_buttons"), list):
            markup = parse_custom_buttons(matched_filter.get("custom_buttons"))

        if file_id:
            try:
                if file_type == "document":
                    sent_message = await msg.reply_document(document=file_id, caption=reply_text, reply_markup=markup, parse_mode="Markdown")
                elif file_type == "photo":
                    sent_message = await msg.reply_photo(photo=file_id, caption=reply_text, reply_markup=markup, parse_mode="Markdown")
                elif file_type == "video":
                    sent_message = await msg.reply_video(video=file_id, caption=reply_text, reply_markup=markup, parse_mode="Markdown")
            except Exception as e:
                logging.warning(f"Media send fallback: {e}")
                sent_message = await msg.reply_text(reply_text, reply_markup=markup)
        else:
            try:
                sent_message = await msg.reply_text(reply_text, reply_markup=markup, parse_mode="Markdown")
            except Exception:
                sent_message = await msg.reply_text(reply_text, reply_markup=markup)
    else:
        reply_text = await get_ai_response(user_text_clean, user_name)
        try:
            sent_message = await msg.reply_text(reply_text, parse_mode="Markdown")
        except Exception:
            sent_message = await msg.reply_text(reply_text)

    if sent_message and is_group:
        asyncio.create_task(
            delete_message_after_delay(context, msg.chat_id, sent_message.message_id, 300)
        )

# ==========================================
# 12. APP STARTUP & HANDLER REGISTRATION
# ==========================================
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_TOKEN environment variable missing!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(MessageHandler(filters.Regex(r'^¥$'), master_menu_cmd))
    
    application.add_handler(CommandHandler("welcome", welcome_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("help", help_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("support", support_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("material", material_cmd, prefixes=PREFIXES))

    application.add_handler(CommandHandler("warn", warn_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("mute", mute_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("silent", mute_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("unmute", unmute_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("unsilent", unmute_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("ban", ban_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("tban", ban_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("unban", unban_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("kick", kick_cmd, prefixes=PREFIXES))

    application.add_handler(CommandHandler("addfilter", add_filter_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("removefilter", remove_filter_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("togglefilter", toggle_filter_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("listfilters", list_filters_cmd, prefixes=PREFIXES))
    application.add_handler(CommandHandler("clearfilters", clear_filters_cmd, prefixes=PREFIXES))

    all_group_messages_filter = ~filters.COMMAND & ~filters.StatusUpdate.ALL
    application.add_handler(MessageHandler(all_group_messages_filter, handle_message))

    logging.info("🚀 SabKraftTech Pro AI Bot Running with Master Vault & Moderation Controls...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
