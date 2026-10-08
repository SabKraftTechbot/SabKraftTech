import asyncio
import json
import os
import re
import threading
from flask import Flask
import google.generativeai as genai
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
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
  return "SabKraftTech JSON-Driven AI Bot Active!", 200


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port, use_reloader=False)


# ==========================================
# 2. CONFIGURATION & BUTTONS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

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
# 3. GEMINI AI SETUP
# ==========================================
SYSTEM_INSTRUCTION = """
You are SabKraftTech AI Assistant — a smart, short-replying, Gen-Z digital partner for Video Editors, Designers, YouTubers, Freelancers, and Students.

CORE RULES:
1. ALWAYS TAG USER: Use the exact tag/name provided in context.
2. CRISP & SHORT: Max 2 to 3 short lines. No long lectures!
3. TECH HELP: Direct 2-step solution for CapCut, Alight Motion, PixelLab, XML, RPM/CTR, Photoshop, Canva.
4. TONE: Clean Hinglish (Latin script), bold highlights, smart emojis (✨, ⚡, 🎬, 🚀, 💡, 🎨).
"""


def get_gemini_model():
  if not GEMINI_KEY:
    return None
  try:
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
            model_name=m, system_instruction=SYSTEM_INSTRUCTION
        )
      except Exception:
        continue
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION
    )
  except Exception:
    return None


ai_model = get_gemini_model()


def get_user_tag(update: Update) -> str:
  user = update.effective_user
  if not user:
    return "Friend"
  if user.username:
    return f"@{user.username}"
  return f"[{user.first_name}](tg://user?id={user.id})"


# ==========================================
# 4. JSON CONFIG & FILTER READER
# ==========================================
def load_json_filters():
  if os.path.exists("filters.json"):
    try:
      with open("filters.json", "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception as e:
      print(f"Error loading filters.json: {e}")
  return {"button_triggers": [], "custom_rules": []}


def get_json_response(lower_text: str, user_tag: str):
  config = load_json_filters()
  rules = config.get("custom_rules", [])

  for rule in rules:
    keywords = rule.get("keywords", [])
    if any(kw in lower_text for kw in keywords):
      reply_template = rule.get("reply", "")
      return reply_template.replace("{user_tag}", user_tag)

  return None


# ==========================================
# 5. UNIFIED MESSAGE HANDLER
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

  # 1. Anti-Spam Link Blocker
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

  # 3. Dynamic Button Triggers from JSON
  config = load_json_filters()
  button_triggers = config.get(
      "button_triggers", ["sabkrafttech", "admin", "channel", "group"]
  )
  show_buttons = any(kw in lower_text for kw in button_triggers)

  reply_text = ""

  # 4. Check JSON Custom Filters First
  json_reply = get_json_response(lower_text, user_tag)
  if json_reply:
    reply_text = json_reply

  # 5. Vision AI (Screenshot Error Scan)
  elif update.message.photo:
    try:
      photo_file = await update.message.photo[-1].get_file()
      photo_bytes = await photo_file.download_as_bytearray()
      image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

      prompt = [
          (
              f"User Tag: {user_tag}\nContext: {user_text_clean or 'Is"
              " screenshot ko analyze karke short 2-step solution do.'}"
          ),
          image_part,
      ]
      if ai_model:
        res = ai_model.generate_content(prompt)
        reply_text = res.text
      else:
        reply_text = (
            f"✨ Hey {user_tag}! Screenshot scan filhaal busy hai. Problem text"
            " me batayein!"
        )
    except Exception:
      reply_text = f"✨ Hey {user_tag}! Problem text me likhkar poochein!"

  # 6. Gemini AI Fallback for Complex Queries
  elif user_text_clean:
    try:
      if ai_model:
        prompt = (
            f"User Tag: {user_tag}\nMessage Context & Query: {user_text_clean}"
        )
        res = ai_model.generate_content(prompt)
        reply_text = res.text
      else:
        reply_text = (
            f"✨ Hey {user_tag}! Batayein, aapki video editing ya channel me"
            " kya help chahiye?"
        )
    except Exception:
      reply_text = (
          f"✨ Hey {user_tag}! Batayein, aapki video editing ya channel me"
          " kya help chahiye?"
      )

  # 7. Send Final Message
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
  application.add_handler(
      MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
  )

  print("🚀 SabKraftTech JSON Filter Bot Active!")
  application.run_polling()


if __name__ == "__main__":
  main()
