import asyncio

from aiogram import Bot, Dispatcher
from telegram_bot.config import Config, load_config
from telegram_bot.handlers import handler_dispatcher, todos, repetition, rates, workouts


# Функция конфигурирования и запуска бота
async def main():
    # Загружаем конфиг в переменную config
    config: Config = load_config()

    # Инициализируем бот и диспетчер
    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher()

    # Регистриуем роутеры в диспетчере
    dp.include_router(handler_dispatcher.router)
    dp.include_router(todos.router)
    dp.include_router(repetition.router)
    dp.include_router(rates.router)
    dp.include_router(workouts.router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


asyncio.run(main())
