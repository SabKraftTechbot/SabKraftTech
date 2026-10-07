import asyncio
import io
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
# 1. FLASK WEB SERVER (24/7 FOR UPTIMEROBOT)
# ==========================================
app = Flask(__name__)


@app.route('/')
def home():
  return 'SabKraftTech Mastermind AI Bot is Live & Active!', 200


def run_flask():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port, use_reloader=False)


# ==========================================
# 2. CONFIGURATION & BUTTONS
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# Main Platform Buttons
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

# Bots Directory Buttons
BOTS_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            '🤖 Mod Apps Bot (@Sabkrafttech_bot)',
            url='https://t.me/Sabkrafttech_bot',
        )
    ],
    [
        InlineKeyboardButton(
            '🛡️ Security Bot (@SabKraftTechHelpbot)',
            url='https://t.me/SabKraftTechHelpbot',
        )
    ],
    [
        InlineKeyboardButton(
            '📢 Main Channel', url='https://t.me/SabKraftTech'
        )
    ],
])

# ==========================================
# 3. GEMINI AI SYSTEM & VISION PROMPT
# ==========================================
if GEMINI_KEY:
  genai.configure(api_key=GEMINI_KEY)

  system_instruction = (
      'You are SabKraftTech Official AI Assistant — an intellectual, highly'
      ' smart, creative, aesthetic, and empathetic digital partner.\n\n'
      'TARGET AUDIENCE & PERSONA:\n'
      'You speak to YouTubers, Video Editors, Graphic Designers, Freelancers,'
      ' Social Media Creators, and Gen-Z members. You understand meme context,'
      ' creator burnout, low CTR, high RPM/CPM, client negotiation, XML'
      ' presets, CapCut errors, Alight Motion, PixelLab, Photoshop, Canva, and'
      ' video rendering bugs.\n\n'
      'CORE COMMANDMENTS:\n'
      '1. ALWAYS address the user by their name/tag provided in context.\n'
      '2. MYSTERY OWNER RULE: If anyone asks who is the owner, creator, or'
      ' boss ("malik kon hai", "who created"), NEVER reveal any name! Reply:'
      ' "Unhone abhi apni identity reveal nahi ki hai. Jab karenge tab sabko'
      ' pata chal jayega! Baaki SabKraftTech ki details yeh hain..."\n'
      '3. CREATOR & GEN-Z TONE: To-the-point, aesthetic, high-value,'
      ' professional yet friendly. Use emojis smartly (✨, ⚡, 🎨, 🎬, 🚀, 💡,'
      ' 🗿, 🤌, 📉, 📈) without overusing them.\n'
      '4. RELIGIOUS GREETINGS & FESTIVALS: Give respectful and warm greetings on'
      ' behalf of SabKraftTech for ALL religions & festivals (Eid, Ramzan,'
      ' Diwali, Holi, Navratri, Chhath Puja, Christmas, Gurpurab, etc.).\n'
      '5. RELATIONSHIP & FAMILY ZONE: For queries about GF, BF, Ex, Breakup,'
      ' Parents (Mom/Dad), Siblings, or Relatives, act as a wise, grounding'
      ' elder brother/smart guide with deep empathy.\n'
      '6. SCREENSHOT & ERROR ANALYSIS: If an image/screenshot is provided'
      ' (CapCut, KineMaster, VN, Telegram, Android errors), scan the visual'
      ' text/context and provide a clean 3-step solution.\n'
      '7. APK REQUESTS: Direct them to search in channel/group or mention that'
      ' Rose Bot / SabKraftTech Team is processing it.\n'
      '8. TONE: Clean Hinglish (Latin script) with aesthetic bold headings and'
      ' bullet points.'
  )

  ai_model = genai.GenerativeModel(
      'gemini-1.5-flash', system_instruction=system_instruction
  )
else:
  ai_model = None


def get_user_tag(update: Update) -> str:
  user = update.effective_user
  if not user:
    return 'Friend'
  if user.username:
    return f'@{user.username}'
  return f'[{user.first_name}](tg://user?id={user.id})'


