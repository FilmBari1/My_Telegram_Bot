import telebot
from telebot import types
import re
import os
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# ==================== CONFIGURATION ====================
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

# MongoDB Connection (আপনার দেওয়া লিংক)
MONGO_URI = 'mongodb+srv://admin:mybot123@cluster0.jtlmjhc.mongodb.net/?appName=Cluster0'
client = MongoClient(MONGO_URI)
db = client['bot_database']
users_col = db['users']
posts_col = db['posts']

bot = telebot.TeleBot(API_TOKEN)
admin_states = {}

# ------ MongoDB Helper Functions ------
def save_user(user_id, referrer_id=None):
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "referred_by": referrer_id, "refer_count": 0})
        if referrer_id:
            users_col.update_one({"user_id": referrer_id}, {"$inc": {"refer_count": 1}})

def get_total_users():
    return users_col.count_documents({})

def get_all_user_ids():
    return [u['user_id'] for u in users_col.find()]

def get_user_refers(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user['refer_count'] if user else 0

def save_post(raw_text, msg_id, content_type, channel_type, file_id=None):
    clean_title = re.sub(r'(https?://[^\s]+)', '', raw_text or "").replace("এখানে চাপুন:", "").replace("MovieGor", "").replace("-", "").strip().lower()
    posts_col.update_one(
        {"text": clean_title, "channel_type": channel_type},
        {"$set": {"msg_id": msg_id, "content_type": content_type, "file_id": file_id}},
        upsert=True
    )

# ------ বট কমান্ড ও হ্যান্ডলার ------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    referrer_id = int(message.text.split()[1]) if len(message.text.split()) > 1 else None
    save_user(user_id, referrer_id)
    bot.reply_to(message, "আমাদের অল-ইন-ওয়ান ভিডিও ও মুভি বক্সে স্বাগতম! যেকোনো নাম লিখে সার্চ করুন।")

@bot.message_handler(commands=['stats', 'broadcast'])
def admin_commands(message):
    if message.chat.id == ADMIN_ID:
        if message.text.startswith('/stats'):
            bot.send_message(ADMIN_ID, f"📊 মোট ইউজার: {get_total_users()}")
        else:
            admin_states[ADMIN_ID] = "BROADCAST"
            bot.send_message(ADMIN_ID, "পোস্টটি পাঠান:")

@bot.message_handler(func=lambda m: admin_states.get(ADMIN_ID) == "BROADCAST", content_types=['text', 'photo'])
def execute_broadcast(message):
    admin_states[ADMIN_ID] = None
    for u_id in get_all_user_ids():
        try: bot.copy_message(u_id, ADMIN_ID, message.message_id)
        except: continue
    bot.send_message(ADMIN_ID, "✅ সম্পন্ন!")

@bot.message_handler(func=lambda m: not m.text.startswith('/'))
def search_post(message):
    query = message.text.lower().strip()
    results = list(posts_col.find({"text": {"$regex": query}}))
    
    if not results:
        bot.reply_to(message, "দুঃখিত, কিছু পাওয়া যায়নি।")
        return

    for p in results:
        markup = types.InlineKeyboardMarkup()
        if p.get('channel_type') == 'movie':
            markup.add(types.InlineKeyboardButton("🌐 মুভি ওয়েবসাইট", url=MOVIE_WEB_LINK))
            caption = f"🎬 মুভি: {p['text'].upper()}"
        else:
            markup.add(types.InlineKeyboardButton("🌐 ওয়েবসাইট", url=MASTER_WEB_LINK),
                       types.InlineKeyboardButton("🔒 টেলিগ্রাম ফ্রি লক", callback_data=f"lock_{p['msg_id']}"))
            caption = f"🎬 ভিডিও: {p['text'].upper()}"
        bot.send_message(message.chat.id, caption, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lock_'))
def lock_menu(call):
    user_id = call.from_user.id
    msg_id = call.data.split('_')[1]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ ভেরিফাই", callback_data=f"verify_{msg_id}"))
    bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id, 
                             caption=f"২ জন বন্ধুকে ইনভাইট করুন! রেফারেল: {get_user_refers(user_id)}/2", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('verify_'))
def verify(call):
    if get_user_refers(call.from_user.id) >= 2:
        bot.answer_callback_query(call.id, "লিংক: " + INVITE_LINK, show_alert=True)
    else:
        bot.answer_callback_query(call.id, "আরও রেফার করুন!", show_alert=True)

@bot.channel_post_handler(content_types=['text', 'photo'])
def handle_channel_post(message):
    ch_id = str(message.chat.id)
    ctype = 'main' if ch_id == CHANNEL_ONE else ('private' if ch_id == CHANNEL_TWO else 'movie')
    save_post(message.text or message.caption, message.message_id, 'text', ctype, message.photo[-1].file_id if message.photo else None)

# ------ ২৪ ঘণ্টা সচল রাখার লজিক ------
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.infinity_polling()
