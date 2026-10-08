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


@app.route('/')
def home():
  return 'SabKraftTech 100% AI Bot Active 24/7!', 200


def run_flask():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port, use_reloader=False)


# ==========================================
# 2. CONFIGURATION & ADMIN SETUP
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# Admin Telegram User ID (Is ID se aap live prompt modify kar sakte hain)
ADMIN_ID = int(os.environ.get('ADMIN_TELEGRAM_ID', '0'))

# Official Buttons (Jab user SabKraftTech/Links poochhe tabhi dikhenge)
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
# 3. DYNAMIC SYSTEM PROMPT (LIVE MODIFIABLE)
# ==========================================
DEFAULT_SYSTEM_PROMPT = """
You are SabKraftTech Official AI Assistant — an intellectual, highly smart, short-replying, empathetic, Gen-Z digital AI partner for Video Editors, Graphic Designers, YouTubers, Freelancers, and Students (India & Pakistan).

CORE BEHAVIOR RULES:
1. ALWAYS ADDRESS USER: Address the user by their exact name/tag provided in prompt context.
2. SHORT & CRISP: Reply in maximum 2 to 3 short sentences or bullet points. Strictly avoid long lectures or unnecessary fluff.
3. CONTEXTUAL & RELIGIOUS RESPECT:
   - Islamic (Aslm, Salam, Eid, Ramzan, etc.): Reply with respectful "Walaikum Assalam" / Mubarakbaad + Tag.
   - Hindu (Namaste, Diwali, Chhath, Navratri, etc.): Reply with respectful "Namaste" / Shubhkaamnayein + Tag.
   - Christian (Merry Christmas, Easter, etc.): Reply with warm greetings + Tag.
   - Universal & Time Greetings (Hi, Hello, GM, GN, GE): Short, aesthetic greeting according to context + Tag.
4. PROFESSION & ROLE SPECIFIC:
   - Video Editors: Short fixes for CapCut, Alight Motion, XML, Premiere, lag issues.
   - Graphic Designers: PixelLab, Photoshop, Canva, fonts, high CTR thumbnail ideas.
   - YouTubers: RPM/CPM boost, CTR optimization, title/SEO tips.
   - Freelancers & Students: Client pricing, free tools, portfolio advice.
5. MYSTERY OWNER RULE:
   - If asked who is owner/created this: 'Unhone identity reveal nahi ki hai! Baki main SabKraftTech AI hu.'
6. TONE & STYLE: Clean Hinglish (Latin script Hindi/Urdu mix), bold highlights, and aesthetic emojis (✨, ⚡, 🎬, 🚀, 💡, 🎨).
"""

# Dynamic prompt variable which can be updated live
LIVE_SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT


def get_gemini_model(custom_instruction=None):
  if not GEMINI_KEY:
    return None
  genai.configure(api_key=GEMINI_KEY)

  prompt_to_use = custom_instruction or LIVE_SYSTEM_PROMPT
  candidate_models = [
      'gemini-2.0-flash',
      'gemini-1.5-flash-latest',
      'gemini-1.5-flash',
      'gemini-1.5-pro',
  ]

  for m in candidate_models:
    try:
      return genai.GenerativeModel(
          model_name=m, system_instruction=prompt_to_use
      )
    except Exception:
      continue

  return genai.GenerativeModel(
      model_name='gemini-1.5-flash', system_instruction=prompt_to_use
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
# 4. LIVE ADMIN PROMPT UPDATE COMMAND (/setprompt)
# ==========================================
async def set_prompt_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  global LIVE_SYSTEM_PROMPT, ai_model

  user_id = update.effective_user.id
  if ADMIN_ID != 0 and user_id != ADMIN_ID:
    await update.message.reply_text(
        '❌ Aapke paas is command ko run karne ki permission nahi hai!'
    )
    return

  new_prompt = ' '.join(context.args)
  if not new_prompt:
    await update.message.reply_text(
        '⚠️ **Usage:** `/setprompt <Naye AI instructions yahan likhein>`',
        parse_mode='Markdown',
    )
    return

  LIVE_SYSTEM_PROMPT = new_prompt
  ai_model = get_gemini_model(LIVE_SYSTEM_PROMPT)

  await update.message.reply_text(
      '✅ **Bot AI Prompt Live Modify Ho Gaya Hai!**\n\n'
      f'**Naya Prompt Active:**\n`{LIVE_SYSTEM_PROMPT}`',
      parse_mode='Markdown',
  )


# ==========================================
# 5. UNIFIED SMART MESSAGE HANDLER
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

  # 1. Anti-Spam Link Blocker (Group me)
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

  # 3. Conditional Buttons (Only when user asks about SabKraftTech or links)
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
          'owner',
          'malik',
      ]
  )

  reply_text = ''

  # 4. Screenshot / Vision AI Scan
  if update.message.photo:
    try:
      photo_file = await update.message.photo[-1].get_file()
      photo_bytes = await photo_file.download_as_bytearray()
      image_part = {'mime_type': '
        
