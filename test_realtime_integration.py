#!/usr/bin/env python3
"""
Test script for OpenAI Realtime API integration
Tests connection, audio streaming, and function calling
"""

import asyncio
import json
import logging
import time
from typing import List, Dict
import numpy as np

from services.realtime_voice_agent_enhanced import RealtimeVoiceAgentEnhanced, ReconnectConfig
from services.workout_service import WorkoutService
from db.session import SessionLocal
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResults:
    """Track test results"""
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
    
    def add_result(self, test_name: str, passed: bool, details: str = ""):
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            self.tests_failed += 1
            status = "❌ FAILED"
        
        self.results.append({
            "test": test_name,
            "status": status,
            "details": details
        })
        
        print(f"{status} - {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def print_summary(self):
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print("="*60)


async def test_connection(api_key: str, workout_service: WorkoutService, results: TestResults):
    """Test basic connection to Realtime API"""
    test_name = "Basic Connection"
    try:
        agent = RealtimeVoiceAgentEnhanced(api_key, workout_service)
        await agent.connect()
        
        # Check if connected
        if agent.is_connected:
            results.add_result(test_name, True, "Successfully connected to Realtime API")
        else:
            results.add_result(test_name, False, "Connection established but is_connected is False")
        
        await agent.disconnect()
        
    except Exception as e:
        results.add_result(test_name, False, f"Connection failed: {str(e)}")


async def test_text_input(api_key: str, workout_service: WorkoutService, results: TestResults):
    """Test text input processing"""
    test_name = "Text Input Processing"
    try:
        agent = RealtimeVoiceAgentEnhanced(api_key, workout_service)
        
        # Track responses
        responses = []
        agent.on_response_text = lambda text: responses.append(text)
        
        await agent.connect()
        
        # Send test message
        await agent.send_text("Hello, can you hear me?")
        
        # Wait for response
        await asyncio.sleep(3)
        
        if responses:
            results.add_result(test_name, True, f"Received response: {''.join(responses)[:50]}...")
        else:
            results.add_result(test_name, False, "No response received")
        
        await agent.disconnect()
        
    except Exception as e:
        results.add_result(test_name, False, f"Error: {str(e)}")


async def test_function_calling(api_key: str, workout_service: WorkoutService, results: TestResults):
    """Test function calling for workout logging"""
    test_name = "Function Calling - Workout Logging"
    try:
        agent = RealtimeVoiceAgentEnhanced(api_key, workout_service)
        
        # Track responses and function calls
        responses = []
        agent.on_response_text = lambda text: responses.append(text)
        
        await agent.connect()
        
        # Send workout command
        await agent.send_text("I just did 15 reps of push-ups with body weight")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Check if workout was logged
        recent_workouts = workout_service.get_recent_workouts(limit=1)
        
        if recent_workouts and recent_workouts[0].exercise.lower() == "push-ups":
            results.add_result(test_name, True, f"Workout logged: {recent_workouts[0].exercise}")
        else:
            results.add_result(test_name, False, "Workout not found in database")
        
        await agent.disconnect()
        
    except Exception as e:
        results.add_result(test_name, False, f"Error: {str(e)}")


async def test_audio_streaming(api_key: str, workout_service: WorkoutService, results: TestResults):
    """Test audio streaming capabilities"""
    test_name = "Audio Streaming"
    try:
        agent = RealtimeVoiceAgentEnhanced(api_key, workout_service)
        
        # Track audio data
        audio_received = []
        agent.on_audio_data = lambda data: audio_received.append(len(data))
        
        await agent.connect()
        
        # Generate test audio (1 second of silence)
        sample_rate = 24000
        duration = 1.0
        samples = int(sample_rate * duration)
        audio_data = np.zeros(samples, dtype=np.int16).tobytes()
        
        # Send audio
        await agent.send_audio(audio_data)
        
        # Wait for any response
        await asyncio.sleep(3)
        
        if audio_received:
            total_bytes = sum(audio_received)
            results.add_result(test_name, True, f"Received {total_bytes} bytes of audio")
        else:
            results.add_result(test_name, False, "No audio response received")
        
        await agent.disconnect()
        
    except Exception as e:
        results.add_result(test_name, False, f"Error: {str(e)}")


async def test_reconnection(api_key: str, workout_service: WorkoutService, results: TestResults):
    """Test automatic reconnection"""
    test_name = "Automatic Reconnection"
    try:
        reconnect_config = ReconnectConfig(
            max_retries=3,
            initial_delay=0.5,
            max_delay=2.0
        )
        
        agent = RealtimeVoiceAgentEnhanced(
            api_key, 
            workout_service,
            reconnect_config=reconnect_config
        )
        
        connection_events = []
        agent.on_connection_status = lambda status: connection_events.append(status)
        
        await agent.connect()
        
        # Simulate connection drop by closing the connection
        if agent.connection:
            await agent.connection.close()
        
        # Wait for reconnection
        await asyncio.sleep(5)
        
        # Check reconnection
        if len(connection_events) >= 2 and connection_events[-1] == True:
            results.add_result(test_name, True, "Successfully reconnected after connection drop")
        else:
            results.add_result(test_name, False, f"Reconnection failed. Events: {connection_events}")
        
        await agent.disconnect()
        
    except Exception as e:
        results.add_result(test_name, False, f"Error: {str(e)}")


async def test_metrics(api_key: str, workout_service: WorkoutService, results: TestResults):
    """Test performance metrics tracking"""
    test_name = "Performance Metrics"
    try:
        agent = RealtimeVoiceAgentEnhanced(api_key, workout_service)
        
        await agent.connect()
        
        # Send some messages
        await agent.send_text("What's my recent workout history?")
        await asyncio.sleep(3)
        
        # Get metrics
        metrics = agent.get_metrics()
        
        if metrics["messages_sent"] > 0 and metrics["messages_received"] > 0:
            results.add_result(
                test_name, 
                True, 
                f"Sent: {metrics['messages_sent']}, Received: {metrics['messages_received']}"
            )
        else:
            results.add_result(test_name, False, f"No messages tracked: {metrics}")
        
        await agent.disconnect()
        
    except Exception as e:
        results.add_result(test_name, False, f"Error: {str(e)}")


async def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("ARNOLD AI - REALTIME API INTEGRATION TESTS")
    print("="*60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in environment")
        return
    
    # Create database session
    db = SessionLocal()
    workout_service = WorkoutService(db)
    
    results = TestResults()
    
    try:
        # Run tests
        print("\nRunning tests...\n")
        
        await test_connection(api_key, workout_service, results)
        await asyncio.sleep(1)
        
        await test_text_input(api_key, workout_service, results)
        await asyncio.sleep(1)
        
        await test_function_calling(api_key, workout_service, results)
        await asyncio.sleep(1)
        
        await test_audio_streaming(api_key, workout_service, results)
        await asyncio.sleep(1)
        
        await test_reconnection(api_key, workout_service, results)
        await asyncio.sleep(1)
        
        await test_metrics(api_key, workout_service, results)
        
        # Print summary
        results.print_summary()
        
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_all_tests())