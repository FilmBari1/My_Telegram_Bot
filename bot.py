import telebot
from telebot import types
import sqlite3
import re

# ==================== CONFIGURATION (ALL SET) ====================
API_TOKEN = '8720201406:AAFlNvQ-tTErzXJ8eV-MkkrTd3ns0qlY6DE'
ADMIN_ID = 8513606329

CHANNEL_ONE = '-1003700030998'    # মেইন পাবলিক চ্যানেল (১ম চ্যানেল)
CHANNEL_TWO = '-1004486324779'    # সেকেন্ড প্রাইভেট চ্যানেল (২য় চ্যানেল)
CHANNEL_MOVIE = '-1003996193613'  # নতুন মুভি চ্যানেল (৩য় চ্যানেল)

INVITE_LINK = 'https://t.me/+bNSTXDGq9Xc4NmY9'  # প্রাইভেট চ্যানেলের জয়েন রিকোয়েস্ট লিংক
MAIN_CHANNEL_PUBLIC_LINK = 'https://t.me/MovieGor'  # মেইন পাবলিক চ্যানেল লিংক
MOVIE_CHANNEL_LINK = 'https://t.me/MovieGorBD'  # মুভি চ্যানেল লিংক

# 🔗 ২টি আলাদা ওয়েবসাইট লিংক (মুভি এবং ভিডিওর জন্য)
MASTER_WEB_LINK = 'https://filmbari1.github.io/MovieGor/?vid=-OvB3edV7fuCrJ7OnY48' # সাধারণ ভিডিও লিংক
MOVIE_WEB_LINK = 'https://filmbari1.github.io/MovieGor/' # মুভি দেখার লিংক
# =================================================================

bot = telebot.TeleBot(API_TOKEN)
DB_FILE = "bot_master_database.db"
admin_states = {}

