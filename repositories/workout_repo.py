from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from fastapi import Depends

from models.workout import Workout
from schemas.workout import WorkoutIn, WorkoutOut
from db.session import get_db


class WorkoutRepository:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def insert(self, workout_in: WorkoutIn) -> WorkoutOut:
        db_workout = Workout(**workout_in.dict())
        self.db.add(db_workout)
        self.db.commit()
        self.db.refresh(db_workout)
        return WorkoutOut.from_orm(db_workout)

    def get_by_exercise_and_date(self, exercise: str, workout_date: date) -> List[WorkoutOut]:
        workouts = self.db.query(Workout).filter(
            Workout.exercise == exercise.lower(),
            Workout.workout_date == workout_date
        ).all()
        return [WorkoutOut.from_orm(w) for w in workouts]

    def get_by_exercise(self, exercise: str) -> List[WorkoutOut]:
        workouts = self.db.query(Workout).filter(
            Workout.exercise == exercise.lower()
        ).order_by(Workout.workout_date.desc()).all()
        return [WorkoutOut.from_orm(w) for w in workouts]

    def get_recent(self, limit: int = 10) -> List[WorkoutOut]:
        workouts = self.db.query(Workout).order_by(
            Workout.created_at.desc()
        ).limit(limit).all()
        return [WorkoutOut.from_orm(w) for w in workouts]