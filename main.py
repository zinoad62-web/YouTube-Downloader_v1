import asyncio
import os
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import yt_dlp

# --- الإعدادات ---
TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- تنظيف المجلد ---
if not os.path.exists("downloads"):
    os.makedirs("downloads")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("أهلاً بك! أرسل رابط الفيديو وسأقوم بتحميله لك.")

@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    msg = await message.answer("⏳ جاري المعالجة...")
    url = message.text.strip()
    task_id = str(uuid.uuid4())[:8]
    file_path = f"downloads/{task_id}.mp4"

    try:
        # إعدادات بسيطة ومستقرة لـ yt-dlp
        ydl_opts = {
            'outtmpl': file_path,
            'format': 'best',
            'quiet': True,
        }
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await asyncio.to_thread(download)

        if os.path.exists(file_path):
            await msg.edit_text("📤 جاري الإرسال...")
            await message.answer_video(video=FSInputFile(file_path))
            await msg.delete()
            os.remove(file_path)
        else:
            await msg.edit_text("❌ لم يتم تحميل الملف. قد يكون الرابط خاصاً.")
            
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {e}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    # ملاحظة: إذا كنت تستخدم Webhook على Render، لا تحتاج لـ setup_application المعقد
    # فقط اجعل البوت يعمل باستخدام start_polling إذا واجهت مشاكل
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
