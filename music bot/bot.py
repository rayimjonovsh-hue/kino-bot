import asyncio
import logging
import sqlite3
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile

from openai import OpenAI
import yt_dlp
from dotenv import load_dotenv

# ============================================================
# SOZLAMALAR
# Bu qiymatlar .env faylidan o'qiladi (xavfsizlik uchun, GitHub'ga
# tokenlar to'g'ridan-to'g'ri kod ichida ketmasligi kerak)
# ============================================================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
print("DEBUG TOKEN:", repr(BOT_TOKEN))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

DB_PATH = "users.db"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ============================================================
# MA'LUMOTLAR BAZASI
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_user_if_new(user_id: int, username: str, first_name: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (user_id, username, first_name, joined_at) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        conn.commit()
    conn.close()


def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, first_name, joined_at FROM users ORDER BY joined_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_user_count():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count


# ============================================================
# HOLATLAR (FSM) - musiqa qidirish jarayoni uchun
# ============================================================
class MusicStates(StatesGroup):
    waiting_query = State()
    waiting_choice = State()


# ============================================================
# /start BUYRUG'I
# ============================================================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    add_user_if_new(
        message.from_user.id,
        message.from_user.username or "-",
        message.from_user.first_name or "-",
    )
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Men sizga quyidagilarda yordam bera olaman:\n"
        "🎵 /music — qo'shiq qidirish va yuklab olish\n"
        "💬 Oddiy xabar yozsangiz — sun'iy intellekt bilan suhbatlashamiz\n"
    )


# ============================================================
# ADMIN STATISTIKASI - faqat ADMIN_ID ko'ra oladi
# ============================================================
@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return  # boshqa hech kim javob olmaydi

    users = get_all_users()
    count = get_user_count()

    text = f"📊 Jami foydalanuvchilar: <b>{count}</b>\n\n"
    text += "So'nggi qo'shilganlar:\n"
    for user_id, username, first_name, joined_at in users[:20]:
        uname = f"@{username}" if username != "-" else "(username yo'q)"
        text += f"• {first_name} {uname} — ID: <code>{user_id}</code> — {joined_at}\n"

    if count > 20:
        text += f"\n... va yana {count - 20} kishi"

    await message.answer(text, parse_mode="HTML")


# ============================================================
# MUSIQA QIDIRISH - /music buyrug'i
# ============================================================
@dp.message(Command("music"))
async def cmd_music(message: Message, state: FSMContext):
    await state.set_state(MusicStates.waiting_query)
    await message.answer("🎵 Qo'shiq nomini yoki qo'shiqchi ismini yozing:")


def search_youtube(query: str, limit: int = 10):
    """YouTube'dan qo'shiq qidirish, natijalarni ro'yxat qilib qaytaradi."""



def format_duration(seconds):
    if not seconds:
        return "?"
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"


@dp.message(MusicStates.waiting_query)
async def process_music_query(message: Message, state: FSMContext):
    query = message.text
    searching_msg = await message.answer("🔍 Qidirilyapti...")

    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, search_youtube, query, 10)
    except Exception as e:
        await searching_msg.edit_text(f"❌ Qidirishda xatolik: {e}")
        await state.clear()
        return

    if not results:
        await searching_msg.edit_text("Hech narsa topilmadi. Boshqa nom bilan urinib ko'ring.")
        await state.clear()
        return

    await state.update_data(results=results)

    text = "Natijalar topildi, raqamini yuboring:\n\n"
    for i, r in enumerate(results, start=1):
        text += f"{i}. {r['title']} ({format_duration(r['duration'])})\n"

    await searching_msg.edit_text(text)
    await state.set_state(MusicStates.waiting_choice)


def download_audio(video_id: str) -> str:
    """Berilgan video ID bo'yicha audio yuklab oladi, fayl yo'lini qaytaradi."""
    output_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")
    ydl_opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "noplaylist": True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

    final_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
    return final_path


@dp.message(MusicStates.waiting_choice)
async def process_music_choice(message: Message, state: FSMContext):
    data = await state.get_data()
    results = data.get("results", [])

    if not message.text or not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam yuboring (masalan: 1)")
        return

    choice = int(message.text)
    if choice < 1 or choice > len(results):
        await message.answer(f"Iltimos 1 dan {len(results)} gacha raqam yuboring")
        return

    selected = results[choice - 1]
    downloading_msg = await message.answer(f"⬇️ Yuklab olinyapti: {selected['title']}...")

    loop = asyncio.get_event_loop()
    try:
        file_path = await loop.run_in_executor(None, download_audio, selected["id"])
        audio_file = FSInputFile(file_path, filename=f"{selected['title']}.mp3")
        await message.answer_audio(audio_file, title=selected["title"])
        await downloading_msg.delete()
        os.remove(file_path)  # diskni tozalab turish uchun
    except Exception as e:
        await downloading_msg.edit_text(f"❌ Yuklab olishda xatolik: {e}")

    await state.clear()


# ============================================================
# GROQ AI CHAT - oddiy xabarlarga javob
# ============================================================
def ask_groq(text: str) -> str:
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": text}],
    )
    return completion.choices[0].message.content


@dp.message(F.text)
async def ai_chat(message: Message):
    thinking_msg = await message.answer("💭 O'ylanyapman...")

    loop = asyncio.get_event_loop()
    try:
        reply = await loop.run_in_executor(None, ask_groq, message.text)
        await thinking_msg.edit_text(reply)
    except Exception as e:
        await thinking_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")


# ============================================================
# BOTNI ISHGA TUSHIRISH
# ============================================================
async def main():
    if not BOT_TOKEN or not GROQ_API_KEY or not ADMIN_ID:
        print("XATO: .env faylida BOT_TOKEN, GROQ_API_KEY yoki ADMIN_ID to'ldirilmagan!")
        return
    init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())