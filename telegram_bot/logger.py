import logging
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

# Создаем логгер
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Установка уровня логирования

# Удаляем стандартные обработчики, если они были добавлены
if logger.hasHandlers():
    logger.handlers.clear()

# Создаем обработчик, который будет писать логи в stdout (консоль)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Создаем форматтер с вашими специальными префиксом и суффиксом
formatter = logging.Formatter('*** %(asctime)s - %(levelname)s - %(name)s *** - %(funcName)s - %(message)s')
console_handler.setFormatter(formatter)

# Добавляем обработчик к логгеру
logger.addHandler(console_handler)


async def log_user_action(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    current_state = await state.get_state() or 'None'
    logger.info(f"Пользователь {user_id}, Сообщение: '{text}', Состояние: {current_state}")
