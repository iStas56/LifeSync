import os
from datetime import datetime

from backend.main import app
from backend.routers.rates import get_and_feel_rates
import pytest
from fastapi.testclient import TestClient
from fastapi import status
import requests_mock


from backend.models import Rates
from backend.routers.rates import get_db
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
def test_rate(db_session):
    rates = [
        Rates(
            code="RUB",
            title="Russian Ruble",
            rate=100,
            created_at=datetime(2024, 1, 1, 12, 0)
        ),
        Rates(
            code="USD",
            title="United States Dollar",
            rate=1.1,
            created_at=datetime(2024, 5, 5, 12, 0)
        ),
        Rates(
            code="EUR",
            title="Euro",
            rate=1,
            created_at=datetime(2024, 1, 2, 12, 0)
        ),
    ]

    db_session.add_all(rates)
    db_session.commit()

    yield rates  # Предоставляем данные для теста

    db_session.query(Rates).delete()  # Очистка тестовых данных после использования
    db_session.commit()


@pytest.mark.asyncio
async def test_get_and_feel_rates(db_session):
    with requests_mock.Mocker() as m:
        m.get(f"http://api.exchangeratesapi.io/v1/symbols?access_key={os.getenv('RATES_TOKEN')}", json={
            "success": True,
            "symbols": {
                "USD": "United States Dollar",
            }
        })
        m.get(f"http://api.exchangeratesapi.io/v1/latest?access_key={os.getenv('RATES_TOKEN')}", json={
            "success": True,
            "rates": {
                "USD": 1.1,
            }
        })

        await get_and_feel_rates(db=db_session)
        usd_rate = db_session.query(Rates).filter_by(code="USD").first()
        assert usd_rate is not None
        assert usd_rate.rate == 1.1


def test_get_last_update(test_rate):
    response = client.get("/rates/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "last_update" in data

    expected_date = "2024-05-05 12:00:00"
    assert data["last_update"] == expected_date


def test_get_rate(test_rate):
    request_data = {
        "source": "RUB",
        "target": "USD",
        "sum": 1000
    }

    response = client.post("/rates/get-rate", json=request_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "result" in data

    expected_rate = 11
    assert data["result"] == expected_rate

    wrong_currency = {
        "source": "RUB",
        "target": "XXX",
        "sum": 1000
    }

    response = client.post("/rates/get-rate", json=wrong_currency)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
    assert data["detail"] == 'Неизвестный код валюты'
