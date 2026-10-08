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
# 1. FLASK WEB SERVER (24/7 RENDER KEEP-ALIVE)
# ==========================================
app = Flask(__name__)


@app.route("/")
def health():
  return "SabKraftTech Ultimate Multi-Category AI Bot Active!", 200


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port, use_reloader=False)


# ==========================================
# 2. CONFIGURATION & DYNAMIC BUTTONS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Official Main Social Buttons
OFFICIAL_BUTTONS = InlineKeyboardMarkup([
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

# Direct Download / Editing Material Buttons
MATERIAL_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            "📦 Download Overlays & Effects", url="https://t.me/SabKraftTech"
        )
    ],
    [
        InlineKeyboardButton(
            "🎨 Download Presets, PNGs & Fonts", url="https://t.me/SabKraftTech"
        )
    ],
    [
        InlineKeyboardButton(
            "🎵 Download BGM & SFX Packs", url="https://t.me/SabKraftTech"
        )
    ],
])

# ==========================================
# 3. GEMINI AI ENGINE SETUP
# ==========================================
SYSTEM_PROMPT = """
You are SabKraftTech AI — an aesthetic, Gen-Z assistant for Video Editors, Graphic Designers, YouTubers, Freelancers, and Students.

CORE RULES:
1. ALWAYS TAG USER: Address the user using exact tag/name provided in context.
2. SHORT & AESTHETIC: Maximum 2 to 3 lines. Use clean, bold headers and aesthetic emojis (✨, ⚡, 🎬, 🚀, 🎨, 💡, 📱, 💼).
3. TARGETED EXPERT ADVICE:
   - Video Editors / Designers: Fast, 2-step solutions for CapCut, Alight Motion, PixelLab, Premiere, XML, Fonts.
   - YouTubers / Creators: Practical advice for CTR, RPM, Hooks, Thumbnails, Titles.
   - Freelancers / Students: Portfolio tips, client acquisition, free resources.
4. TROUBLESHOOTING: If user mentions an error or crash without an image, ALWAYS ask them to share a SCREENSHOT.
5. TONE: Supportive, smart, professional Hinglish.
"""


def get_ai_model():
  if not GEMINI_KEY:
    return None
  try:
    genai.configure(api_key=GEMINI_KEY)
    models = [
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]
    for m in models:
      try:
        return genai.GenerativeModel(
            model_name=m, system_instruction=SYSTEM_PROMPT
        )
      except Exception:
        continue
  except Exception as e:
    print(f"AI Init Error: {e}")
  return None


ai_model = get_ai_model()


def extract_user_tag(update: Update) -> str:
  user = update.effective_user
  if not user:
    return "Creator"
  if user.username:
    return f"@{user.username}"
  return f"[{user.first_name}](tg://user?id={user.id})"


# ==========================================
# 4. JSON CONFIG & FILTER READER
# ==========================================
def load_json_config():
  if os.path.exists("filters.json"):
    try:
      with open("filters.json", "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception as e:
      print(f"JSON Load Error: {e}")
  return {"button_triggers": [], "custom_rules": []}


def get_filter_reply(lower_text: str, user_tag: str) -> str:
  config = load_json_config()
  rules = config.get("custom_rules", [])

  for rule in rules:
    keywords = rule.get("keywords", [])
    if any(kw in lower_text for kw in keywords):
      reply = rule.get("reply", "")
      return reply.replace("{user_tag}", user_tag)

  return ""


def is_only_emoji(text: str) -> bool:
  emoji_pattern = re.compile(
      r"^[\s\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]+$"
  )
  return bool(emoji_pattern.match(text))


# ==========================================
# 5. MAIN MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not update.message:
    return

  chat_type = update.message.chat.type
  user_tag = extract_user_tag(update)
  bot_username = context.bot.username or ""
  is_group = chat_type in ["group", "supergroup"]

  user_text = update.message.text or update.message.caption or ""
  user_text_clean = user_text.strip()
  lower_text = user_text_clean.lower()

  # 1. Anti-Spam Link Blocker (In Groups)
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

  # 3. Check Button Triggers
  config = load_json_config()
  material_triggers = [
      "material",
      "materials",
      "overlay",
      "transition",
      "preset",
      "png",
      "bgm",
      "sfx",
      "font",
      "apk",
      "download",
  ]

  show_official_buttons = any(
      kw in lower_text for kw in ["sabkrafttech", "admin", "malik", "owner"]
  )
  show_material_buttons = any(kw in lower_text for kw in material_triggers)

  reply_text = ""

  # Step A: Check JSON Custom Rules First
  matched_reply = get_filter_reply(lower_text, user_tag)
  if matched_reply:
    reply_text = matched_reply

  # Step B: Pure Emoji or Sticker Received
  elif is_only_emoji(user_text_clean) or update.message.sticker:
    reply_text = f"Hey {user_tag}! 🔥 Great vibe! What content are you working on today?"

  # Step C: Screenshot Received (Vision AI Scan)
  elif update.message.photo:
    try:
      photo_file = await update.message.photo[-1].get_file()
      photo_bytes = await photo_file.download_as_bytearray()
      image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

      # FIXED LINE HERE: Properly closed quotes and braces
      prompt = [
          (
              f"User Tag: {user_tag}\nQuery: {user_text_clean or 'Is error"
              " screenshot ko analyze karke short 2-step solution do.'}"
          ),
          image_part,
      ]
      model = ai_model or get_ai_model()
      if model:
        res = model.generate_content(prompt)
        reply_text = res.text
      else:
        reply_text = (
            f"✨ Hey {user_tag}! Received your screenshot. Our team will verify"
            " it soon!"
        )
    except Exception:
      reply_text = (
          f"✨ Hey {user_tag}! Thanks for sending the screenshot. Please describe"
          " the exact tool/app name!"
      )

  # Step D: Complex Query via Gemini AI
  elif user_text_clean:
    try:
      model = ai_model or get_ai_model()
      if model:
        prompt = (
            f"User Tag: {user_tag}\nMessage Context & Query: {user_text_clean}"
        )
        res = model.generate_content(prompt)
        reply_
        
