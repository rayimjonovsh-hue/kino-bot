import asyncio
import logging
import os
import re
import aiohttp
from urllib.parse import quote
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import yt_dlp

# SOZLAMALAR
BOT_TOKEN = "8848060623:AAFcjLeYLzMWpUi1Rpr-36bzxP-ZW2-T97A"
CHANNEL_USERNAME = "@filimlar9"  # MAJBURIY OBUNA KANALI (bot shu yerda ADMIN bo'lishi shart!)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# UPTIME ROBOT VA RENDER UCHUN VEB-SERVER (503 XATOSI BO'LMASLIGI UCHUN)
async def handle(request):
    return web.Response(text="Bot 24/7 holatda ishlamoqda!")

async def start_web():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# TUGMALAR MENYUSI
bosh_menyu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="ℹ️ Yordam")],
        [KeyboardButton(text="👨‍💻 Admin")]
    ],
    resize_keyboard=True
)

# MAJBURIY OBUNA UCHUN YORDAMCHI FUNKSIYALAR
def subscribe_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📢 Kanalga o'tish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [types.InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="check_sub")]
    ])

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        logging.exception("Obunani tekshirishda xatolik (bot kanalda admin emasmi?)")
        return False

async def require_subscription(message: types.Message) -> bool:
    if await check_subscription(message.from_user.id):
        return True
    await message.answer(
        f"🚀 Botdan foydalanish uchun avval kanalimizga obuna bo'ling:\n{CHANNEL_USERNAME}",
        reply_markup=subscribe_keyboard()
    )
    return False

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.edit_text("✅ Obuna tasdiqlandi! Endi botdan foydalanishingiz mumkin.")
        await callback.message.answer("Bosh menyu:", reply_markup=bosh_menyu)
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmagansiz.", show_alert=True)

# HELPER: MATNDAN NOKERAKLI LINK/REKLAMA MATNLARINI TOZALASH
def clean_title(raw_title: str) -> str:
    if not raw_title:
        return "Yuklangan Video"
    cleaned = re.sub(r'https?://\S+', '', raw_title)
    cleaned = re.sub(r't\.me/\S+', '', cleaned)
    cleaned = cleaned.strip()
    return cleaned if cleaned else "Yuklangan Video"

