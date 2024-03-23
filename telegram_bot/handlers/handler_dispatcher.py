from aiogram import types, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, \
    CallbackQuery

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
    button_trainings = InlineKeyboardButton(text='🏋️ Менеджер тренировок', callback_data='trainings')

    # Создаем объект инлайн-клавиатуры и добавляем в него кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button_todos], [button_repetition], [button_rates], [button_trainings]])

    await message.answer(text='🇲 🇪 🇳 🇺', reply_markup=keyboard)


def get_repetition_keyboard():
    back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="start")
    new_word_button = types.InlineKeyboardButton(text="➕ Новое слово", callback_data="new_word")
    repeat_words_button = types.InlineKeyboardButton(text="🔄 Повторить слова", callback_data="repeat_word")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[repeat_words_button], [new_word_button], [back_button]])
    return keyboard


def get_cancel_keyboard():
    cancel_button = InlineKeyboardButton(text="❌ Остановить добавление ❌", callback_data="cancel")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[cancel_button]])
    return keyboard


@router.callback_query(F.data == "cancel")
async def process_cancel(callback_query: CallbackQuery, state: FSMContext):
    await state.clear()  # Сброс состояния
    await callback_query.message.edit_text("🚫 Добавление отменено 🚫")
    await callback_query.answer()


async def extract_source_info(source):
    if isinstance(source, types.CallbackQuery):
        user_id = source.from_user.id
        message = source.message
        await source.answer()
    elif isinstance(source, types.Message):
        user_id = source.from_user.id
        message = source
    else:
        user_id = None
        message = None
    return user_id, message