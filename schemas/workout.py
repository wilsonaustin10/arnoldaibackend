from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import Optional


class WorkoutBase(BaseModel):
    workout_date: date
    exercise: str
    reps: int = Field(gt=0, description="Number of repetitions")
    weight_lbs: float = Field(ge=0, description="Weight in pounds")

    @validator('exercise')
    def exercise_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Exercise name cannot be empty')
        return v.strip().lower()


class WorkoutIn(WorkoutBase):
    pass


class WorkoutOut(WorkoutBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True