# ==========================================
# 4. CUSTOM KEYWORD DICTIONARY
# ==========================================
def get_custom_response(user_text: str, user_tag: str):
  lower_text = user_text.lower()

  # 1. Owner / Malik Mystery Filter
  if any(
      kw in lower_text
      for kw in [
          'owner',
          'malik',
          'maalik',
          'kon hai',
          'kiska hai',
          'who created',
          'admin name',
          'boss',
      ]
  ):
    return (
        f'🕵️ **Identity Status: Classified**\n'
        f'━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Aapko batate hain {user_tag}... Unhone abhi apni identity **reveal'
        ' nahi ki hai**! 🤫\n'
        f'Jab sahi waqt aayega tab sabko pata chal jayega. Tab tak'
        ' **SabKraftTech** ke premium content aur tools ka maza lein!\n\n'
        f'✨ **SabKraftTech Purpose:**\n'
        f'• High-Level Video Editing & Presets\n'
        f'• Premium Unlocked Mod Apps\n'
        f'• Content Strategy & AI Tech Tools',
        MAIN_BUTTONS,
    )

  # 2. Both Bots Info & Redirect Filter
  if any(
      kw in lower_text
      for kw in [
          'bot info',
          'other bot',
          'bots',
          'sabkrafttech_bot',
          'helpbot',
          'security bot',
          'mod bot',
      ]
  ):
    return (
        f'🤖 **SabKraftTech Official Bot Ecosystem**\n'
        f'━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Hey {user_tag}! Humare 2 main official bots hain:\n\n'
        f'1️⃣ **@Sabkrafttech_bot** — Mod Apps & Premium Tech Support\n'
        f'2️⃣ **@SabKraftTechHelpbot** — Security & Community Moderation\n\n'
        f'👉 Direct access ke liye niche buttons par click karein!',
        BOTS_BUTTONS,
    )

  # 3. Purpose & Channel Overview Filter
  if any(
      kw in lower_text
      for kw in [
          'purpose',
          'sabkrafttech',
          'about channel',
          'youtube',
          'instagram',
          'details',
      ]
  ):
    return (
        f'🚀 **SabKraftTech Official Overview**\n'
        f'━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Welcome {user_tag}!\n\n'
        f'📌 **Purpose:** Content creation with intent, not noise! Focused on'
        f' structure, flow & execution for creators, Gen-Z, and students.\n\n'
        f'✨ **What You Get:**\n'
        f'• CapCut Ultra, KineMaster, Alight Motion Presets & XML\n'
        f'• PicsArt, PixelLab, Canva & Photoshop Assets\n'
        f'• YouTube Growth, High RPM/CPM & Earning Tips',
        MAIN_BUTTONS,
    )

  # 4. Universal Religious Greetings & Festivals Filter
  greet_keywords = [
      'aslm',
      'assalam',
      'salam',
      'walekum',
      'namaste',
      'hi',
      'hello',
      'good morning',
      'good night',
      'gm',
      'gn',
      'eid',
      'ramzan',
      'ramadan',
      'bakrid',
      'diwali',
      'holi',
      'muharram',
      'chhath',
      'navratri',
      'christmas',
      'xmas',
      'gurpurab',
      'shivratri',
      'janmashtami',
      'rakhi',
      'raksha bandhan',
  ]
  if any(kw in lower_text for kw in greet_keywords):
    return (
        f'✨ **Warm Wishes & Greetings from SabKraftTech!**\n'
        f'━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Aapko aur aapki family ko **SabKraftTech** ki taraf se dil se bohot'
        f' bohot mubarakbaad aur greetings {user_tag}! 🌟\n\n'
        f'Aapki aaj kya help kar sakta hu? App, preset, ya koi guidance'
        f' chahiye?',
        MAIN_BUTTONS,
    )

  # 5. Apps & Premium Mods Filter
  app_keywords = [
      'apk',
      'mod',
      'premium',
      'capcut',
      'alight motion',
      'aftermotion',
      'vn',
      'picsart',
      'movie box',
      'kinemaster',
      'pro app',
  ]
  if any(kw in lower_text for kw in app_keywords):
    return (
        f'📱 **Premium APK & Mod Support**\n'
        f'━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Hey {user_tag}! Premium Mod Apps ke liye:\n\n'
        f'1️⃣ Channel/Group me app ka naam type karke search karein.\n'
        f'2️⃣ Agar nahi mila toh wait karein! **Rose Bot / SabKraftTech Team**'
        f' process kar rahi hai.\n'
        f'3️⃣ Screenshot bhej kar error ya app problem bhi puch sakte hain!',
        MAIN_BUTTONS,
    )

  return None, None


