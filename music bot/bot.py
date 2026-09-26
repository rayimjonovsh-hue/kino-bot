import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import yt_dlp

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8848060623:AAFcjLeYLzMWpUi1Rpr-36bzxP-ZW2-T97A"
ADMIN_ID = 8358382613

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

FOYDALANUVCHILAR = set()

# ==================== WEB SERVER (UptimeRobot uchun) ====================
async def handle(request):
    return web.Response(text="Bot ishlamoqda")

async def start_web():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# ==================== TUGMALAR ====================
bosh_menyu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="ℹ️ Yordam")],
        [KeyboardButton(text="👨‍💻 Admin")]
    ],
    resize_keyboard=True
)

# ==================== YOUTUBE YUKLOVCHI ====================
def download_youtube_audio(query: str, user_id: int):
    filename = f"music_{user_id}.m4a"
    
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'default_search': 'ytsearch1:'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if 'entries' in info and len(info['entries']) > 0:
            title = info['entries'][0].get('title', 'Musiqa')
        else:
            title = info.get('title', 'Musiqa')
        return filename, title

# ==================== BOT BUYRUQLARI ====================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer(
        f"Salom, {message.from_user.first_name}!\n\n"
        f"🎵 Musiqa botiga xush kelibsiz!\n\n"
        f"Qo'shiq nomini yoki ijrochini yozib yuboring.",
        reply_markup=bosh_menyu,
        parse_mode="Markdown"
    )

@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer(f"📊 Jami foydalanuvchilar: {len(FOYDALANUVCHILAR)} ta")

@dp.message(F.text == "👨‍💻 Admin")
async def show_admin(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer("👨‍💻 Admin: @mrbek077")

@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer(
        "ℹ️ Botdan foydalanish yo'riqnomasi:\n\n"
        "🔍 Qo'shiq izlash:\n"
        "Shunchaki qo'shiq nomini yoki ijrochini yozib yuboring (Masalan: Sherali Jorayev)."
    )

# ==================== QIDIRUV VA YUKLASH ====================
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_music_search(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    text = message.text.strip()

    wait_msg = await message.answer(f"🔍 \"{text}\" qidirilmoqda...")

    try:
        loop = asyncio.get_event_loop()
        file_path, title = await loop.run_in_executor(None, download_youtube_audio, text, message.from_user.id)

        if os.path.exists(file_path):
            audio_file = types.FSInputFile(file_path, filename=f"{title}.m4a")
            await message.answer_audio(audio=audio_file, caption=f"🎵 {title}\n\n✅ Bot orqali yuklab olindi")
            await wait_msg.delete()
            os.remove(file_path)
        else:
            await wait_msg.edit_text("❌ Musiqani yuklab bo'lmadi, boshqacharoq nom yozib ko'ring.")
    except Exception as e:
        await wait_msg.edit_text("❌ Musiqani yuklab bo'lmadi, boshqacharoq nom yozib ko'ring.")

# ==================== ADMIN RASSILKA ====================
@dp.message(F.text.startswith("/send") & (F.from_user.id == ADMIN_ID))
async def send_broadcast(message: types.Message):
    text_to_send = message.text.replace("/send", "").strip()
    if not text_to_send:
        await message.answer("❌ Matn yozmadingiz! Namuna: /send Salom")
        return
        
    count = 0
    await message.answer("🚀 Xabar yuborilmoqda...")
    for user_id in list(FOYDALANUVCHILAR):
        try:
            await bot.send_message(chat_id=user_id, text=text_to_send)
            count += 1
            await asyncio.sleep(0.03)
        except Exception:
            pass

    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi!")

# ==================== ISHGA TUSHIRISH ====================
async def main():
    logging.basicConfig(level=logging.INFO)
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Webhook o'chirishda xato: {e}")

    asyncio.create_task(start_web())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())