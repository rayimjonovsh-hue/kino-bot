import json
import os
import asyncio
import logging
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    TelegramObject,
)
from typing import Any, Awaitable, Callable, Dict

# =========================================================
# 1. SOZLAMALAR
# =========================================================
# Xavfsizlik uchun tavsiya: tokenni Render/Railway'dagi "Environment
# Variables" bo'limiga BOT_TOKEN nomi bilan qo'shing. Agar u yerda
# topilmasa, pastdagi qiymat zaxira sifatida ishlatiladi.
BOT_TOKEN = os.environ.get(
    "BOT_TOKEN", "8775079643:AAHv382ZXL7N3dAwrZ3Eg4l5FzDiirgXDmI"
)
KANAL_ID = -1003874841801          # Kino postlari joylashgan kanal (copy_message uchun)
KANAL_USERNAME = "@filimlar9"      # Majburiy obuna talab qilinadigan kanal
ADMIN_ID = 8358382613              # O'zingizning Telegram ID-ngiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =========================================================
# 2. BAZA BILAN ISHLASH (JSON)
# =========================================================
DB_FILE = "users.json"


def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")


def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logging.warning("users.json o'qib bo'lmadi, yangi baza yaratiladi.")
    return {"users": [], "today_date": get_today_str(), "today_users": [], "left_count": 0}


DATA = load_data()
FOYDALANUVCHILAR = set(DATA.get("users", []))


def _persist():
    """Baza faylini xavfsiz (vaqtinchalik fayl orqali) saqlaydi."""
    tmp_file = DB_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(DATA, f, ensure_ascii=False)
    os.replace(tmp_file, DB_FILE)


def save_user(user_id: int):
    today = get_today_str()
    if DATA.get("today_date") != today:
        DATA["today_date"] = today
        DATA["today_users"] = []

    changed = False
    if user_id not in FOYDALANUVCHILAR:
        FOYDALANUVCHILAR.add(user_id)
        DATA["users"] = list(FOYDALANUVCHILAR)
        changed = True

    if user_id not in DATA["today_users"]:
        DATA["today_users"].append(user_id)
        changed = True

    if changed:
        _persist()


def log_left_user():
    DATA["left_count"] = DATA.get("left_count", 0) + 1
    _persist()


# =========================================================
# 3. MAJBURIY OBUNA (@filimlar9)
# =========================================================
def obuna_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga o'tish", url=f"https://t.me/{KANAL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")],
        ]
    )


async def is_subscribed(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=KANAL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        # Bot kanalda admin bo'lmasa yoki foydalanuvchi hali botga umuman
        # ko'rinmasa ham botni butunlay to'xtatib qo'ymaslik uchun False qaytaramiz,
        # lekin xatoni logga yozamiz — diagnostika uchun foydali.
        logging.warning(f"Obunani tekshirishda xato (user_id={user_id}): {e}")
        return False


class SubscriptionMiddleware(BaseMiddleware):
    """Har bir xabardan oldin foydalanuvchi @filimlar9 ga obuna bo'lganini tekshiradi."""

async def call(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user is not None and not await is_subscribed(user.id):
            await event.answer(
                "🔒 Botdan foydalanish uchun avval quyidagi kanalga obuna bo'ling, "
                "so'ngra \"✅ Tekshirish\" tugmasini bosing:",
                reply_markup=obuna_keyboard(),
            )
            return  # handlerga o'tkazilmaydi
        return await handler(event, data)


dp.message.middleware(SubscriptionMiddleware())


@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        save_user(callback.from_user.id)
        await callback.message.delete()
        await callback.message.answer(
            f"✅ Rahmat! Obuna tasdiqlandi, {callback.from_user.first_name}.\n\n"
            "🎬 Kino ko'rish uchun uning kodini (masalan: 1, 2, 15) yuboring.\n\n"
            "Kerakli bo'limni tanlang 👇",
            reply_markup=bosh_menyu,
        )
    else:
        await callback.answer(
            "❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True
        )


# =========================================================
# 4. TUGMALAR (Reply Keyboard)
# =========================================================
bosh_menyu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎭 Janrlar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="ℹ️ Yordam"), KeyboardButton(text="👤 Admin")],
    ],
    resize_keyboard=True,
)


# =========================================================
# 5. START BUYRUG'I
# =========================================================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    save_user(message.from_user.id)
    jami = len(FOYDALANUVCHILAR)
    await message.answer(
        f"👋 Salom, {message.from_user.first_name}!\n\n"
        "🎬 Kinolar olami botiga xush kelibsiz.\n"
        f"👥 Hozirda botda {jami} ta foydalanuvchi bor.\n\n"
        "Kino ko'rish uchun uning kodini (masalan: 1, 2, 15) yuboring.\n\n"
        "Kerakli bo'limni tanlang 👇",
        reply_markup=bosh_menyu,
    )


# =========================================================
# 6. ADMIN RASSILKA (/send matn)
# =========================================================
@dp.message(F.text.startswith("/send") & (F.from_user.id == ADMIN_ID))
async def send_broadcast(message: types.Message):
    text_to_send = message.text.replace("/send", "").strip()
    if not text_to_send:
        await message.answer("❌ Matn yozmadingiz! Namuna: /send Salom barchaga")
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