# ------ ডেটাবেজ কোর ফাংশনসমূহ ------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")  # এন্টি-লক WAL মোড সচল
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, 
                        referred_by INTEGER,
                        refer_count INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        text TEXT, 
                        msg_id INTEGER, 
                        content_type TEXT,
                        file_id TEXT,
                        channel_type TEXT DEFAULT 'main')''')
    
    # অটো-কলাম ভেরিফায়ার ও ফিক্সার (যাতে no such column এরর না আসে)
    try:
        cursor.execute("SELECT channel_type FROM posts LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE posts ADD COLUMN channel_type TEXT DEFAULT 'main'")
            conn.commit()
            print("🚀 'channel_type' কলামটি সফলভাবে ডেটাবেজে ভেরিফাই ও যুক্ত হয়েছে!")
        except Exception as e:
            print(f"কলাম তৈরিতে সমস্যা: {e}")
            
    conn.commit()
    conn.close()

init_db()

def delete_invalid_post(post_title, channel_type):
    """চ্যানেল থেকে ডিলিট হওয়া পোস্ট ডেটাবেজ থেকেও মুছে ফেলার সেফ ফাংশন"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM posts WHERE text = ? AND channel_type = ?", (post_title, channel_type))
        conn.commit()
        print(f"🗑️ লাইভ না থাকায় পোস্ট ডেটাবেজ থেকে ক্লিনড: {post_title} ({channel_type})")
    except Exception as e:
        print(f"Error cleaning post: {e}")
    finally:
        if conn:
            conn.close()

def is_post_alive(channel_id, msg_id):
    """পোস্টটি চ্যানেলে এখনও আছে নাকি ডিলিট হয়ে গেছে তা রিয়েল-টাইমে চেক করার লজিক"""
    try:
        check_msg = bot.forward_message(chat_id=ADMIN_ID, from_chat_id=channel_id, message_id=msg_id, disable_notification=True)
        if check_msg:
            try:
                bot.delete_message(chat_id=ADMIN_ID, message_id=check_msg.message_id)
            except:
                pass
            return True
    except:
        return False
    return False

def save_user(user_id, referrer_id=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, referrer_id))
            if referrer_id:
                cursor.execute("UPDATE users SET refer_count = refer_count + 1 WHERE user_id = ?", (referrer_id,))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving user: {e}")

def get_total_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def get_all_user_ids():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()
        return [u[0] for u in users]
    except:
        return []

def get_user_refers(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT refer_count FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else 0
    except:
        return 0

def save_post(raw_text, message_id, content_type, channel_type, file_id=None):
    try:
        if raw_text:
            clean_title = raw_text
            clean_title = clean_title.replace("এখানে চাপুন:", "")
            clean_title = clean_title.replace("MovieGor", "")
            clean_title = clean_title.replace("-", "")
            
            urls = re.findall(r'(https?://[^\s]+)', clean_title)
            for url in urls:
                clean_title = clean_title.replace(url, "")
                
            clean_title = clean_title.replace('\n', ' ').strip().lower()
            clean_title = re.sub(r'\s+', ' ', clean_title)
            
            if clean_title == "" or clean_title == " ":
                clean_title = "untitled_post"

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO posts (text, msg_id, content_type, file_id, channel_type) VALUES (?, ?, ?, ?, ?)", 
                           (clean_title, message_id, content_type, file_id, channel_type))
            conn.commit()
            conn.close()
            print(f"✅ {channel_type} থেকে নতুন পোস্ট ট্র্যাক হয়েছে: {clean_title}")
    except Exception as e:
        print(f"Error saving post: {e}")


# ------ বট কমান্ড ও হ্যান্ডলার সেকশন ------

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    command_text = message.text.split()
    
    referrer_id = None
    if len(command_text) > 1:
        try:
            possible_referrer = int(command_text[1])
            if possible_referrer != user_id:
                referrer_id = possible_referrer
        except:
            pass

    save_user(user_id, referrer_id)
    
    welcome_text = (
        "আমাদের অল-ইন-ওয়ান ভিডিও ও মুভি বক্সে স্বাগতম!\n"
        "বটটি ব্যবহার করার জন্য ধন্যবাদ 😊\n\n"
        "আপনি যেকোনো ভাইরাল ভিডিও কিংবা মুভির নাম লিখে এখানে সার্চ করুন।"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.chat.id == ADMIN_ID:
        total_users = get_total_users()
        stats_text = (
            "📊 **বট লাইভ স্ট্যাটাস (Admin Dashboard)**\n"
            "------------------------------------\n"
            "👥 **মোট একটিভ ইউজার:** {} জন\n\n"
            "📢 **অ্যাডমিন নোটিশ:**\n"
            "সব ইউজারের কাছে প্রমোশনাল পোস্ট পাঠাতে টাইপ করুন: /broadcast"
        ).format(total_users)
        bot.send_message(ADMIN_ID, stats_text, parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def start_broadcast(message):
    if message.chat.id == ADMIN_ID:
        admin_states[ADMIN_ID] = "WAITING_FOR_BROADCAST_POST"
        bot.send_message(ADMIN_ID, "📢 **প্রমোশন মোড অ্যাক্টিভেটেড!**\n\n"
                                   "আপনি যে পোস্টটি সব ইউজারের কাছে পাঠাতে চান, সেটি এখন এখানে সেন্ড বা ফরোয়ার্ড করুন:")

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and admin_states.get(ADMIN_ID) == "WAITING_FOR_BROADCAST_POST", content_types=['text', 'photo', 'video', 'document', 'audio'])
def execute_broadcast(message):
    admin_states[ADMIN_ID] = None  
    all_users = get_all_user_ids()
    
    bot.send_message(ADMIN_ID, f"🔄 মোট {len(all_users)} জন ইউজারের কাছে প্রমোশন পাঠানো শুরু হয়েছে। দয়া করে অপেক্ষা করুন...")
    
    success_count = 0
    for u_id in all_users:
        try:
            bot.copy_message(chat_id=u_id, from_chat_id=ADMIN_ID, message_id=message.message_id)
            success_count += 1
        except:
            continue  
            
    bot.send_message(ADMIN_ID, f"✅ **প্রমোশন সফলভাবে সম্পন্ন হয়েছে!**\n\n📊 মোট **{success_count}** জনের ইনবক্সে পোস্টটি পৌঁছে গেছে।")


# 🎯 শক্তিশালী ও ফিক্সড গ্লোবাল সার্চ হ্যান্ডলার (আংশিক ও সম্পূর্ণ নাম দিয়ে মুভি খোঁজার ১০০% গ্যারান্টি)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def search_post(message):
    query = message.text.lower().strip()
    user_id = message.chat.id
    save_user(user_id)

    if query.startswith('/'):
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 🔍 যেকোনো আংশিক বা ফুল ম্যাচ খুঁজে বের করার শক্তিশালী SQL কুয়েরি
        cursor.execute("SELECT text, channel_type, msg_id, content_type, file_id FROM posts WHERE text LIKE ?", ('%' + query + '%',))
        matched_rows = cursor.fetchall()
        conn.close()
        
        if not matched_rows:
            bot.reply_to(message, "দুঃখিত, এই নামে কোনো পোস্ট, ভিডিও বা মুভি আমাদের ডাটাবেজে পাওয়া যায়নি।")
            return

        valid_suggestions_sent = 0
        invalid_posts_to_clean = []
        processed_titles = set() # ডুপ্লিকেট মেসেজ রোধ করার জন্য সেফটি গার্ড

        for row in matched_rows:
            post_title, ch_type, msg_id, c_type, f_id = row
            
            # একই টাইটেল বারবার প্রসেস করা থেকে বিরত রাখার লজিক
            unique_key = f"{post_title}_{ch_type}"
            if unique_key in processed_titles:
                continue
            processed_titles.add(unique_key)

            # চ্যানেল আইডি ম্যাপিং ভেরিফিকেশন
            ch_id = CHANNEL_ONE if ch_type == 'main' else (CHANNEL_TWO if ch_type == 'private' else CHANNEL_MOVIE)
            
            # লাইভ স্ট্যাটাস চেক
            if not is_post_alive(ch_id, msg_id):
                invalid_posts_to_clean.append((post_title, ch_type))
                continue

            markup = types.InlineKeyboardMarkup()
            
            # 🎬 [কন্ডিশন ১]: যদি মুভি চ্যানেল থেকে ডেটা ম্যাচ করে (১০০% ফিক্সড)
            if ch_type == 'movie':
                btn_movie_web = types.InlineKeyboardButton("🌐 ডিরেক্ট মুভি ওয়েবসাইট", url=MOVIE_WEB_LINK)
                btn_movie_join = types.InlineKeyboardButton("📢 নতুন মুভি আপডেট পেতে জয়েন করুন", url=MOVIE_CHANNEL_LINK)
                markup.add(btn_movie_web)
                markup.add(btn_movie_join)
                search_caption = (
                    f"🎬 **কাঙ্ক্ষিত মুভি পাওয়া গেছে!**\n"
                    f"📌 নাম: {post_title.upper()}\n\n"
                    f"মুভিটি দেখার জন্য নিচের ওয়েবসাইটের বাটনে ক্লিক করুন।\n\n"
                    f"📢 **অ্যাডমিন নোটিশ:**\n"
                    f"আপনি যদি নিয়মিত নতুন নতুন সব মুভির আপডেট সবার আগে পেতে চান, তবে নিচে থাকা বাটনে ক্লিক করে আমাদের মুভি চ্যানেলে জয়েন করে রাখুন!"
                )
            
            # 📹 [কন্ডিশন ২]: সাধারণ ভিডিও ক্যাটাগরি (মেইন ও প্রাইভেট উভয় ক্ষেত্রে)
            else:
                # চেক করা হচ্ছে এই কন্টেন্টটি প্রাইভেট চ্যানেলেও আছে কিনা
                temp_conn = get_db_connection()
                temp_cursor = temp_conn.cursor()
                temp_cursor.execute("SELECT msg_id FROM posts WHERE channel_type = 'private' AND text = ?", (post_title,))
                has_private = temp_cursor.fetchone()
                temp_conn.close()

                if has_private and ch_type == 'main':
                    btn1 = types.InlineKeyboardButton("🌐 ডিরেক্ট ওয়েবসাইট থেকে দেখুন", url=MASTER_WEB_LINK)
                    btn2 = types.InlineKeyboardButton("🔒 টেলিগ্রামে ফ্রিতে দেখুন (২ শেয়ার)", callback_data=f"lockmenu_{msg_id}")
                    markup.add(btn1)
                    markup.add(btn2)
                    search_caption = (
                        f"🎬 **ভিডিও পাওয়া গেছে!**\n"
                        f"📌 টাইটেল: {post_title.upper()}\n\n"
                        f"ভিডিওটি দেখার জন্য নিচের যেকোনো একটি অপশন বেছে নিন:\n"
                        f"👉 ওয়েবসাইট থেকে সরাসরি দেখতে **১ম বাটনে** ক্লিক করুন।\n"
                        f"👉 টেলিগ্রামে ফ্রিতে দেখতে চাইলে **২য় বাটনে** ক্লিক করে টাস্ক পূরণ করুন।"
                    )
                elif ch_type == 'private':
                    btn_lock = types.InlineKeyboardButton("🔒 টেলিগ্রামে ফ্রিতে দেখুন (২ শেয়ার)", callback_data=f"lockmenu_{msg_id}")
                    markup.add(btn_lock)
                    search_caption = (
                        f"🎬 **ভিডিও পাওয়া গেছে!**\n"
                        f"📌 টাইটেল: {post_title.upper()}\n\n"
                        f"এই ভিডিওটি আমাদের প্রাইভেট গ্রুপে রয়েছে। টেলিগ্রামে সম্পূর্ণ ভিডিওটি ফ্রিতে দেখতে নিচের বাটনে ক্লিক করে ২ জন বন্ধুকে শেয়ার সম্পন্ন করুন! 🔥"
                    )
                else: # শুধু মেইন চ্যানেলে থাকলে
                    btn_web = types.InlineKeyboardButton("🌐 ডিরেক্ট ওয়েবসাইট থেকে দেখুন", url=MASTER_WEB_LINK)
                    btn_join = types.InlineKeyboardButton("📢 আমাদের মেইন চ্যানেলে জয়েন করুন", url=MAIN_CHANNEL_PUBLIC_LINK)
                    markup.add(btn_web)
                    markup.add(btn_join)
                    search_caption = (
                        f"🎬 **ভিডিও পাওয়া গেছে!**\n"
                        f"📌 টাইটেল: {post_title.upper()}\n\n"
                        f"ভিডিওটি সরাসরি ওয়েবসাইট থেকে দেখতে নিচের **১ম বাটনে** ক্লিক করুন।\n"
                        f"আমাদের সমস্ত নতুন ভিডিওর আপডেট সবার আগে পেতে **২য় বাটনে** ক্লিক করে মেইন চ্যানেলে জয়েন করে রাখুন! 😊"
                    )

            # থাম্বনেইল ছবি ভেরিফিকেশন সহ মেসেজ পাঠানো হচ্ছে
            try:
                if c_type == 'photo' and f_id:
                    bot.send_photo(chat_id=user_id, photo=f_id, caption=search_caption, parse_mode="Markdown", reply_markup=markup)
                else:
                    bot.send_message(user_id, search_caption, parse_mode="Markdown", reply_markup=markup)
                valid_suggestions_sent += 1
            except Exception as send_err:
                print(f"Error sending message to user: {send_err}")
                
        # ডিলিট হওয়া ক্যাশ ডাটা একবারে ব্যাকএন্ড থেকে ক্লিন করা হচ্ছে
        for invalid_title, channel_t in invalid_posts_to_clean:
            delete_invalid_post(invalid_title, channel_t)

        if valid_suggestions_sent == 0:
            bot.reply_to(message, "দুঃখিত, এই নামে কোনো পোস্ট বা ভিডিও আমাদের ডাটাবেজে পাওয়া যায়নি।")
        
    except Exception as e:
        bot.reply_to(message, "দুঃখিত, এই মুহূর্তে সিস্টেমে সমস্যা হচ্ছে। দয়া করে আবার সার্চ করুন।")
        print(f"Critical Search Error: {e}")

# 🔒 [২ জন শেয়ার টাস্ক এবং বাটন লজিক - সচল ও ফিক্সড]
@bot.callback_query_handler(func=lambda call: call.data.startswith('lockmenu_'))
def lock_menu(call):
    user_id = call.from_user.id
    msg_id = call.data.split('_')[1]
    
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    current_refers = get_user_refers(user_id)
    
    markup = types.InlineKeyboardMarkup()
    share_url = f"https://t.me/share/url?url={ref_link}&text=এখানে%20সব%20ভাইরাল%20ভিডিও%20এবং%20মুভি%20একসাথে%20পাওয়া%20যায়!%20একবার%20সার্চ%20করে%20দেখো%20🔥"
    btn_share = types.InlineKeyboardButton("🚀 বন্ধুদের সাথে শেয়ার করুন", url=share_url)
    btn_verify = types.InlineKeyboardButton("✅ ভেরিফাই করুন ও জয়েন লিংক নিন", callback_data=f"verify_{msg_id}")
    markup.add(btn_share)
    markup.add(btn_verify)
    
    lock_text = (
        "🔒 **টেলিগ্রাম ফ্রি অ্যাক্সেস লকড!**\n\n"
        "টেলিগ্রামে সম্পূর্ণ কন্টেন্টটি দেখতে হলে আপনাকে এই বটটি যেকোনো **২ জন বন্ধুকে** রেফার করতে হবে। তারা আপনার লিংকে জয়েন করলেই লক খুলে যাবে।\n\n"
        "📊 আপনার বর্তমান সফল রেফারেল: {}/২ জন\n\n"
        "নিচের বাটনে ক্লিক করে শেয়ার সম্পন্ন করুন এবং 'ভেরিফাই করুন' বাটনে চাপুন।"
    ).format(current_refers)
    
    try:
        bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id, caption=lock_text, parse_mode="Markdown", reply_markup=markup)
    except:
        try:
            bot.send_message(user_id, lock_text, parse_mode="Markdown", reply_markup=markup)
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('verify_'))
def verify_referral(call):
    user_id = call.from_user.id
    current_refers = get_user_refers(user_id)
    
    if current_refers >= 2:
        markup = types.InlineKeyboardMarkup()
        btn_vip = types.InlineKeyboardButton("VIP প্রাইভেট চ্যানেলে জয়েন করুন 🔗", url=INVITE_LINK)
        markup.add(btn_vip)
        
        success_text = (
            "✅ **অভিনন্দন! আপনার ২ জন রেফারেল সফল হয়েছে।**\n\n"
            "নিচের বাটনে ক্লিক করে আমাদের প্রাইভেট চ্যানেলে জয়েন রিকোয়েস্ট পাঠান। আপনার রিকোয়েস্ট এপ্রুভ হওয়ার সাথে সাথে সম্পূর্ণ ফাইলটি দেখতে পারবেন।"
        )
        try:
            bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id, caption=success_text, parse_mode="Markdown", reply_markup=markup)
        except:
            bot.send_message(user_id, success_text, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, f"আপনার লিংকে মাত্র {current_refers} জন জয়েন করেছে! ২ জন করতে হবে। আরও শেয়ার করুন।", show_alert=True)

# 📡 রিয়েল-টাইম ৩-চ্যানেল পোস্ট লিসেনার ও ট্র্যাকার
@bot.channel_post_handler(content_types=['text', 'photo'])
def handle_channel_post(message):
    current_channel = str(message.chat.id)
    caption = message.text if message.text else message.caption
    
    if not caption:
        return
        
    content_type = 'text'
    file_id = None
    if message.photo:
        content_type = 'photo'
        file_id = message.photo[-1].file_id

    # ৩টি চ্যানেল থেকেই রিয়েল-টাইমে পোস্ট ডাটাবেজে সঠিক টাইপসহ সেভ করা হচ্ছে
    if current_channel == str(CHANNEL_ONE):
        save_post(caption, message.message_id, content_type, 'main', file_id)
        
    elif current_channel == str(CHANNEL_TWO):
        save_post(caption, message.message_id, content_type, 'private', file_id)
        
    elif current_channel == str(CHANNEL_MOVIE):
        save_post(caption, message.message_id, content_type, 'movie', file_id)

print("ভিডিও + মুভি অল-ইন-ওয়ান সিস্টেম সফলভাবে লাইভ হয়েছে...")
bot.polling(none_stop=True)