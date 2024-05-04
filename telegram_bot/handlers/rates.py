from datetime import datetime

import httpx
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from telegram_bot.handlers.handler_dispatcher import *

router = Router()


@router.callback_query(lambda c: c.data == 'rates')
async def rates_page(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    rates_date = await get_keyboard_rates(user_id)

    await callback_query.message.answer(text="━━━━━━━━━━━━━━━━━\n 📚 Конвертация валют 📚\n━━━━━━━━━━━━━━━━━\n")
    await callback_query.message.answer(rates_date['text'],
                                        reply_markup=rates_date['keyboard'])


async def get_keyboard_rates(user_id):
    keyboard = get_rates_keyboard(user_id)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://web:8000/rates/")
        if response.status_code == 200:
            last_update = response.json()['last_update']
            last_update_datetime = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")
            formatted_date = last_update_datetime.strftime("%d-%m-%Y")

            text = f"🕒 Курсы актуальны на 📅 {formatted_date} 🚀"
        else:
            text = 'Не удалось получить данные по курсам'

    return {'keyboard': keyboard, 'text': text}


@router.callback_query(lambda c: c.data == 'update_rates')
async def update_rates(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://web:8000/rates/update-rates")
        if response.status_code == 200:
            await callback_query.message.answer(text="Курсы обновлены ✅")
        else:
            await callback_query.message.answer(text="Не удалось обновить курсы")

    rates_buttons = await get_keyboard_rates(user_id)
    await callback_query.message.answer(rates_buttons['text'], reply_markup=rates_buttons['keyboard'])


class ConvertGetting(StatesGroup):
    waiting_for_source = State()
    waiting_for_target = State()
    waiting_for_sum = State()


# Логика конвертации
def get_cancel_rates():
    cancel_button = InlineKeyboardButton(text="❌ Отменить ❌", callback_data="cancel_convert")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[cancel_button]])
    return keyboard


@router.callback_query(F.data == "cancel_convert")
async def process_cancel(callback_query: CallbackQuery, state: FSMContext):
    await state.clear()  # Сброс состояния
    await callback_query.message.edit_text("🚫 Отменено 🚫")

    user_id = callback_query.from_user.id
    rates_buttons = await get_keyboard_rates(user_id)
    await callback_query.message.answer(rates_buttons['text'], reply_markup=rates_buttons['keyboard'])


@router.callback_query(lambda c: c.data == 'get_rates')
async def rate_start(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Введите код исходной валюты в формате RUB, USD, EUR и т.д. 💱",
        reply_markup=get_cancel_rates()
    )
    await state.set_state(ConvertGetting.waiting_for_source)


@router.message(StateFilter(ConvertGetting.waiting_for_source))
async def process_source_sent(message: Message, state: FSMContext):
    source = message.text.strip()
    if len(message.text.strip()) < 3:
        await message.answer("⚠️ Исходная валюта должна быть в формате RUB, USD, EUR, THB и т.д. ⚠️")
        return

    await state.update_data(source=source.upper())
    await message.answer(
        "Введите код валюты назначения в формате RUB, USD, EUR и т.д. 💱",
        reply_markup=get_cancel_rates()
    )

    await state.set_state(ConvertGetting.waiting_for_target)


@router.message(StateFilter(ConvertGetting.waiting_for_target))
async def process_target_sent(message: Message, state: FSMContext):
    target = message.text.strip()
    if len(message.text.strip()) < 3:
        await message.answer("⚠️ Валюта назначения должна быть в формате RUB, USD, EUR, THB и т.д. ⚠️")
        return

    await state.update_data(target=target.upper())
    await message.answer(
        "Введите сумму 💱",
        reply_markup=get_cancel_rates()
    )

    await state.set_state(ConvertGetting.waiting_for_sum)


@router.message(StateFilter(ConvertGetting.waiting_for_sum))
async def process_sum_sent(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    sum = message.text.strip()
    if float(sum) <= 0:
        await message.answer("⚠️ Сумма должна быть выше ноля ⚠️")
        return

    rate_data = {
        'sum': float(sum)
    }

    current_state = await state.get_data()
    rate_data.update(current_state)

    result = await convert_rate(rate_data)
    res_sum = float("{:.2f}".format(result['result']))
    if res_sum > 0:
        await message.answer(text=f"━━━━━━━━━━━━━━━━━\n{res_sum} {current_state['target']}\n"
                                  f"━━━━━━━━━━━━━━━━━\n", reply_markup=get_rates_keyboard(user_id))
    else:
        await message.answer(text='Произошла ошибка при конвертации ❌', reply_markup=get_rates_keyboard(user_id))
    await state.clear()


async def convert_rate(rate_data):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://web:8000/rates/get-rate", json=rate_data)
        if response.status_code == 200:
            return response.json()
