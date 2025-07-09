#!/usr/bin/env python3
"""
Simple test of Arnold.ai functionality using the API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("🏋️  Testing Arnold.ai Voice Assistant")
print("=" * 50)

# Test 1: Basic chat
print("\n1. Testing basic chat functionality...")
response = requests.post(
    f"{BASE_URL}/audio/chat",
    json={"text": "Hello Arnold, I'm ready to work out!"}
)
if response.status_code == 200:
    print(f"✅ Arnold says: {response.json()['response']}")
else:
    print(f"❌ Chat failed: {response.status_code}")

# Test 2: Log a workout
print("\n2. Logging a workout...")
response = requests.post(
    f"{BASE_URL}/audio/chat",
    json={"text": "I just did 8 reps of pullups with 25 pounds added weight"}
)
if response.status_code == 200:
    print(f"✅ Arnold says: {response.json()['response']}")
else:
    print(f"❌ Workout logging failed: {response.status_code}")

# Test 3: Query workouts
print("\n3. Querying recent workouts...")
response = requests.post(
    f"{BASE_URL}/audio/chat",
    json={"text": "What workouts have I done today?"}
)
if response.status_code == 200:
    print(f"✅ Arnold says: {response.json()['response'][:200]}...")
else:
    print(f"❌ Query failed: {response.status_code}")

# Test 4: Multiple commands in sequence
print("\n4. Testing conversation flow...")
conversation = []

commands = [
    "I'm going to do some deadlifts now",
    "Just finished 5 reps at 405 pounds",
    "That was tough! What's my deadlift PR?"
]

for cmd in commands:
    print(f"\n💬 You: {cmd}")
    
    response = requests.post(
        f"{BASE_URL}/audio/chat",
        json={
            "text": cmd,
            "conversation_history": conversation
        }
    )
    
    if response.status_code == 200:
        ai_response = response.json()["response"]
        print(f"🏋️  Arnold: {ai_response}")
        
        # Update conversation history
        conversation.append({"role": "user", "content": cmd})
        conversation.append({"role": "assistant", "content": ai_response})
    else:
        print(f"❌ Error: {response.status_code}")

# Test 5: Direct workout endpoint
print("\n5. Testing direct workout logging...")
workout_data = {
    "workout_date": "2025-07-07",
    "exercise": "lat_pulldown",
    "reps": 12,
    "weight_lbs": 120
}

response = requests.post(f"{BASE_URL}/workouts/", json=workout_data)
if response.status_code == 201:
    print(f"✅ Directly logged: {response.json()}")
else:
    print(f"❌ Direct logging failed: {response.status_code}")

print("\n" + "=" * 50)
print("✅ Testing complete!")
print("\nArnold.ai is ready to help you track your workouts!")
print("Use the interactive demo (python demo_arnold.py) for a full experience.")