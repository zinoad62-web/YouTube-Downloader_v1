import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import yt_dlp

TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
URL = "https://youtube-bot-pig5.onrender.com/"
CHANNEL_USERNAME = "@zinoad6162" # ضع معرف قناتك هنا

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

@app.route('/')
def home(): return "Bot is working!"

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً! أرسل لي أي رابط (يوتيوب، تيك توك، إلخ) وسأعطيك رابط التحميل المباشر.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("اشترك في القناة 📢", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        bot.reply_to(message, "يجب الاشتراك في القناة أولاً:", reply_markup=markup)
        return

    raw_url = message.text.strip()
    msg = bot.reply_to(message, "⏳ جاري استخراج الرابط...")
    
    ydl_opts = {
        'quiet': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(raw_url, download=False)
            # الحصول على الرابط المباشر
            direct_url = info.get('url') or (info.get('formats')[-1]['url'] if info.get('formats') else None)
            title = info.get('title', 'فيديو')
        
        if direct_url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📥 اضغط هنا للتحميل/المشاهدة", url=direct_url))
            bot.edit_message_text(f"✅ تم استخراج الرابط بنجاح:\n\n{title[:50]}", message.chat.id, msg.message_id, reply_markup=markup)
        else:
            bot.edit_message_text("❌ تعذر استخراج رابط مباشر. حاول مع فيديو آخر.", message.chat.id, msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"⚠️ خطأ: {str(e)}", message.chat.id, msg.message_id)

if __name__ == '__main__':
    try:
        bot.remove_webhook()
        bot.set_webhook(url=URL + TOKEN)
    except: pass
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
