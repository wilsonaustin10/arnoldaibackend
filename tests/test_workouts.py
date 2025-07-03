import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date

from main import app
from db.database import Base
from db.session import get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def test_create_workout():
    response = client.post(
        "/workouts/",
        json={
            "workout_date": str(date.today()),
            "exercise": "bench_press",
            "reps": 10,
            "weight_lbs": 135.5
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["exercise"] == "bench_press"
    assert data["reps"] == 10
    assert data["weight_lbs"] == 135.5
    assert "id" in data
    assert "created_at" in data


def test_create_workout_invalid_reps():
    response = client.post(
        "/workouts/",
        json={
            "workout_date": str(date.today()),
            "exercise": "squat",
            "reps": 0,
            "weight_lbs": 225
        }
    )
    assert response.status_code == 422


def test_get_workouts_by_exercise():
    client.post(
        "/workouts/",
        json={
            "workout_date": str(date.today()),
            "exercise": "deadlift",
            "reps": 5,
            "weight_lbs": 315
        }
    )
    
    response = client.get("/workouts/?exercise=deadlift")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["exercise"] == "deadlift"


def test_get_recent_workouts():
    response = client.get("/workouts/recent?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}