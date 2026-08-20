import asyncio
import os
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile, CallbackQuery
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import yt_dlp

# --- الإعدادات الأساسية ---
TOKEN = "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4"
BASE_URL = "https://youtube-downloader-v1.onrender.com"  # رابط سيرفرك على Render
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

PORT = int(os.environ.get("PORT", 5000))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ذاكرة مؤقتة بحجم صغير لحفظ بيانات التحميل بين الأزرار
CACHE = {}

# إعدادات شمولية لتجاوز القيود على جميع المنصات
YDL_OPTS_BASE = {
    'quiet': True,
    'no_warnings': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'extractor_args': {
        'youtube': {'player_client': ['ios', 'android']},
    },
}

# --- 1. الرسالة الترحيبية الاحترافية ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "أهلاً بك في **بوت التحميل الشامل** 🚀\n\n"
        "يمكنك التحميل بسهولة من جميع منصات التواصل الاجتماعي بأعلى كفاءة وبجودات متعددة:\n"
        "• 🔴 **يوتيوب** (فيديوهات / شورتس)\n"
        "• 🎵 **تيك توك** (بدون علامة مائية)\n"
        "• 📸 **إنستغرام** (ريلز / منشورات)\n"
        "• 🔵 **فيسبوك** (فيديوهات / ريلز)\n"
        "• 🐦 **تويتر / X** والعديد من المواقع الأخرى!\n\n"
        "📌 **كيفية الاستخدام:**\n"
        "1️⃣ أرسل رابط الفيديو المطلوب فقط.\n"
        "2️⃣ اختر الجودة المناسبة لك أو خيار MP3.\n"
        "3️⃣ سيتم تحميل الفيديو وإرساله لك خلال ثوانٍ ⚡"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

# --- 2. استقبال الرابط واستخراج الجودات المتاحة ---
@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    msg = await message.answer("🔍 جاري فحص الرابط واستخراج الجودات المتاحة...")
    url = message.text.strip()
    
    try:
        loop = asyncio.get_running_loop()
        
        def extract():
            with yt_dlp.YoutubeDL(YDL_OPTS_BASE) as ydl:
                return ydl.extract_info(url, download=False)
                
        info = await loop.run_in_executor(None, extract)
        title = info.get('title', 'فيديو')
        
        # معرف فريد للعملية
        task_id = str(uuid.uuid4())[:8]
        CACHE[task_id] = {'url': url, 'title': title}
        
        # استخراج ارتفاعات الفيديو المتاحة (الجودات)
        formats = info.get('formats', [])
        available_heights = set()
        
        for f in formats:
            h = f.get('height')
            if h and h in [240, 360, 480, 720, 1080]:
                available_heights.add(h)
                
        sorted_heights = sorted(list(available_heights))
        
        # إنشاء الأزرار التفاعلية
        builder = InlineKeyboardBuilder()
        
        if sorted_heights:
            for h in sorted_heights:
                builder.button(text=f"🎬 {h}p", callback_data=f"dl:{task_id}:{h}")
        else:
            # خيار افتراضي للمنابر التي لا تحدد جودات دقيقة (مثل بعض فيديوهات تيك توك/فيسبوك)
            builder.button(text="🎬 أفضل جودة متاحة", callback_data=f"dl:{task_id}:best")
            
        # إضافة خيار التحميل الصوتي MP3
        builder.button(text="🎵 MP3 (صوت فقط)", callback_data=f"dl:{task_id}:mp3")
        builder.adjust(2)  # زرين في كل سطر
        
        await msg.edit_text(
            f"🎬 **{title[:60]}**\n\nاختر الجودة أو الصيغة المطلوبة للتحميل:",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await show_error_message(msg)

# --- 3. معالجة اختيار الجودة والتحميل ---
@dp.callback_query(F.data.startswith("dl:"))
async def process_download(callback: CallbackQuery):
    _, task_id, quality = callback.data.split(":")
    
    data = CACHE.get(task_id)
    if not data:
        await callback.message.edit_text("❌ انتهت صلاحية هذا الطلب، يرجى إعادة إرسال الرابط من جديد.")
        return

    url = data['url']
    title = data['title']
    
    await callback.message.edit_text(f"⏳ جاري تحميل [{title[:30]}...] بالجودة المحددة، يرجى الانتظار...")
    
    file_prefix = f"dl_{task_id}"
    file_path = None
    
    try:
        loop = asyncio.get_running_loop()
        
        # تحديد خيارات التحميل حسب الجودة
        ydl_opts = dict(YDL_OPTS_BASE)
        if quality == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['outtmpl'] = f'{file_prefix}.%(ext)s'
        elif quality == 'best':
            ydl_opts['format'] = 'best'
            ydl_opts['outtmpl'] = f'{file_prefix}.%(ext)s'
        else:
            # اختيار الجودة المطلوبة دون تجاوزها
            ydl_opts['format'] = f'best[height<={quality}]/best'
            ydl_opts['outtmpl'] = f'{file_prefix}.%(ext)s'

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                download_info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(download_info)

        file_path = await loop.run_in_executor(None, download)
        
        # إرسال الملف بناءً على النوع (صوت أو فيديو)
        if file_path and os.path.exists(file_path):
            input_file = FSInputFile(file_path)
            
            if quality == 'mp3':
                await callback.message.answer_audio(
                    audio=input_file,
                    caption=f"🎵 **{title[:50]}**\n\nتم التحميل بنجاح عبر البوت ✅",
                    parse_mode="Markdown"
                )
            else:
                await callback.message.answer_video(
                    video=input_file,
                    caption=f"🎬 **{title[:50]}**\n\nالجودة: {quality}p\nتم التحميل بنجاح ✅",
                    parse_mode="Markdown"
                )
            await callback.message.delete()
        else:
            await show_error_message(callback.message)

    except Exception as e:
        await show_error_message(callback.message)
        
    finally:
        # 🧹 تنظيف الذاكرة والسيرفر وحذف الملف فوراً بعد الانتهاء
        if task_id in CACHE:
            del CACHE[task_id]
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

# --- 4. دالة عرض رسائل الخطأ الاحترافية ---
async def show_error_message(message: types.Message):
    error_text = (
        "❌ **عذراً، تعذر إتمام عملية التحميل**\n\n"
        "**الأسباب المحتملة:**\n"
        "• المحتوى خاص (Private) أو يتطلب تسجيل دخول.\n"
        "• الرابط غير صحيح أو تم حذف الفيديو من المصدر.\n"
        "• الجودة المطلوبة غير متوفرة لهذا الفيديو بحد ذاته.\n\n"
        "💡 **تأكد من أن حساب صاحب الفيديو عام (Public) وثم أعد محاولة إرسال الرابط.**"
    )
    try:
        await message.edit_text(error_text, parse_mode="Markdown")
    except:
        await message.answer(error_text, parse_mode="Markdown")

# --- 5. تشغيل خادم Webhook والمشغلات ---
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