# ==========================================
# 5. AUTO-DELETE TASK (10 MIN FOR GROUPS)
# ==========================================
async def auto_delete_msg(bot, chat_id, message_id, delay=600):
  await asyncio.sleep(delay)
  try:
    await bot.delete_message(chat_id=chat_id, message_id=message_id)
  except Exception:
    pass


# ==========================================
# 6. UNIFIED HANDLER (TEXT + SCREENSHOTS)
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

  # 1. Anti-Spam Link Blocker (Group me)
  if is_group and user_text_clean:
    if re.search(r'http[s]?://|t\.me/|telegram\.me/', user_text_clean):
      try:
        await update.message.delete()
        return
      except Exception:
        pass

  # Group Tag Check
  is_tagged_or_replied = False
  if is_group:
    if bot_username and f'@{bot_username}' in user_text_clean:
      is_tagged_or_replied = True
    elif (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    ):
      is_tagged_or_replied = True

  # 2. Check Photo / Screenshot (Gemini Vision Input)
  if update.message.photo:
    if is_group and not is_tagged_or_replied:
      return

    try:
      photo_file = await update.message.photo[-1].get_file()
      photo_bytes = await photo_file.download_as_bytearray()
      image_part = {'mime_type': 'image/jpeg', 'data': bytes(photo_bytes)}

      prompt = (
          f'User Tag: {user_tag}\n'
          f"User Query/Caption: {user_text_clean or 'Analyze this screenshot, identify the app or error/problem shown, and provide a clear step-by-step fix in Hinglish.'}"
      )

      ai_response = ai_model.generate_content([prompt, image_part])
      ai_text = (
          ai_response.text
          if ai_response.text
          else f'Screenshot scan hone me dikkat aayi {user_tag}, dobara bhejein.'
      )

      sent_msg = await update.message.reply_text(
          ai_text, parse_mode='Markdown', reply_markup=MAIN_BUTTONS
      )

      if is_group and sent_msg:
        asyncio.create_task(
            auto_delete_msg(
                context.bot, update.message.chat_id, sent_msg.message_id, 600
            )
        )
      return
    except Exception as e:
      print(f'Vision Error: {e}')
      await update.message.reply_text(
          f'🔍 Screenshot scan karne me dikkat aayi {user_tag}. Clear photo ya'
          ' error text bhejein!'
      )
      return

  # 3. Check Custom Text Keywords
  if user_text_clean:
    response_text, response_buttons = get_custom_response(
        user_text_clean, user_tag
    )

    if response_text:
      sent_msg = await update.message.reply_text(
          response_text,
          parse_mode='Markdown',
          reply_markup=response_buttons or MAIN_BUTTONS,
      )
      if is_group and sent_msg:
        asyncio.create_task(
            auto_delete_msg(
                context.bot, update.message.chat_id, sent_msg.message_id, 600
            )
        )
      return

  if is_group and not is_tagged_or_replied:
    return

  # 4. Gemini Smart AI Response
  if ai_model and user_text_clean:
    try:
      prompt_with_context = (
          f'User Tag/Name: {user_tag}\nUser Message: {user_text_clean}'
      )
      ai_response = ai_model.generate_content(prompt_with_context)
      ai_text = (
          ai_response.text
          if ai_response.text
          else f'Processing me dikkat aayi {user_tag}, dobara puchein.'
      )
    except Exception:
      ai_text = (
          f'⚡ **SabKraftTech AI:** Thodi der me try karein {user_tag} ya hamara'
          ' Telegram Channel check karein!'
      )

    sent_msg = await update.message.reply_text(
        ai_text, parse_mode='Markdown', reply_markup=MAIN_BUTTONS
    )

    if is_group and sent_msg:
      asyncio.create_task(
          auto_delete_msg(
              context.bot, update.message.chat_id, sent_msg.message_id, 600
          )
      )


# ==========================================
# 7. MAIN APPLICATION RUNNER
# ==========================================
def main():
  if not TELEGRAM_TOKEN:
    print('Error: TELEGRAM_BOT_TOKEN missing!')
    return

  threading.Thread(target=run_flask, daemon=True).start()

  app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

  app_bot.add_handler(
      MessageHandler(
          (filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message
      )
  )

  print('SabKraftTech Ultra Advanced Bot Started Successfully!')
  app_bot.run_polling()


if __name__ == '__main__':
  main()
