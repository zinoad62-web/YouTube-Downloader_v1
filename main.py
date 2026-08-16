import os
import telebot
from flask import Flask, request

TOKEN = "8932809251:AAExxj0ORQhI_tFWY6wsbzmjJYgtlegNb_o"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# رابط الخدمة الخاص بك على Render
URL = "https://youtube-bot-pig5.onrender.com/"

@app.route('/')
def home():
    return "Bot is running via Webhook!"

# نقطة استلام الرسائل من تلجرام
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# دالة الاستجابة لأمر start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! تم ربط البوت بنجاح عبر الـ Webhook 🚀")

# دالة الاستجابة للرسائل العامة
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"تم استلام: {message.text}")

if __name__ == "__main__":
    # إزالة أي webhook قديم ثم تفعيل الرابط الجديد
    bot.remove_webhook()
    bot.set_webhook(url=URL + TOKEN)
    
    # تشغيل خادم Flask على المنفذ المخصص
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
