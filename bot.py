import asyncio
import os
import re
import threading
from flask import Flask
import google.generativeai as genai
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==========================================
# 1. FLASK WEB SERVER (24/7 FOR RENDER)
# ==========================================
app = Flask(__name__)


@app.route("/")
def home():
  return "SabKraftTech Dynamic AI Bot is Active!", 200


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port, use_reloader=False)


# ==========================================
# 2. CONFIGURATION & BUTTONS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

# Official Buttons (Sirf SabKraftTech ya Admin likhne par hi dikhenge)
MAIN_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            "📢 Telegram Channel", url="https://t.me/SabKraftTech"
        ),
        InlineKeyboardButton(
            "👥 Telegram Group", url="https://t.me/TeamSabKraftTech"
        ),
    ],
    [
        InlineKeyboardButton(
            "▶️ YouTube Channel",
            url="https://youtube.com/@sabkrafttech?si=BvFSMTysyXScxEj2",
        ),
        InlineKeyboardButton(
            "📸 Instagram ID", url="https://instagram.com/sabkrafttech"
        ),
    ],
])

# ==========================================
# 3. GEMINI AI SYSTEM INSTRUCTIONS
# ==========================================
SYSTEM_INSTRUCTION = """
You are SabKraftTech Official AI Assistant — an intellectual, short-replying, Gen-Z digital partner for Video Editors, Graphic Designers, YouTubers, Freelancers, and Students.

CORE RULES:
1. ALWAYS TAG USER: Address the user using their exact tag/name provided in context.
2. SHORT & CRISP: Maximum 2 to 3 short sentences or bullet points per response. No long lectures!
3. SPECIFIC GREETINGS RESPONSES:
   - Muslim (aslm, salam, ramzan, eid, etc.): Respond with respectful "Walaikum Assalam" / Mubarakbaad + Tag.
   - Hindu (namaste, jai shree ram, diwali, holi, etc.): Respond with respectful "Namaste" / Shubhkaamnayein + Tag.
   - Time-based (GM, GN, GE, Good Morning/Night/Evening): Respond specifically according to morning, evening, or night context + Tag.
   - Bye/Take Care: Send warm exit wishes + Tag.
4. DOMAIN HELP (APK, Video Editing, Graphics, YouTube, Tools):
   - Give direct, 2-step practical actionable short guide (CapCut, Alight Motion, PixelLab, XML, RPM/CTR, Photoshop).
5. MYSTERY OWNER RULE:
   - If asked who is owner/admin/created this: "Unhone identity reveal nahi ki hai! Baki main SabKraftTech AI hu."
6. TONE: Clean Hinglish (Latin script Hindi), bold key points, professional & aesthetic emojis (✨, ⚡, 🎬, 🚀, 💡, 🎨).
"""

LIVE_SYSTEM_PROMPT = SYSTEM_INSTRUCTION


def get_gemini_model():
  if not GEMINI_KEY:
    return None
  genai.configure(api_key=GEMINI_KEY)

  candidate_models = [
      "gemini-2.0-flash",
      "gemini-1.5-flash-latest",
      "gemini-1.5-flash",
      "gemini-1.5-pro",
  ]
  for m in candidate_models:
    try:
      return genai.GenerativeModel(
          model_name=m, system_instruction=LIVE_SYSTEM_PROMPT
      )
    except Exception:
      continue
  return genai.GenerativeModel(
      model_name="gemini-1.5-flash", system_instruction=LIVE_SYSTEM_PROMPT
  )


ai_model = get_gemini_model()


def get_user_tag(update: Update) -> str:
  user = update.effective_user
  if not user:
    return "Friend"
  if user.username:
    return f"@{user.username}"
  return f"[{user.first_name}](tg://user?id={user.id})"


# ==========================================
# 4. LIVE ADMIN COMMAND (/setprompt)
# ==========================================
async def set_prompt_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  global LIVE_SYSTEM_PROMPT, ai_model
  if ADMIN_ID != 0 and update.effective_user.id != ADMIN_ID:
    return

  new_prompt = " ".join(context.args)
  if not new_prompt:
    await update.message.reply_text(
        "⚠️ Usage: `/setprompt Naya prompt text`", parse_mode="Markdown"
    )
    return

  LIVE_SYSTEM_PROMPT = new_prompt
  ai_model = get_gemini_model()
  await update.message.reply_text(
      "✅ **AI Instruction Prompt Live Update Ho Gaya!**", parse_mode="Markdown"
  )


# ==========================================
# 5. MAIN UNIFIED MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not update.message:
    return

  chat_type = update.message.chat.type
  user_tag = get_user_tag(update)
  bot_username = context.bot.username or ""
  is_group = chat_type in ["group", "supergroup"]

  user_text = update.message.text or update.message.caption or ""
  user_text_clean = user_text.strip()
  lower_text = user_text_clean.lower()

  # 1. Anti-Spam Link Blocker (Group me)
  if is_group and user_text_clean:
    if re.search(r"http[s]?://|t\.me/|telegram\.me/", user_text_clean):
      try:
        await update.message.delete()
        return
      except Exception:
        pass

  # 2. Group Mention Check
  if is_group:
    is_tagged = (bot_username and f"@{bot_username}" in user_text_clean) or (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )
    if not is_tagged:
      return

  # 3. STRICT BUTTON TRIGGER CONDITION
  # Buttons SIRF TABHI AAYENGE jab user "sabkrafttech" ya "admin" ya official links puchega
  button_triggers = [
      "sabkrafttech",
      "admin",
      "malik",
      "owner",
      "channel",
      "group",
      "youtube",
      "instagram",
      "social",
      "links",
  ]
  show_buttons = any(kw in lower_text for kw in button_triggers)

  reply_text = ""

  # 4. Screenshot Error Processing (Vision AI)
  if update.message.photo:
    try:
      photo_file = await update.message.photo[-1].get_file()
      photo_bytes = await photo_file.download_as_bytearray()
      image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

      prompt = [
          (
              f"User Tag: {user_tag}\nContext: {user_text_clean or 'Is'}"
              " screenshot ko analyze karke short 2-step solution do."
          ),
          image_part,
      ]
      if ai_model:
        res = ai_model.generate_content(prompt)
        reply_text = res.text
    except Exception:
      reply_text = (
          f"✨ Hey {user_tag}! Screenshot scan me error aaya. Text me problem"
          " batayein!"
      )

  # 5. Smart Contextual Dynamic Text Response
  elif user_text_clean:
    try:
      if ai_model:
        prompt = (
            f"User Tag: {user_tag}\nMessage Context & Query: {user_text_clean}"
        )
        res = ai_model.generate_content(prompt)
        reply_text = res.text
      else:
        reply_text = f"✨ Hey {user_tag}! Batayein, aaj kya help karu?"
    except Exception:
      reply_text = f"✨ Hey {user_tag}! Batayein, aapki kya help kar sakta hu?"

  # 6. Send Response
  if reply_text:
    markup = MAIN_BUTTONS if show_buttons else None
    try:
      await update.message.reply_text(
          reply_text, reply_markup=markup, parse_mode="Markdown"
      )
    except Exception:
      await update.message.reply_text(reply_text, reply_markup=markup)


# ==========================================
# 6. BOT RUNNER
# ==========================================
def main():
  threading.Thread(target=run_flask, daemon=True).start()

  if not TELEGRAM_TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN missing!")
    return

  application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  application.add_handler(CommandHandler("setprompt", set_prompt_command))
  application.add_handler(
      MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
  )

  print("🚀 SabKraftTech Ultimate AI Bot Active!")
  application.run_polling()


if __name__ == "__main__":
  main()
        
