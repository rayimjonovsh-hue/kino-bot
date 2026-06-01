import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart

# 1. TAYYORGARLIK: Ma'lumotlarni shu yerga kiriting
BOT_TOKEN = "8775079643:AAELIzIgt_sztnwPkqI8rOAZ5JoOQMfcDYM"
KANAL_ID = -1003874841801  # Bu yerga boya botdan olgan kanal ID-sini yozing

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Botga /start bosilganda ko'rsatiladigan menyu
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Salom! Kinobotimizga xush kelibsiz.\n\n"
        "🎬 Kino ko'rish uchun uning kodini yuboring (Masalan: 1, 2, 15)."
    )

# Foydalanuvchi biror matn yoki kod yuborganida
@dp.message(F.text)
async def check_movie_code(message: types.Message):
    kod = message.text.strip()

    # Foydalanuvchi faqat raqam yuborganini tekshiramiz
    if kod.isdigit():
        message_id = int(kod)
        
        try:
            # Bot yopiq kanaldagi xabarni (kinoni) foydalanuvchiga nusxalab beradi
            await bot.copy_message(
                chat_id=message.chat.id,      # Kimga yuborish kerak
                from_chat_id=KANAL_ID,       # Qaysi kanaldan olish kerak
                message_id=message_id        # Kanaldagi xabar raqami (Kino kodi)
            )
        except Exception as e:
            # Agar kanalda bunday raqamli xabar bo'lmasa yoki o'chib ketgan bo'lsa
            logging.error(f"Xatolik yuz berdi: {e}")
            await message.answer("❌ Afsuski, bunday kodli kino topilmadi. Kodni to'g'ri kiritganingizga ishonch hosil qiling.")
    else:
        await message.answer("⚠️ Iltimos, kino kodini faqat raqamlarda yuboring (Masalan: 5).")

import os
from aiohttp import web

# Server o'chib qolmasligi uchun kichik Web-interfeys
async def handle(request):
    return web.Response(text="Bot ishlamoqda!")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Render serveri uchun portni sozlash
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get('/', handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # Bir vaqtning o'zida ham botni, ham veb-saytni ishga tushiramiz
    await asyncio.gather(
        dp.start_polling(bot),
        site.start()
    )

if __name__ == "__main__":
    asyncio.run(main())