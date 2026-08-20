import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import yt_dlp

TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
URL = "https://youtube-downloader-v1.onrender.com/"
CHANNEL_USERNAME = "@zinoad6162"  # ⚠️ ضع معرف قناتك هنا

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_data = {}

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

@app.route('/')
def home(): return "Bot is running!"

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك في بوت التحميل السريع 🚀\nأرسل لي رابط أي فيديو وسأستخرج لك روابط التحميل فوراً وبدون تأخير.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("اشترك في القناة 📢", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        markup.add(InlineKeyboardButton("تحقق من الاشتراك ✅", callback_data="check_sub"))
        bot.reply_to(message, "يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت 👇", reply_markup=markup)
        return

    raw_url = message.text.strip()
    if not raw_url.startswith(("http://", "https://")):
        bot.reply_to(message, "يرجى إرسال رابط صحيح 🔗")
        return
        
    msg = bot.reply_to(message, "⏳ جاري فحص الرابط واستخراج خيارات التحميل...")
    
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'extractor_args': {'youtube': {'player_client': ['android']}}, 
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(raw_url, download=False)
            title = info.get('title', 'فيديو') if info else 'فيديو'
        
        user_data[message.chat.id] = {'url': raw_url, 'title': title}
        
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("🎬 جودة عالية", callback_data="q_high"),
            InlineKeyboardButton("⚡ جودة منخفضة", callback_data="q_low"),
            InlineKeyboardButton("🎵 صوت فقط (MP3)", callback_data="q_mp3")
        )
        bot.edit_message_text(f"📹 **{title[:50]}...**\n\nاختر الجودة المطلوبة:", message.chat.id, msg.message_id, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        bot.edit_message_text("❌ تعذر جلب معلومات الفيديو. تأكد أن الرابط عام.", message.chat.id, msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'check_sub')
def process_check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "شكراً لاشتراكك!", show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "ممتاز! أرسل رابط الفيديو الآن 🎬")
    else:
        bot.answer_callback_query(call.id, "لم تقم بالاشتراك بعد! ❌", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('q_'))
def process_download(call):
    chat_id = call.message.chat.id
    data = user_data.get(chat_id)
    if not data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أعد إرسال الرابط.")
        return
        
    quality = call.data.split('_')[1]
    url = data['url']
    
    bot.edit_message_text(f"⏳ جاري استخراج رابط التحميل السريع...", chat_id, call.message.message_id)
    
    if quality == 'high':
        fmt = 'best[ext=mp4]/best'
    elif quality == 'low':
        fmt = 'worst[ext=mp4]/worst'
    else:
        fmt = 'bestaudio/best'
        
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'extractor_args': {'youtube': {'player_client': ['android']}}, 
        'format': fmt,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get('url')
            
        if not direct_url:
            raise Exception("No direct URL")
            
        if quality == 'mp3':
            bot.send_message(chat_id, f"🎵 **رابط الصوت المباشر:**\n{direct_url}", parse_mode="Markdown")
        else:
            bot.send_video(chat_id, direct_url, caption="تم استخراج الفيديو بنجاح بسرعة فائقة! 🚀")
            
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except: pass
        
    except Exception as e:
        bot.edit_message_text("❌ فشل استخراج الرابط المباشر لهذا الفيديو.", chat_id, call.message.message_id)
    finally:
        user_data.pop(chat_id, None)

if __name__ == '__main__':
    try:
        bot.remove_webhook()
        bot.set_webhook(url=URL + TOKEN)
    except: pass
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
