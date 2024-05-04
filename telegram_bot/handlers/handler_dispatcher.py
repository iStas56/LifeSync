from aiogram import types, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, \
    CallbackQuery
import os
from dotenv import load_dotenv

load_dotenv()

router = Router()


@router.callback_query(lambda c: c.data == 'start')
async def return_to_start(callback_query: types.CallbackQuery):
    await process_start_command(callback_query.message)


@router.message(CommandStart())
async def process_start_command(message: Message):
    # Создаем инлайн-кнопки
    button_todos = InlineKeyboardButton(text='📋 Список дел', callback_data='todos')
    button_repetition = InlineKeyboardButton(text='🧠 Интервальное повторение', callback_data='words')
    button_rates = InlineKeyboardButton(text='💱 Конвертация валют', callback_data='rates')
    button_workouts = InlineKeyboardButton(text='🏋️ Менеджер тренировок', callback_data='workouts')

    # Создаем объект инлайн-клавиатуры и добавляем в него кнопки
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[button_todos], [button_repetition], [button_rates], [button_workouts]])

    await message.answer(text='🇲 🇪 🇳 🇺', reply_markup=keyboard)


def get_repetition_keyboard():
    back_button = get_back_button()
    new_word_button = types.InlineKeyboardButton(text="➕ Новое слово", callback_data="new_word")
    repeat_words_button = types.InlineKeyboardButton(text="🔄 Повторить слова", callback_data="repeat_word")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[repeat_words_button], [new_word_button], [back_button]])
    return keyboard


def get_rates_keyboard(user_id):
    back_button = get_back_button()
    convert_button = types.InlineKeyboardButton(text="💹 Узнать курс", callback_data="get_rates")

    keyboard_buttons = [[convert_button], [back_button]]

    # Если пользователь является администратором, добавляем кнопку обновления курсов валют
    if user_id == int(os.getenv('ADMIN_USER_ID')):
        update_rates_button = types.InlineKeyboardButton(text="🔄 Обновить курсы валют", callback_data="update_rates")
        keyboard_buttons.insert(0, [update_rates_button])

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard


def get_workouts_keyboard():
    text = ("🏋️ Менеджер тренировок 🏋️\n\n"
            "📌 Тут можно задать параметры тела для мониторинга изменений 📌\n"
            "📓 Вести дневник тренировок (количество подходов, вес, название упражнения) 📓\n"
            "📊 Получить данные прошедших тренировок 📊")

    back_button = get_back_button()
    measurements_button = types.InlineKeyboardButton(text="📏 Параметры тела", callback_data="measurements")
    add_exercise_button = types.InlineKeyboardButton(text="➕ Добавить тренировку", callback_data="add_exercise")
    show_exercises_button = types.InlineKeyboardButton(text="👀 Посмотреть тренировки", callback_data="show_exercises")

    keyboard_buttons = [[measurements_button, add_exercise_button], [show_exercises_button], [back_button]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    return {'text': text, 'keyboard': keyboard}


def get_back_button():
    return types.InlineKeyboardButton(text="🔙 Назад", callback_data="start")

