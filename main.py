import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import yt_dlp

TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
BOT_URL = "https://youtube-bot-pig5.onrender.com"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_data = {}

try:
    bot.remove_webhook()
    bot.set_webhook(url=f"{BOT_URL}/{TOKEN}")
except Exception as e:
    print(f"Error setting webhook: {e}")

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Forbidden", 403

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! 🎬\nأرسل لي رابط أي فيديو وسأقوم بجلبه لك.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text.strip()

    if not url.startswith(("http://", "https://")):
        bot.reply_to(message, "يرجى إرسال رابط صحيح يبدأ بـ http أو https")
        return

    msg = bot.reply_to(message, "جاري فحص الرابط وإحضار الفيديو... ⏳")

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("فشل في جلب البيانات")
            title = info.get('title', 'فيديو بدون عنوان')

        user_data[message.chat.id] = {'url': url, 'title': title}

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📥 تحميل الفيديو", callback_data="q_video"),
            InlineKeyboardButton("🎵 تحميل صوت MP3", callback_data="q_mp3")
        )

        bot.edit_message_text(
            f"📹 **{title[:50]}**\n\nاختر الصيغة المطلوب تحميلها:", 
            message.chat.id, 
            msg.message_id, 
            parse_mode="Markdown", 
            reply_markup=markup
        )

    except Exception as e:
        bot.edit_message_text(
            "❌ تعذر جلب الفيديو.\nتأكد من صحة الرابط أو أن الحساب ليس خاصاً (Private).", 
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

    action = call.data.split('_')[1]
    url = data['url']
    file_prefix = f"file_{chat_id}"

    bot.edit_message_text("جاري التحميل والإرسال إلى تلجرام... ⏳", chat_id, call.message.message_id)

    ydl_opts = {
        'quiet': True,
        'outtmpl': f"{file_prefix}.%(ext)s",
        'max_filesize': 50 * 1024 * 1024,
    }

    if action == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = 'best[ext=mp4]/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        bot.send_chat_action(chat_id, 'upload_document')
        
        with open(filename, 'rb') as f:
            if action == 'mp3':
                bot.send_audio(chat_id, f, caption="تم التحميل بنجاح! 🎵")
            else:
                bot.send_video(chat_id, f, caption="تم التحميل بنجاح! 🎉")

        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        bot.send_message(chat_id, "❌ فشل التحميل. قد يكون حجم الفيديو أكبر من 50MB.")

    finally:
        user_data.pop(chat_id, None)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
                raise Exception("فشل في جلب البيانات")
            title = info.get('title', 'فيديو بدون عنوان')

        user_data[message.chat.id] = {'url': url, 'title': title}

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📥 تحميل الفيديو", callback_data="q_video"),
            InlineKeyboardButton("🎵 تحميل صوت MP3", callback_data="q_mp3")
        )

        bot.edit_message_text(
            f"📹 **{title[:50]}**\n\nاختر الصيغة المطلوب تحميلها:", 
            message.chat.id, 
            msg.message_id, 
            parse_mode="Markdown", 
            reply_markup=markup
        )

    except Exception as e:
        bot.edit_message_text(
            "❌ تعذر جلب الفيديو.\nتأكد من صحة الرابط أو أن الحساب ليس خاصاً (Private).", 
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

    action = call.data.split('_')[1]
    url = data['url']
    file_prefix = f"file_{chat_id}"

    bot.edit_message_text("جاري التحميل والإرسال إلى تلجرام... ⏳", chat_id, call.message.message_id)

    ydl_opts = {
        'quiet': True,
        'outtmpl': f"{file_prefix}.%(ext)s",
        'max_filesize': 50 * 1024 * 1024,
    }

    if action == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = 'best[ext=mp4]/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        bot.send_chat_action(chat_id, 'upload_document')
        
        with open(filename, 'rb') as f:
            if action == 'mp3':
                bot.send_audio(chat_id, f, caption="تم التحميل بنجاح! 🎵")
            else:
                bot.send_video(chat_id, f, caption="تم التحميل بنجاح! 🎉")

        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        bot.send_message(chat_id, "❌ فشل التحميل. قد يكون حجم الفيديو أكبر من 50MB.")

    finally:
        user_data.pop(chat_id, None)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
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
