import json
import os
import asyncio
import logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. SOZLAMALAR
BOT_TOKEN = "8775079643:AAGYoXpUFdJtIqaHwjQwUuvtBmsJt3PyUjE"
KANAL_ID = -1003874841801
ADMIN_ID = 8358382613 # O'zingizning Telegram ID-ngiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 2. BAZA BILAN ISHLASH (JSON)
DB_FILE = "users.json"

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": [], "today_date": get_today_str(), "today_users": [], "left_count": 0}

DATA = load_data()
FOYDALANUVCHILAR = set(DATA.get("users", []))

def save_user(user_id):
    today = get_today_str()
    if DATA.get("today_date") != today:
        DATA["today_date"] = today
        DATA["today_users"] = []
    
    if user_id not in FOYDALANUVCHILAR:
        FOYDALANUVCHILAR.add(user_id)
        DATA["users"] = list(FOYDALANUVCHILAR)
        if user_id not in DATA["today_users"]:
            DATA["today_users"].append(user_id)
            
    with open(DB_FILE, "w") as f:
        json.dump(DATA, f)

def log_left_user():
    DATA["left_count"] = DATA.get("left_count", 0) + 1
    with open(DB_FILE, "w") as f:
        json.dump(DATA, f)

# 3. TUGMALAR (Reply Keyboard)
bosh_menyu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎭 Janrlar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="ℹ️ Yordam"), KeyboardButton(text="👤 Admin")]
    ],
    resize_keyboard=True
)

# 4. START BUYRUG'I
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    save_user(message.from_user.id)
    await message.answer(
        f"👋 Salom, {message.from_user.first_name}!\n\n"
        "🎬 Kinolar olami botiga xush kelibsiz.\n"
        "Kino ko'rish uchun uning kodini (masalan: 1, 2, 15) yuboring.\n\n"
        "Kerakli bo'limni tanlang 👇",
        reply_markup=bosh_menyu
    )

# 5. ADMIN RASSILKA (/send matn)
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
            await asyncio.sleep(0.05)
        except Exception:
            log_left_user()

    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga muvaffaqiyatli yuborildi!")

# 6. STATISTIKA (Faqat Admin uchun)
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        today = get_today_str()
        if DATA.get("today_date") != today:
            DATA["today_date"] = today
            DATA["today_users"] = []
            with open(DB_FILE, "w") as f:
                json.dump(DATA, f)

        jami = len(FOYDALANUVCHILAR)
        bugun = len(DATA.get("today_users", []))
        chiqqanlar = DATA.get("left_count", 0)

        text = (
            f"📊 Bot statistikasi:\n\n"
            f"👥 Jami foydalanuvchilar: {jami} ta\n"
            f"📥 Bugun qo'shilganlar: {bugun} ta\n"
            f"📤 Botdan chiqqanlar: {chiqqanlar} ta"
        )
        await message.answer(text, parse_mode="Markdown")
    else:
        await message.answer("⚠️ Bu bo'lim faqat admin uchun!")

# 7. JANRLAR TUGMASI
@dp.message(F.text == "🎭 Janrlar")
async def show_genres(message: types.Message):
    save_user(message.from_user.id)
    text = (
        "Mavjud kino janrlari:\n"
        "🍿 Boyevik\n"
        "🤣 Komediya\n"
        "🤖 Fantastika\n"
        "❤️ Melodrama\n\n"
        "💡 Janrlar bo'yicha kinolar kodini kanalimizdan topishingiz mumkin!\n"
        "👉 https://t.me/filimlar9"
    )
    await message.answer(text)

# 8. YORDAM TUGMASI
@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    save_user(message.from_user.id)
    await message.answer("🤖 Botdan foydalanish uchun kino kodini raqamda yuboring (Masalan: 1, 2, 5).")

# 9. ADMIN TUGMASI
@dp.message(F.text == "👤 Admin")
async def show_admin(message: types.Message):
    save_user(message.from_user.id)
    await message.answer("👨‍💻 Admin bilan bog'lanish: @filimlar9")

# 10. KINO QIDIRISH (Kino kodi yuborilganda)
@dp.message(F.text.isdigit())
async def get_movie(message: types.Message):
    save_user(message.from_user.id)
    movie_code = message.text
    try:
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=KANAL_ID,
            message_id=int(movie_code)
        )
    except Exception:
        await message.answer("❌ Bu kod bo'yicha kino topilmadi. Kodi to'g'riligini tekshirib ko'ring!")

# 11. BOSHQA NOTO'G'RI MATNLAR UCHUN JAVOB
@dp.message()
async def unknown_message(message: types.Message):
    save_user(message.from_user.id)
    await message.answer("⚠️ Iltimos, kino kodini faqat raqamda yuboring yoki menyudagi tugmalardan foydalaning.")

# 12. VEB-SERVER (Render uchun)
async def handle(request):
    return web.Response(text="Bot ishlamoqda!")

async def start_web():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    await start_web()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())