from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, status

from services.workout_service import WorkoutService
from schemas.workout import WorkoutIn, WorkoutOut

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=WorkoutOut)
def log_workout(
    workout_in: WorkoutIn,
    service: WorkoutService = Depends()
):
    """Log a new workout set."""
    return service.create_workout(workout_in)


@router.get("/", response_model=List[WorkoutOut])
def fetch_workouts(
    exercise: str = Query(..., description="Exercise name to query"),
    date: Optional[date] = Query(None, description="Optional date filter"),
    service: WorkoutService = Depends()
):
    """Fetch workouts by exercise and optional date."""
    return service.query_workouts(exercise=exercise, workout_date=date)


@router.get("/recent", response_model=List[WorkoutOut])
def get_recent_workouts(
    limit: int = Query(10, ge=1, le=100, description="Number of recent workouts to fetch"),
    service: WorkoutService = Depends()
):
    """Get the most recent workout entries."""
    return service.get_recent_workouts(limit=limit)