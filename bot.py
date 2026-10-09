# ==============================================================
# SABKRAFTTECH PRO AI BOT - FINAL COMPLETE SOURCE CODE
# ==============================================================

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
# Admin ID set karein (Environment Variable ya direct ID)
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

# ==========================================
# 4. SMART USER TAGGING & TARGETING HELPER
# ==========================================
def get_target_user(msg):
    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user
    return msg.from_user

def extract_user_tag(user) -> str:
    if not user:
        return "User"
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
       - If the user uses standard greetings, reply with authentic respectful greetings directly.
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
# 7. ADVANCED ADMIN MODERATION SUITE
# ==========================================
async def check_admin_privileges(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private":
        return True
    if user.id == ADMIN_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ["creator", "administrator"]
    except Exception:
        return False

async def notify_user_punishment(context: ContextTypes.DEFAULT_TYPE, target_user, action_name: str, duration_str: str, reason: str, chat_title: str):
    if not hasattr(target_user, "id"):
        return False
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
    target = get_target_user(msg)
    target_tag = extract_user_tag(target)
    raw_args = context.args if context.args else (msg.text.split()[1:] if msg.text else [])
    reason = " ".join(raw_args) if raw_args else "Group rules violation"
    await msg.reply_text(f"⚠️ **Warning Issued!**\n\n👤 **Target User:** {target_tag}\n📝 **Reason:** {reason}\n🚨 Kripya rules follow karein!", parse_mode="Markdown")

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    target = get_target_user(msg)
    target_tag = extract_user_tag(target)
    raw_args = context.args if context.args else (msg.text.split()[1:] if msg.text else [])
    reason = " ".join(raw_args) if raw_args else "Spamming / Rules violation"
    until_date = datetime.now() + timedelta(hours=24)
    permissions = ChatPermissions(can_send_messages=False)
    try:
        if hasattr(target, "id"):
            await context.bot.restrict_chat_member(msg.chat_id, target.id, permissions=permissions, until_date=until_date)
            await notify_user_punishment(context, target, "Mute 🔕", "24 Hours", reason, msg.chat.title)
        await msg.reply_text(f"🔕 {target_tag} ko **24 Hours** ke liye mute kar diya gaya hai.\n📝 **Reason:** {reason}", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    target = get_target_user(msg)
    target_tag = extract_user_tag(target)
    permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
    try:
        if hasattr(target, "id"):
            await context.bot.restrict_chat_member(msg.chat_id, target.id, permissions=permissions)
        await msg.reply_text(f"🔔 {target_tag} ko unmute kar diya gaya hai!", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    target = get_target_user(msg)
    target_tag = extract_user_tag(target)
    raw_args = context.args if context.args else (msg.text.split()[1:] if msg.text else [])
    reason = " ".join(raw_args) if raw_args else "Strict violation"
    until_date = datetime.now() + timedelta(days=7)
    try:
        if hasattr(target, "id"):
            await context.bot.ban_chat_member(msg.chat_id, target.id, until_date=until_date)
            await notify_user_punishment(context, target, "Ban 🚫", "1 Week", reason, msg.chat.title)
        await msg.reply_text(f"🚫 {target_tag} ko **1 Week** ke liye ban kar diya gaya hai.\n📝 **Reason:** {reason}", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    target = get_target_user(msg)
    target_tag = extract_user_tag(target)
    try:
        if hasattr(target, "id"):
            await context.bot.unban_chat_member(msg.chat_id, target.id, only_if_banned=True)
        await msg.reply_text(f"✅ {target_tag} ko unban kar diya gaya hai!", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_privileges(update, context):
        return
    msg = update.effective_message
    target = get_target_user(msg)
    target_tag = extract_user_tag(target)
    raw_args = context.args if context.args else (msg.text.split()[1:] if msg.text else [])
    reason = " ".join(raw_args) if raw_args else "Kicked by Admin"
    try:
        if hasattr(target, "id"):
            await context.bot.ban_chat_member(msg.chat_id, target.id, until_date=datetime.now() + timedelta(days=1))
            await context.bot.unban_chat_member(msg.chat_id, target.id, only_if_banned=True)
            await notify_user_punishment(context, target, "Kick 🦶", "Temporary", reason, msg.chat.title)
        await msg.reply_text(f"🦶 {target_tag} ko group se kick kar diya gaya hai.\n📝 **Reason:** {reason}", parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Action failed: {e}")


# ==========================================
# 8. MASTER MENU & QUICK COMMANDS
# ==========================================
async def master_menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_user = get_target_user(msg)
    user_tag = extract_user_tag(target_user)
    menu_text = (
        f"⚡ **SabKraftTech Master Vault & Menu**\n"
        f"Suno {user_tag}, niche di gayi commands ka upyog karein:\n\n"
        f"¥welcome - Welcome greeting\n"
        f"¥help - Help & Support Center\n"
        f"¥support - Direct Support Desk\n"
        f"¥material - Editing Assets Vault\n\n"
        f"📂 **Filter Management (Admin Only):**\n"
        f"¥addfilter keyword | text | button\n"
        f"¥removefilter keyword\n"
        f"¥togglefilter keyword\n"
        f"¥listfilters\n"
        f"¥clearfilters\n\n"
        f"🛡 **Moderation (Admin Only):**\n"
        f"¥warn, ¥mute, ¥unmute, ¥kick, ¥ban, ¥unban"
    )
    await msg.reply_text(menu_text, parse_mode="Markdown")

async def welcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_user = get_target_user(msg)
    user_tag = extract_user_tag(target_user)
    await msg.reply_text(f"✨ Welcome {user_tag}! SabKraftTech mein swagat hai. Aaj kis par discussion karein? 🚀", parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_user = get_target_user(msg)
    user_tag = extract_user_tag(target_user)
    await msg.reply_text(f"🤝 Help & Support Desk: Pareshan mat ho {user_tag}, main yahan aapki har problem solve karne ke liye hoon! ⚡", parse_mode="Markdown")

async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_user = get_target_user(msg)
    user_tag = extract_user_tag(target_user)
    await msg.reply_text(f"🤝 Support Desk: {user_tag}, apni query yahan drop karein, humari team turant assist karegi! ⚡", parse_mode="Markdown")

async def material_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target_user = get_target_user(msg)
    user_tag = extract_user_tag(target_user)
    await msg.reply_text(f"🎬 Material Vault: {user_tag}, in keywords ka use karein: `overlays`, `effects`, `png`, `apng`. ⚡", reply_markup=MATERIAL_BUTTONS, parse_mode="Markdown")

# ==========================================
# 9. FILTER MANAGEMENT (WITH EXACT SPACING & MEDIA)
# ==========================================
async def add_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not await check_admin_privileges(update, context):
        await msg.reply_text("⛔ **Access Denied:** Sirf Admin hi filters add kar sakta hai!")
        return

    reply_to = msg.reply_to_message
    file_id = None
    file_type = None

    if reply_to:
        if reply_to.document: 
            file_id, file_type = reply_to.document.file_id, "document"
        elif reply_to.photo: 
            file_id, file_type = reply_to.photo[-1].file_id, "photo"
        elif reply_to.video: 
            file_id, file_type = reply_to.video.file_id, "video"

    text_content = msg.text or msg.caption or ""
    parts_cmd = text_content.split(maxsplit=1)
    
    if len(parts_cmd) < 2 and not reply_to:
        await msg.reply_text("❌ **Usage:** `¥addfilter keyword1, keyword2 | Line 1 text\nLine 2 exact spacing | official`", parse_mode="Markdown")
        return

    query_body = parts_cmd[1] if len(parts_cmd) > 1 else ""
    parts = query_body.split("|")
    
    raw_keywords = parts[0].strip().lower().split(",")
    keywords = [k.strip() for k in raw_keywords if k.strip()]
    
    reply_content = parts[1].strip().replace("\\n", "\n") if len(parts) > 1 else (reply_to.caption if reply_to and reply_to.caption else "")
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
        media_status = f"\n📎 **Attached Media:** {file_type.capitalize()}" if file_id else ""
        await msg.reply_text(f"✅ **Filter Saved with Exact Spacing!**\n\n🔑 **Keywords:** `{', '.join(keywords)}`\n💬 **Reply:**\n{reply_content}{media_status}", parse_mode="Markdown")
    else:
        await msg.reply_text("❌ Error saving filter.")

async def remove_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not await check_admin_privileges(update, context):
        return
    raw_args = context.args if context.args else (msg.text.split()[1:] if msg.text else [])
    target_kw = " ".join(raw_args).strip().lower()
    filters_list = load_filters()
    new_list = [f for f in filters_list if target_kw not in [k.lower() for k in f.get("keywords", [])]]
    if len(new_list) < len(filters_list):
        save_filters(new_list)
        await msg.reply_text(f"🗑️ Filter `{target_kw}` deleted successfully!", parse_mode="Markdown")
    else:
        await msg.reply_text(f"⚠️ Filter `{target_kw}` nahi mila.", parse_mode="Markdown")

async def toggle_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not await check_admin_privileges(update, context):
        return
    raw_args = context.args if context.args else (msg.text.split()[1:] if msg.text else [])
    target_kw = " ".join(raw_args).strip().lower()
    filters_list = load_filters()
    found = False
    for f_item in filters_list:
        if target_kw in [k.lower() for k in f_item.get("keywords", [])]:
            f_item["active"] = not f_item.get("active", True)
            found = True
            status = "🟢 Active" if f_item["active"] else "🔴 Paused"
            break
    if found:
        save_filters(filters_list)
        await msg.reply_text(f"⚙️ Filter `{target_kw}` status: **{status}**", parse_mode="Markdown")
    else:
        await msg.reply_text(f"⚠️ Filter `{target_kw}` nahi mila.", parse_mode="Markdown")

async def list_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not await check_admin_privileges(update, context):
        return
    filters_list = load_filters()
    if not filters_list:
        await msg.reply_text("📁 Koi active filter nahi hai.")
        return
    out = "📋 **Configured Filters:**\n\n"
    for idx, f_item in enumerate(filters_list, 1):
        status = "🟢" if f_item.get("active", True) else "🔴"
        kws = ", ".join(f_item.get("keywords", []))
        media_tag = f" [Media: {f_item.get('file_type')}]" if f_item.get('file_id') else ""
        out += f"{idx}. {status} `{kws}`{media_tag}\n"
    await msg.reply_text(out, parse_mode="Markdown")

async def clear_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not await check_admin_privileges(update, context):
        return
    save_filters([])
    await msg.reply_text("🗑️ Saare custom filters clear kar diye gaye!")

# ==========================================
# 10. CORE MESSAGE HANDLER & AUTO-DELETE
# ==========================================
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text:
        return
    
    chat_type = msg.chat.type
    is_group = chat_type in ["group", "supergroup"]
    
    if msg.from_user and msg.from_user.is_bot:
        return

    user_text_clean = msg.text.strip()
    lower_text = user_text_clean.lower()
    target_user = get_target_user(msg)
    user_tag = extract_user_tag(target_user)
    user_name = target_user.first_name if target_user else "Creator"

    matched_filter = find_matching_filter(lower_text)
    sent_message = None

    if matched_filter:
        raw_reply = matched_filter.get("reply", "")
        reply_text = raw_reply.replace("{user_tag}", user_tag).replace("{username}", user_tag)
        
        btn_type = matched_filter.get("button_type", "none")
        markup = OFFICIAL_BUTTONS if btn_type == "official" else (MATERIAL_BUTTONS if btn_type == "material" else None)
        
        file_id = matched_filter.get("file_id")
        file_type = matched_filter.get("file_type")

        try:
            if file_id and file_type == "photo":
                sent_message = await msg.reply_photo(photo=file_id, caption=reply_text, reply_markup=markup, parse_mode="Markdown")
            elif file_id and file_type == "video":
                sent_message = await msg.reply_video(video=file_id, caption=reply_text, reply_markup=markup, parse_mode="Markdown")
            elif file_id and file_type == "document":
                sent_message = await msg.reply_document(document=file_id, caption=reply_text, reply_markup=markup, parse_mode="Markdown")
            else:
                sent_message = await msg.reply_text(reply_text, reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Filter send error: {e}")
            sent_message = await msg.reply_text(reply_text, reply_markup=markup)

    else:
        words = user_text_clean.split()
        if len(words) > 3:
            reply_text = await get_ai_response(user_text_clean, user_name)
            try:
                sent_message = await msg.reply_text(reply_text, parse_mode="Markdown")
            except Exception:
                sent_message = await msg.reply_text(reply_text)

    if sent_message and is_group:
        asyncio.create_task(delete_message_after_delay(context, msg.chat_id, sent_message.message_id, 300))

# ==========================================
# 11. MAIN RUNNER (Regex Handlers + Flask)
# ==========================================
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_BOT_TOKEN is missing from environment variables!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    def rx(pattern):
        return filters.Regex(re.compile(pattern, re.IGNORECASE))
    
    application.add_handler(MessageHandler(rx(r'^¥$'), master_menu_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]welcome(?:\s+|$)'), welcome_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]help(?:\s+|$)'), help_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]support(?:\s+|$)'), support_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]material(?:\s+|$)'), material_cmd))

    # Moderation Commands
    application.add_handler(MessageHandler(rx(r'^[/\¥]warn(?:\s+|$)'), warn_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥](mute|silent)(?:\s+|$)'), mute_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥](unmute|unsilent)(?:\s+|$)'), unmute_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥](ban|tban)(?:\s+|$)'), ban_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]unban(?:\s+|$)'), unban_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]kick(?:\s+|$)'), kick_cmd))

    # Filter Management Commands
    application.add_handler(MessageHandler(rx(r'^[/\¥]addfilter(?:\s+|$)'), add_filter_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]removefilter(?:\s+|$)'), remove_filter_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]togglefilter(?:\s+|$)'), toggle_filter_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]listfilters(?:\s+|$)'), list_filters_cmd))
    application.add_handler(MessageHandler(rx(r'^[/\¥]clearfilters(?:\s+|$)'), clear_filters_cmd))

    # General Message Handler for AI and Filters
    application.add_handler(MessageHandler(~filters.COMMAND & ~filters.StatusUpdate.ALL, handle_message))

    logging.info("🚀 SabKraftTech Pro AI Bot Running Successfully...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
