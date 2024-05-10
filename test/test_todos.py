import pytest
from starlette import status

from backend.models import Todos
from fastapi.testclient import TestClient
from backend.main import app
from backend.routers.todos import get_db
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
def test_todo(db_session):
    todos = [
        Todos(
            title="Learn to code!",
            description="Need to learn everyday!",
            priority=5,
            complete=False,
            owner_id=1,
        ),
        Todos(
            title="Check",
            description="Check this out!",
            priority=3,
            complete=False,
            owner_id=1,
        ),
        Todos(
            title="Another user",
            description="Descr todos",
            priority=5,
            complete=False,
            owner_id=2,
        )
    ]

    db_session.add_all(todos)
    db_session.commit()

    yield todos  # Предоставляем данные для теста

    db_session.query(Todos).delete()  # Очистка тестовых данных после использования
    db_session.commit()


def test_read_all_by_user(test_todo):
    response = client.get("/todos/?user_id=1")
    assert response.status_code == status.HTTP_200_OK

    assert response.json() == [
        {
            "priority": 5,
            "title": "Learn to code!",
            "owner_id": 1,
            "id": 1,
            "description": "Need to learn everyday!",
            "complete": False
        },
        {
            "priority": 3,
            "title": "Check",
            "owner_id": 1,
            "id": 2,
            "description": "Check this out!",
            "complete": False
        }
    ]


def test_read_one_not_found(test_todo):
    response = client.get("/todos/?user_id=7")
    assert response.json() == []


def test_read_one_todo(test_todo):
    response = client.get("/todos/todo/1")
    assert response.json() == {
        "priority": 5,
        "title": "Learn to code!",
        "owner_id": 1,
        "id": 1,
        "description": "Need to learn everyday!",
        "complete": False
    }


def test_read_one_todo_not_found(test_todo):
    response = client.get("/todos/todo/90")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Todo not found.'}


def test_create_todo(test_todo, db_session):
    request_data = {
        'title': 'New Todo!',
        'description': 'New todo description',
        'priority': 5,
        'complete': False,
        'owner_id': 1,
    }

    response = client.post('/todos/todo', json=request_data)
    assert response.status_code == status.HTTP_201_CREATED

    model = db_session.query(Todos).filter(Todos.id == 4).first()
    assert model.title == request_data['title']
    assert model.description == request_data['description']
    assert model.priority == request_data['priority']
    assert model.complete == request_data['complete']
    assert model.owner_id == request_data['owner_id']

    # with open('response_data.json', 'w') as file:
    #     json.dump(response.json(), file, indent=4)


def test_update_todo(test_todo, db_session):
    response = client.put('/todos/todo/3')
    assert response.status_code == status.HTTP_204_NO_CONTENT

    model = db_session.query(Todos).filter(Todos.id == 3).first()
    assert model.complete


def test_update_todo_not_found(test_todo, db_session):
    response = client.put('/todos/todo/3')
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_todo(test_todo, db_session):
    response = client.delete('/todos/todo/1')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    model = db_session.query(Todos).filter(Todos.id == 1).first()
    assert model is None


def test_delete_todo_not_found(test_todo, db_session):
    response = client.delete('/todos/todo/7')
    assert response.status_code == status.HTTP_404_NOT_FOUND
