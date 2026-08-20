import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import yt_dlp

TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
URL = "https://youtube-bot-pig5.onrender.com/"
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
    bot.reply_to(message, "أهلاً بك في بوت التحميل الشامل! 🎬\nأرسل لي رابط أي فيديو (يوتيوب، تيك توك، انستغرام...) وسأتينا لك بالخيارات.")

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
        
    msg = bot.reply_to(message, "⏳ جاري فحص الرابط واستخراج معلومات الفيديو...")
    
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
            InlineKeyboardButton("🎵 MP3 (صوت فقط)", callback_data="q_mp3")
        )
        bot.edit_message_text(f"📹 **{title[:50]}...**\n\nاختر الجودة المطلوبة للتحميل:", message.chat.id, msg.message_id, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        bot.edit_message_text("❌ تعذر جلب الفيديو. تأكد أن الرابط عام وليس من حساب خاص.", message.chat.id, msg.message_id)

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
    
    file_path = f"file_{chat_id}.mp3" if quality == 'mp3' else f"file_{chat_id}.mp4"
    bot.edit_message_text(f"⏳ جاري تنزيل وتجهيز الملف...", chat_id, call.message.message_id)
    
    if quality == 'mp3':
        fmt = 'bestaudio/best'
    elif quality == 'high':
        fmt = 'best[ext=mp4]/best'
    else:
        fmt = 'worst[ext=mp4]/worst'
        
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'extractor_args': {'youtube': {'player_client': ['android']}}, 
        'max_filesize': 50 * 1024 * 1024, # حد أقصى 50 ميغا لكي لا ينهار السيرفر المجاني
        'format': fmt, 
        'outtmpl': file_path
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        bot.send_chat_action(chat_id, 'upload_document')
        with open(file_path, 'rb') as f:
            if quality == 'mp3':
                bot.send_audio(chat_id, f, caption="تم التحميل بنجاح! 🎵")
            else:
                bot.send_video(chat_id, f, caption="تم التحميل بنجاح! 🎉")
    except Exception as e:
        bot.send_message(chat_id, "❌ فشل التحميل. قد يكون حجم الفيديو أكبر من 50MB أو أن المنصة حظرت الرابط.")
    finally:
        # 🧹 تنظيف الذاكرة: حذف الملف من السيرفر فوراً بعد الإرسال سواء نجح أو فشل
        if os.path.exists(file_path):
            os.remove(file_path)
        user_data.pop(chat_id, None)

if __name__ == '__main__':
    try:
        bot.remove_webhook()
        bot.set_webhook(url=URL + TOKEN)
    except: pass
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
