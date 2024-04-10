import httpx
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from telegram_bot.handlers.handler_dispatcher import *
from telegram_bot.logger import logger, log_user_action

router = Router()
word_storage = {}


@router.callback_query(lambda c: c.data == 'words')
async def words_page(source):
    user_id, message = await extract_source_info(source)

    # Добавляем кнопки действий в отдельный ряд
    keyboard = get_repetition_keyboard()

    if message:
        text = ("━━━━━━━━━━━━━━━━━\n 📚 Интервальное повторение слов 📚\n━━━━━━━━━━━━━━━━━━━\n➡️ "
                "Выберите действие:")
        await message.edit_text(text, reply_markup=keyboard) \
            if isinstance(source, types.CallbackQuery) \
            else await message.answer(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == 'repeat_word')
async def get_word(callback_query: types.CallbackQuery):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://web:8000/word/")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                word_storage[callback_query.from_user.id] = data

                next_word_button = types.InlineKeyboardButton(text="➡️ Следующее", callback_data="repeat_word")
                translate_button = types.InlineKeyboardButton(text="👁 Перевод", callback_data="show_translation")
                back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="words")

                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[[next_word_button, translate_button], [back_button]])

                await callback_query.message.edit_text(text=f"🇬🇧 {data['word']}", reply_markup=keyboard)
            else:
                await callback_query.message.answer(
                    f"🚫 {data['message']} 🚫 \nКажется, на сегодня все задания выполнены! 🎉")
                await words_page(callback_query.message)
        await callback_query.answer()


@router.callback_query(lambda c: c.data == 'show_translation')
async def show_translation(callback_query: types.CallbackQuery):
    data = word_storage.get(callback_query.from_user.id, {})
    if data:
        next_word_button = types.InlineKeyboardButton(text="Следующее", callback_data="repeat_word")
        back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="words")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[next_word_button, back_button]])
        await callback_query.message.edit_text(f"🇬🇧 {data['word']}\n🇷🇺 {data['translation']}", reply_markup=keyboard)
    else:
        await callback_query.message.edit_text("Извините, произошла ошибка.")
    await callback_query.answer()


class WordCreation(StatesGroup):
    waiting_for_word = State()
    waiting_for_translate = State()


# Логика добавления слова
@router.callback_query(lambda c: c.data == 'new_word')
async def new_word_start(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "🇬🇧 Введите слово на английском ✏️",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(WordCreation.waiting_for_word)


@router.message(StateFilter(WordCreation.waiting_for_word))
async def process_word_sent(message: Message, state: FSMContext):

    word = message.text.strip()
    if len(message.text.strip()) < 2:
        await message.answer("⚠️ Слово должно содержать минимум 2 символа. Пожалуйста, попробуйте снова ⚠️")
        return

    await state.update_data(word=word)
    await message.answer(
        "🇷🇺 Введите перевод: ✏️",
        reply_markup=get_cancel_keyboard()
    )

    await state.set_state(WordCreation.waiting_for_translate)


@router.message(StateFilter(WordCreation.waiting_for_translate))
async def process_translate_sent(message: types.Message, state: FSMContext):

    translate = message.text.strip()
    if len(message.text.strip()) < 2:
        await message.answer("⚠️ Перевод должен содержать минимум 2 символа. Пожалуйста, попробуйте снова ⚠️")
        return

    user_id = message.from_user.id

    # Собираем все данные для новой задачи
    word_data = {
        'translation': translate,
        'user_id': user_id,
    }

    # Добавляем остальные данные из состояния
    word_data.update(await state.get_data())

    # Попытка добавить новую задачу через API
    if await add_new_word(word_data):
        await message.answer(text='Слово добавлено! ✅', reply_markup=get_repetition_keyboard())
    else:
        await message.answer(text='Произошла ошибка при добавлении слова ❌', reply_markup=get_repetition_keyboard())
    await state.clear()


async def add_new_word(word_data):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://web:8000/word/", json=word_data)
        return response.status_code == 201
