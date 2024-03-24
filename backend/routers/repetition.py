from datetime import datetime, timedelta
from sqlalchemy import func
from fastapi import APIRouter, Depends
from typing import Annotated
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import UserWord
from starlette import status
from pydantic import BaseModel

router = APIRouter(
    prefix="/word",
    tags=["words"],
    responses={404: {"description": "Not found"}}
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
REPEAT_SCHEDULE = [1, 7, 14, 30, 60, 120, 180]


class WordRequest(BaseModel):
    user_id: int
    word: str
    translation: str


@router.get('/', status_code=status.HTTP_200_OK)
async def get_word(db: db_dependency):
    current_utc = datetime.utcnow().date()  # Получаем текущую дату без времени
    word_model = db.query(UserWord).filter(func.date(UserWord.reminder_date) <= current_utc).first()

    if word_model:
        # Проверяем, является ли текущий интервал последним в расписании
        if word_model.interval == REPEAT_SCHEDULE[-1]:
            # Поскольку это последний интервал, возвращаем слово пользователю и удаляем его из базы данных
            response = {"success": True, "word": word_model.word, "translation": word_model.translation}

            # Удаление слова из базы данных
            db.delete(word_model)
            db.commit()

            response["message"] = "Это было последнее повторение, слово будет удалено!"
            return response
        else:
            # Находим следующий интервал для повторения
            element_index = REPEAT_SCHEDULE.index(word_model.interval)
            next_index = element_index + 1 if element_index + 1 < len(REPEAT_SCHEDULE) else element_index
            new_reminder_date = current_utc + timedelta(days=REPEAT_SCHEDULE[element_index])
            new_interval = REPEAT_SCHEDULE[next_index]

            # Обновляем дату напоминания и интервал в модели
            word_model.reminder_date = new_reminder_date
            word_model.interval = new_interval
            db.commit()

            return {"success": True, "word": word_model.word, "translation": word_model.translation, 'date': word_model.reminder_date}
    else:
        return {"success": False, "message": "Нет слов для повторения"}


@router.post('/', status_code=status.HTTP_201_CREATED)
async def add_word(db: db_dependency, word_request: WordRequest):
    word_model = UserWord(
        user_id=word_request.user_id,
        word=word_request.word,
        translation=word_request.translation,
        interval=REPEAT_SCHEDULE[1],
        reminder_date=datetime.utcnow().date() + timedelta(days=REPEAT_SCHEDULE[0])
    )
    db.add(word_model)
    db.commit()
    db.refresh(word_model)