# =========================================================
# 7. STATISTIKA (Faqat Admin uchun)
# =========================================================
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ Bu bo'lim faqat admin uchun!")
        return

    today = get_today_str()
    if DATA.get("today_date") != today:
        DATA["today_date"] = today
        DATA["today_users"] = []
        _persist()

    jami = len(FOYDALANUVCHILAR)
    bugun = len(DATA.get("today_users", []))
    chiqqanlar = DATA.get("left_count", 0)

    text = (
        "📊 Bot statistikasi:\n\n"
        f"👥 Jami foydalanuvchilar: {jami} ta\n"
        f"🆕 Bugun qo'shilganlar: {bugun} ta\n"
        f"🚪 Botdan chiqqanlar: {chiqqanlar} ta"
    )
    await message.answer(text)

# =========================================================
# 8. JANRLAR TUGMASI
# =========================================================
@dp.message(F.text == "🎭 Janrlar")
async def show_genres(message: types.Message):
    save_user(message.from_user.id)
    text = (
        "Mavjud kino janrlari:\n"
        "🔫 Boyevik\n"
        "😂 Komediya\n"
        "👽 Fantastika\n"
        "💖 Melodrama\n\n"
        "🏆 Janrlar bo'yicha kinolar kodini kanalimizdan topishingiz mumkin!\n"
        f"👉 https://t.me/{KANAL_USERNAME.lstrip('@')}"
    )
    await message.answer(text)


# =========================================================
# 9. YORDAM TUGMASI
# =========================================================
@dp.message(F.text.in_({"ℹ️ Yordam", "Yordam"}))
async def show_help(message: types.Message):
    save_user(message.from_user.id)
    jami = len(FOYDALANUVCHILAR)
    text = (
        "ℹ️ Bot haqida ma'lumot va yo'riqnoma\n\n"
        f"👥 Botda hozircha {jami} ta foydalanuvchi bor.\n\n"
        "🎬 Ushbu botda turli xil janrdagi saralangan kinolar va seriallarni yuqori sifatda tomosha qilishingiz mumkin!\n\n"
        f"📢 Botdan foydalanish uchun {KANAL_USERNAME} kanaliga obuna bo'lishingiz shart.\n\n"
        "🎬 Kino tomosha qilish tartibi:\n"
        f"1. Kunning eng yangi va zo'r kinolari kodlarini 👉 {KANAL_USERNAME} kanalimizdan topasiz.\n"
        "2. U yerdagi kino kodini botga shunchaki raqamda yuborasiz (Masalan: 12).\n"
        "3. Bot sizga kinoni lahzalarda yetkazib beradi!\n\n"
        "💖 Bizning kamtarona mehnatimizni qadrlab, kanalimizga obuna bo'lib qo'llab-quvvatlaysiz degan umiddamiz!"
    )
    await message.answer(text, disable_web_page_preview=True)


# =========================================================
# 10. ADMIN TUGMASI
# =========================================================
@dp.message(F.text.in_({"👤 Admin", "Admin"}))
async def show_admin(message: types.Message):
    save_user(message.from_user.id)
    text = (
        "👤 Bot admini bilan bog'lanish:\n\n"
        "Barcha savollar bo'yicha profilga yozishingiz mumkin:\n"
        f"👉 [Admin Profiliga O'tish](tg://user?id={ADMIN_ID})"
    )
    await message.answer(text, parse_mode="Markdown")


# =========================================================
# 11. KINO QIDIRISH (Kino kodi yuborilganda)
# =========================================================
@dp.message(F.text.isdigit())
async def get_movie(message: types.Message):
    save_user(message.from_user.id)
    movie_code = message.text
    try:
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=KANAL_ID,
            message_id=int(movie_code),
        )
    except Exception:
        await message.answer("❌ Bu kod bo'yicha kino topilmadi. Kodi to'g'riligini tekshirib ko'ring!")


# =========================================================
# 12. BOSHQA NOTO'G'RI MATNLAR UCHUN JAVOB
# =========================================================
@dp.message()
async def unknown_message(message: types.Message):
    save_user(message.from_user.id)
    await message.answer("⚠️ Iltimos, kino kodini faqat raqamda yuboring yoki menyudagi tugmalardan foydalaning.")


# =========================================================
# 13. FOYDALANUVCHILAR SONINI "TEPADA" KO'RSATISH
# =========================================================
# Bot profilining tepasida (chat ochilganda, /start bosilmasdan oldin)
# ko'rinadigan tavsifni har necha daqiqada bir yangilab turadi.
async def update_bot_description():
    while True:
        jami = len(FOYDALANUVCHILAR)
        try:
            await bot.set_my_short_description(
                short_description=f"🎬 Kinolar olami | 👥 {jami} ta foydalanuvchi"
            )
            await bot.set_my_description(
               description=(
                    "🎬 Kinolar olami botiga xush kelibsiz!\n"
                    f"👥 Hozirda botda {jami} ta foydalanuvchi bor.\n\n"
                    f"📢 Ishga tushirish uchun {KANAL_USERNAME} kanaliga obuna bo'ling va /start bosing."
                )
            )
        except Exception as e:
            logging.warning(f"Bot tavsifini yangilashda xato: {e}")
        await asyncio.sleep(300)  # 5 daqiqada bir yangilanadi


# =========================================================
# 14. VEB-SERVER (Render / UptimeRobot uchun) — o'zgartirilmagan
# =========================================================
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

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Webhook o'chirishda xato: {e}")

    asyncio.create_task(start_web())
    asyncio.create_task(update_bot_description())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())  