#!/usr/bin/env python3
"""Test script for Arnold.ai voice agent functionality"""

import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test if the server is running"""
    print("1. Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✓ Health check: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_text_chat():
    """Test the text-based chat interface"""
    print("\n2. Testing text chat...")
    
    test_commands = [
        "I just did 10 reps of bench press with 135 pounds",
        "What are my recent workouts?",
        "I completed 3 sets of squats: 8 reps at 225, 6 reps at 245, and 4 reps at 265",
        "Show me my bench press history"
    ]
    
    for command in test_commands:
        print(f"\n   Command: {command}")
        try:
            response = requests.post(
                f"{BASE_URL}/audio/chat",
                json={"text": command}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   ✓ AI Response: {result['response'][:100]}...")
            else:
                print(f"   ✗ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")

def test_workout_endpoints():
    """Test direct workout endpoints"""
    print("\n3. Testing workout endpoints...")
    
    # Test creating a workout
    print("\n   a) Creating a workout...")
    workout_data = {
        "workout_date": date.today().isoformat(),
        "exercise": "deadlift",
        "reps": 5,
        "weight_lbs": 315
    }
    
    try:
        response = requests.post(f"{BASE_URL}/workouts/", json=workout_data)
        if response.status_code == 201:
            print(f"   ✓ Workout created: {response.json()}")
        else:
            print(f"   ✗ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test fetching recent workouts
    print("\n   b) Fetching recent workouts...")
    try:
        response = requests.get(f"{BASE_URL}/workouts/recent?limit=5")
        if response.status_code == 200:
            workouts = response.json()
            print(f"   ✓ Found {len(workouts)} recent workouts")
            for w in workouts[:3]:  # Show first 3
                print(f"      - {w['exercise']}: {w['reps']} reps @ {w['weight_lbs']} lbs")
        else:
            print(f"   ✗ Error: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

def test_tts():
    """Test text-to-speech endpoint"""
    print("\n4. Testing TTS...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/audio/tts",
            json={"text": "Great job on your workout today! You crushed it!"}
        )
        if response.status_code == 200:
            print(f"   ✓ TTS successful, audio file size: {len(response.content)} bytes")
        else:
            print(f"   ✗ Error: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

def test_voice_command_simulation():
    """Simulate a full voice command flow using text"""
    print("\n5. Testing full voice agent flow (text simulation)...")
    
    # Simulate multiple commands in sequence
    conversation = []
    
    commands = [
        "Hi Arnold, I'm about to start my workout",
        "I just finished 8 reps of bench press at 185 pounds",
        "Now I did 6 reps at 205 pounds",
        "What's my bench press progress looking like?"
    ]
    
    for cmd in commands:
        print(f"\n   User: {cmd}")
        try:
            response = requests.post(
                f"{BASE_URL}/audio/chat",
                json={
                    "text": cmd,
                    "conversation_history": conversation
                }
            )
            if response.status_code == 200:
                ai_response = response.json()["response"]
                print(f"   Arnold: {ai_response}")
                
                # Add to conversation history
                conversation.append({"role": "user", "content": cmd})
                conversation.append({"role": "assistant", "content": ai_response})
            else:
                print(f"   ✗ Error: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")

if __name__ == "__main__":
    print("=== Arnold.ai Voice Agent Test Suite ===\n")
    
    # Check if server is running
    if not test_health_check():
        print("\n⚠️  Server is not running! Please start it with: python main.py")
        exit(1)
    
    # Run all tests
    test_text_chat()
    test_workout_endpoints()
    test_tts()
    test_voice_command_simulation()
    
    print("\n\n=== Test Suite Complete ===")
    print("\nTo test with actual audio:")
    print("1. Record yourself saying a workout command")
    print("2. Use: curl -X POST 'http://localhost:8000/audio/process-voice-command' -F 'file=@your_audio.wav'")