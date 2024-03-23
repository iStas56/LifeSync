from fastapi import FastAPI

from backend.database import engine, Base
from backend.routers import todos

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.get('/healthy')
async def health_check():
    return {'status': 'Healthy'}


app.include_router(todos.router)