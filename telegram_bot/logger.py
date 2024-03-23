import logging
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


async def log_user_action(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    current_state = await state.get_state() or 'None'
    logger.info(f"Пользователь {user_id}, Сообщение: '{text}', Состояние: {current_state}")
