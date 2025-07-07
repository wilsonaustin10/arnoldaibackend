#!/usr/bin/env python3
"""
Arnold.ai CLI - Direct database interaction without API dependencies
"""

import os
import json
from datetime import date, datetime
from dotenv import load_dotenv
from db.database import engine
from sqlalchemy import text
import requests

load_dotenv()

class ArnoldCLI:
    def __init__(self):
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not self.OPENAI_API_KEY:
            raise ValueError("Please set OPENAI_API_KEY in your .env file")
    
    def log_workout(self, exercise, reps, weight):
        """Log a workout directly to database"""
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO workouts (workout_date, exercise, reps, weight_lbs, created_at)
                    VALUES (:date, :exercise, :reps, :weight, datetime('now'))
                """),
                {
                    "date": date.today(),
                    "exercise": exercise.lower(),
                    "reps": reps,
                    "weight": weight
                }
            )
            conn.commit()
        return f"✅ Logged: {reps} reps of {exercise} at {weight} lbs"
    
    def get_recent_workouts(self, limit=10):
        """Get recent workouts from database"""
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT exercise, reps, weight_lbs, workout_date 
                    FROM workouts 
                    ORDER BY id DESC 
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            
            workouts = []
            for row in result:
                workouts.append({
                    "exercise": row[0],
                    "reps": row[1],
                    "weight": row[2],
                    "date": row[3]
                })
            return workouts
    
    def query_exercise(self, exercise):
        """Query specific exercise history"""
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT reps, weight_lbs, workout_date 
                    FROM workouts 
                    WHERE exercise = :exercise
                    ORDER BY workout_date DESC
                    LIMIT 20
                """),
                {"exercise": exercise.lower()}
            )
            
            history = []
            for row in result:
                history.append({
                    "reps": row[0],
                    "weight": row[1],
                    "date": row[2]
                })
            return history
    
    def get_ai_response(self, prompt):
        """Get AI response using OpenAI API directly"""
        headers = {
            "Authorization": f"Bearer {self.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4-turbo-preview",
            "messages": [
                {
                    "role": "system",
                    "content": "You are Arnold, a motivational workout assistant. Be encouraging and helpful."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"AI Error: {response.status_code}"
        except Exception as e:
            return f"AI Error: {str(e)}"

def main():
    print("🏋️  Arnold.ai CLI - Workout Tracker")
    print("=" * 50)
    
    arnold = ArnoldCLI()
    
    while True:
        print("\nOptions:")
        print("1. Log a workout")
        print("2. View recent workouts")
        print("3. Query specific exercise")
        print("4. Get motivation")
        print("5. Quit")
        
        choice = input("\nChoice (1-5): ").strip()
        
        if choice == "1":
            exercise = input("Exercise name: ").strip()
            reps = int(input("Reps: ").strip())
            weight = float(input("Weight (lbs): ").strip())
            result = arnold.log_workout(exercise, reps, weight)
            print(result)
            
        elif choice == "2":
            workouts = arnold.get_recent_workouts()
            print("\n📊 Recent Workouts:")
            for w in workouts:
                print(f"  • {w['exercise']}: {w['reps']} reps @ {w['weight']} lbs ({w['date']})")
            
        elif choice == "3":
            exercise = input("Exercise to query: ").strip()
            history = arnold.query_exercise(exercise)
            if history:
                print(f"\n📈 {exercise} History:")
                for h in history:
                    print(f"  • {h['reps']} reps @ {h['weight']} lbs ({h['date']})")
            else:
                print(f"No history found for {exercise}")
            
        elif choice == "4":
            prompt = "Give me a short motivational message for my workout"
            motivation = arnold.get_ai_response(prompt)
            print(f"\n💪 {motivation}")
            
        elif choice == "5":
            print("\n🏋️  Keep crushing those workouts! See you next time!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🏋️  Keep pushing! See you next time!")
    except Exception as e:
        print(f"\n❌ Error: {e}")