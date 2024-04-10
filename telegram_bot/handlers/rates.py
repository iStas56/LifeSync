from datetime import datetime

import httpx
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from telegram_bot.handlers.handler_dispatcher import *
from telegram_bot.logger import logger, log_user_action
router = Router()


@router.callback_query(lambda c: c.data == 'rates')
async def rates_page(source):
    user_id, message = await extract_source_info(source)

    keyboard = get_rates_keyboard(user_id)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://0.0.0.0:8000/rates/")
        if response.status_code == 200:
            last_update = response.json()['last_update']
            last_update_datetime = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")
            formatted_date = last_update_datetime.strftime("%d-%m-%Y")

    if message:
        text = ("━━━━━━━━━━━━━━━━━\n 📚 Конвертация валют 📚\n━━━━━━━━━━━━━━━━━\n"
                f"🕒 Курсы актуальны на 📅 {formatted_date} 🚀")
        await message.edit_text(text, reply_markup=keyboard) \
            if isinstance(source, types.CallbackQuery) \
            else await message.answer(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == 'update_rates')
async def update_rates(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://0.0.0.0:8000/rates/update-rates")
        text = "Неудалось обновить курсы"
        if response.status_code == 200:
            text = "Курсы обновлен ✅"
        await callback_query.message.answer(
            text,
            reply_markup=get_rates_keyboard(user_id)
        )


class ConvertGetting(StatesGroup):
    waiting_for_source = State()
    waiting_for_target = State()
    waiting_for_sum = State()


# Логика конвертации
@router.callback_query(lambda c: c.data == 'get_rates')
async def rate_start(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Введите код исходной валюты в формате RUB, USD, EUR и т.д. 💱",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ConvertGetting.waiting_for_source)


@router.message(StateFilter(ConvertGetting.waiting_for_source))
async def process_source_sent(message: Message, state: FSMContext):
    await log_user_action(message, state)

    source = message.text.strip()
    if len(message.text.strip()) < 3:
        await message.answer("⚠️ Исходная валюта должна быть в формате RUB, USD, EUR, THB и т.д. ⚠️")
        return

    await state.update_data(source=source.upper())
    await message.answer(
        "Введите код валюты назначения в формате RUB, USD, EUR и т.д. 💱",
        reply_markup=get_cancel_keyboard()
    )

    await state.set_state(ConvertGetting.waiting_for_target)


@router.message(StateFilter(ConvertGetting.waiting_for_target))
async def process_target_sent(message: Message, state: FSMContext):
    await log_user_action(message, state)

    target = message.text.strip()
    if len(message.text.strip()) < 3:
        await message.answer("⚠️ Валюта назначения должна быть в формате RUB, USD, EUR, THB и т.д. ⚠️")
        return

    await state.update_data(target=target.upper())
    await message.answer(
        "Введите сумму 💱",
        reply_markup=get_cancel_keyboard()
    )

    await state.set_state(ConvertGetting.waiting_for_sum)


@router.message(StateFilter(ConvertGetting.waiting_for_sum))
async def process_sum_sent(message: types.Message, state: FSMContext):
    await log_user_action(message, state)

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
        response = await client.post(f"http://0.0.0.0:8000/rates/get-rate", json=rate_data)
        if response.status_code == 200:
            return response.json()
