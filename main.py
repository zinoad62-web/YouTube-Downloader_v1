import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import yt_dlp

TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
BASE_URL = "https://youtube-downloader-v1.onrender.com"  # رابط تطبيقك على Render
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

PORT = int(os.environ.get("PORT", 5000))

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("أهلاً بك في بوت التحميل 🚀\nأرسل رابط أي فيديو (يوتيوب، تيك توك) وسأقوم بتحميله وإرساله لك فوراً.")

@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    msg = await message.answer("⏳ جاري تحميل الفيديو وإرساله...")
    file_path = None
    try:
        loop = asyncio.get_running_loop()
        
        # إعدادات التحميل المؤقت وتجاوز القيود
        ydl_opts = {
            'format': 'best[filesize<50M]/best',  # اختيار أفضل جودة بحجم مناسب لسرعة الإرسال
            'outtmpl': 'video_temp.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
            'extractor_args': {
                'youtube': {'player_client': ['ios', 'android']},
            },
        }
        
        def download_video():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(message.text, download=True)
                return ydl.prepare_filename(info), info.get('title', 'فيديو')

        # تنفيذ التحميل في الخلفية لكي لا يتجمد البوت
        file_path, title = await loop.run_in_executor(None, download_video)
        
        if file_path and os.path.exists(file_path):
            video_file = types.FSInputFile(file_path)
            await message.answer_video(
                video=video_file, 
                caption=f"🎬 **{title[:50]}**\n\nتم التحميل بنجاح ✅", 
                parse_mode="Markdown"
            )
            await msg.delete()
        else:
            await msg.edit_text("❌ تعذر تحميل الفيديو، تأكد أن الرابط عام وصحيح.")
            
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ أثناء التحميل:\n`{str(e)}`", parse_mode="Markdown")
        
    finally:
        # 🧹 تنظيف مساحة السيرفر وحذف الملف المؤقت فوراً بعد الإرسال
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

async def on_startup(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)

async def main():
    dp.startup.register(on_startup)
    
    app = web.Application()
    
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    async def home(request):
        return web.Response(text="Bot is running via Webhook!")
    app.router.add_get("/", home)

    setup_application(app, dp, bot=bot)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
