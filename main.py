import asyncio
import os
import uuid
import logging
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import yt_dlp

# --- الإعدادات ---
TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
CHANNEL_ID = "@zinoad6162"  # <-- ضع معرف قناتك هنا (مثلاً @MyChannel)
BASE_URL = "https://youtube-downloader-v1.onrender.com"
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"
PORT = int(os.environ.get("PORT", 5000))

# إعدادات التسجيل لمتابعة الأخطاء
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
CACHE = {}

# --- Middleware للتحقق من الاشتراك ---
class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message) and event.text and event.text.startswith("/"):
            return await handler(event, data)
        
        try:
            member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=event.from_user.id)
            if member.status in ['left', 'kicked']:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 اشترك في القناة الآن", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")]
                ])
                await event.answer("⚠️ **عذراً، يجب عليك الاشتراك في القناة لاستخدام البوت.**\n\nاضغط على الزر أدناه للاشتراك:", reply_markup=keyboard, parse_mode="Markdown")
                return
        except Exception:
            pass # إذا كان البوت ليس أدمن في القناة قد يحدث خطأ، تجاهله
        return await handler(event, data)

dp.update.middleware(SubscriptionMiddleware())

# --- التحميل والمنطق ---
YDL_OPTS_BASE = {
    'quiet': True, 'no_warnings': True, 'geo_bypass': True, 'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'extractor_args': {'youtube': {'player_client': ['ios', 'android']}},
}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 أهلاً بك في البوت الاحترافي للتحميل.\n\nأرسل رابط أي فيديو وسأقوم بتحميله لك فوراً بجودات عالية! 🚀", parse_mode="Markdown")

@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    msg = await message.answer("⏳ جاري تحليل الرابط... يرجى الانتظار")
    url = message.text.strip()
    try:
        loop = asyncio.get_running_loop()
        def extract():
            with yt_dlp.YoutubeDL(YDL_OPTS_BASE) as ydl: return ydl.extract_info(url, download=False)
        info = await loop.run_in_executor(None, extract)
        title = info.get('title', 'فيديو')
        task_id = str(uuid.uuid4())[:8]
        CACHE[task_id] = {'url': url, 'title': title}
        
        formats = info.get('formats', [])
        heights = sorted(list({f.get('height') for f in formats if f.get('height') in [360, 480, 720, 1080]}))
        builder = InlineKeyboardBuilder()
        for h in heights: builder.button(text=f"🎬 {h}p", callback_data=f"dl:{task_id}:{h}")
        builder.button(text="🎵 MP3", callback_data=f"dl:{task_id}:mp3")
        builder.adjust(2)
        await msg.edit_text(f"🎬 **{title[:50]}**\n\nاختر الجودة المطلوبة:", reply_markup=builder.as_markup(), parse_mode="Markdown")
    except:
        await msg.edit_text("❌ خطأ: الرابط غير صالح أو الفيديو خاص. تأكد من إرسال رابط عام.")

@dp.callback_query(lambda c: c.data and c.data.startswith("dl:"))
async def process_download(callback: CallbackQuery):
    await callback.answer("جاري المعالجة...")
    _, task_id, quality = callback.data.split(":")
    data = CACHE.get(task_id)
    if not data:
        return await callback.message.edit_text("⚠️ انتهت صلاحية الطلب. أرسل الرابط مرة أخرى.")
    
    await callback.message.edit_text("⏳ جاري التحميل والرفع... قد يستغرق الأمر ثوانٍ.")
    file_path = None
    try:
        ydl_opts = dict(YDL_OPTS_BASE)
        ydl_opts.update({'format': 'bestaudio/best' if quality == 'mp3' else f'best[height<={quality}]/best', 'outtmpl': f'temp_{task_id}.%(ext)s'})
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: return ydl.prepare_filename(ydl.extract_info(data['url'], download=True))
        file_path = await asyncio.to_thread(download)
        
        if quality == 'mp3':
            await callback.message.answer_audio(audio=FSInputFile(file_path), caption=f"✅ تم تحميل: {data['title'][:50]}")
        else:
            await callback.message.answer_video(video=FSInputFile(file_path), caption=f"✅ تم تحميل: {data['title'][:50]}")
        await callback.message.delete()
    except Exception as e:
        await callback.message.edit_text(f"❌ حدث خطأ أثناء التحميل.\n`{str(e)[:50]}`", parse_mode="Markdown")
    finally:
        if file_path and os.path.exists(file_path): os.remove(file_path)
        if task_id in CACHE: del CACHE[task_id]

async def main():
    await bot.set_webhook(WEBHOOK_URL)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
