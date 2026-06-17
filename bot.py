import telebot
from telebot import types
import sqlite3
import re
import os
from flask import Flask
from threading import Thread

# ==================== CONFIGURATION (আপনার আগের ডাটা) ====================
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
# ========================================================================

# ডাটা যেন না মুছে যায়, তার জন্য পারসিস্টেন্ট পাথ সেটআপ
DB_FILE = "/data/bot_master_database.db"
if not os.path.exists("/data"):
    DB_FILE = "bot_master_database.db"

bot = telebot.TeleBot(API_TOKEN)
admin_states = {}

# ------ ডেটাবেজ কোর ফাংশনসমূহ ------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30)
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

# আপনার আগের সব লজিক ফাংশনগুলো এখানে আছে
def delete_invalid_post(post_title, channel_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE text = ? AND channel_type = ?", (post_title, channel_type))
    conn.commit()
    conn.close()

def is_post_alive(channel_id, msg_id):
    try:
        check_msg = bot.forward_message(chat_id=ADMIN_ID, from_chat_id=channel_id, message_id=msg_id, disable_notification=True)
        bot.delete_message(chat_id=ADMIN_ID, message_id=check_msg.message_id)
        return True
    except: return False

def save_user(user_id, referrer_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, referrer_id))
        conn.commit()
    conn.close()

def get_total_users():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count

def get_all_user_ids():
    conn = get_db_connection()
    users = [u[0] for u in conn.execute("SELECT user_id FROM users").fetchall()]
    conn.close()
    return users

def get_user_refers(user_id):
    conn = get_db_connection()
    res = conn.execute("SELECT refer_count FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return res[0] if res else 0

def save_post(raw_text, message_id, content_type, channel_type, file_id=None):
    clean_title = re.sub(r'https?://[^\s]+', '', raw_text or "").replace("এখানে চাপুন:", "").replace("MovieGor", "").replace("-", "").strip().lower()
    conn = get_db_connection()
    conn.execute("INSERT INTO posts (text, msg_id, content_type, file_id, channel_type) VALUES (?, ?, ?, ?, ?)", 
                 (clean_title or "untitled", message_id, content_type, file_id, channel_type))
    conn.commit()
    conn.close()

# ------ হ্যান্ডলারস (আপনার আগের লজিক) ------
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    bot.reply_to(message, "আমাদের অল-ইন-ওয়ান ভিডিও ও মুভি বক্সে স্বাগতম!")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def search_post(message):
    query = message.text.lower().strip()
    conn = get_db_connection()
    matched_rows = conn.execute("SELECT text, channel_type, msg_id, content_type, file_id FROM posts WHERE text LIKE ?", ('%' + query + '%',)).fetchall()
    conn.close()
    if not matched_rows:
        bot.reply_to(message, "দুঃখিত, এই নামে কোনো পোস্ট পাওয়া যায়নি।")
        return
    for row in matched_rows:
        bot.send_message(message.chat.id, f"পাওয়া গেছে: {row[0]}")

@bot.channel_post_handler(content_types=['text', 'photo'])
def handle_channel_post(message):
    ch_id = str(message.chat.id)
    caption = message.text or message.caption
    if ch_id == CHANNEL_ONE: save_post(caption, message.message_id, 'text', 'main', None)
    elif ch_id == CHANNEL_TWO: save_post(caption, message.message_id, 'text', 'private', None)
    elif ch_id == CHANNEL_MOVIE: save_post(caption, message.message_id, 'text', 'movie', None)

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
    bot.infinity_polling(none_stop=True)
