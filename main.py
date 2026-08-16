import os
import telebot
from flask import Flask, request
import yt_dlp

TOKEN = "8932809251:AAExxj0ORQhI_tFWY6wsbzmjJYgtlegNb_o"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

URL = "https://youtube-bot-pig5.onrender.com/"

@app.route('/')
def home():
    return "Bot is running via Webhook!"

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# دالة الاستجابة لأمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أرسل لي رابط فيديو (يوتيوب، تيك توك، إلخ) وسأقوم بتحميله لك فوراً 🎬")

# دالة معالجة وتحميل الفيديو من الرابط
@bot.message_handler(func=lambda message: True)
def download_and_send_video(message):
    url = message.text.strip()
    
    if not url.startswith("http://") and not url.startswith("https://"):
        bot.reply_to(message, "يرجى إرسال رابط فيديو صحيح يبدأ بـ http أو https")
        return

    msg = bot.reply_to(message, "جاري تحميل الفيديو، انتظر لحظات... ⏳")

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'video.mp4',
        'quiet': True,
        'max_filesize': 50 * 1024 * 1024  # الحد الأقصى 50 ميجابايت لتناسب تلجرام
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # إرسال الفيديو للمستخدم
        with open('video.mp4', 'rb') as video:
            bot.send_video(message.chat.id, video, caption="تم التحميل بنجاح! 🎉")
            
        # حذف الملف بعد الإرسال لتوفير المساحة
        if os.path.exists('video.mp4'):
            os.remove('video.mp4')
            
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء التحميل: قد يكون حجم الفيديو كبيراً جداً أو الرابط غير مدعوم.")
        if os.path.exists('video.mp4'):
            os.remove('video.mp4')

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=URL + TOKEN)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
