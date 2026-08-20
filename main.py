import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiohttp import web
import yt_dlp

TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
PORT = int(os.environ.get("PORT", 5000))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# إعدادات لتجاوز الحماية كمتصفح حقيقي
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("أهلاً بك في بوت التحميل السريع 🚀\nأرسل رابط أي فيديو (يوتيوب، تيك توك) وسأجلب لك رابط التحميل فوراً وبدون استهلاك لموارد السيرفر.")

@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    msg = await message.answer("⏳ جاري استخراج الرابط المباشر...")
    try:
        loop = asyncio.get_running_loop()
        
        def extract():
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                return ydl.extract_info(message.text, download=False)
                
        info = await loop.run_in_executor(None, extract)
        video_url = info.get('url')
        title = info.get('title', 'فيديو')
            
        if video_url:
            await message.answer_video(video=video_url, caption=f"🎬 **{title[:50]}**\n\nتم التحميل بنجاح بسرعة فائقة ⚡", parse_mode="Markdown")
            await msg.delete()
        else:
            await msg.edit_text("❌ تعذر استخراج الرابط المباشر لهذا الفيديو.")
            
    except Exception as e:
        await msg.edit_text("❌ حدث خطأ أو أن الرابط غير مدعوم أو محمي.")

# سيرفر وهمي لتلبية شروط استضافة Render
async def handle(request):
    return web.Response(text="Bot is running and alive!")

async def web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    # 🛠️ الحل هنا: حذف أي Webhook قديم عالق في تيليجرام قبل بدء البوت
    await bot.delete_webhook(drop_pending_updates=True)
    
    # تشغيل السيرفر الوهمي وبوت تيليجرام معاً
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
