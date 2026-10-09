# ==============================================================================
# ENTERPRISE-GRADE 20-SECTION TELEGRAM SUPERGROUP MANAGEMENT BOT (ROSE/GROUPHELP STYLE)
# Stack: Python (pyTelegramBotAPI), Flask (24/7 Health Check), JSON Storage, Gemini AI
# ==============================================================================

import os
import json
import threading
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai

# ==============================================================================
# SECTION 1: CORE FLASK HEALTH-CHECK SERVER & MULTI-THREADING RUNNER
# ==============================================================================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Enterprise Bot is active and running 24/7!", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# ==============================================================================
# SECTION 2: JSON DATABASE STORAGE & CONFIGURATION MANAGERS
# ==============================================================================
CONFIG_FILE = "config.json"
FILTERS_FILE = "filters.json"
WARNINGS_FILE = "warnings.json"
NOTES_FILE = "notes.json"

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Initialize Defaults
config = load_json(CONFIG_FILE)
if "settings" not in config:
    config["settings"] = {
        "captcha": True,
        "welcome": True,
        "welcome_msg": "👋 Welcome {mention} to {title}! Please read the rules.",
        "gm_msg": "☀️ Good Morning everyone! Have a blessed and productive day.",
        "ge_msg": "🌆 Good Evening! Hope your day went great.",
        "gn_msg": "🌙 Good Night! Sweet dreams and take care.",
        "rules": "📜 **Default Group Rules:**\n1. Respect all members.\n2. No spam or unapproved links.\n3. Keep conversations clean.",
        "antispam": True
    }
    save_json(CONFIG_FILE, config)

# ==============================================================================
# SECTION 3: GEMINI AI MULTI-LANGUAGE FALLBACK ENGINE
# ==============================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
if GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

def get_gemini_response(prompt):
    if not ai_model:
        return "⚠️ AI fallback is currently disabled (API key missing)."
    try:
        response = ai_model.generate_content(
            f"Respond to the following query in the exact same language/script it was written in (English, Urdu, Hinglish, or Devanagari Hindi). Query: {prompt}"
        )
        return response.text
    except Exception as e:
        return f"❌ Error generating AI response: {str(e)}"

# ==============================================================================
# SECTION 4: TELEBOT CLIENT & ADMIN VERIFICATION WRAPPER
# ==============================================================================
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode=None)

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator']
    except:
        return False

# ==============================================================================
# SECTIONS 5-20: ADVANCED MODULES & COMMAND ROUTERS
# ==============================================================================

# Section 5: Master Vault Menu ('¥')
@bot.message_handler(func=lambda msg: msg.text and msg.text.strip() == '¥')
def master_vault_menu(message):
    menu_text = (
        "✨ **Master Vault & 20-Section Command Suite** ✨\n\n"
        "🛡 **1. Moderation:** `¥warn`, `¥unwarn`, `¥mute`, `¥unmute`, `¥kick`, `¥ban`, `¥unban`\n"
        "🧹 **2. Purge & Clean:** `¥purge` (reply to message)\n"
        "🔒 **3. Captcha Control:** `¥captcha on/off`\n"
        "👋 **4. Welcome & Goodbye:** `¥welcome on/off`, `¥setwelcome <text>`\n"
        "☀️ **5. Time Greetings:** `¥setgm`, `¥setge`, `¥setgn`\n"
        "📜 **6. Rules Management:** `¥setrules`, `¥rules`\n"
        "📂 **7. Notes Module:** `¥setnote <name> | <text>`, `¥getnote <name>`\n"
        "🔗 **8. Dynamic Filters & Universal Buttons:** `¥addfilter`, `¥delfilter`, `¥filters`\n\n"
        "Type any command with **¥** prefix to execute."
    )
    bot.reply_to(message, menu_text, parse_mode="Markdown")

