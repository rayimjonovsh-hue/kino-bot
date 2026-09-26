import asyncio
import logging
import os
import re
import aiohttp
from aiohttp import web
import yt_dlp

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile

# ==========================================
# 1. SOZLAMALAR
# ==========================================
# Tokeningizni va Admin ID'ingizni kiriting
BOT_TOKEN = "8848060623:AAFcjLeYLzMWpUi1Rpr-36bzxP-ZW2-T97A"
ADMIN_ID = 8358382613

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# 2. YOUTUBE QIDIRUV FUNKSIYASI (yt-dlp)
# ==========================================
def search_youtube(query: str, max_results: int = 10):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'extract_flat': 'in_playlist',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            return results.get('entries', [])
        except Exception as e:
            logging.error(f"YouTube search error: {e}")
            return []

def download_audio(video_id: str):
    url = f"https://www.youtube.com/watch?v={video_id}"
    file_path = f"song_{video_id}.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'song_{video_id}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # Yuklangan fayl nomini aniqlash
    if os.path.exists(file_path):
        return file_path
    for f in os.listdir('.'):
        if f.startswith(f"song_{video_id}"):
            return f
    return None

# ==========================================
# 3. INSTAGRAM YUKLOVCHI FUNKSIYASI
# ==========================================
def download_instagram_video(url: str):
    file_path = "insta_video.mp4"
    if os.path.exists(file_path):
        os.remove(file_path)

    ydl_opts = {
        'format': 'best',
        'outtmpl': file_path,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return file_path if os.path.exists(file_path) else None

# ==========================================
# 4. BOT HANDLERLARI
# ==========================================

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        f"👋 Salom, {message.from_user.first_name}!\n\n"
        "🎶 Musiqalar qidiruvi: Qo'shiqchi yoki qo'shiq nomini yozing, men 10 ta eng sarasini topib beraman.\n"
        "📹 Instagram downloader: Instagram video havolasini yuboring, uni yuklab beraman!"
    )

# 1. Instagram Link kelganda
@dp.message(F.text.contains("instagram.com"))
async def handle_instagram(message: types.Message):
    msg = await message.answer("📥 Instagram video yuklanmoqda, kuting...")
    try:
        loop = asyncio.get_event_loop()
        video_file = await loop.run_in_executor(None, download_instagram_video, message.text.strip())
        
        if video_file and os.path.exists(video_file):
            video_input = FSInputFile(video_file)
            await message.answer_video(video=video_input, caption="🎬 Instagram'dan yuklab olindi!")
            await msg.delete()
            os.remove(video_file)
        else:
            await msg.edit_text("❌ Videoni yuklab bo'lmadi. Havola to'g'riligini tekshiring.")
    except Exception as e:
        logging.error(f"Insta error: {e}")
        await msg.edit_text("❌ Xatolik yuz berdi yoki video shaxsiy (private) akkauntdan.")

# 2. Qo'shiq qidiruvi va 10 ta ro'yxat chiqarish
@dp.message(F.text)
async def handle_music_search(message: types.Message):
    query = message.text.strip()
    msg = await message.answer("🔎 YouTube'dan musiqa qidirilmoqda...")
    
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, search_youtube, query, 10)
    
    if not results:
        await msg.edit_text("❌ Hech qanday musiqa topilmadi.")
        return

    text = f"🎵 '{query}' bo'yicha topilgan qo'shiqlar:\n\n"
    keyboard = []
    row = []

    for idx, item in enumerate(results, start=1):
        title = item.get('title', 'Noma\'lum qo\'shiq')
        video_id = item.get('id')
        text += f"{idx}. {title}\n"

        # Tugmalarni 2 tadan qatoyga taxlash
        row.append(InlineKeyboardButton(text=f"🎵 {idx}", callback_query_data=f"dl_{video_id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await msg.edit_text(text, reply_markup=markup, parse_mode="Markdown")

# 3. Tugma bosilganda audioni yuklab berish
@dp.callback_query(F.data.startswith("dl_"))
async def process_download_callback(call: CallbackQuery):
    video_id = call.data.split("dl_")[1]
    await call.answer("📥 Musiqa yuklanmoqda...")
    await call.message.answer("⌛ Qo'shiq tayyorlanmoqda, biroz kuting...")

    loop = asyncio.get_event_loop()
    audio_file = await loop.run_in_executor(None, download_audio, video_id)

    if audio_file and os.path.exists(audio_file):
        audio_input = FSInputFile(audio_file)
        await call.message.answer_audio(audio=audio_input, caption="🎧 Bot orqali yuklab olindi")
        os.remove(audio_file)
    else:
        await call.message.answer("❌ Musiqani yuklab bo'lmadi.")

# ==========================================
# 5. RENDER BEPUL SERVER (PORT KONTROLLI)
# ==========================================
async def handle_web(request):
    return web.Response(text="Musiqa Boti faol ishlamoqda!")

async def start_web():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Kino bot bilan urushmaslik uchun PORT o'zgaruvchisidan foydalanamiz
    port = int(os.environ.get("PORT", 8081))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Webhook error: {e}")

    asyncio.create_task(start_web())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())