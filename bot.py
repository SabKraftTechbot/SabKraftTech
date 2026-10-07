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
# 1. FLASK WEB SERVER (24/7 FOR RENDER)
# ==========================================
app = Flask(__name__)


@app.route('/')
def home():
  return 'SabKraftTech Ultra Smart AI Bot Active!', 200


def run_flask():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port, use_reloader=False)


# ==========================================
# 2. CONFIGURATION & BUTTONS
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# Buttons tabhi attach honge jab user SabKraftTech ya Links poochega
MAIN_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            '📢 Telegram Channel', url='https://t.me/SabKraftTech'
        ),
        InlineKeyboardButton(
            '👥 Telegram Group', url='https://t.me/TeamSabKraftTech'
        ),
    ],
    [
        InlineKeyboardButton(
            '▶️ YouTube Channel',
            url='https://youtube.com/@sabkrafttech?si=BvFSMTysyXScxEj2',
        ),
        InlineKeyboardButton(
            '📸 Instagram ID', url='https://instagram.com/sabkrafttech'
        ),
    ],
])

# ==========================================
# 3. GEMINI AI SYSTEM PROMPT & FALLBACK
# ==========================================
SYSTEM_INSTRUCTION = (
    'You are SabKraftTech Official AI Assistant — an intellectual, highly'
    ' smart, short-replying, Gen-Z digital partner.\n\n'
    'CRITICAL COMMANDMENTS:\n'
    '1. ALWAYS ADDRESS USER: Always include the user tag (e.g. @username or'
    ' Name) provided in prompt context.\n'
    '2. CRISP & SHORT: Maximum 2 to 3 short sentences or bullet points per'
    ' reply. Strictly avoid long essays or lectures.\n'
    '3. CONTEXTUAL GREETINGS:\n'
    '   - Time-based (GM, GN, GE, Good Morning/Night/Evening in short/long):'
    ' Reply warmly according to time.\n'
    '   - Religious Greetings (Salam/Aslm, Namaste, Eid, Ramzan, Chhath,'
    ' Diwali, Navratri, Christmas, etc.): Respectful, warm, specific aesthetic'
    ' greeting.\n'
    '   - Non-Religious / Casual (Hi, Hello, Hey, Kya haal): Smart, cool, Gen-Z'
    ' creator tone.\n'
    '4. APK / TECH / EDITING / ERRORS:\n'
    '   - Give direct, 2-step actionable short solutions (CapCut, Alight'
    ' Motion, PixelLab, XML, rendering issues, APK requests).\n'
    '5. MYSTERY OWNER RULE:\n'
    "   - If asked owner/creator: 'Unhone identity reveal nahi ki hai! Baki main"
    " SabKraftTech AI hu.'\n"
    '6. AESTHETIC & EMOJIS: Clean Hinglish (Latin script Hindi), bold key words,'
    ' and tasteful emojis (✨, ⚡, 🎬, 🚀, 💡, 🎨).\n'
    '7. DYNAMIC REPLIES: Understand the unique context of every message;'
    ' NEVER send identical static text.'
)


def get_gemini_model():
  if not GEMINI_KEY:
    return None
  genai.configure(api_key=GEMINI_KEY)

  candidate_models = [
      'gemini-2.0-flash',
      'gemini-1.5-flash-latest',
      'gemini-1.5-flash',
      'gemini-1.5-pro',
  ]
  for m in candidate_models:
    try:
      return genai.GenerativeModel(
          model_name=m, system_instruction=SYSTEM_INSTRUCTION
      )
    except Exception:
      continue
  return genai.GenerativeModel(
      model_name='gemini-1.5-flash', system_instruction=SYSTEM_INSTRUCTION
  )


ai_model = get_gemini_model()


def get_user_tag(update: Update) -> str:
  user = update.effective_user
  if not user:
    return 'Friend'
  if user.username:
    return f'@{user.username}'
  return f'[{user.first_name}](tg://user?id={user.id})'


# ==========================================
# 4. UNIFIED MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not update.message:
    return

  chat_type = update.message.chat.type
  user_tag = get_user_tag(update)
  bot_username = context.bot.username or ''
  is_group = chat_type in ['group', 'supergroup']

  user_text = update.message.text or update.message.caption or ''
  user_text_clean = user_text.strip()
  lower_text = user_text_clean.lower()

  # 1. Anti-Spam Link Blocker (In Groups)
  if is_group and user_text_clean:
    if re.search(r'http[s]?://|t\.me/|telegram\.me/', user_text_clean):
      try:
        await update.message.delete()
        return
      except Exception:
        pass

  # 2. Group Mention Check
  if is_group:
    is_tagged = (bot_username and f'@{bot_username}' in user_text_clean) or (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )
    if not is_tagged:
      return

  # 3. Check if Buttons should be attached (ONLY when user asks about SabKraftTech or links)
  show_buttons = any(
      kw in lower_text
      for kw in [
          'sabkrafttech',
          'channel',
          'group',
          'social',
          'links',
          'youtube',
          'instagram',
          'bot info',
          'owner',
          'malik',
      ]
  )

  reply_text = ''

  # 4. Photo / Screenshot Scan (Vision AI)
  if update.message.photo:
    try:
      photo_file = await update.message.photo[-1].get_file()
      photo_bytes = await photo_file.download_as_bytearray()
      image_part = {'mime_type': 'image/jpeg', 'data': bytes(photo_bytes)}

      prompt = [
          (
              f'User Tag: {user_tag}\nContext: {user_text_clean or "Is"}'
              ' screenshot/error ko scan karke direct short 2-step solution'
              ' do.'
          ),
          image_part,
      ]
      if ai_model:
        res = ai_model.generate_content(prompt)
        reply_text = res.text
    except Exception:
      reply_text = (
          f'✨ Hey {user_tag}! Screenshot scan karne me dikkat aayi. Error text'
          ' me likh kar poochein!'
      )

  # 5. Text Message Processing (Smart Dynamic AI Response)
  elif user_text_clean:
    try:
      if ai_model:
        prompt = (
            f'User Tag/Name: {user_tag}\nUser Message Context:'
            f' {user_text_clean}'
        )
        res = ai_model.generate_content(prompt)
        reply_text = res.text
      else:
        reply_text = f'✨ Hey {user_tag}! Batayein, aaj kya help karu?'
    except Exception:
      reply_text = (
          f'✨ Hey {user_tag}! Thoda issue aaya, ek baar dobara poochiye.'
      )

  # 6. Send Response
  if reply_text:
    markup = MAIN_BUTTONS if show_buttons else None
    try:
      await update.message.reply_text(
          reply_text, reply_markup=markup, parse_mode='Markdown'
      )
    except Exception:
      await update.message.reply_text(reply_text, reply_markup=markup)


# ==========================================
# 5. BOT RUNNER
# ==========================================
def main():
  threading.Thread(target=run_flask, daemon=True).start()

  if not TELEGRAM_TOKEN:
    print('❌ ERROR: TELEGRAM_BOT_TOKEN missing!')
    return

  application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  application.add_handler(
      MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
  )

  print('🚀 SabKraftTech Ultra Smart Bot Running Successfully!')
  application.run_polling()


if __name__ == '__main__':
  main()
