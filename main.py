import asyncio
import os
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# --- الإعدادات ---
TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
CHANNEL_ID = "@zinoad6162"  # معرف قناتك

bot = Bot(token=TOKEN)
dp = Dispatcher()

# إنشاء مجلد التحميلات إذا لم يكن موجوداً
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# --- دالة التحقق من الاشتراك ---
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"خطأ في فحص الاشتراك: {e}")
        return False

# --- الأمر start ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 أهلاً بك! أرسل رابط الفيديو وسأقوم بتحميله لك فوراً.")

# --- معالجة الروابط والتحميل ---
@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    # 1. فحص الاشتراك أولاً
    if not await is_subscribed(message.from_user.id):
        channel_username = CHANNEL_ID.replace("@", "")
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📢 اشترك في القناة الآن", url=f"https://t.me/{channel_username}")
        ]])
        return await message.answer(
            "⚠️ **عذراً، يجب عليك الاشتراك في قناتنا أولاً لتتمكن من التحميل:**", 
            reply_markup=kb,
            parse_mode="Markdown"
        )

    # 2. البدء في التحميل إذا كان مشتركاً
    msg = await message.answer("⏳ **جاري التحميل والمعالجة...**", parse_mode="Markdown")
    url = message.text.strip()
    task_id = str(uuid.uuid4())[:8]
    file_path = f"downloads/{task_id}.mp4"

    try:
        ydl_opts = {
            'outtmpl': file_path,
            'format': 'best',
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await asyncio.to_thread(download)

        if os.path.exists(file_path):
            await msg.edit_text("📤 **جاري الرفع إلى تليجرام...**", parse_mode="Markdown")
            await message.answer_video(video=FSInputFile(file_path), caption="✅ **تم التحميل بنجاح!**", parse_mode="Markdown")
            await msg.delete()
        else:
            await msg.edit_text("❌ **تعذر العثور على الملف بعد التنزيل.**", parse_mode="Markdown")
            
    except Exception as e:
        print(f"Download Error: {e}")
        await msg.edit_text("❌ **حدث خطأ أثناء التحميل. تأكد من أن الرابط عام وصحيح.**", parse_mode="Markdown")
        
    finally:
        # تنظيف الملفات المؤقتة دائماً
        if os.path.exists(file_path):
            os.remove(file_path)

# --- تشغيل البوت ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 البوت يعمل الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
