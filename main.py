
import os
from threading import Thread
from flask import Flask
import telebot
from yt_dlp import YoutubeDL

# --- خادم الويب الوهمي لحفظ البوت يعملاً 24/7 على Render ---
app = Flask('')


@app.route('/')
def home():
  return 'Bot is alive!'


def run():
  app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


def keep_alive():
  t = Thread(target=run)
  t.start()


# --- كود البوت الخاص بك ---
TOKEN = '8932809251:AAExxj0ORQhI_tFWY6wsbzmjJYgtlegNb_o'
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
  bot.reply_to(message, 'أهلاً بك! قم بإرسال رابط الفيديو لتنزيله.')


@bot.message_handler(func=lambda message: True)
def download_video(message):
  url = message.text
  if 'youtube.com' in url or 'youtu.be' in url:
    bot.reply_to(message, 'جاري التحميل...')
    # كود التحميل بـ yt-dlp الخاص بك
  else:
    bot.reply_to(message, 'أرسل رابط يوتيوب صحيح.')


if __name__ == '__main__':
  keep_alive()  # تشغيل خادم الويب
  bot.infinity_polling()  # تشغيل البوت بدون توقف