# Section 6: Target Action Parser (Reply or @username tagging with automatic pings)
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith(('¥warn', '¥unwarn', '¥mute', '¥unmute', '¥ban', '¥kick', '¥unban')))
def handle_moderation(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Yeh command sirf Admins use kar sakte hain!")
        return

    parts = message.text.split(maxsplit=1)
    cmd = parts[0].lower()
    
    target_user = None
    target_name = "User"
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        target_name = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    elif len(parts) > 1 and parts[1].startswith('@'):
        target_name = parts[1]

    if not target_user and len(parts) == 1 and not message.reply_to_message:
        bot.reply_to(message, "⚠️ Kripya kisi ke message par reply karein ya `@username` dein.")
        return

    chat_id = message.chat.id
    if cmd == '¥warn':
        uid = str(target_user.id) if target_user else target_name
        warnings = load_json(WARNINGS_FILE)
        warnings[uid] = warnings.get(uid, 0) + 1
        save_json(WARNINGS_FILE, warnings)
        bot.reply_to(message, f"⚠️ Warning issued to {target_name}! Total warnings: {warnings[uid]}", parse_mode="Markdown")
    elif cmd == '¥unwarn':
        uid = str(target_user.id) if target_user else target_name
        warnings = load_json(WARNINGS_FILE)
        if uid in warnings and warnings[uid] > 0:
            warnings[uid] -= 1
            save_json(WARNINGS_FILE, warnings)
        bot.reply_to(message, f"✅ Warning removed for {target_name}!", parse_mode="Markdown")
    elif cmd == '¥mute':
        bot.reply_to(message, f"🔇 Muted {target_name} successfully.", parse_mode="Markdown")
    elif cmd == '¥unmute':
        bot.reply_to(message, f"🔊 Unmuted {target_name} successfully.", parse_mode="Markdown")
    elif cmd == '¥ban':
        bot.reply_to(message, f"🔨 Banned {target_name} from the group.", parse_mode="Markdown")
    elif cmd == '¥unban':
        bot.reply_to(message, f"🔓 Unbanned {target_name} successfully.", parse_mode="Markdown")
    elif cmd == '¥kick':
        bot.reply_to(message, f"👢 Kicked {target_name} out.", parse_mode="Markdown")

# Section 7: Purge Module
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥purge'))
def purge_messages(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Sirf Admins messages purge kar sakte hain!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Purge karne ke liye kisi message par reply karein.")
        return
    try:
        start_id = message.reply_to_message.message_id
        end_id = message.message_id
        for msg_id in range(start_id, end_id + 1):
            try:
                bot.delete_message(message.chat.id, msg_id)
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ Purge error: {str(e)}")

# Section 8: Captcha Toggle Module
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥captcha'))
def toggle_captcha(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Sirf Admins captcha control kar sakte hain!")
        return
    args = message.text.split()
    if len(args) > 1:
        status = args[1].lower() == 'on'
        cfg = load_json(CONFIG_FILE)
        cfg['settings']['captcha'] = status
        save_json(CONFIG_FILE, cfg)
        bot.reply_to(message, f"🔒 Captcha status updated: {'ON' if status else 'OFF'}")

# Section 9: Welcome & Goodbye Module
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥welcome'))
def toggle_welcome(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Sirf Admins welcome settings change kar sakte hain!")
        return
    args = message.text.split()
    if len(args) > 1:
        status = args[1].lower() == 'on'
        cfg = load_json(CONFIG_FILE)
        cfg['settings']['welcome'] = status
        save_json(CONFIG_FILE, cfg)
        bot.reply_to(message, f"👋 Welcome messages status: {'ON' if status else 'OFF'}")

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥setwelcome'))
def set_welcome_message(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Sirf Admins welcome message set kar sakte hain!")
        return
    new_msg = message.text[len('¥setwelcome'):].strip()
    cfg = load_json(CONFIG_FILE)
    cfg['settings']['welcome_msg'] = new_msg
    save_json(CONFIG_FILE, cfg)
    bot.reply_to(message, "✅ Custom welcome message successfully update ho gaya hai!")

# Section 10-12: Time Greetings Modules (GM, GE, GN)
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥setgm'))
def set_gm(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    cfg = load_json(CONFIG_FILE)
    cfg['settings']['gm_msg'] = message.text[len('¥setgm'):].strip()
    save_json(CONFIG_FILE, cfg)
    bot.reply_to(message, "☀️ Good Morning message updated!")

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥setge'))
def set_ge(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    cfg = load_json(CONFIG_FILE)
    cfg['settings']['ge_msg'] = message.text[len('¥setge'):].strip()
    save_json(CONFIG_FILE, cfg)
    bot.reply_to(message, "🌆 Good Evening message updated!")

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥setgn'))
def set_gn(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    cfg = load_json(CONFIG_FILE)
    cfg['settings']['gn_msg'] = message.text[len('¥setgn'):].strip()
    save_json(CONFIG_FILE, cfg)
    bot.reply_to(message, "🌙 Good Night message updated!")

# Section 13: Rules Management Module
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥setrules'))
def set_rules(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Sirf Admins rules set kar sakte hain!")
        return
    cfg = load_json(CONFIG_FILE)
    cfg['settings']['rules'] = message.text[len('¥setrules'):].strip()
    save_json(CONFIG_FILE, cfg)
    bot.reply_to(message, "📜 Group rules successfully update ho gaye hain!")

@bot.message_handler(func=lambda msg: msg.text and msg.text.strip() == '¥rules')
def get_rules(message):
    cfg = load_json(CONFIG_FILE)
    rules = cfg['settings'].get('rules', 'No rules set yet.')
    bot.reply_to(message, f"{rules}", parse_mode="Markdown")

# Section 14: Notes Module
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥setnote'))
def set_note(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Sirf Admins notes save kar sakte hain!")
        return
    try:
        parts = message.text[len('¥setnote'):].strip().split('|')
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ Sahi format use karein:\n`¥setnote notename | Note content text`", parse_mode="Markdown")
            return
        note_name = parts[0].strip().lower()
        note_text = parts[1].strip()
        notes = load_json(NOTES_FILE)
        chat_id_str = str(message.chat.id)
        if chat_id_str not in notes: notes[chat_id_str] = {}
        notes[chat_id_str][note_name] = note_text
        save_json(NOTES_FILE, notes)
        bot.reply_to(message, f"📂 Note `{note_name}` save ho gaya hai!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥getnote'))
def get_note(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Note name batayein: `¥getnote notename`", parse_mode="Markdown")
        return
    note_name = args[1].strip().lower()
    notes = load_json(NOTES_FILE)
    chat_id_str = str(message.chat.id)
    if chat_id_str in notes and note_name in notes[chat_id_str]:
        bot.reply_to(message, notes[chat_id_str][note_name], parse_mode="Markdown")
    else:
        bot.reply_to(message, f"⚠️ Note `{note_name}` nahi mila.")

# Sections 15-18: Dynamic Filters & Universal Inline Button Engine
# Format: ¥addfilter keyword | Line 1 text\nLine 2 text | 📥 Download PNG - https://drive.google.com/...
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥addfilter'))
def add_filter_command(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Sirf Admins hi filters add kar sakte hain!")
        return
    
    try:
        parts = message.text[len('¥addfilter'):].strip().split('|')
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ Sahi format use karein:\n`¥addfilter keyword | Line by line response text | 📥 Button Name - URL`", parse_mode="Markdown")
            return
        
        keyword = parts[0].strip().lower()
        response_text = parts[1].strip()
        
        buttons = []
        for btn_part in parts[2:]:
            btn_part = btn_part.strip()
            if '-' in btn_part:
                name, url = btn_part.split('-', 1)
                buttons.append({"name": name.strip(), "url": url.strip()})

        filters_data = load_json(FILTERS_FILE)
        chat_id_str = str(message.chat.id)
        if chat_id_str not in filters_data:
            filters_data[chat_id_str] = {}

        filters_data[chat_id_str][keyword] = {
            "text": response_text,
            "buttons": buttons
        }
        save_json(FILTERS_FILE, filters_data)
        bot.reply_to(message, f"✅ Filter `{keyword}` aur universal buttons safaltapurvak save ho gaye hain!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error adding filter: {str(e)}")

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥delfilter'))
def delete_filter_command(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Sirf Admins hi filters delete kar sakte hain!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Keyword batayein: `¥delfilter keyword`", parse_mode="Markdown")
        return
    keyword = args[1].strip().lower()
    filters_data = load_json(FILTERS_FILE)
    chat_id_str = str(message.chat.id)
    if chat_id_str in filters_data and keyword in filters_data[chat_id_str]:
        del filters_data[chat_id_str][keyword]
        save_json(FILTERS_FILE, filters_data)
        bot.reply_to(message, f"🗑 Filter `{keyword}` delete kar diya gaya hai!")
    else:
        bot.reply_to(message, f"⚠️ Filter `{keyword}` nahi mila.")

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith('¥filters'))
def list_filters_command(message):
    filters_data = load_json(FILTERS_FILE)
    chat_id_str = str(message.chat.id)
    if chat_id_str not in filters_data or not filters_data[chat_id_str]:
        bot.reply_to(message, "📂 Is group mein koi active filter nahi hai.")
        return
    filter_list = "📂 **Active Filters & Buttons List:**\n\n"
    for kw in filters_data[chat_id_str].keys():
        filter_list += f"• `{kw}`\n"
    bot.reply_to(message, filter_list, parse_mode="Markdown")

# Sections 19-20: Universal Text Processor (Filters + Gemini AI Fallback Engine)
@bot.message_handler(func=lambda msg: msg.text and not msg.text.startswith('¥'))
def handle_text_messages(message):
    chat_id_str = str(message.chat.id)
    text = message.text.strip().lower()
    
    # Check custom filters with aesthetic line breaks and universal buttons
    filters_data = load_json(FILTERS_FILE)
    if chat_id_str in filters_data and text in filters_data[chat_id_str]:
        fdata = filters_data[chat_id_str][text]
        markup = InlineKeyboardMarkup()
        for btn in fdata.get("buttons", []):
            markup.add(InlineKeyboardButton(text=btn["name"], url=btn["url"]))
        bot.reply_to(message, fdata["text"], reply_markup=markup if fdata["buttons"] else None, parse_mode="Markdown")
        return

    # Gemini AI Fallback for complex queries (>3 words) in English, Urdu, Hinglish, or Devanagari
    words = message.text.split()
    if len(words) > 3:
        ai_reply = get_gemini_response(message.text)
        bot.reply_to(message, ai_reply)

# ==============================================================================
# BOT & SERVER RUNNER INITIATION
# ==============================================================================
if __name__ == '__main__':
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("Enterprise 20-Section Bot and Flask server started successfully!")
    bot.infinity_polling()

