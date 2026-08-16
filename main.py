import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import yt_dlp

TOKEN = "8932809251:AAExxj0ORQhI_tFWY6wsbzmjJYgtlegNb_o"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

URL = "https://youtube-bot-pig5.onrender.com/"

user_data = {}

# دالة لتنظيف وتحويل روابط يوتيوب والشورتس
def clean_youtube_url(url):
    if "youtube.com/shorts/" in url:
        url = url.replace("youtube.com/shorts/", "youtube.com/watch?v=")
    if "youtu.be/" in url:
        url = url.replace("youtu.be/", "youtube.com/watch?v=")
    url = url.split("?")[0]
    return url

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
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

    # إعدادات محاكاة الهواتف لتجاوز حظر Render IP
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb']
            }
        },
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
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

    except Exception as e:
        bot.send_message(chat_id, "فشل التحميل. قد يكون حجم الفيديو يتجاوز 50MB المسموحة في تلجرام.")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=URL + TOKEN)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