# HELPER: DEEZER ORQALI ANIQ QO'SHIQ NOMINI TOPISH (yuklamasdan, faqat nom uchun)
async def get_track_title_from_deezer(query):
    search_url = f"https://api.deezer.com/search?q={quote(query)}"
    async with aiohttp.ClientSession() as session:
        async with session.get(search_url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get('data'):
                    track = data['data'][0]
                    return f"{track['artist']['name']} - {track['title']}"
    return None

# HELPER: DEEZER ORQALI 30 SONIYALIK PREVIEW YUKLASH (YouTube ishlamasa, zaxira variant)
async def search_deezer_music(query):
    search_url = f"https://api.deezer.com/search?q={quote(query)}"
    async with aiohttp.ClientSession() as session:
        async with session.get(search_url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get('data'):
                    track = data['data'][0]
                    title = f"{track['artist']['name']} - {track['title']}"
                    audio_url = track['preview']

                    async with session.get(audio_url) as a_resp:
                        if a_resp.status == 200:
                            filename = f"music_{track['id']}.mp3"
                            with open(filename, 'wb') as f:
                                f.write(await a_resp.read())
                            return filename, title
    return None, None

# HELPER: YOUTUBE ORQALI TO'LIQ QO'SHIQNI YUKLASH
def download_full_audio_youtube(query, user_id):
    # Avvalgi fayllarni tozalash
    for f in os.listdir('.'):
        if f.startswith(f"audio_{user_id}."):
            os.remove(f)

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': f"audio_{user_id}.%(ext)s",
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'default_search': 'ytsearch1',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if 'entries' in info:
            info = info['entries'][0]
        title = clean_title(info.get('title', query))
        ext = info.get('ext', 'm4a')
        filename = f"audio_{user_id}.{ext}"

    if os.path.exists(filename):
        return filename, title
    return None, None

# HELPER: INSTAGRAM VA YOUTUBE LINKIDAN VIDEO YUKLASH (yt-dlp)
def download_media_link(url, user_id):
    filename = f"video_{user_id}.mp4"
    if os.path.exists(filename):
        os.remove(filename)

    ydl_opts = {
        'format': 'mp4/bestvideo+bestaudio/best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = clean_title(info.get('title', 'Yuklangan Video'))
        return filename, title

# BOT HANDLERLARI
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    if not await require_subscription(message):
        return
    await message.answer(
        f"👋 Salom, {message.from_user.first_name}!\n\n"
        f"🤖 Men ko'p funksiyali media botman:\n"
        f"1️⃣ Musiqa nomini yozing — ijrochini topib beraman.\n"
        f"2️⃣ Instagram yoki YouTube havolasini yuboring — videoni yuklab beraman!",
        parse_mode="Markdown",
        reply_markup=bosh_menyu
    )

@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if not await require_subscription(message):
        return
    await message.answer("📊 Bot statistikasi:\n\n🟢 Holati: Online (24/7 Uptime Robot ulaangan)", parse_mode="Markdown")

@dp.message(F.text == "👨‍💻 Admin")
async def show_admin(message: types.Message):
    if not await require_subscription(message):
        return
    await message.answer("👨‍💻 Admin bilan bog'lanish: @mrbek077")

@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    if not await require_subscription(message):
        return
    await message.answer("ℹ️ Yordam:\n- Qo'shiq topish uchun nomini yozing.\n- Video yuklash uchun Instagram Reel yoki YouTube linkini tashlang.", parse_mode="Markdown")

# XABARLARNI QAYTA ISHLASH (LINK YOKI MATN)
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_user_input(message: types.Message):
    if not await require_subscription(message):
        return

    text = message.text.strip()

    # Instagram yoki YouTube linki bo'lsa
    if "instagram.com" in text or "youtu.be" in text or "youtube.com" in text:
        wait_msg = await message.answer("📥 Video yuklanmoqda... Kuting...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        try:
            filename, title = await loop.run_in_executor(None, download_media_link, text, message.from_user.id)
            if filename and os.path.exists(filename):
                video = types.FSInputFile(filename)
                bot_username = (await bot.get_me()).username
                await message.answer_video(
                    video=video,
                    caption=f"🎬 {title}\n\n🤖 @{bot_username}",
                    parse_mode="Markdown"
                )
                await wait_msg.delete()
                os.remove(filename)
            else:
                await wait_msg.edit_text("❌ Videoni yuklab bo'lmadi. Link maxfiy bo'lishi yoki o'chirilgan bo'lishi mumkin.")
        except Exception:
            logging.exception("Video yuklashda xatolik")
            await wait_msg.edit_text("❌ Videoni yuklashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

    # Oddiy matn bo'lsa (Musiqa qidirish)
    else:
        wait_msg = await message.answer(f"🔍 \"{text}\" qo'shiq qidirilmoqda...", parse_mode="Markdown")

        # 1) Avval Deezer orqali aniq ijrochi/nom topamiz (qidiruv sifatini oshirish uchun)
        exact_title = await get_track_title_from_deezer(text)
        search_query = exact_title if exact_title else text

        filename, title = None, None

        # 2) YouTube orqali TO'LIQ qo'shiqni yuklashga urinamiz
        try:
            loop = asyncio.get_event_loop()
            filename, title = await loop.run_in_executor(None, download_full_audio_youtube, search_query, message.from_user.id)
        except Exception:
            logging.exception("YouTube orqali yuklashda xatolik")
            filename, title = None, None

        # 3) Agar YouTube ishlamasa (bloklansa), Deezer 30 soniyalik preview'ga qaytamiz
        if not filename or not os.path.exists(filename):
            filename, title = await search_deezer_music(search_query)

        if filename and os.path.exists(filename):
            bot_username = (await bot.get_me()).username
            audio = types.FSInputFile(filename, filename=f"{title}.mp3")
            await message.answer_audio(
                audio=audio,
                caption=f"🎵 {title}\n\n🤖 @{bot_username}",
                parse_mode="Markdown"
            )
            await wait_msg.delete()
            os.remove(filename)
        else:
            await wait_msg.edit_text("❌ Musiqa topilmadi. Qo'shiq nomini yoki artistni to'g'rilab yozing.")

# MAIN FUNCTION
async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(start_web())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())