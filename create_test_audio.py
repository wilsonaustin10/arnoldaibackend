#!/usr/bin/env python3
"""Create a test audio file using TTS"""

import requests
import json

# Create a test audio file by using the TTS endpoint
response = requests.post(
    "http://localhost:8000/audio/tts",
    json={"text": "I did twenty reps of squats with two hundred and fifty pounds"}
)

if response.status_code == 200:
    with open("test_workout_command.wav", "wb") as f:
        f.write(response.content)
    print("✓ Created test_workout_command.wav")
    print("  This audio says: 'I did twenty reps of squats with two hundred and fifty pounds'")
else:
    print(f"✗ Failed to create audio: {response.status_code}")