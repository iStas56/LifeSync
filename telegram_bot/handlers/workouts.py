import os
from datetime import datetime
from typing import Union

from aiogram import types, Router
import httpx
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telegram_bot.handlers.handler_dispatcher import get_workouts_keyboard, get_back_button
from aiogram.types import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, InputFile, FSInputFile)
from telegram_bot.logger import logger, log_user_action

router = Router()


@router.callback_query(lambda c: c.data == 'workouts')
async def workouts_page(callback_query: types.CallbackQuery):
    workouts = get_workouts_keyboard()

    await callback_query.message.answer(workouts['text'], reply_markup=workouts['keyboard'])


param_names = {
    "hips": "Объем бедер",
    "chest": "Объем груди",
    "biceps": "Бицепс (ненапряженный)",
    "biceps_tense": "Бицепс (напряженный)",
    "waist": "Объем талии",
    "thighs": "Объем бедра",
    "calf": "Объем икры",
    "weight": "Вес"
}


async def get_body_measurements_buttons(user_id: int) -> Union[
    dict[str, Union[InlineKeyboardMarkup, str]], InlineKeyboardMarkup]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://web:8000/workout/measure", params={"user_id": user_id})
        if response.status_code == 200 and response.json():
            measurements = response.json()
            measurements_id = measurements.get('id')
            measurements.pop("id", None)
        else:
            measurements_add_button = types.InlineKeyboardButton(text="➕ Ввести параметры",
                                                                 callback_data="add_measurements")
            back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="workouts")
            text = "🚫 У вас еще не заданы параметры тела 📏\n""Для запуска сценария добавления параметров нажмите кнопку ниже 👇"
            return {'keyboard': types.InlineKeyboardMarkup(inline_keyboard=[[measurements_add_button], [back_button]]),
                    'text': text}

    measurements_buttons = [
        [types.InlineKeyboardButton(text=f"{param_names.get(measure, measure)} - {value}",
                                    callback_data=f"measure_{measure}_{measurements_id}")]
        for measure, value in measurements.items() if measure in param_names
    ]

    back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="workouts")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=measurements_buttons + [[back_button]])
    text = "📏 Ваши параметры тела 📏\n✏️ Для изменения данных нажмите на нужный параметр 👇\n"

    return {'keyboard': keyboard, 'text': text}


@router.callback_query(lambda c: c.data == 'measurements')
async def show_measurements(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    buttons = await get_body_measurements_buttons(user_id)

    await callback_query.message.answer(buttons['text'],
                                        reply_markup=buttons['keyboard'])


@router.callback_query(lambda c: c.data and c.data.startswith('cancel_'))
async def process_cancel(callback_query: CallbackQuery, state: FSMContext):
    mode = callback_query.data.split('_')[1]

    if mode == 'exercise':
        workouts = get_workouts_keyboard()
        await callback_query.message.answer("🚫 Отменено 🚫\n\n")
        await callback_query.message.answer(workouts['text'], reply_markup=workouts['keyboard'])

    else:
        word = "обновление" if mode == "update" else "добавление"
        text = f"🚫 Отменено {word} 🚫\nВыберите нажмите на параметр для изменения👇"

        user_id = callback_query.from_user.id
        result = await get_body_measurements_buttons(user_id)

        await callback_query.message.answer(text, reply_markup=result['keyboard'])
    await state.clear()


# Логика обновления параметров
class MeasurementUpdate(StatesGroup):
    waiting_for_value = State()


@router.callback_query(lambda c: c.data and c.data.startswith('measure_'))
async def update_measure(callback_query: types.CallbackQuery, state: FSMContext):
    _, measure_code, measurements_id = callback_query.data.split('_', 2)

    await state.update_data(id=measurements_id, code=measure_code)

    cancel_button = InlineKeyboardButton(text="❌ Отменить ❌", callback_data="cancel_update")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[cancel_button]])

    await callback_query.message.answer(
        f"✏️ Введите значение для параметра \"{param_names.get(measure_code, measure_code)}\"",
        reply_markup=keyboard
    )

    await state.set_state(MeasurementUpdate.waiting_for_value)


