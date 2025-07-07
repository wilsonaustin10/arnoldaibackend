#!/usr/bin/env python3
"""
Demonstrates the complete voice flow of Arnold.ai
"""

import os
from dotenv import load_dotenv
from db.database import engine
from sqlalchemy import text
from datetime import date

load_dotenv()

print("🎯 Arnold.ai Voice Flow Demonstration")
print("=" * 50)

# Simulate the complete voice flow
print("\n1️⃣ USER SPEAKS (Audio Input):")
print('   🎤 "I just did 12 reps of barbell rows with 185 pounds"')

print("\n2️⃣ SPEECH-TO-TEXT (OpenAI Whisper):")
print('   📝 Transcript: "I just did 12 reps of barbell rows with 185 pounds"')

print("\n3️⃣ AI PROCESSING (GPT-4):")
print("   🧠 Understanding: Exercise=barbell rows, Reps=12, Weight=185 lbs")
print("   💾 Function Call: log_workout(exercise='barbell rows', reps=12, weight_lbs=185)")

# Actually log the workout to demonstrate
with engine.connect() as conn:
    conn.execute(
        text("""
            INSERT INTO workouts (workout_date, exercise, reps, weight_lbs, created_at)
            VALUES (:date, :exercise, :reps, :weight, datetime('now'))
        """),
        {
            "date": date.today(),
            "exercise": "barbell rows",
            "reps": 12,
            "weight": 185
        }
    )
    conn.commit()

print("\n4️⃣ DATABASE UPDATE:")
print("   ✅ Workout logged to database")

print("\n5️⃣ AI RESPONSE GENERATION:")
response = "Excellent work on those barbell rows! 12 reps at 185 pounds is solid. Keep pulling heavy!"
print(f'   💬 "{response}"')

print("\n6️⃣ TEXT-TO-SPEECH (ElevenLabs):")
print("   🔊 Audio generated with natural voice")

print("\n7️⃣ USER HEARS:")
print(f'   🎧 "{response}"')

print("\n" + "=" * 50)
print("✅ Complete Voice Pipeline:")
print("   Audio → Text → AI → Database → Response → Audio")

# Show the logged workout
print("\n📊 Verifying workout was logged:")
with engine.connect() as conn:
    result = conn.execute(
        text("""
            SELECT exercise, reps, weight_lbs, workout_date 
            FROM workouts 
            WHERE exercise = 'barbell rows'
            ORDER BY id DESC 
            LIMIT 1
        """)
    )
    row = result.fetchone()
    if row:
        print(f"   ✅ Found: {row[0]} - {row[1]} reps @ {row[2]} lbs on {row[3]}")

print("\n🎯 API Endpoints Available:")
print("   • POST /audio/process-voice-command - Full voice pipeline")
print("   • POST /audio/chat - Text-based chat")
print("   • POST /audio/transcribe - STT only")
print("   • POST /audio/tts - TTS only")
print("   • POST /workouts/ - Direct workout logging")
print("   • GET /workouts/recent - Query recent workouts")

print("\n💡 To test with real audio:")
print('   curl -X POST "http://localhost:8000/audio/process-voice-command" \\')
print('     -F "file=@your_workout_audio.wav;type=audio/wav"')