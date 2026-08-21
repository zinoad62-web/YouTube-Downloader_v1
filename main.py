import asyncio
import os
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
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

bot = Bot(token=TOKEN)
dp = Dispatcher()
CACHE = {}

# --- دالة التحقق من الاشتراك ---
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# --- الرسالة الترحيبية ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 **أهلاً بك في البوت العملاق للتحميل!**\n\n"
        "أنا أساعدك في تحميل فيديوهاتك المفضلة من جميع المنصات (يوتيوب، تيك توك، انستغرام، فيسبوك) وبأعلى جودة.\n\n"
        "🔗 **فقط أرسل رابط الفيديو وسأقوم بالباقي!**",
        parse_mode="Markdown"
    )

# --- معالجة الروابط ---
@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    # 1. التحقق من الاشتراك
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 اشترك في القناة الآن", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")]])
        return await message.answer("⚠️ **عذراً، يجب عليك الاشتراك في قناتنا أولاً لتتمكن من التحميل:**", reply_markup=kb)

    msg = await message.answer("⏳ **جاري فحص الرابط واستخراج المعلومات...**")
    try:
        url = message.text.strip()
        def extract():
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl: return ydl.extract_info(url, download=False)
        info = await asyncio.to_thread(extract)
        
        task_id = str(uuid.uuid4())[:8]
        CACHE[task_id] = {'url': url, 'title': info.get('title', 'Video')}
        
        formats = info.get('formats', [])
        heights = sorted(list({f.get('height') for f in formats if f.get('height') in [360, 480, 720, 1080]}))
        
        builder = InlineKeyboardBuilder()
        for h in heights: builder.button(text=f"🎬 {h}p", callback_data=f"dl:{task_id}:{h}")
        builder.button(text="🎵 MP3", callback_data=f"dl:{task_id}:mp3")
        builder.adjust(2)
        
        await msg.edit_text(f"🎥 **{info.get('title', 'فيديو')[:50]}**\n\nاختر الجودة المطلوبة:", reply_markup=builder.as_markup())
    except:
        await msg.edit_text("❌ **تعذر جلب البيانات. تأكد أن الرابط عام.**")

# --- التحميل ---
@dp.callback_query(lambda c: c.data and c.data.startswith("dl:"))
async def process_download(callback: types.CallbackQuery):
    if not await is_subscribed(callback.from_user.id):
        return await callback.answer("❌ يجب الاشتراك في القناة أولاً!", show_alert=True)
    
    await callback.message.edit_text("⏳ **جاري التحميل... يرجى الانتظار (قد يستغرق 10 ثوانٍ).**")
    _, task_id, quality = callback.data.split(":")
    data = CACHE.get(task_id)
    
    if not data: return await callback.message.edit_text("⚠️ **انتهت صلاحية الطلب. أرسل الرابط مرة أخرى.**")

    file_path = f"video_{task_id}.mp4"
    try:
        def download():
            opts = {'format': 'bestaudio/best' if quality == 'mp3' else f'best[height<={quality}]/best', 'outtmpl': file_path}
            with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([data['url']])
        await asyncio.to_thread(download)
        
        await callback.message.edit_text("📤 **جاري الرفع إلى تليجرام...**")
        if quality == 'mp3':
            await callback.message.answer_audio(audio=FSInputFile(file_path), caption="✅ **تم التحميل بنجاح!**")
        else:
            await callback.message.answer_video(video=FSInputFile(file_path), caption="✅ **تم التحميل بنجاح!**")
        await callback.message.delete()
    except Exception as e:
        await callback.message.edit_text(f"❌ **حدث خطأ أثناء التحميل.**")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        if task_id in CACHE: del CACHE[task_id]

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
