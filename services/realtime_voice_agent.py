import asyncio
import json
import logging
from datetime import date, datetime
from typing import Dict, Any, Optional, Callable
from openai import AsyncOpenAI
from services.workout_service import WorkoutService
from schemas.workout import WorkoutIn
import base64

logger = logging.getLogger(__name__)


class RealtimeVoiceAgent:
    """
    Realtime Voice Agent using OpenAI's Realtime API for low-latency voice interactions.
    Provides bidirectional audio streaming with integrated function calling.
    """
    
    def __init__(self, api_key: str, workout_service: WorkoutService):
        self.client = AsyncOpenAI(api_key=api_key)
        self.workout_service = workout_service
        self.connection_manager = None # Add this line
        self.connection = None
        self.is_connected = False
        self.audio_buffer = bytearray()
        self.conversation_id = None
        
        # Callbacks for audio output
        self.on_audio_data: Optional[Callable[[bytes], None]] = None
        self.on_transcript: Optional[Callable[[str], None]] = None
        self.on_response_text: Optional[Callable[[str], None]] = None
        
    async def connect(self):
        """Establish WebSocket connection to OpenAI Realtime API"""
        try:
            self.connection_manager = self.client.beta.realtime.connect(
                model="gpt-4o-realtime-preview"
            )
            self.connection = await self.connection_manager.__aenter__()
            # Configure session
            await self.connection.session.update(
                session={
                    'modalities': ['text', 'audio'],
                    'instructions': self._create_system_instructions(),
                    'voice': 'alloy',  # Can be changed to other voices
                    'input_audio_format': 'pcm16',
                    'output_audio_format': 'pcm16',
                    'input_audio_transcription': {
                        'model': 'whisper-1'
                    },
                    'turn_detection': {
                        'type': 'server_vad',
                        'threshold': 0.5,
                        'prefix_padding_ms': 300,
                        'silence_duration_ms': 200
                    },
                    'tools': self._create_tools()
                }
            )
            
            self.is_connected = True
            logger.info("Connected to OpenAI Realtime API")
            
            # Start event handler
            asyncio.create_task(self._handle_events())
            
        except Exception as e:
            logger.error(f"Failed to connect to Realtime API: {e}")
            raise
    
    def _create_system_instructions(self) -> str:
        return """You are Arnold, an AI workout assistant with real-time voice capabilities. 
You help users track their workouts by understanding voice commands about exercises, reps, and weights.

Key responsibilities:
1. Parse workout information from natural language in real-time
2. Store workouts in the database using function calls
3. Query historical workout data when asked
4. Provide workout insights and progress tracking
5. Be encouraging and motivational
6. Respond naturally and conversationally

When a user tells you about a workout, extract:
- Exercise name (e.g., "bench press", "squats", "deadlifts")
- Number of reps
- Weight in pounds

Respond concisely and naturally. Use a friendly, encouraging tone."""

    def _create_tools(self) -> list:
        return [
            {
                "type": "function",
                "name": "log_workout",
                "description": "Log a new workout set to the database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "exercise": {
                            "type": "string",
                            "description": "The name of the exercise"
                        },
                        "reps": {
                            "type": "integer",
                            "description": "Number of repetitions performed"
                        },
                        "weight_lbs": {
                            "type": "number",
                            "description": "Weight used in pounds"
                        },
                        "workout_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Date of the workout (YYYY-MM-DD format)"
                        }
                    },
                    "required": ["exercise", "reps", "weight_lbs"]
                }
            },
            {
                "type": "function",
                "name": "get_recent_workouts",
                "description": "Get the most recent workout entries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of recent workouts to retrieve",
                            "default": 10
                        }
                    }
                }
            },
            {
                "type": "function",
                "name": "query_workouts_by_exercise",
                "description": "Query workout history for a specific exercise",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "exercise": {
                            "type": "string",
                            "description": "The exercise name to query"
                        },
                        "workout_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Optional date filter"
                        }
                    },
                    "required": ["exercise"]
                }
            }
        ]
    
    async def _handle_events(self):
        """Handle incoming events from the Realtime API"""
        try:
            async for event in self.connection:
                event_type = event.type
                
                if event_type == 'error':
                    logger.error(f"Realtime API error: {event}")
                    
                elif event_type == 'session.created':
                    logger.info("Session created successfully")
                    
                elif event_type == 'input_audio_buffer.speech_started':
                    logger.debug("User started speaking")
                    
                elif event_type == 'input_audio_buffer.speech_stopped':
                    logger.debug("User stopped speaking")
                    
                elif event_type == 'conversation.item.created':
                    if hasattr(event, 'item') and event.item.get('role') == 'user':
                        # Handle user input transcript
                        if self.on_transcript:
                            content = event.item.get('content', [])
                            for c in content:
                                if c.get('type') == 'input_text':
                                    self.on_transcript(c.get('text', ''))
                
                elif event_type == 'response.audio.delta':
                    # Stream audio output
                    if hasattr(event, 'delta'):
                        audio_data = base64.b64decode(event.delta)
                        if self.on_audio_data:
                            self.on_audio_data(audio_data)
                
                elif event_type == 'response.text.delta':
                    # Stream text response
                    if self.on_response_text and hasattr(event, 'delta'):
                        self.on_response_text(event.delta)
                
                elif event_type == 'response.function_call_arguments.done':
                    # Handle function call
                    await self._handle_function_call(event)
                    
                elif event_type == 'response.done':
                    logger.debug("Response completed")
                    
        except Exception as e:
            logger.error(f"Error handling events: {e}")
            self.is_connected = False
    
    async def _handle_function_call(self, event):
        """Execute function calls and send results back"""
        try:
            function_name = event.name
            arguments = json.loads(event.arguments)
            
            # Execute the function
            result = await self._execute_function(function_name, arguments)
            
            # Send function result back
            await self.connection.conversation.item.create(
                item={
                    "type": "function_call_output",
                    "call_id": event.call_id,
                    "output": json.dumps(result)
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling function call: {e}")
            await self.connection.conversation.item.create(
                item={
                    "type": "function_call_output",
                    "call_id": event.call_id,
                    "output": json.dumps({"error": str(e)})
                }
            )
    
    async def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute the requested function with the given arguments"""
        try:
            if function_name == "log_workout":
                if "workout_date" not in arguments:
                    arguments["workout_date"] = date.today()
                else:
                    arguments["workout_date"] = datetime.fromisoformat(arguments["workout_date"]).date()
                
                workout_in = WorkoutIn(**arguments)
                result = self.workout_service.create_workout(workout_in)
                return {
                    "success": True,
                    "message": f"Logged {result.reps} reps of {result.exercise} at {result.weight_lbs} lbs",
                    "workout": {
                        "id": result.id,
                        "exercise": result.exercise,
                        "reps": result.reps,
                        "weight_lbs": result.weight_lbs,
                        "date": result.workout_date.isoformat()
                    }
                }
            
            elif function_name == "get_recent_workouts":
                limit = arguments.get("limit", 10)
                workouts = self.workout_service.get_recent_workouts(limit=limit)
                return {
                    "success": True,
                    "workouts": [
                        {
                            "id": w.id,
                            "exercise": w.exercise,
                            "reps": w.reps,
                            "weight_lbs": w.weight_lbs,
                            "date": w.workout_date.isoformat()
                        } for w in workouts
                    ]
                }
            
            elif function_name == "query_workouts_by_exercise":
                exercise = arguments["exercise"]
                workout_date = None
                if "workout_date" in arguments:
                    workout_date = datetime.fromisoformat(arguments["workout_date"]).date()
                
                workouts = self.workout_service.query_workouts(
                    exercise=exercise,
                    workout_date=workout_date
                )
                return {
                    "success": True,
                    "exercise": exercise,
                    "workouts": [
                        {
                            "id": w.id,
                            "reps": w.reps,
                            "weight_lbs": w.weight_lbs,
                            "date": w.workout_date.isoformat()
                        } for w in workouts
                    ]
                }
            
            else:
                return {"success": False, "error": f"Unknown function: {function_name}"}
                
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to the Realtime API"""
        if not self.is_connected:
            logger.warning("Not connected to Realtime API")
            return
        
        try:
            # Convert audio to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Append audio to input buffer
            await self.connection.input_audio_buffer.append(
                audio=audio_base64
            )
            
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
    
    async def send_text(self, text: str):
        """Send text input to the Realtime API"""
        if not self.is_connected:
            logger.warning("Not connected to Realtime API")
            return
        
        try:
            await self.connection.conversation.item.create(
                item={
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}]
                }
            )
            
            # Create response
            await self.connection.response.create()
            
        except Exception as e:
            logger.error(f"Error sending text: {e}")
    
    async def disconnect(self):
        """Close the WebSocket connection"""
        if self.connection_manager:
            
            self.is_connected = False
            await self.connection_manager.__aexit__(None, None, None)
            logger.info("Disconnected from Realtime API")