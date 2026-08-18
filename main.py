import os, telebot, yt_dlp
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request

TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
URL = "https://youtube-bot-pig5.onrender.com/"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_data = {}

def clean_youtube_url(url):
    if "youtube.com/shorts/" in url: url = url.replace("youtube.com/shorts/", "youtube.com/watch?v=")
    if "youtu.be/" in url: url = url.replace("youtu.be/", "youtube.com/watch?v=")
    return url.split("?")[0]

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
    raw_url = message.text.strip()
    url = clean_youtube_url(raw_url)
    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "يرجى إرسال رابط صحيح يبدأ بـ http أو https")
        return
    msg = bot.reply_to(message, "جاري فحص الرابط وتجاوز حماية يوتيوب... ⏳")
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'mweb']}}, 'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15'}
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('q_'))
def process_download(call):
    chat_id = call.message.chat.id
    data = user_data.get(chat_id)
    if not data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أعد إرسال الرابط.")
        return
    quality = call.data.split('_')[1]
    url = data['url']
    file_path = f"file_{chat_id}"
    bot.edit_message_text(f"جاري التحميل بجودة {quality}... ⏳", chat_id, call.message.message_id)
    common_opts = {'quiet': True, 'no_warnings': True, 'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'mweb']}}, 'max_filesize': 50 * 1024 * 1024}
    if quality == 'mp3':
        file_path += '.mp3'
        ydl_opts = {**common_opts, 'format': 'bestaudio/best', 'outtmpl': file_path}
    else:
        file_path += '.mp4'
        ydl_opts = {**common_opts, 'format': f'best[height<={quality}][ext=mp4]/best', 'outtmpl': file_path}
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
    else:
        file_path += '.mp4'
        ydl_opts = {
            **common_opts,
            'format': f'best[height<={quality}][ext=mp4]/best',
            'outtmpl': file_path,
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
    except Exception:
        pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
            title = info.get('title', 'فيديو')

        user_data[message.chat.id] = {'url': url, 'title': title}

        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("🎬 عالية (720p)", callback_data="q_720"),
            InlineKeyboardButton("📱 متوسطة (480p)", callback_data="q_480"),
            InlineKeyboardButton("⚡ منخفضة (360p)", callback_data="q_360"),
            InlineKeyboardButton("🎵 MP3 (صوت فقط)", callback_data="q_mp3")
        )

        bot.edit_message_text(f"📹 **{title[:50]}...**\n\nاختر الجودة المطلوبة:", 
                              message.chat.id, msg.message_id, parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        bot.edit_message_text("تعذر جلب الفيديو. يوتيوب يحظر السيرفرات المجانية أو أن الفيديو محمي.", message.chat.id, msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('q_'))
def process_download(call):
    chat_id = call.message.chat.id
    data = user_data.get(chat_id)

    if not data:
        bot.answer_callback_query(call.id, "انتهت الجلسة، أعد إرسال الرابط.")
        return

    quality = call.data.split('_')[1]
    url = data['url']
    file_path = f"file_{chat_id}"

    bot.edit_message_text(f"جاري التحميل بجودة {quality}... ⏳", chat_id, call.message.message_id)

    common_opts = {
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb']
            }
        },
        'max_filesize': 50 * 1024 * 1024
    }

    if quality == 'mp3':
        file_path += '.mp3'
        ydl_opts = {
            **common_opts,
            'format': 'bestaudio/best',
            'outtmpl': file_path,
        }
    else:
        file_path += '.mp4'
        ydl_opts = {
            **common_opts,
            'format': f'best[height<={quality}][ext=mp4]/best',
            'outtmpl': file_path,
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

    except Exception as e:
        bot.send_message(chat_id, "فشل التحميل. قد يكون حجم الفيديو يتجاوز 50MB المسموحة في تلجرام.")

    finally:
        user_data.pop(chat_id, None)

if __name__ == '__main__':
    try:
        bot.remove_webhook()
        bot.set_webhook(url=URL + TOKEN)
    except Exception:
        pass
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

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
