import asyncio

from aiogram import Bot, Dispatcher
from telegram_bot.config import Config, load_config
from telegram_bot.handlers import handler_dispatcher, todos, repetition


# Функция конфигурирования и запуска бота
async def main():
    # Загружаем конфиг в переменную config
    config: Config = load_config()

    # Инициализируем бот и диспетчер
    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher()

    # Регистриуем роутеры в диспетчере
    dp.include_router(handler_dispatcher.routdocer)
    dp.include_router(todos.router)
    dp.include_router(repetition.router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


asyncio.run(main())
