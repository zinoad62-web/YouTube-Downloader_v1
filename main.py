import asyncio
import glob
import os
import uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import yt_dlp

# --- الإعدادات ---
TOKEN = os.environ.get("BOT_TOKEN", "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4")
CHANNEL_ID = "@zinoad6162"  # تأكد من إضافة البوت كمشرف في هذه القناة
BASE_URL = os.environ.get("BASE_URL", "https://youtube-downloader-v1.onrender.com")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"
PORT = int(os.environ.get("PORT", 5000))

bot = Bot(token=TOKEN)
dp = Dispatcher()
CACHE = {}

# مجلد مؤقت لحفظ التحميلات
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- دالة التحقق من الاشتراك ---
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Subscription check error: {e}")
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
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📢 اشترك في القناة الآن", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")
        ]])
        return await message.answer("⚠️ **عذراً، يجب عليك الاشتراك في قناتنا أولاً لتتمكن من التحميل:**", reply_markup=kb)

    msg = await message.answer("⏳ **جاري فحص الرابط واستخراج المعلومات...**")
    try:
        url = message.text.strip()
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        
        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
                
        info = await asyncio.to_thread(extract)
        
        task_id = str(uuid.uuid4())[:8]
        CACHE[task_id] = {'url': url, 'title': info.get('title', 'Video')}
        
        formats = info.get('formats', [])
        heights = sorted(list({f.get('height') for f in formats if f.get('height') and f.get('height') in [360, 480, 720, 1080]}))
        
        builder = InlineKeyboardBuilder()
        
        if heights:
            for h in heights:
                builder.button(text=f"🎬 {h}p", callback_data=f"dl:{task_id}:{h}")
        else:
            builder.button(text="🎬 فيديو (أعلى جودة)", callback_data=f"dl:{task_id}:best")
            
        builder.button(text="🎵 MP3 (صوت)", callback_data=f"dl:{task_id}:mp3")
        builder.adjust(2)
        
        title = info.get('title', 'فيديو') or 'فيديو'
        await msg.edit_text(f"🎥 **{title[:50]}**\n\nاختر الجودة المطلوبة:", reply_markup=builder.as_markup())
    except Exception as e:
        print(f"Extract error: {e}")
        await msg.edit_text("❌ **تعذر جلب البيانات. تأكد أن الرابط عام وصحيح.**")

# --- معالجة التنزيل ---
@dp.callback_query(lambda c: c.data and c.data.startswith("dl:"))
async def process_download(callback: types.CallbackQuery):
    if not await is_subscribed(callback.from_user.id):
        return await callback.answer("❌ يجب الاشتراك في القناة أولاً!", show_alert=True)
    
    await callback.message.edit_text("⏳ **جاري التحميل... يرجى الانتظار.**")
    _, task_id, quality = callback.data.split(":")
    data = CACHE.get(task_id)
    
    if not data:
        return await callback.message.edit_text("⚠️ **انتهت صلاحية الطلب. أرسل الرابط مرة أخرى.**")

    out_template = os.path.join(DOWNLOAD_DIR, f"{task_id}.%(ext)s")
    
    try:
        def download():
            common_opts = {
                'outtmpl': out_template,
                'quiet': True,
                'no_warnings': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            }

            if quality == 'mp3':
                opts = {
                    **common_opts,
                    'format': 'bestaudio/best',
                }
            elif quality == 'best':
                opts = {
                    **common_opts,
                    'format': 'best',
                }
            else:
                opts = {
                    **common_opts,
                    'format': f'best[height<={quality}]/best',
                }
                
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([data['url']])

        await asyncio.to_thread(download)
        
        downloaded_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{task_id}.*"))
        
        if not downloaded_files:
            raise FileNotFoundError("لم يتم العثور على الملف المحمل.")
            
        downloaded_file = downloaded_files[0]

        await callback.message.edit_text("📤 **جاري الرفع إلى تليجرام...**")
        
        if quality == 'mp3':
            await callback.message.answer_audio(audio=FSInputFile(downloaded_file), caption="✅ **تم التحميل بنجاح!**")
        else:
            await callback.message.answer_video(video=FSInputFile(downloaded_file), caption="✅ **تم التحميل بنجاح!**")
            
        await callback.message.delete()

    except Exception as e:
        print(f"Download error: {e}")
        await callback.message.edit_text("❌ **حدث خطأ أثناء التحميل أو الرفع.**")
        
    finally:
        downloaded_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{task_id}.*"))
        for f in downloaded_files:
            if os.path.exists(f):
                os.remove(f)
        if task_id in CACHE:
            del CACHE[task_id]

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
