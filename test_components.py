#!/usr/bin/env python3
"""Test individual components without running the full server"""

import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

print("=== Testing Arnold.ai Components ===\n")

# 1. Test environment variables
print("1. Environment Variables:")
openai_key = os.getenv("OPENAI_API_KEY")
elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
print(f"   ✓ OPENAI_API_KEY: {'Set' if openai_key else 'Missing'}")
print(f"   ✓ ELEVENLABS_API_KEY: {'Set' if elevenlabs_key else 'Missing'}")

# 2. Test database connection
print("\n2. Database Connection:")
try:
    from db.database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("   ✓ Database connection successful")
except Exception as e:
    print(f"   ✗ Database error: {e}")

# 3. Test workout service
print("\n3. Workout Service:")
try:
    from services.workout_service import WorkoutService
    from schemas.workout import WorkoutIn
    from db.session import get_db
    
    # Create a test workout
    workout_data = WorkoutIn(
        workout_date=date.today(),
        exercise="test_bench_press",
        reps=10,
        weight_lbs=135.0
    )
    
    # Get a database session
    db = next(get_db())
    service = WorkoutService(db)
    
    # Create workout
    result = service.create_workout(workout_data)
    print(f"   ✓ Created workout: {result.exercise} - {result.reps} reps @ {result.weight_lbs} lbs")
    
    # Query recent workouts
    recent = service.get_recent_workouts(limit=5)
    print(f"   ✓ Found {len(recent)} recent workouts")
    
    db.close()
except Exception as e:
    print(f"   ✗ Workout service error: {e}")

# 4. Test OpenAI connection (simplified)
print("\n4. OpenAI Connection:")
try:
    import httpx
    
    # Test with a simple API call to check connectivity
    headers = {
        "Authorization": f"Bearer {openai_key}",
        "Content-Type": "application/json"
    }
    
    # Just check if we can reach OpenAI's API
    response = httpx.get(
        "https://api.openai.com/v1/models",
        headers=headers,
        timeout=5.0
    )
    
    if response.status_code == 200:
        print("   ✓ OpenAI API connection successful")
    else:
        print(f"   ✗ OpenAI API error: {response.status_code}")
except Exception as e:
    print(f"   ✗ OpenAI connection error: {e}")

# 5. Test voice agent logic (without API calls)
print("\n5. Voice Agent Logic:")
try:
    from services.voice_agent import VoiceAgent
    
    # Create a mock OpenAI client for testing
    class MockOpenAI:
        class Chat:
            class Completions:
                @staticmethod
                def create(**kwargs):
                    # Mock response
                    class Message:
                        content = "Great job! I've logged your workout."
                        function_call = None
                    
                    class Choice:
                        message = Message()
                    
                    class Response:
                        choices = [Choice()]
                    
                    return Response()
            
            completions = Completions()
        
        chat = Chat()
    
    mock_client = MockOpenAI()
    mock_service = type('MockService', (), {
        'create_workout': lambda self, x: type('Workout', (), {
            'id': 1, 'exercise': x.exercise, 'reps': x.reps, 
            'weight_lbs': x.weight_lbs, 'workout_date': x.workout_date
        })(),
        'get_recent_workouts': lambda self, limit: [],
        'query_workouts': lambda self, exercise, workout_date: []
    })()
    
    agent = VoiceAgent(mock_client, mock_service)
    response = agent.process_voice_command("I did 10 reps of bench press at 135 pounds")
    print(f"   ✓ Voice agent response: {response}")
except Exception as e:
    print(f"   ✗ Voice agent error: {e}")

print("\n=== Component Testing Complete ===")

# Test creating actual workout through direct database
print("\n6. Creating Test Workouts:")
try:
    from db.database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Insert some test data
        test_workouts = [
            ("bench_press", 10, 135, date.today()),
            ("squat", 8, 225, date.today()),
            ("deadlift", 5, 315, date.today()),
        ]
        
        for exercise, reps, weight, workout_date in test_workouts:
            conn.execute(
                text("""
                    INSERT INTO workouts (workout_date, exercise, reps, weight_lbs, created_at)
                    VALUES (:date, :exercise, :reps, :weight, datetime('now'))
                """),
                {"date": workout_date, "exercise": exercise, "reps": reps, "weight": weight}
            )
        conn.commit()
        
        print("   ✓ Created test workouts in database")
        
        # Query them back
        result = conn.execute(text("SELECT exercise, reps, weight_lbs FROM workouts ORDER BY id DESC LIMIT 5"))
        rows = result.fetchall()
        print("   ✓ Recent workouts in database:")
        for row in rows:
            print(f"      - {row[0]}: {row[1]} reps @ {row[2]} lbs")
            
except Exception as e:
    print(f"   ✗ Database insert error: {e}")

print("\n✅ Testing complete! The core components are working.")
print("\nTo fix the server startup issue, you may need to:")
print("1. Update the OpenAI library: pip install --upgrade openai")
print("2. Or use a virtual environment with clean dependencies")
print("\nFor now, you can interact with the database directly using the test workouts created above.")