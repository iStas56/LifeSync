from aiogram import types, Router, F
import httpx
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from telegram_bot.handlers.menu import process_start_command
from aiogram.types import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message)
from telegram_bot.logger import logger, log_user_action

router = Router()


@router.callback_query(lambda c: c.data == 'start')
async def return_to_start(callback_query: types.CallbackQuery):
    await process_start_command(callback_query.message)


@router.callback_query(lambda c: c.data and c.data.startswith('todos'))
async def show_todos(source):
    if isinstance(source, types.CallbackQuery):
        user_id = source.from_user.id
        message = source.message
        await source.answer()  # Для CallbackQuery
    elif isinstance(source, types.Message):
        user_id = source.from_user.id
        message = source

    async with httpx.AsyncClient() as client:
        # Пример запроса, замените на ваш фактический запрос
        response = await client.get(f"http://0.0.0.0:8000/todos/", params={"user_id": user_id})
        if response.status_code == 200:
            todos = response.json()
        else:
            todos = []

    task_buttons = [
        [types.InlineKeyboardButton(text=f"{todo['title']} {'✅' if todo['complete'] else '➖'}", callback_data=f"todo_detail_{todo['id']}")]
        for todo in todos
    ]

    back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="start")
    new_task_button = types.InlineKeyboardButton(text="➕ Новая задача", callback_data="new_todo")

    # Добавляем кнопки действий в отдельный ряд
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=task_buttons + [[back_button, new_task_button]])

    if isinstance(source, types.CallbackQuery):
        await message.edit_text("Текущий список задач:", reply_markup=keyboard)
    elif isinstance(source, types.Message):
        await message.answer("Текущий список задач:", reply_markup=keyboard)


@router.callback_query(lambda c: c.data and c.data.startswith('todo_detail_'))
async def show_todo_details(callback_query: types.CallbackQuery):
    todo_id = callback_query.data.split('_')[2]

    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://0.0.0.0:8000/todos/todo/{todo_id}")
        if response.status_code == 200:
            todo = response.json()
        else:
            await callback_query.answer("Задача не найдена", show_alert=True)

    back_button = types.InlineKeyboardButton(text="🔙 Назад", callback_data="todos")
    remove_button = types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"todo_remove_{todo['id']}")
    complete_button = types.InlineKeyboardButton(text="Изменить статус", callback_data=f"todo_update_{todo['id']}")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[remove_button, complete_button], [back_button]])

    message_text = (
        f"<b>Задача</b>: {todo['title']}\n\n"
        f"<b>Описание</b>: {todo['description']}"
    )

    await callback_query.message.answer(message_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(lambda c: c.data and c.data.startswith('todo_remove_'))
async def remove_todo(callback_query: types.CallbackQuery):
    todo_id = callback_query.data.split('_')[2]

    async with httpx.AsyncClient() as client:
        response = await client.delete(f"http://0.0.0.0:8000/todos/todo/{todo_id}")
        if response.status_code == 204:
            await callback_query.message.edit_text("Задача успешно удалена ✅")
            await show_todos(callback_query)


@router.callback_query(lambda c: c.data and c.data.startswith('todo_update_'))
async def update_todo(callback_query: types.CallbackQuery):
    todo_id = callback_query.data.split('_')[2]

    async with httpx.AsyncClient() as client:
        response = await client.put(f"http://0.0.0.0:8000/todos/todo/{todo_id}")
        if response.status_code == 204:
            await callback_query.answer()
            await show_todos(callback_query)


class TodoCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_priority = State()


def get_cancel_keyboard():
    cancel_button = InlineKeyboardButton(text="❌ остановить добавление задачи", callback_data="cancel")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[cancel_button]])
    return keyboard


@router.callback_query(F.data == "cancel")
async def process_cancel(callback_query: CallbackQuery, state: FSMContext):
    await state.clear()  # Сброс состояния
    await callback_query.message.edit_text("Добавление задачи отменено.")
    await callback_query.answer()


# Логика добавления новой задачи
@router.callback_query(lambda c: c.data and c.data.startswith('new_todo'))
async def new_todo_start(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Введите название задачи:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TodoCreation.waiting_for_title)


@router.message(StateFilter(TodoCreation.waiting_for_title))
async def process_title_sent(message: Message, state: FSMContext):
    await log_user_action(message, state)

    title = message.text.strip()
    if len(message.text.strip()) < 2:
        await message.answer("Название должно содержать минимум 2 символа. Пожалуйста, попробуйте снова:")
        return

    await state.update_data(title=title)
    await message.answer(
        "Введите описание задачи:",
        reply_markup=get_cancel_keyboard()
    )

    await state.set_state(TodoCreation.waiting_for_description)


@router.message(StateFilter(TodoCreation.waiting_for_description))
async def process_description_sent(message: Message, state: FSMContext):
    await log_user_action(message, state)

    description = message.text.strip()
    if len(message.text.strip()) < 2:
        await message.answer("Описание должно содержать минимум 2 символа. Пожалуйста, попробуйте снова:")
        return

    await state.update_data(description=description)
    await message.answer(
        "Введите приоритет от 1 до 5:",
        reply_markup=get_cancel_keyboard()
    )

    await state.set_state(TodoCreation.waiting_for_priority)


@router.message(StateFilter(TodoCreation.waiting_for_priority))
async def process_priority_sent(message: types.Message, state: FSMContext):
    await log_user_action(message, state)

    priority_text = message.text.strip()
    if not priority_text.isdigit() or not 1 <= int(priority_text) <= 5:
        await message.answer("Приоритет должен быть числом от 1 до 5. Попробуйте ещё раз:")
        return

    priority = priority_text
    user_id = message.from_user.id

    # Собираем все данные для новой задачи
    task_data = {
        'priority': priority,
        'owner_id': user_id,
        'complete': False
    }

    # Добавляем остальные данные из состояния
    task_data.update(await state.get_data())

    # Попытка добавить новую задачу через API
    if await add_new_task(task_data):
        await message.answer(text='Задача добавлена!')
        await show_todos(message)
    else:
        await message.answer(text='Произошла ошибка при добавлении задачи.')

    await state.clear()


async def add_new_task(task_data):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://0.0.0.0:8000/todos/todo", json=task_data)
        return response.status_code == 201