@router.message(StateFilter(MeasurementUpdate.waiting_for_value))
async def process_param_sent(message: types.Message, state: FSMContext):
    param_value = message.text.strip()
    if not param_value.isdigit() or not float(param_value) > 0:
        await message.answer("⚠️ Значение должно быть выше 0. Попробуйте ещё раз ⚠️")
        return

    await state.update_data(value=float(param_value))

    param_data = await state.get_data()

    if await update_measurements_param(param_data):
        await message.answer(text='Параметр обновлен ✅')
        user_id = message.from_user.id
        result = await get_body_measurements_buttons(user_id)
        await message.answer("Ваши обновленные параметры тела:", reply_markup=result['keyboard'])
    else:
        await message.answer(text='Произошла ошибка при обновлении параметра ❌')
        user_id = message.from_user.id
        result = await get_body_measurements_buttons(user_id)
        await message.answer("Попробуйте изменить параметр ещё раз или выберите другой параметр для изменения:",
                             reply_markup=result['keyboard'])

    await state.clear()


async def update_measurements_param(data):
    async with httpx.AsyncClient() as client:
        response = await client.put(f"http://web:8000/workout/measure/{data['id']}",
                                    json={data['code']: data['value']})
        return response.status_code == 201


# Логика добавления параметров
def get_cancel_button_for_add_process():
    cancel_button = InlineKeyboardButton(text="❌ Отменить ❌", callback_data="cancel_add")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[cancel_button]])
    return keyboard


class MeasurementInput(StatesGroup):
    waiting_for_input = State()


@router.callback_query(lambda c: c.data == "add_measurements")
async def start_adding_measurements(callback_query: types.CallbackQuery, state: FSMContext):
    first_param = list(param_names.keys())[0]
    await state.update_data(current_param=first_param)

    await callback_query.message.answer(
        f"✏️ Введите значение для параметра \"{param_names[first_param]}\". Если хотите пропустить этот параметр, введите 0.",
        reply_markup=get_cancel_button_for_add_process()
    )
    await state.set_state(MeasurementInput.waiting_for_input)


@router.message(StateFilter(MeasurementInput.waiting_for_input))
async def receive_measurement_input(message: types.Message, state: FSMContext):
    param_value = message.text.strip()
    user_data = await state.get_data()
    current_param = user_data["current_param"]

    if not param_value.isdigit() or int(param_value) < 0:
        await message.answer("⚠️ Параметр должен быть числом 0(если хотите пропустить) и выше. Попробуйте ещё раз ⚠️")
        return

    user_data[current_param] = param_value
    await state.update_data(user_data)

    param_index = list(param_names.keys()).index(current_param)
    if param_index + 1 < len(param_names):
        # Переход к следующему параметру
        next_param = list(param_names.keys())[param_index + 1]
        await state.update_data(current_param=next_param)
        await message.answer(
            f"✏️ Введите значение для параметра \"{param_names[next_param]}\". Если хотите пропустить этот параметр, введите 0.",
            reply_markup=get_cancel_button_for_add_process()
        )
    else:
        user_data = await state.get_data()
        user_data.pop('current_param', None)
        logger.info(user_data)
        user_id = message.from_user.id

        if await add_measurements_param(user_data, user_id):
            text = "Параметры заданы ✅\nВаши текущие параметры:"
        else:
            text = "Произошла ошибка при обновлении параметра ❌"

        result = await get_body_measurements_buttons(user_id)
        await message.answer(text=text, reply_markup=result['keyboard'])

        await state.clear()


async def add_measurements_param(data, user_id):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://web:8000/workout/measure", params={"user_id": user_id},
                                     json=data)
        return response.status_code == 201


# Логика добавления упражнения
def get_cancel_add_exercise_keyboard():
    cancel_button = InlineKeyboardButton(text="❌ Отменить ❌", callback_data="cancel_exercise")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[cancel_button]])
    return keyboard


class ExerciseInput(StatesGroup):
    waiting_for_title = State()
    waiting_for_sets = State()
    waiting_for_repetitions = State()
    waiting_for_weight = State()
    waiting_for_date = State()


@router.callback_query(lambda c: c.data == "add_exercise")
async def start_adding_exercise(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        f"✏️ Введите названия упражнения",
        reply_markup=get_cancel_add_exercise_keyboard()
    )
    await state.set_state(ExerciseInput.waiting_for_title)


@router.message(StateFilter(ExerciseInput.waiting_for_title))
async def process_title_sent(message: Message, state: FSMContext):

    title = message.text.strip()
    if len(message.text.strip()) < 2:
        await message.answer(
            "⚠️ Название упражнения должно содержать минимум 2 символа. Пожалуйста, попробуйте снова ⚠️")
        return

    await state.update_data(exercise_name=title)
    await message.answer(
        "✏️ Введите количество подходов 🔢",
        reply_markup=get_cancel_add_exercise_keyboard()
    )

    await state.set_state(ExerciseInput.waiting_for_sets)


