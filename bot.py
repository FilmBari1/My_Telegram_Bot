import telebot
from telebot import types
import sqlite3
import re
import os
from flask import Flask
from threading import Thread

# ==================== CONFIGURATION (LOADED) ====================
API_TOKEN = '8720201406:AAFlNvQ-tTErzXJ8eV-MkkrTd3ns0qlY6DE'
ADMIN_ID = 8513606329

CHANNEL_ONE = '-1003700030998'
CHANNEL_TWO = '-1004486324779'
CHANNEL_MOVIE = '-1003996193613'

INVITE_LINK = 'https://t.me/+bNSTXDGq9Xc4NmY9'
MAIN_CHANNEL_PUBLIC_LINK = 'https://t.me/MovieGor'
MOVIE_CHANNEL_LINK = 'https://t.me/MovieGorBD'

MASTER_WEB_LINK = 'https://filmbari1.github.io/MovieGor/?vid=-OvB3edV7fuCrJ7OnY48'
MOVIE_WEB_LINK = 'https://filmbari1.github.io/MovieGor/'
# ===============================================================

# ডাটা যেন না মুছে যায়, তার জন্য ডিস্ক পাথ সেট করা
DB_PATH = "/data/bot_master_database.db"
if not os.path.exists("/data"):
    DB_PATH = "bot_master_database.db"

bot = telebot.TeleBot(API_TOKEN)
admin_states = {}

# ------ DATABASE CORE ------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, referred_by INTEGER, refer_count INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, msg_id INTEGER, content_type TEXT, file_id TEXT, channel_type TEXT DEFAULT 'main')''')
    conn.commit()
    conn.close()

init_db()

# (আপনার আগের সব ফাংশনগুলো যেমন: save_post, is_post_alive, save_user ইত্যাদি এখানে থাকবে)
# আমি আপনার মূল ফাংশনগুলো এখানে রেখে দিয়েছি:

def save_post(raw_text, message_id, content_type, channel_type, file_id=None):
    try:
        if raw_text:
            clean_title = raw_text.replace("এখানে চাপুন:", "").replace("MovieGor", "").replace("-", "").strip().lower()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO posts (text, msg_id, content_type, file_id, channel_type) VALUES (?, ?, ?, ?, ?)", 
                           (clean_title, message_id, content_type, file_id, channel_type))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Error saving: {e}")

# [আপনার আগের সব হ্যান্ডলার কোড এখানে থাকবে...]
# @bot.message_handler(commands=['start']) ... ইত্যাদি সব আগের মতোই থাকবে।

# --- সার্ভার লজিক (২৪ ঘণ্টা সচল রাখতে) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    print("বট এবং সার্ভার উভয়ই সফলভাবে চালু হয়েছে...")
    bot.infinity_polling(none_stop=True)
