import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. SOZLAMALAR
BOT_TOKEN = "8775079643:AAELiZIgt_sztnwPkqI8rOAZ5JoOQMfcDYM"
KANAL_ID = -1003874841801
ADMIN_ID = 8358382613  # O'zingizning Telegram ID-ngizni yozing

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Foydalanuvchilar bazasi
FOYDALANUVCHILAR = set()

# Asosiy tugmalar (Reply Keyboard)
bosh_menyu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎭 Janrlar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="ℹ️ Yordam"), KeyboardButton(text="👨‍💻 Admin")]
    ],
    resize_keyboard=True
)

# /start bosilganda
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer(
        f"👋 Salom, {message.from_user.first_name}!\n\n"
        "🎬 Kinolar olami botiga xush kelibsiz.\n"
        "Kino ko'rish uchun uning kodini (masalan: 1, 2, 15) yuboring.\n\n"
        "Kerakli bo'limni tanlang 👇",
        reply_markup=bosh_menyu
    )

# 📊 Statistika (Hammaga ko'rinadi)
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    jami = len(FOYDALANUVCHILAR)
    await message.answer(
        f"📊 Bot statistikasi:\n\n"
        f"👥 Jami foydalanuvchilar: {jami} ta\n"
        f"⚡️ Bot faol holatda ishlamoqda!"
    )

# 🎭 Janrlar
@dp.message(F.text == "🎭 Janrlar")
async def show_genres(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    matn = (
        "🎭 Mavjud kino janrlari:\n\n"
        "💥 Boevik / Jangari\n"
        "😱 Ujas / Qorqinchli\n"
        "😂 Komediya\n"
        "🤖 Fantastika\n"
        "❤️ Melodrama\n\n"
        "💡 Janrlar bo'yicha kinolar kodini kanaldan topishingiz mumkin!"
    )
    await message.answer(matn)

# ℹ️ Yordam
@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    matn = (
        "ℹ️ Botdan foydalanish yo'riqnomasi:\n\n"
        "1. Kanalimizdagi kinolarning pastida berilgan kodni ko'rib oling.\n"
        "2. O'sha kodni botga shunchaki raqamda yuboring (Masalan: 12).\n"
        "3. Bot sizga kinoni bir necha soniyada tashlab beradi!"
    )
    await message.answer(matn)

# 👨‍💻 Admin
@dp.message(F.text == "👨‍💻 Admin")
async def show_admin(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    await message.answer("👨‍💻 Admin bilan bog'lanish uchun: @admin_username")

# Kino kodini tekshirish va kanaldan nusxalab berish
@dp.message(F.text)
async def check_movie_code(message: types.Message):
    FOYDALANUVCHILAR.add(message.from_user.id)
    kod = message.text.strip()

    if kod.isdigit():
        message_id = int(kod)
        try:
            await bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=KANAL_ID,
                message_id=message_id
            )
        except Exception as e:
            logging.error(f"Xatolik: {e}")
            await message.answer("❌ Afsuski, bunday kodli kino topilmadi. Kodni to'g'ri kiritganingizni tekshiring.")
    else:
        await message.answer("⚠️ Iltimos, kino kodini faqat raqamda yuboring yoki menyudagi tugmalardan foydalaning.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())