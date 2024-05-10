import pytest

from backend.database import Base
from sqlalchemy import create_engine
import os
from sqlalchemy.orm import sessionmaker


TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL')
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    session = TestingSessionLocal()
    Base.metadata.create_all(bind=engine)  # Создаем все таблицы

    yield session  # Предоставляем сессию для теста

    session.close()  # Закрываем сессию после теста
    Base.metadata.drop_all(bind=engine)  # Удаляем все таблицы для очистки