@router.message(StateFilter(ExerciseInput.waiting_for_sets))
async def process_sets_sent(message: Message, state: FSMContext):

    sets = message.text.strip()
    if not sets.isdigit() or int(sets) <= 0:
        await message.answer("⚠️ Количество подходов должно быть выше ноля. Пожалуйста, попробуйте снова ⚠️")
        return

    await state.update_data(sets=int(sets))
    await message.answer(
        "✏️ Введите количество повторений 🔢",
        reply_markup=get_cancel_add_exercise_keyboard()
    )

    await state.set_state(ExerciseInput.waiting_for_repetitions)


@router.message(StateFilter(ExerciseInput.waiting_for_repetitions))
async def process_repetitions_sent(message: Message, state: FSMContext):

    repetitions = message.text.strip()
    if not repetitions.isdigit() or int(repetitions) <= 0:
        await message.answer("⚠️ Количество повторений должно быть выше ноля. Пожалуйста, попробуйте снова ⚠️")
        return

    await state.update_data(repetitions=int(repetitions))
    await message.answer(
        "✏️ Введите вес, если упражнение выполнялось без веса, то укажите 0 🔢",
        reply_markup=get_cancel_add_exercise_keyboard()
    )

    await state.set_state(ExerciseInput.waiting_for_weight)


def get_date_keyboard():
    today_button = InlineKeyboardButton(text="Сегодня", callback_data="date_today")
    input_date_button = InlineKeyboardButton(text="Введите дату", callback_data="date_input")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[today_button], [input_date_button]])
    return keyboard


@router.message(StateFilter(ExerciseInput.waiting_for_weight))
async def process_weight_sent(message: types.Message, state: FSMContext):
    weight = message.text.strip()
    if not weight.isdigit() or not int(weight) >= 0:
        await message.answer("⚠️ Значение должно быть выше 0. Попробуйте ещё раз ⚠️")
        return

    await state.update_data(weight=int(weight))

    # После ввода веса предлагаем пользователю выбрать дату
    await message.answer("Выберите дату тренировки:", reply_markup=get_date_keyboard())
    await state.set_state(ExerciseInput.waiting_for_date)


@router.callback_query(lambda c: c.data == "date_today", StateFilter(ExerciseInput.waiting_for_date))
async def date_today_selected(callback_query: types.CallbackQuery, state: FSMContext):
    formatted_date = datetime.now().strftime("%Y-%m-%dT00:00:00")
    await state.update_data(workout_date=formatted_date)
    logger.info(await state.get_data())


@router.callback_query(lambda c: c.data == "date_input", StateFilter(ExerciseInput.waiting_for_date))
async def date_input_selected(callback_query: types.CallbackQuery, state: FSMContext):
    # Просто просим пользователя ввести дату, состояние уже установлено на ожидание даты
    await callback_query.message.answer("Введите дату выполнения упражнения в формате ДД.ММ.ГГГГ",
                                        reply_markup=types.ReplyKeyboardRemove())


@router.message(StateFilter(ExerciseInput.waiting_for_date))
async def process_date_sent(message: types.Message, state: FSMContext):
    date_input = message.text.strip().lower()
    try:
        workout_date = datetime.strptime(date_input, "%d.%m.%Y")
    except ValueError:
        await message.answer("⚠️ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (08.12.2024) ⚠️")
        return

    formatted_date = workout_date.strftime("%Y-%m-%dT00:00:00")
    await state.update_data(workout_date=formatted_date)
    logger.info(await state.get_data())
    param_data = await state.get_data()

    user_id = message.from_user.id
    if await add_exercise(param_data, user_id):
        await message.answer(text='Упражнение добавлено ✅\n\n')
    else:
        await message.answer(text='Произошла ошибка при обновлении параметра ❌\n\n')
    workouts = get_workouts_keyboard()

    await message.answer(workouts['text'], reply_markup=workouts['keyboard'])

    await state.clear()


async def add_exercise(data, user_id):
    logger.info(data)
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://web:8000/workout/", params={'user_id': user_id},
                                     json=data)
        return response.status_code == 201


