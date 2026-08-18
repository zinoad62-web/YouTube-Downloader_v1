import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import yt_dlp

# ⚠️ قم بتغيير التوكن فوراً من BotFather لأن القديم تم كشفه!
TOKEN = os.environ.get("BOT_TOKEN", "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_data = {}

@app.route('/')
def home():
    return "Bot is running successfully!"

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! 🎬\nأرسل لي أي رابط (YouTube, TikTok, Instagram, Facebook, Twitter...) وسأقوم بجلبه لك.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "يرجى إرسال رابط صحيح يبدأ بـ http أو https")
        return

    msg = bot.reply_to(message, "جاري فحص الرابط ومعالجة الفيديو... ⏳")

    # إعدادات عامة تناسب جميع المواقع
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        # لتجاوز حظر يوتيوب على Render، يفضل إضافة ملف cookies.txt في مجلد المشروع
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise Exception("فشل في استخراج البيانات")
                
            title = info.get('title', 'فيديو بدون عنوان')

        user_data[message.chat.id] = {'url': url, 'title': title}

        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("🎬 فيديو (أعلى جودة)", callback_data="q_best"),
            InlineKeyboardButton("📱 فيديو (جودة متوسطة)", callback_data="q_480"),
            InlineKeyboardButton("🎵 MP3 (صوت فقط)", callback_data="q_mp3")
        )

        bot.edit_message_text(
            f"📹 **{title[:60]}**\n\nاختر الصيغة والجودة المطلوبة:", 
            message.chat.id, 
            msg.message_id, 
            parse_mode="Markdown", 
            reply_markup=markup
        )

    except Exception as e:
        bot.edit_message_text(
            "❌ تعذر جلب الفيديو.\nتأكد من صحة الرابط، أو أن الحساب ليس خاصاً (Private).", 
            message.chat.id, 
            msg.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('q_'))
def process_download(call):
    chat_id = call.message.chat.id
    data = user_data.get(chat_id)

    if not data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أعد إرسال الرابط.")
        return

    quality = call.data.split('_')[1]
    url = data['url']
    file_prefix = f"download_{chat_id}"

    bot.edit_message_text("جاري التحميل والمعالجة... ⏳", chat_id, call.message.message_id)

    # إعدادات التحميل الموحدة
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'max_filesize': 50 * 1024 * 1024, # حد تلجرام 50 ميجابايت
    }

    if quality == 'mp3':
        file_path = f"{file_prefix}.mp3"
        ydl_opts.update({
            'format': 'bestaudio/best',
            'outtmpl': file_prefix,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    elif quality == '480':
        file_path = f"{file_prefix}.mp4"
        ydl_opts.update({
            'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best',
            'outtmpl': file_path,
        })
    else:
        file_path = f"{file_prefix}.mp4"
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': file_path,
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # البحث عن الملف المحمل في حال تغير الامتداد تلقائياً
        final_file = file_path
        if not os.path.exists(final_file):
            for file in os.listdir('.'):
                if file.startswith(file_prefix):
                    final_file = file
                    break

        bot.send_chat_action(chat_id, 'upload_document')
        
        with open(final_file, 'rb') as f:
            if quality == 'mp3':
                bot.send_audio(chat_id, f, caption="تم التحميل بنجاح! 🎵")
            else:
                bot.send_video(chat_id, f, caption="تم التحميل بنجاح! 🎉", supports_streaming=True)

        # تنظيف الملفات بعد الإرسال
        if os.path.exists(final_file):
            os.remove(final_file)

    except Exception as e:
        bot.send_message(chat_id, "❌ فشل التحميل. قد يكون حجم الفيديو أكبر من 50MB أو أن الموقع يحظر السيرفر.")

    finally:
        user_data.pop(chat_id, None)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
