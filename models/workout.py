from sqlalchemy import Column, Integer, Float, String, Date, DateTime, Index
from sqlalchemy.sql import func
from db.database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    workout_date = Column(Date, nullable=False)
    exercise = Column(String, nullable=False, index=True)
    reps = Column(Integer, nullable=False)
    weight_lbs = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('idx_exercise_date', 'exercise', 'workout_date'),
    )