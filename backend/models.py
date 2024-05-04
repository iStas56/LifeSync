from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from backend.database import Base


class Todos(Base):
    __tablename__ = 'todos'

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, index=True)
    title = Column(String)
    description = Column(String)
    priority = Column(Integer)
    complete = Column(Boolean, default=False)


class UserWord(Base):
    __tablename__ = 'user_words'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    word = Column(String, nullable=False)
    translation = Column(String, nullable=False)
    interval = Column(Integer, nullable=True)
    reminder_date = Column(DateTime)


class Rates(Base):
    __tablename__ = 'rates'
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    rate = Column(Float, nullable=False)
    created_at = Column(DateTime)


class Currency(Base):
    __tablename__ = 'currency'
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)


class WorkoutRecord(Base):
    __tablename__ = 'workout_record'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    exercise_name = Column(String, nullable=False)
    sets = Column(Integer, nullable=False)
    repetitions = Column(Integer, nullable=False)
    weight = Column(Float, nullable=True)
    workout_date = Column(DateTime)


class BodyMeasurements(Base):
    __tablename__ = 'body_measurements'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    hips = Column(Float, nullable=True)  # Обхват бедра в сантиметрах
    chest = Column(Float, nullable=True)  # Обхват груди в сантиметрах
    biceps = Column(Float, nullable=True)
    waist = Column(Float, nullable=True)
    biceps_tense = Column(Float, nullable=True)
    thighs = Column(Float, nullable=True)  # Обхват бедер в сантиметрах
    calf = Column(Float, nullable=True)  # Обхват икры в сантиметрах
    weight = Column(Float, nullable=True)
