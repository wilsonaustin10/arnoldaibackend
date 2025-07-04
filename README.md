# Arnold.ai Workout Tracker MVP

A FastAPI-based backend for tracking workout sets with voice integration support.

## Architecture

```
┌──────────────────────────┐
│ 1. Frontend Voice Agent  │
│  (STT / TTS handled here)│
└──────────────┬───────────┘
               ▼  HTTPS/JSON
┌──────────────────────────┐
│ 2. API Layer (FastAPI)   │
└──────────────┬───────────┘
               ▼
┌──────────────────────────┐
│ 3. Service Layer         │
└──────────────┬───────────┘
               ▼
┌──────────────────────────┐
│ 4. Repository Layer      │
└──────────────┬───────────┘
               ▼
┌──────────────────────────┐
│ 5. Relational DB         │
└──────────────────────────┘
```

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run database migrations:
```bash
alembic init alembic/versions
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

3. Start the server:
```bash
uvicorn main:app --reload
```

4. Access API documentation:
- http://localhost:8000/docs

## API Endpoints

- `POST /workouts/` - Log a new workout set
- `GET /workouts/?exercise={name}&date={date}` - Query workouts by exercise
- `GET /workouts/recent?limit={n}` - Get recent workouts

## Example Request

```json
POST /workouts/
{
  "workout_date": "2025-07-02",
  "exercise": "bench_press",
  "reps": 10,
  "weight_lbs": 135.5
}
```

## Database Schema

- `id` (INTEGER) - Primary key
- `workout_date` (DATE) - Date of workout
- `exercise` (TEXT) - Exercise name
- `reps` (INTEGER) - Number of repetitions
- `weight_lbs` (REAL) - Weight in pounds
- `created_at` (TIMESTAMP) - Record creation time

## Development

- SQLite for local development
- Environment variable `DATABASE_URL` for production database
- Alembic for database migrations
- FastAPI auto-generates OpenAPI documentation

TO INSTALL
- portaudio