from sqlalchemy import Column, Integer, String, Boolean, DateTime
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
