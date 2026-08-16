import telebot
from flask import Flask
from threading import Thread

# 1. إعداد خادم الويب لإبقاء البوت نشطاً على Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. إعداد البوت والتوكن
TOKEN = "8932809251:AAExxj0ORQhI_tFWY6wsbzmjJYgtlegNb_o"
bot = telebot.TeleBot(TOKEN)

# 3. دالة الاستجابة لأمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! البوت يعمل بنجاح الآن 🚀")

# 4. دالة الاستجابة للرسائل العامة أو الروابط
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"تم استلام رسالتك: {message.text}")

# 5. تشغيل البوت
if __name__ == '__main__':
    keep_alive()
    bot.remove_webhook(drop_pending_updates=True)
    bot.infinity_polling()
