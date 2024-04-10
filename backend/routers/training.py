from collections import defaultdict
from enum import Enum
from weasyprint import HTML
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from datetime import datetime, timedelta

from sqlalchemy import func
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import WorkoutRecord, BodyMeasurements
from typing import Annotated, Optional
from pydantic import BaseModel, Field
from starlette import status
from calendar import monthrange
from jinja2 import Environment, FileSystemLoader
import os


templates = Jinja2Templates(directory='backend/templates')
templateLoader = FileSystemLoader(searchpath='backend/templates')

# Создаём объект Environment для загрузки шаблонов
env = Environment(loader=templateLoader)

router = APIRouter(
    prefix="/workout",
    tags=["workout"],
    responses={404: {"description": "Not found"}}
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


class WorkoutRecordRequest(BaseModel):
    exercise_name: str = Field(min_length=2)
    sets: int = Field(gt=0)
    repetitions: int = Field(gt=0)
    weight: int = Field(ge=0)
    workout_date: datetime


def get_period_start_end(period: str):
    today = datetime.today().date()

    if period == 'current-week':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period == 'last-week':
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
    elif period == 'current-month':
        start = today.replace(day=1)
        end = today.replace(day=monthrange(today.year, today.month)[1])
    elif period == 'last-month':
        first_day_last_month = today.replace(day=1) - timedelta(days=1)
        start = first_day_last_month.replace(day=1)
        end = first_day_last_month.replace(day=monthrange(first_day_last_month.year, first_day_last_month.month)[1])
    else:
        start = end = None

    return start, end


allowed_periods = ["current-week", "last-week", "current-month", "last-month", "last-workout"]


async def prepare_pdf(workouts):
    workouts_by_date = defaultdict(list)
    for workout in workouts:
        date = workout.workout_date.date()
        workouts_by_date[date].append(workout)

    template = env.get_template('workouts.html')
    html_content = template.render(workouts_by_date=workouts_by_date)
    pdf = HTML(string=html_content).write_pdf()
    return pdf


@router.get('/', status_code=status.HTTP_200_OK)
async def get_workouts(
        request: Request,
        user_id: int,
        date: Optional[str] = Query(None, description="Дата в формате ДД.ММ.ГГГГ"),
        period: Optional[str] = Query(None, description="Выберите период или оставьте пустым:", enum=allowed_periods),
        exercise_name: Optional[str] = None,
        db: Session = Depends(get_db)
):
    query = db.query(WorkoutRecord).filter(WorkoutRecord.user_id == user_id)

    # фильтр по дате
    if date:
        specific_date = datetime.strptime(date, "%d.%m.%Y").date()
        query = query.filter(WorkoutRecord.workout_date == specific_date)
    # по периоду(неделя, месяц)
    elif period:
        if period == 'last-workout':
            # Получаем дату последней тренировки
            last_workout_date = db.query(func.max(WorkoutRecord.workout_date)).filter(WorkoutRecord.user_id == user_id).scalar()
            if last_workout_date:
                # Получаем все записи за последнюю тренировку
                workouts = query.filter(WorkoutRecord.workout_date == last_workout_date).all()
                pdf = await prepare_pdf(workouts)

                headers = {
                    'Content-Disposition': 'attachment; filename="workout_report.pdf"',
                }
                return Response(content=pdf, media_type='application/pdf', headers=headers)
            else:
                return {"message": "Последняя тренировка не найдена."}
        else:
            start, end = get_period_start_end(period)
            if start and end:
                query = query.filter(WorkoutRecord.workout_date >= start, WorkoutRecord.workout_date <= end)
    # по названию упражнения
    if exercise_name:
        query = query.filter(WorkoutRecord.exercise_name.ilike(f"%{exercise_name}%"))

    if period != 'last-workout':  # Убедимся, что мы не обрабатываем это условие еще раз
        workouts = query.order_by(WorkoutRecord.workout_date.desc()).all()

        if not workouts:
            return {"message": "Ничего не найдено по заданным критериям."}

        pdf = await prepare_pdf(workouts)

        headers = {
            'Content-Disposition': 'attachment; filename="workout_report.pdf"',
        }
        return Response(content=pdf, media_type='application/pdf', headers=headers)


@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_workout(user_id: int, workout_request: WorkoutRecordRequest, db: db_dependency):
    todo_model = WorkoutRecord(**workout_request.model_dump(), user_id=user_id)

    db.add(todo_model)
    db.commit()


class BodyMeasurementsRequest(BaseModel):
    hips: Optional[float] = Field(None, description="Обхват бедер в сантиметрах.")
    chest: Optional[float] = Field(None, description="Обхват груди в сантиметрах.")
    biceps: Optional[float] = Field(None, description="Обхват бицепса в расслабленном состоянии в сантиметрах.")
    biceps_tense: Optional[float] = Field(None, description="Обхват бицепса в напряженном состоянии в сантиметрах.")
    waist: Optional[float] = Field(None, description="Обхват талии в сантиметрах.")
    thighs: Optional[float] = Field(None, description="Обхват бедра в сантиметрах.")
    calf: Optional[float] = Field(None, description="Обхват икры в сантиметрах.")
    weight: Optional[float] = Field(None, description="Вес тела в килограммах.")


@router.get('/measure', status_code=status.HTTP_200_OK)
async def get_measurements(user_id: int, db: db_dependency):
    return db.query(BodyMeasurements).filter(BodyMeasurements.user_id == user_id).first()


@router.post('/measure', status_code=status.HTTP_201_CREATED)
async def create_measurements(user_id: int, measurements_request: BodyMeasurementsRequest, db: db_dependency):
    todo_model = BodyMeasurements(**measurements_request.model_dump(), user_id=user_id)

    db.add(todo_model)
    db.commit()


@router.put('/measure/{id}', status_code=status.HTTP_201_CREATED)
async def update_measurements(id: int, measurements_request: BodyMeasurementsRequest, db: db_dependency):
    db_measurement = db.query(BodyMeasurements).filter(BodyMeasurements.id == id).first()
    if not db_measurement:
        raise HTTPException(status_code=404, detail="Измерение не найдено")

    update_data = measurements_request.model_dump()

    for field_name, value in update_data.items():
        if value is not None and value > 0:
            setattr(db_measurement, field_name, value)

    db.commit()
