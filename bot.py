import json
import os
import re
import threading
import logging
from flask import Flask
import google.generativeai as genai
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==========================================
# 1. FLASK WEB SERVER (24/7 KEEP-ALIVE)
# ==========================================
app = Flask(__name__)

@app.route("/")
def health():
    return "SabKraftTech Ultimate AI Bot is Active & Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. ENVIRONMENT & BUTTONS CONFIG
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Official Social Buttons
OFFICIAL_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📢 Telegram Channel", url="https://t.me/SabKraftTech"),
        InlineKeyboardButton("👥 Telegram Group", url="https://t.me/TeamSabKraftTech")
    ],
    [
        InlineKeyboardButton("▶️ YouTube Channel", url="https://youtube.com/@sabkrafttech?si=BvFSMTysyXScxEj2"),
        InlineKeyboardButton("📸 Instagram ID", url="https://instagram.com/sabkrafttech")
    ]
])

# Editing Material Buttons
MATERIAL_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📦 Download Overlays & Effects", url="https://t.me/SabKraftTech")
    ],
    [
        InlineKeyboardButton("🎨 Download Presets, PNGs & Fonts", url="https://t.me/SabKraftTech")
    ],
    [
        InlineKeyboardButton("🎵 Download BGM & SFX Packs", url="https://t.me/SabKraftTech")
    ]
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
5. TONE: Supportive
