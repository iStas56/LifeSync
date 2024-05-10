import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func
from starlette import status
from backend.main import app

from backend.models import WorkoutRecord, BodyMeasurements
from fastapi.testclient import TestClient
from backend.routers.training import get_db
from test.db_conection import TestingSessionLocal, db_session


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def test_body_measurements(db_session):
    measurement = BodyMeasurements(
        user_id=1,
        hips=58,
        chest=103,
        biceps=32,
        biceps_tense=38,
        waist=94,
        thighs=100,
        calf=37.5,
        weight=80,
    )

    db_session.add(measurement)
    db_session.commit()

    yield measurement

    db_session.query(BodyMeasurements).delete()
    db_session.commit()


def test_get_body_measurements(test_body_measurements):
    response = client.get('/workout/measure?user_id=1')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "chest": 103.0,
        "id": 1,
        "hips": 58.0,
        "biceps_tense": 38.0,
        "calf": 37.5,
        "user_id": 1,
        "biceps": 32.0,
        "waist": 94.0,
        "thighs": 100.0,
        "weight": 80.0
    }


def test_get_body_measurements_not_found(test_body_measurements):
    response = client.get('/workout/measure?user_id=7777')
    assert response.json


def test_create_measurement(test_body_measurements, db_session):
    request_data = {
        "hips": 110,
        "chest": 112,
        "biceps": 3,
        "biceps_tense": 4,
        "waist": 5,
        "thighs": 6,
        "calf": 7,
        "weight": 8
    }

    response = client.post('/workout/measure?user_id=789', json=request_data)
    assert response.status_code == status.HTTP_201_CREATED

    model = db_session.query(BodyMeasurements).filter(BodyMeasurements.user_id == 789).first()
    assert model.hips == request_data["hips"]
    assert model.chest == request_data["chest"]
    assert model.biceps == request_data["biceps"]
    assert model.biceps_tense == request_data["biceps_tense"]
    assert model.waist == request_data["waist"]
    assert model.thighs == request_data["thighs"]
    assert model.calf == request_data["calf"]
    assert model.weight == request_data["weight"]


def test_body_measurements_update(test_body_measurements, db_session):
    request_data = {
        "weight": 85
    }

    response = client.put('/workout/measure/1', json=request_data)
    assert response.status_code == status.HTTP_201_CREATED

    model = db_session.query(BodyMeasurements).filter(BodyMeasurements.id == 1).first()
    assert model.weight == request_data["weight"]


@pytest.fixture
def test_workouts(db_session):
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_last_week = start_of_week - timedelta(weeks=1)
    start_of_month = today.replace(day=1)
    start_of_last_month = (start_of_month - timedelta(days=1)).replace(day=1)

    workouts = [
        # фиксированное число для фильтра по дате
        WorkoutRecord(
            user_id=1,
            exercise_name="Жим гантелей",
            sets=4,
            repetitions=12,
            weight=75,
            workout_date=datetime(2024, 1, 1, 0, 0)
        ),
        # Текущая неделя
        WorkoutRecord(
            user_id=1,
            exercise_name="Жим штанги лежа",
            sets=4,
            repetitions=10,
            weight=50,
            workout_date=start_of_week + timedelta(days=1)  # Один день назад с начала недели
        ),
        # Прошлая неделя/Текущий месяц
        WorkoutRecord(
            user_id=1,
            exercise_name="Приседания",
            sets=3,
            repetitions=12,
            weight=80,
            workout_date=start_of_last_week + timedelta(days=3)  # Три дня назад с начала прошлой недели
        ),
        # Прошлый месяц
        WorkoutRecord(
            user_id=1,
            exercise_name="Приседания со штангой",
            sets=3,
            repetitions=10,
            weight=90,
            workout_date=start_of_last_month + timedelta(days=15)  # Пятнадцать дней назад с начала прошлого месяца
        )
    ]

    db_session.add_all(workouts)
    db_session.commit()

    yield workouts  # Предоставляем данные для теста

    db_session.query(WorkoutRecord).delete()  # Очистка тестовых данных после использования
    db_session.commit()


def test_workouts_by_filter(test_workouts, db_session):
    # тест фильтра по дате
    response = client.get('/workout/?user_id=1&date=01.01.2024')
    assert response.headers['content-type'] == 'application/pdf'
    assert int(response.headers['content-length']) > 0

    # тест фильтра по названию
    response = client.get('/workout/?user_id=1&exercise_name=Жим гантелей')
    assert response.headers['content-type'] == 'application/pdf'
    assert int(response.headers['content-length']) > 0

    # тест по текущей неделе
    response = client.get('/workout/?user_id=1&period=current-week')
    assert response.headers['content-type'] == 'application/pdf'
    assert int(response.headers['content-length']) > 0

    # тест по прошлой неделе
    response = client.get('/workout/?user_id=1&period=last-workout')
    assert response.headers['content-type'] == 'application/pdf'
    assert int(response.headers['content-length']) > 0

    # тест все записи
    response = client.get('/workout/?user_id=1')
    assert response.headers['content-type'] == 'application/pdf'
    assert int(response.headers['content-length']) > 0


def test_workouts_by_filter_not_found(test_workouts, db_session):
    response = client.get('/workout/?user_id=1&date=01.01.2023')
    assert response.json()['message'] == 'Ничего не найдено по заданным критериям.'


def test_create_workout(test_workouts, db_session):
    request_data = {
        "exercise_name": "Присед",
        "sets": 5,
        "repetitions": 10,
        "weight": 100,
        "workout_date": "2024-05-10T12:55:33.468Z"
    }

    response = client.post('/workout/?user_id=1', json=request_data)
    assert response.status_code == status.HTTP_201_CREATED
