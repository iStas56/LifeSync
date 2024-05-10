from datetime import datetime, timedelta

import pytest
from sqlalchemy import func
from starlette import status
from backend.main import app

from backend.models import UserWord
from fastapi.testclient import TestClient
from backend.routers.repetition import get_db
from test.db_conection import TestingSessionLocal, db_session, engine


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def test_word(db_session):
    words = [
        UserWord(
            user_id=1,
            word='test',
            translation='тест',
            interval=2,
            reminder_date=datetime.utcnow().date(),
        ),
        UserWord(
            user_id=1,
            word='check',
            translation='проверка',
            interval=2,
            reminder_date=datetime.utcnow().date(),
        )
    ]

    db_session.add_all(words)
    db_session.commit()

    yield words  # Предоставляем данные для теста

    db_session.query(UserWord).delete()  # Очистка тестовых данных после использования
    db_session.commit()


def test_add_word(test_word, db_session):
    request_data = {
        "user_id": 1,
        "word": "execution",
        "translation": "исполнение",
        'interval': 2,
    }

    response = client.post("/word/", json=request_data)
    assert response.status_code == status.HTTP_201_CREATED

    model = db_session.query(UserWord).filter(UserWord.id == 3).first()
    assert model.user_id == request_data.get('user_id')
    assert model.word == request_data.get('word')
    assert model.translation == request_data.get('translation')
    assert model.interval == request_data.get('interval')


def test_get_word_and_change_interval(test_word, db_session):
    response = client.get('/word/')
    assert response.status_code == 200

    # Получаем текущую дату без времени и добавляем 2 дня
    today = datetime.utcnow().date()
    next_date = today + timedelta(days=2)

    # Ищем слово с обновленной датой напоминания
    word_model = db_session.query(UserWord).filter(func.date(UserWord.reminder_date) == next_date).first()

    assert word_model is not None
    assert word_model.reminder_date.date() == next_date
