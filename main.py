import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import yt_dlp

TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
URL = "https://youtube-bot-pig5.onrender.com/"
CHANNEL_USERNAME = "@zinoad6162"  # ⚠️ ضع معرف قناتك هنا (مثلاً @MyChannel)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_data = {}

def clean_youtube_url(url):
    url = url.replace("youtube.com/shorts/", "youtube.com/watch?v=").replace("youtu.be/", "youtube.com/watch?v=")
    return url.split("?")[0]

# دالة للتحقق من اشتراك المستخدم في القناة
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أرسل لي رابط أي فيديو وسأقوم بجلبه لك 🎬")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    user_id = message.from_user.id
    
    # 1. التحقق من الاشتراك الإجباري أولاً
    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("اشترك في القناة 📢", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        markup.add(InlineKeyboardButton("تحقق من الاشتراك ✅", callback_data="check_sub"))
        
        bot.reply_to(
            message, 
            "عذراً عزيزي، يجب عليك الاشتراك في قناتنا أولاً لتتمكن من استخدام البوت 👇", 
            reply_markup=markup
        )
        return

    # 2. استكمال عملية التحميل العادية إذا كان مشتركاً
    raw_url = message.text.strip()
    url = clean_youtube_url(raw_url)
    if not url.startswith(("http://", "https://")):
        bot.reply_to(message, "يرجى إرسال رابط صحيح يبدأ بـ http أو https")
        return
        
    msg = bot.reply_to(message, "جاري فحص الرابط وتجاوز حماية يوتيوب... ⏳")
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'mweb']}}, 
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'فيديو') if info else 'فيديو'
        
        user_data[message.chat.id] = {'url': url, 'title': title}
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("🎬 عالية (720p)", callback_data="q_720"),
            InlineKeyboardButton("📱 متوسطة (480p)", callback_data="q_480"),
            InlineKeyboardButton("⚡ منخفضة (360p)", callback_data="q_360"),
            InlineKeyboardButton("🎵 MP3 (صوت فقط)", callback_data="q_mp3")
        )
        bot.edit_message_text(f"📹 **{title[:50]}...**\n\nاختر الجودة المطلوبة:", message.chat.id, msg.message_id, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        bot.edit_message_text("تعذر جلب الفيديو. يوتيوب يحظر السيرفرات المجانية أو أن الفيديو محمي.", message.chat.id, msg.message_id)

# معالجة الضغط على زر "تحقق من الاشتراك"
@bot.callback_query_handler(func=lambda call: call.data == 'check_sub')
def process_check_sub(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "شكراً لاشتراكك! يمكنك الآن إرسال الرابط.", show_alert=True)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(call.message.chat.id, "ممتاز! أرسل رابط الفيديو الذي تريد تحميله الآن 🎬")
    else:
        bot.answer_callback_query(call.id, "لم تقم بالاشتراك في القناة بعد! ❌", show_alert=True)

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
    
    bot.edit_message_text(f"جاري التحميل بجودة {quality}... ⏳", chat_id, call.message.message_id)
    fmt = 'bestaudio/best' if quality == 'mp3' else f'best[height<={quality}][ext=mp4]/best'
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'mweb']}}, 
        'max_filesize': 50 * 1024 * 1024, 
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
                bot.send_video(chat_id, f, caption=f"تم التحميل بجودة {quality}p! 🎉")
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        bot.send_message(chat_id, "فشل التحميل. قد يكون حجم الفيديو يتجاوز 50MB المسموحة في تلجرام.")
    finally:
        user_data.pop(chat_id, None)

if __name__ == '__main__':
    try:
        bot.remove_webhook()
        bot.set_webhook(url=URL + TOKEN)
    except Exception: pass
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
