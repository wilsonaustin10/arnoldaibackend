from typing import List, Optional
from datetime import date
from fastapi import Depends, HTTPException

from repositories.workout_repo import WorkoutRepository
from schemas.workout import WorkoutIn, WorkoutOut


class WorkoutService:
    def __init__(self, repo: WorkoutRepository = Depends()):
        self.repo = repo

    def create_workout(self, workout_in: WorkoutIn) -> WorkoutOut:
        if workout_in.weight_lbs < 0:
            raise HTTPException(status_code=400, detail="Weight cannot be negative")
        
        if workout_in.reps <= 0:
            raise HTTPException(status_code=400, detail="Reps must be positive")
        
        return self.repo.insert(workout_in)

    def query_workouts(self, exercise: str, workout_date: Optional[date] = None) -> List[WorkoutOut]:
        if not exercise or not exercise.strip():
            raise HTTPException(status_code=400, detail="Exercise name is required")
        
        if workout_date:
            return self.repo.get_by_exercise_and_date(exercise, workout_date)
        else:
            return self.repo.get_by_exercise(exercise)

    def get_recent_workouts(self, limit: int = 10) -> List[WorkoutOut]:
        if limit <= 0 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        return self.repo.get_recent(limit)