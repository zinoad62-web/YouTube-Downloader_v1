import os
import telebot
from yt_dlp import YoutubeDL

# استبدل النص بين التنصيص بتوكن بوتك من BotFather
TOKEN = "8932809251:AAExxj0ORQhI_tFWY6wsbzmjJYgtlegNb_o"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك! 🎬\nأرسل لي أي رابط فيديو من يوتيوب وسأقوم بتنزيله لك.")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        bot.reply_to(message, "الرجاء إرسال رابط صحيح.")
        return

    msg = bot.reply_to(message, "⏳ جاري تحميل الفيديو، انتظر لحظة...")

    ydl_opts = {
        'format': 'best',
        'outtmpl': 'video.%(ext)s',
        'max_filesize': 50 * 1024 * 1024,  # حد أقصى 50 ميجابايت للتليجرام
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        with open(filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption="تم التنزيل بنجاح! ✨")

        os.remove(filename)  # حذف الملف من الخادم بعد الإرسال
        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ أثناء التنزيل: {str(e)}", message.chat.id, msg.message_id)

bot.infinity_polling()
