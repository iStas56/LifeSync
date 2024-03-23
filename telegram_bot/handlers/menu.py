from aiogram import types, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

router = Router()


@router.message(CommandStart())
async def process_start_command(message: Message):
    # Создаем инлайн-кнопки
    button_todos = InlineKeyboardButton(text='Список дел', callback_data='todos')
    button_repetition = InlineKeyboardButton(text='Интервальное повторение', callback_data='repetition')
    button_rates = InlineKeyboardButton(text='Конвертация валют', callback_data='rates')
    button_trainings = InlineKeyboardButton(text='Менеджер тренировок', callback_data='trainings')

    # Создаем объект инлайн-клавиатуры и добавляем в него кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button_todos], [button_repetition], [button_rates], [button_trainings]])

    await message.answer(text='Выберите действие ниже:', reply_markup=keyboard)
