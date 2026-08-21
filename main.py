import asyncio
import glob
import os
import uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
import yt_dlp

# --- الإعدادات ---
TOKEN = os.environ.get("BOT_TOKEN", "8932809251:AAFQ8MpRrCQHm38-25r3e0ttghMeJuoYjX4")
CHANNEL_ID = "@zinoad6162"  # تأكد من رفع البوت مشرفاً في القناة
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=TOKEN)
dp = Dispatcher()

CACHE = {}
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- دالة فحص الاشتراك ---
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# --- لوحة أزرار الاشتراك ---
def get_sub_keyboard():
    channel_username = CHANNEL_ID.replace("@", "")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 اشترك في القناة الآن", url=f"https://t.me/{channel_username}")],
        [InlineKeyboardButton(text="✅ تحقق من الاشتراك", callback_data="check_subscription")]
    ])

# --- الأمر /start ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "🚀 **أهلاً بك في بوت التحميل السريع!**\n\n"
        "يمكنني تحميل الفيديوهات والمقاطع الصوتية من مختلف المنصات:\n"
        "🔹 **Facebook** | **TikTok** | **YouTube** | **Instagram**\n\n"
        "💡 **كيفية الاستخدام:**\n"
        "أرسل رابط الفيديو مباشرة واختر الجودة المناسبة لك."
    )
    await message.answer(welcome_text, parse_mode="Markdown")

# --- معالجة زر التحقق من الاشتراك ---
@dp.callback_query(F.data == "check_subscription")
async def verify_sub_callback(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.answer("✅ تم التحقق بنجاح! أنت مشترك الآن.", show_alert=True)
        await callback.message.edit_text(
            "🎉 **أهلاً بك! تم التاكد من اشتراكك.**\n\nقم بإرسال رابط الفيديو الآن للتحميل 📥",
            parse_mode="Markdown"
        )
    else:
        await callback.answer("❌ لم تشترك في القناة بعد! يرجى الاشتراك أولاً ثم المحاولة.", show_alert=True)

# --- معالجة الروابط وعرض الجودات ---
@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        return await message.answer(
            "⚠️ **عذراً عزيزي، يجب عليك الاشتراك في القناة لاستخدام البوت:**\n\n"
            "اشترك ثم اضغط على زر **(✅ تحقق من الاشتراك)** بالأسفل.",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )

    msg = await message.answer("🔍 **جاري فحص الرابط وجلب الجودات...**", parse_mode="Markdown")
    url = message.text.strip()

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }

        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        info = await asyncio.to_thread(extract)
        task_id = str(uuid.uuid4())[:8]
        title = info.get('title', 'فيديو') or 'فيديو'
        CACHE[task_id] = {'url': url, 'title': title}

        formats = info.get('formats', [])
        heights = sorted(list({f.get('height') for f in formats if f.get('height') and f.get('height') in [360, 480, 720, 1080]}))

        builder = InlineKeyboardBuilder()
        if heights:
            for h in heights:
                builder.button(text=f"🎬 {h}p", callback_data=f"dl:{task_id}:{h}")
        
        builder.button(text="🎬 أعلى جودة متاحة", callback_data=f"dl:{task_id}:best")
        builder.button(text="🎵 ملف صوتي (MP3)", callback_data=f"dl:{task_id}:mp3")
        builder.adjust(2)

        await msg.edit_text(
            f"📌 **العنوان:** {title[:50]}\n\n👇 **اختر الجودة أو الصيغة المطلوبة:**",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Extract Error: {e}")
        await msg.edit_text("❌ **تعذر استخراج بيانات الفيديو. تأكد من صحة الرابط وأن الحساب عام.**", parse_mode="Markdown")

# --- تنزيل ورفع الملف ---
@dp.callback_query(F.data.startswith("dl:"))
async def process_download(callback: types.CallbackQuery):
    if not await is_subscribed(callback.from_user.id):
        return await callback.answer("❌ يجب الاشتراك في القناة أولاً!", show_alert=True)

    _, task_id, quality = callback.data.split(":")
    data = CACHE.get(task_id)

    if not data:
        return await callback.message.edit_text("⚠️ **انتهت صلاحية هذا الطلب. يرجى إعادة إرسال الرابط.**", parse_mode="Markdown")

    await callback.message.edit_text("⏳ **جاري تنزيل الملف، يرجى الانتظار...**", parse_mode="Markdown")
    out_template = os.path.join(DOWNLOAD_DIR, f"{task_id}.%(ext)s")

    try:
        common_opts = {
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }

        if quality == 'mp3':
            opts = {**common_opts, 'format': 'bestaudio/best'}
        elif quality == 'best':
            opts = {**common_opts, 'format': 'best'}
        else:
            opts = {**common_opts, 'format': f'best[height<={quality}]/best'}

        def download():
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([data['url']])

        await asyncio.to_thread(download)

        downloaded_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{task_id}.*"))
        if not downloaded_files:
            raise FileNotFoundError("الملف غير موجود")

        downloaded_file = downloaded_files[0]
        await callback.message.edit_text("📤 **جاري الرفع إلى تليجرام...**", parse_mode="Markdown")

        caption = f"✅ **تم التحميل بنجاح!**\n🎬 **العنوان:** {data['title'][:60]}"

        if quality == 'mp3':
            await callback.message.answer_audio(audio=FSInputFile(downloaded_file), caption=caption, parse_mode="Markdown")
        else:
            await callback.message.answer_video(video=FSInputFile(downloaded_file), caption=caption, parse_mode="Markdown")

        await callback.message.delete()

    except Exception as e:
        print(f"Download Error: {e}")
        await callback.message.edit_text("❌ **حدث خطأ أثناء التحميل أو الرفع.**", parse_mode="Markdown")
    finally:
        downloaded_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{task_id}.*"))
        for f in downloaded_files:
            if os.path.exists(f):
                os.remove(f)
        if task_id in CACHE:
            del CACHE[task_id]

# --- نقطة فحص Render ---
async def health_check(request):
    return web.Response(text="Bot is online!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    print("🤖 البوت يعمل بنجاح...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
