import asyncio
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
  return "SabKraftTech Ultra Bot Online & Active!", 200


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port, use_reloader=False)


# ==========================================
# 2. CONFIGURATION & BUTTONS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Official Buttons (SIRF 'SabKraftTech', 'admin', 'channel', etc. par aayenge)
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

# ==========================================
# 3. GEMINI AI ENGINE SETUP
# ==========================================
SYSTEM_PROMPT = """
You are SabKraftTech AI — a smart, short-replying, Gen-Z assistant for Video Editors, Graphic Designers, YouTubers, Freelancers, and Content Creators.

CORE BEHAVIOR RULES:
1. ALWAYS TAG USER: Use exact user tag/name provided in context.
2. SHORT & AESTHETIC: Maximum 2 to 3 short lines per reply. Bold key terms and use clean emojis (✨, ⚡, 🎬, 🚀, 🎨, 💡).
3. TARGET AUDIENCE HELPER:
   - Video Editors: CapCut, Alight Motion, Premiere, XML, Lag/Export fixes.
   - Designers: PixelLab, Photoshop, Canva, Fonts, High CTR Thumbnails.
   - YouTubers / Creators: Title SEO, CTR boost, RPM/CPM guidance.
   - Freelancers & Students: Client rates, portfolio tips, unlocked tools.
4. TONE: Professional, supportive, Hinglish (Latin script Hindi/Urdu).
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
    print(f"AI Init Warning: {e}")
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
# 4. INSTANT LOCAL GREETINGS ROUTER
# ==========================================
def get_greeting_reply(text_lower: str, user_tag: str) -> str:
  # Islamic Greetings
  if any(
      k in text_lower
      for k in [
          "aslm",
          "salam",
          "assalamu",
          "walekum",
          "ramzan",
          "eid",
          "jumma",
      ]
  ):
    return (
        f"Walaikum Assalam {user_tag}! 🌙 Mubarakbaad! Aaj editing, design, ya"
        " YouTube project me kya help chahiye?"
    )

  # Hindu Greetings
  if any(
      k in text_lower
      for k in [
          "namaste",
          "namaskar",
          "jai shree ram",
          "ram ram",
          "radhe radhe",
          "diwali",
          "holi",
          "chhath",
      ]
  ):
    return (
        f"Namaste {user_tag}! 🙏 Shubhkaamnayein! Batayein aaj kaunsa naya"
        " creative project chal raha hai?"
    )

  # Good Morning
  if any(k in text_lower for k in ["good morning", "gm", "gud morning"]):
    return (
        f"Good Morning {user_tag}! ☀️ Naye din ke sath naya content create"
        " karte hain. Aaj kya guide karu?"
    )

  # Good Evening
  if any(k in text_lower for k in ["good evening", "ge", "gud evening"]):
    return (
        f"Good Evening {user_tag}! 🌇 Chai ke sath editing session chalu?"
        " Batayein kya help chahiye!"
    )

  # Good Night
  if any(
      k in text_lower
      for k in ["good night", "gn", "gud night", "gud nite", "shubh ratri"]
  ):
    return (
        f"Good Night {user_tag}! 🌙 Aaj ka work save karke rest karein. Kal"
        " milte hain fresh ideas ke sath!"
    )

  # General Hi / Hello
  if text_lower in [
      "hi",
      "hello",
      "helo",
      "hey",
      "sup",
      "whats up",
      "kya haal",
      "kya hal",
  ]:
    return (
        f"Hey {user_tag}! ⚡ Bilkul badhiya! Aap batao, aaj video editing,"
        " thumbnail ya graphics me kya create ho raha hai?"
    )

  # Goodbye / Bye
  if any(k in text_lower for k in ["bye", "by", "good bye", "tc", "take care"]):
    return (
        f"Take Care {user_tag}! 👋 Kuch bhi issue aaye toh group me message kar"
        " dena. Keep creating! 🚀"
    )

  # Mystery Owner Rule
  if any(
      k in text_lower
      for k in ["owner", "malik", "maalik", "who created", "creator of bot"]
  ):
    return (
        f"🕵️ Hey {user_tag}! Unhone abhi identity **reveal nahi ki hai**!"
        " Baki main SabKraftTech AI Assistant hu. ✨"
    )

  return ""


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

  # 3. BUTTON TRIGGER CHECK (Only on SabKraftTech / Links related queries)
  button_keywords = [
      "sabkrafttech",
      "admin",
      "malik",
      "owner",
      "channel",
      "group",
      "youtube",
      "instagram",
      "links",
      "social",
  ]
  show_buttons = any(kw in lower_text for kw in button_keywords)

  reply_text = ""

  # Step A: Local Greeting Match (Instant & Accurate)
  greeting_reply = get_greeting_reply(lower_text, user_tag)
  if greeting_reply:
    reply_text = greeting_reply

  # Step B: Photo / Screenshot Vision Scan
  elif update.message.photo:
    try:
      photo_file = await update.message.photo[-1].get_file()
      photo_bytes = await photo_file.download_as_bytearray()
      image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}

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
            f"✨ Hey {user_tag}! Screenshot scan busy hai. Problem text me"
            " likhein!"
        )
    except Exception:
      reply_text = f"✨ Hey {user_tag}! Problem text me likhkar poochein!"

  # Step C: Gemini AI for Editing / Graphics / YouTube / Freelance Queries
  elif user_text_clean:
    try:
      model = ai_model or get_ai_model()
      if model:
        prompt = (
            f"User Tag: {user_tag}\nMessage Context & Query: {user_text_clean}"
        )
        res = model.generate_content(prompt)
        reply_text = res.text
      else:
        reply_text = (
            f"✨ Hey {user_tag}! Main active hu. Batayein, aaj editing ya"
            " design me kya help chahiye?"
        )
    except Exception:
      reply_text = (
          f"✨ Hey {user_tag}! Direct apna issue type karein, main madad"
          " karunga!"
      )

  # Send Final Output
  if reply_text:
    markup = OFFICIAL_BUTTONS if show_buttons else None
    try:
      await update.message.reply_text(
          reply_text, reply_markup=markup, parse_mode="Markdown"
      )
    except Exception:
      await update.message.reply_text(reply_text, reply_markup=markup)


# ==========================================
# 6. APPLICATION STARTUP
# ==========================================
def main():
  threading.Thread(target=run_flask, daemon=True).start()

  if not TELEGRAM_TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN missing in Environment Variables!")
    return

  application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  application.add_handler(
      MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
  )

  print("🚀 SabKraftTech Single-File Bot Active & Running!")
  application.run_polling()


if __name__ == "__main__":
  main()
        
