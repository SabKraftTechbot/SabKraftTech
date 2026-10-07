import os
import re
import threading
from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==========================================
# 1. FLASK WEB SERVER (FOR UPTIMEROBOT 24/7)
# ==========================================
app = Flask(__name__)


@app.route('/')
def home():
  return 'SabKraftTech Bot Server is Alive & Active!', 200


def run_flask():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


# ==========================================
# 2. CONFIGURATION & GEMINI AI
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

if GEMINI_KEY:
  genai.configure(api_key=GEMINI_KEY)
  ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
  ai_model = None

# Custom Keyword Dictionary
QUICK_RESPONSES = {
    'aslm': 'Walaikum Assalam! SabKraftTech Bot me aapka swagat hai.',
    'assalam': 'Walaikum Assalam! Kaise hain aap?',
    'hi': 'Hello! Main SabKraftTech AI Bot hu. Aapki kya madad kar sakta hu?',
    'hello': 'Hello! Kaise hain aap?',
    'capcut': (
        '🎬 **CapCut Editing Assets & Apps:**\n👉 Direct Channel Link:'
        ' https://t.me/sabkrafttech'
    ),
    'kinemaster': (
        '🎬 **KineMaster Pro:**\n👉 Direct Channel Link:'
        ' https://t.me/sabkrafttech'
    ),
    'alight motion': (
        '🎬 **Alight Motion Presets & App:**\n👉 Direct Channel Link:'
        ' https://t.me/sabkrafttech'
    ),
    'preset': (
        '🎨 **Latest Editing Presets:**\n👉 Direct Channel Link:'
        ' https://t.me/sabkrafttech'
    ),
}


# Auto-Delete Task (10 Minutes for Groups)
async def auto_delete_msg(context: ContextTypes.DEFAULT_TYPE):
  job = context.job
  try:
    await context.bot.delete_message(
        chat_id=job.chat_id, message_id=job.data
    )
  except Exception:
    pass


# Message Handler Logic
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not update.message or not update.message.text:
    return

  chat_type = update.message.chat.type
  user_text = update.message.text.strip()
  lower_text = user_text.lower()

  # 1. Anti-Spam Link Blocker (Group me)
  if chat_type in ['group', 'supergroup']:
    if re.search(r'http[s]?://|t\.me/|telegram\.me/', user_text):
      try:
        await update.message.delete()
        return
      except Exception:
        pass

  # 2. Check Custom Keywords
  reply_sent = False
  for key, response in QUICK_RESPONSES.items():
    if key in lower_text:
      sent_msg = await update.message.reply_text(
          response, parse_mode='Markdown'
      )
      reply_sent = True

      if chat_type in ['group', 'supergroup'] and sent_msg:
        if context.job_queue:
          context.job_queue.run_once(
              auto_delete_msg,
              600,
              chat_id=update.message.chat_id,
              data=sent_msg.message_id,
          )
      break

  if reply_sent:
    return

  # 3. Gemini Smart AI Response
  if ai_model:
    try:
      ai_response = ai_model.generate_content(
          f'Answer concisely and nicely in Hinglish: {user_text}'
      )
      ai_text = (
          ai_response.text
          if ai_response.text
          else 'Processing me dikkat aayi, dobara puchein.'
      )
    except Exception:
      ai_text = 'Abhi AI busy hai, kripya thodi der baad try karein.'

    sent_msg = await update.message.reply_text(ai_text)

    if chat_type in ['group', 'supergroup'] and sent_msg:
      if context.job_queue:
        context.job_queue.run_once(
            auto_delete_msg,
            600,
            chat_id=update.message.chat_id,
            data=sent_msg.message_id,
        )


# Main Application Runner
def main():
  if not TELEGRAM_TOKEN:
    print('Error: TELEGRAM_BOT_TOKEN missing!')
    return

  # Start Web Server in background thread
  threading.Thread(target=run_flask, daemon=True).start()

  # Start Telegram Bot
  app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  app_bot.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
  )

  print('SabKraftTech Bot Started Successfully!')
  app_bot.run_polling()


if __name__ == '__main__':
  main()
    
