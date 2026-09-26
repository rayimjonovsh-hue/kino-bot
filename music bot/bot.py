import asyncio
import logging
import os
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import yt_dlp

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8848060623:AAFcjLeYLzMWpUi1Rpr-36bzxP-ZW2-T97A"
ADMIN_ID = 8358382613  # Sizning Telegram ID-ngiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Foydalanuvchilar bazasi (xotirada)
FOYDALANUVCHILAR = set()

# ==================== WEB SERVER (UptimeRobot / Render uchun) ====================
async def handle(request):
    return web.Response(text="Bot 24/7 faol ishlamoqda!")

async def start_web_server():
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

# ==================== BOT BUYRUQLARI ====================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer(
        f"Salom, {message.from_user.first_name}!\n\n"
        f"🎵 Musiqa va Video Yuklovchi Botga xush kelibsiz!\n\n"
        f"📌 Nima qila olaman?\n"
        f"1. Qo'shiq nomini yozing — YouTube'dan topib MP3 qilib beraman.\n"
        f"2. Instagram linkini yuboring — videoni yuklab beraman.",
        reply_markup=bosh_menyu,
        parse_mode="Markdown"
    )

@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer(
        f"📊 Bot statistikasi:\n\n"
        f"👥 Jami foydalanuvchilar: {len(FOYDALANUVCHILAR)} ta\n"
        f"⚡️ Bot serverda 24/7 va tezkor ishlamoqda!"
    )

@dp.message(F.text == "👨‍💻 Admin")
async def show_admin(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer("👨‍💻 Admin bilan bog'lanish: @shamsodbek_username")

@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer(
        "ℹ️ Botdan foydalanish yo'riqnomasi:\n\n"
        "🔍 Qo'shiq izlash:\n"
        "Shunchaki qo'shiq nomini yoki ijrochini yozib yuboring (Masalan: *Janob Rasul Yiglama*).\n\n"
        "📥 Instagram Video:\n"
        "Instagram post/reels linkini yuboring."
    )

# ==================== YOUTUBE DANI QIDIRISH VA MP3 YUKLASH ====================
def search_and_download_yt_mp3(query: str, filename_prefix: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'default_search': 'ytsearch1:',  # Birinchi topilgan natijani oladi
        'outtmpl': f'{filename_prefix}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        title = info['entries'][0]['title'] if 'entries' in info else info.get('title', 'Musiqa')
        return title

# ==================== INSTAGRAM VIDEO YUKLASH ====================
def download_insta_video(url: str, filename: str):
    ydl_opts = {
        'format': 'best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
# ==================== MATN VA LINKLARNI QABUL QILISH ====================
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_user_input(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    text = message.text

    # 1. Instagram linki kelgan bo'lsa
    if "instagram.com" in text:
        wait_msg = await message.answer("📥 Instagram video yuklanmoqda...")
        file_path = f"insta_{message.from_user.id}.mp4"
        try:
            await asyncio.to_thread(download_insta_video, text, file_path)
            if os.path.exists(file_path):
                video_file = types.FSInputFile(file_path)
                await message.answer_video(video=video_file, caption="✅ Video yuklab olindi!")
                await wait_msg.delete()
                os.remove(file_path)
            else:
                await wait_msg.edit_text("❌ Videoni yuklab bo'lmadi.")
        except Exception:
            await wait_msg.edit_text("❌ Xatolik yuz berdi. Linkni tekshiring.")
            if os.path.exists(file_path):
                os.remove(file_path)

    # 2. Qo'shiq nomi (Shazam funksiyasi)
    else:
        wait_msg = await message.answer(f"🔍 \"{text}\" YouTube'dan qidirilmoqda...")
        file_prefix = f"audio_{message.from_user.id}"
        mp3_path = f"{file_prefix}.mp3"
        
        try:
            # YouTube'dan qidirib yuklash
            title = await asyncio.to_thread(search_and_download_yt_mp3, text, file_prefix)
            
            if os.path.exists(mp3_path):
                audio_file = types.FSInputFile(mp3_path, filename=f"{title}.mp3")
                await message.answer_audio(audio=audio_file, caption=f"🎵 {title}\n\n✅ Bot orqali yuklandi")
                await wait_msg.delete()
                os.remove(mp3_path)
            else:
                await wait_msg.edit_text("❌ Musiqa topilmadi.")
        except Exception as e:
            await wait_msg.edit_text("❌ Musiqani yuklab bo'lmadi, boshqacharoq nom yozib ko'ring.")
            if os.path.exists(mp3_path):
                os.remove(mp3_path)

# ==================== ADMIN RASSILKA ====================
@dp.message(F.text.startswith("/send") & (F.from_user.id == ADMIN_ID))
async def send_broadcast(message: types.Message):
    text_to_send = message.text.replace("/send", "").strip()
    if not text_to_send:
        await message.answer("❌ Matn yozmadingiz! Namuna: /send Salom barchaga", parse_mode="Markdown")
        return
        
    count = 0
    await message.answer("🚀 Xabar yuborish boshlandi...")
    for user_id in list(FOYDALANUVCHILAR):
        try:
            await bot.send_message(chat_id=user_id, text=text_to_send)
            count += 1
            await asyncio.sleep(0.03)
        except Exception:
            pass

    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga muvaffaqiyatli yuborildi!")

# ==================== ASOSIY ISHGA TUSHIRISH ====================
async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Render va UptimeRobot uchun web serverni yurgizish
    await start_web_server()
    
    # Eskilarini tozalash
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Polling boshlash
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())