# логика получения тренировок
async def get_filtres_buttons():
    text = "📊 Получить данные прошедших тренировок по фильтрам(pdf) 📊"

    back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="workouts")
    last_workout_button = types.InlineKeyboardButton(text="Последняя тренировка",
                                                     callback_data="show_workout_last-workout")
    show_curweek_button = types.InlineKeyboardButton(text="За текущую неделю",
                                                     callback_data="show_workout_current-week")
    show_lastweek_button = types.InlineKeyboardButton(text="За прошлую неделю", callback_data="show_workout_last-week")
    show_curmonth_button = types.InlineKeyboardButton(text="За текущый месяц",
                                                      callback_data="show_workout_current-month")
    show_lastmonth_button = types.InlineKeyboardButton(text="За прошлый месяц",
                                                       callback_data="show_workout_last-month")
    show_all_workouts_button = types.InlineKeyboardButton(text="Все тренировки", callback_data="show_workout_all")
    show_date_button = types.InlineKeyboardButton(text="По дате", callback_data="show_workout_date")
    name_exercise_button = types.InlineKeyboardButton(text="По названию", callback_data="show_workout_exercise-name")

    keyboard_buttons = [
        [show_date_button], [name_exercise_button],
        [last_workout_button], [show_curweek_button], [show_lastweek_button], [show_curmonth_button],
        [show_lastmonth_button], [show_all_workouts_button],
        [back_button]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    return {'text': text, 'keyboard': keyboard}


@router.callback_query(lambda c: c.data == "show_exercises")
async def show_exercises_filters(callback_query: types.CallbackQuery):
    buttons = await get_filtres_buttons()

    await callback_query.message.answer(buttons['text'],
                                        reply_markup=buttons['keyboard'])


class WorkoutFilters(StatesGroup):
    waiting_for_input = State()


@router.callback_query(lambda c: c.data and c.data.startswith('show_workout_'))
async def filter_workouts(callback_query: types.CallbackQuery, state: FSMContext):
    filter_type = callback_query.data.split("_")[-1]

    # Проверяем, требуется ли ввод с клавиатуры
    if filter_type in ["date", "exercise-name"]:
        # Если нужен ввод, переходим в соответствующее состояние
        await state.set_state(WorkoutFilters.waiting_for_input)
        await state.update_data(filter_type=filter_type)

        prompt_text = "Введите дату тренировки (ДД.ММ.ГГГГ)" if filter_type == "date" else "Введите название упражнения"
        cancel_button = InlineKeyboardButton(text="❌ Отменить ❌", callback_data="show_exercises")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[cancel_button]])
        await callback_query.message.answer(prompt_text, reply_markup=keyboard)
    else:
        back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="show_exercises")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[back_button]])
        file = await get_workouts_by_filter(callback_query.from_user.id, filter_type, 'period', callback_query)
        if file:
            await callback_query.bot.send_document(callback_query.from_user.id, FSInputFile(file))
            await callback_query.message.answer('Для возврата к фильтрам нажмите кнопку ниже', reply_markup=keyboard)
        else:
            await callback_query.message.answer('😔 По заданному периоду тренировок не найдено', reply_markup=keyboard)


@router.message(StateFilter(WorkoutFilters.waiting_for_input))
async def receive_filter_input(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    filter_type = user_data.get("filter_type")

    if filter_type == "date":
        # Обработка введенной даты
        date_input = message.text.strip().lower()
        try:
            workout_date = datetime.strptime(date_input, "%d.%m.%Y")
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (08.12.2024) ⚠️")
            return
        await state.update_data(target=date_input)

    elif filter_type == "exercise-name":
        # Обработка введенного названия упражнения
        input_name = message.text.strip()
        if len(message.text.strip()) < 2:
            await message.answer("⚠️ Название должно содержать минимум 2 символа. Пожалуйста, попробуйте снова ⚠️")
            return
        await state.update_data(target=input_name)

    back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="show_exercises")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[back_button]])
    data = await state.get_data()
    file = await get_workouts_by_filter(message.from_user.id, data['target'], filter_type, message)

    if file:
        await message.answer_document(FSInputFile(file))
        await message.answer('Для возврата к фильтрам нажмите кнопку ниже', reply_markup=keyboard)
    else:
        await message.answer('😔 По заданному периоду тренировок не найдено', reply_markup=keyboard)
    await state.clear()


async def get_workouts_by_filter(user_id, filter, type, obj):
    logger.info(type)
    params = {'user_id': user_id}
    if type == 'period' and filter != 'all':
        params['period'] = filter
    elif type == 'date':
        params['date'] = filter
    elif type == 'exercise-name':
        params['exercise_name'] = filter

    headers = {'Accept': 'application/pdf'}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://web:8000/workout/", params=params, headers=headers)
        if response.status_code == 200 and response.headers['Content-Type'] == 'application/pdf':
            # Получаем содержимое ответа как PDF файл
            pdf_content = response.content

            # Путь к временному файлу для сохранения PDF
            temp_pdf_path = f"temp_{obj.from_user.id}.pdf"

            # запись в файл
            with open(temp_pdf_path, 'wb') as pdf_file:
                pdf_file.write(pdf_content)

            return temp_pdf_path
        return False



