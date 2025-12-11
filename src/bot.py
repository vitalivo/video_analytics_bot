import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

from src.config import BOT_TOKEN
from src.llm_service import generate_sql_from_text
from src.db import execute_sql_query

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Я аналитический бот. Спроси меня что-нибудь о статистике видео.")

@dp.message()
async def handle_text_query(message: Message):
    user_text = message.text
    
    # 1. Генерация SQL через LLM
    sql_query = await generate_sql_from_text(user_text)
    
    if not sql_query:
        await message.answer("Не удалось понять запрос или сгенерировать SQL.")
        return

    # Для отладки (можно убрать в проде)
    logging.info(f"Generated SQL: {sql_query}")

    # 2. Выполнение запроса
    result = await execute_sql_query(sql_query)
    
    if result is None:
         await message.answer("Ошибка выполнения запроса к базе данных.")
    else:
        # 3. Отправка ответа (одно число)
        await message.answer(str(result))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())