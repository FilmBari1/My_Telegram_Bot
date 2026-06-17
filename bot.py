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

# MongoDB Connection
MONGO_URI = 'mongodb+srv://admin:mybot123@cluster0.jtlmjhc.mongodb.net/?appName=Cluster0'
client = MongoClient(MONGO_URI)
db = client['bot_database']
users_col = db['users']
posts_col = db['posts']

bot = telebot.TeleBot(API_TOKEN)
admin_states = {}

# --- ফাংশনসমূহ (পুরানো লজিকসহ) ---
def save_user(user_id, referrer_id=None):
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "referred_by": referrer_id, "refer_count": 0})
        if referrer_id:
            users_col.update_one({"user_id": referrer_id}, {"$inc": {"refer_count": 1}})

def get_user_refers(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user['refer_count'] if user else 0

def save_post(text, msg_id, content_type, channel_type, file_id=None):
    clean_title = re.sub(r'(https?://[^\s]+)', '', text or "").replace("এখানে চাপুন:", "").replace("MovieGor", "").replace("-", "").strip().lower()
    posts_col.update_one(
        {"text": clean_title, "channel_type": channel_type},
        {"$set": {"msg_id": msg_id, "content_type": content_type, "file_id": file_id}},
        upsert=True
    )

# --- হ্যান্ডলারসমূহ ---
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    bot.reply_to(message, "আমাদের অল-ইন-ওয়ান ভিডিও ও মুভি বক্সে স্বাগতম! ভিডিও বা মুভির নাম লিখে সার্চ করুন।")

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.chat.id == ADMIN_ID:
        count = users_col.count_documents({})
        bot.send_message(ADMIN_ID, f"📊 মোট ইউজার: {count}")

@bot.message_handler(commands=['broadcast'])
def start_broadcast(message):
    if message.chat.id == ADMIN_ID:
        admin_states[ADMIN_ID] = "BROADCAST"
        bot.send_message(ADMIN_ID, "পোস্ট পাঠান:")

@bot.message_handler(func=lambda m: admin_states.get(ADMIN_ID) == "BROADCAST", content_types=['text', 'photo'])
def execute_broadcast(message):
    admin_states[ADMIN_ID] = None
    all_users = users_col.find()
    for u in all_users:
        try: bot.copy_message(u['user_id'], ADMIN_ID, message.message_id)
        except: continue
    bot.send_message(ADMIN_ID, "✅ সম্পন্ন হয়েছে।")

@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def search_post(message):
    query = message.text.lower().strip()
    results = list(posts_col.find({"text": {"$regex": query}}))
    
    if not results:
        bot.reply_to(message, "দুঃখিত, কিছু পাওয়া যায়নি।")
        return
    
    for p in results:
        markup = types.InlineKeyboardMarkup()
        if p['channel_type'] == 'movie':
            markup.add(types.InlineKeyboardButton("🌐 মুভি দেখুন", url=MOVIE_WEB_LINK))
        else:
            markup.add(types.InlineKeyboardButton("🌐 ওয়েবসাইট", url=MASTER_WEB_LINK))
            markup.add(types.InlineKeyboardButton("🔒 টেলিগ্রাম লক", callback_data=f"lock_{p['msg_id']}"))
        bot.send_message(message.chat.id, f"🎬 {p['text'].upper()}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lock_'))
def lock_menu(call):
    user_id = call.from_user.id
    refers = get_user_refers(user_id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ ভেরিফাই", callback_data="verify"))
    bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id, 
                             caption=f"আপনার রেফারেল: {refers}/2 জন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify(call):
    if get_user_refers(call.from_user.id) >= 2:
        bot.answer_callback_query(call.id, "লিংক: " + INVITE_LINK, show_alert=True)
    else:
        bot.answer_callback_query(call.id, "আরও রেফার করুন!", show_alert=True)

@bot.channel_post_handler(content_types=['text', 'photo'])
def handle_channel_post(message):
    ch_id = str(message.chat.id)
    ctype = 'main' if ch_id == CHANNEL_ONE else ('private' if ch_id == CHANNEL_TWO else 'movie')
    save_post(message.text or message.caption, message.message_id, 'text', ctype)

# --- সার্ভার লুপ ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.infinity_polling(none_stop=True)
