import asyncio
import json
import logging
import time
from datetime import date, datetime
from typing import Dict, Any, Optional, Callable
from openai import AsyncOpenAI
from services.workout_service import WorkoutService
from schemas.workout import WorkoutIn
import base64
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ReconnectConfig:
    """Configuration for automatic reconnection"""
    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base


class RealtimeVoiceAgentEnhanced:
    """
    Enhanced Realtime Voice Agent with robust error handling, reconnection,
    and performance optimization for OpenAI's Realtime API.
    """
    
    def __init__(
        self, 
        api_key: str, 
        workout_service: WorkoutService,
        reconnect_config: Optional[ReconnectConfig] = None
    ):
        self.client = AsyncOpenAI(api_key=api_key, max_retries=3)
        self.workout_service = workout_service
        self.reconnect_config = reconnect_config or ReconnectConfig()
        
        # Connection state
        self.connection = None
        self.is_connected = False
        self.is_reconnecting = False
        self.connection_id = None
        self.retry_count = 0
        
        # Performance metrics
        self.metrics = {
            "connection_start": None,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "reconnects": 0,
            "function_calls": 0,
            "average_latency": 0
        }
        
        # Audio buffer for smooth playback
        self.audio_buffer = bytearray()
        self.audio_buffer_lock = asyncio.Lock()
        
        # Callbacks
        self.on_audio_data: Optional[Callable[[bytes], None]] = None
        self.on_transcript: Optional[Callable[[str], None]] = None
        self.on_response_text: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_connection_status: Optional[Callable[[bool], None]] = None
        
        # Event handlers task
        self._event_handler_task = None
        self._heartbeat_task = None
    
    @asynccontextmanager
    async def managed_connection(self):
        """Context manager for automatic connection management"""
        try:
            await self.connect()
            yield self
        finally:
            await self.disconnect()
    
    async def connect(self):
        """Establish WebSocket connection with retry logic"""
        self.retry_count = 0
        
        while self.retry_count < self.reconnect_config.max_retries:
            try:
                await self._establish_connection()
                self.retry_count = 0  # Reset on successful connection
                return
            except Exception as e:
                self.retry_count += 1
                if self.retry_count >= self.reconnect_config.max_retries:
                    logger.error(f"Failed to connect after {self.retry_count} attempts")
                    raise
                
                delay = min(
                    self.reconnect_config.initial_delay * (self.reconnect_config.exponential_base ** (self.retry_count - 1)),
                    self.reconnect_config.max_delay
                )
                
                logger.warning(f"Connection attempt {self.retry_count} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
    
    async def _establish_connection(self):
        """Establish the actual WebSocket connection"""
        try:
            self.metrics["connection_start"] = time.time()
            
            self.connection = await self.client.beta.realtime.connect(
                model="gpt-4o-realtime-preview"
            )
            
            # Configure session with optimizations
            await self.connection.session.update(
                session={
                    'modalities': ['text', 'audio'],
                    'instructions': self._create_system_instructions(),
                    'voice': 'alloy',
                    'input_audio_format': 'pcm16',
                    'output_audio_format': 'pcm16',
                    'input_audio_transcription': {
                        'enabled': True,
                        'model': 'whisper-1'
                    },
                    'turn_detection': {
                        'type': 'server_vad',
                        'threshold': 0.5,
                        'prefix_padding_ms': 300,
                        'silence_duration_ms': 200
                    },
                    'temperature': 0.8,
                    'max_response_output_tokens': 4096,
                    'tools': self._create_tools()
                }
            )
            
            self.is_connected = True
            self.connection_id = f"conn_{int(time.time())}"
            
            # Notify connection status
            if self.on_connection_status:
                self.on_connection_status(True)
            
            logger.info(f"Connected to OpenAI Realtime API (ID: {self.connection_id})")
            
            # Start background tasks
            self._event_handler_task = asyncio.create_task(
                self._handle_events_with_error_recovery()
            )
            self._heartbeat_task = asyncio.create_task(
                self._heartbeat()
            )
            
        except Exception as e:
            self.is_connected = False
            self.metrics["errors"] += 1
            logger.error(f"Failed to establish connection: {e}")
            raise
    
    async def _handle_events_with_error_recovery(self):
        """Handle events with automatic error recovery"""
        while self.is_connected:
            try:
                await self._handle_events()
            except Exception as e:
                logger.error(f"Event handler error: {e}")
                self.metrics["errors"] += 1
                
                if self.on_error:
                    self.on_error(e)
                
                # Attempt reconnection if not already reconnecting
                if not self.is_reconnecting:
                    asyncio.create_task(self._reconnect())
                
                break
    
    async def _reconnect(self):
        """Reconnect to the Realtime API"""
        if self.is_reconnecting:
            return
        
        self.is_reconnecting = True
        self.is_connected = False
        self.metrics["reconnects"] += 1
        
        try:
            logger.info("Attempting to reconnect...")
            
            # Close existing connection
            if self.connection:
                try:
                    await self.connection.close()
                except:
                    pass
            
            # Notify disconnection
            if self.on_connection_status:
                self.on_connection_status(False)
            
            # Reconnect
            await self.connect()
            
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            if self.on_error:
                self.on_error(e)
        finally:
            self.is_reconnecting = False
    
    async def _heartbeat(self):
        """Send periodic heartbeat to maintain connection"""
        while self.is_connected:
            try:
                await asyncio.sleep(30)  # Every 30 seconds
                # You can send a simple message or check connection health here
                logger.debug(f"Heartbeat - Messages: sent={self.metrics['messages_sent']}, "
                           f"received={self.metrics['messages_received']}")
            except:
                break
    
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

Respond concisely and naturally. Use a friendly, encouraging tone.
Keep responses brief unless the user asks for detailed information."""

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
        async for event in self.connection:
            self.metrics["messages_received"] += 1
            event_type = event.type
            
            try:
                if event_type == 'error':
                    logger.error(f"Realtime API error: {event}")
                    self.metrics["errors"] += 1
                    
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
                    # Stream audio output with buffering
                    if hasattr(event, 'delta'):
                        await self._handle_audio_delta(event.delta)
                
                elif event_type == 'response.text.delta':
                    # Stream text response
                    if self.on_response_text and hasattr(event, 'delta'):
                        self.on_response_text(event.delta)
                
                elif event_type == 'response.function_call_arguments.done':
                    # Handle function call
                    self.metrics["function_calls"] += 1
                    await self._handle_function_call(event)
                    
                elif event_type == 'response.done':
                    logger.debug("Response completed")
                    
            except Exception as e:
                logger.error(f"Error processing event {event_type}: {e}")
                self.metrics["errors"] += 1
    
    async def _handle_audio_delta(self, delta: str):
        """Handle audio data with buffering for smooth playback"""
        try:
            audio_data = base64.b64decode(delta)
            
            # Add to buffer
            async with self.audio_buffer_lock:
                self.audio_buffer.extend(audio_data)
                
                # If buffer is large enough, send it
                if len(self.audio_buffer) >= 4800:  # 100ms at 24kHz
                    if self.on_audio_data:
                        self.on_audio_data(bytes(self.audio_buffer))
                    self.audio_buffer.clear()
        except Exception as e:
            logger.error(f"Error handling audio delta: {e}")
    
    async def _handle_function_call(self, event):
        """Execute function calls with error handling"""
        try:
            function_name = event.name
            arguments = json.loads(event.arguments)
            
            # Measure function call latency
            start_time = time.time()
            
            # Execute the function
            result = await self._execute_function(function_name, arguments)
            
            # Update metrics
            latency = time.time() - start_time
            self.metrics["average_latency"] = (
                (self.metrics["average_latency"] * (self.metrics["function_calls"] - 1) + latency) 
                / self.metrics["function_calls"]
            )
            
            # Send function result back
            await self.connection.conversation.item.create(
                item={
                    "type": "function_call_output",
                    "call_id": event.call_id,
                    "output": json.dumps(result)
                }
            )
            
            self.metrics["messages_sent"] += 1
            
        except Exception as e:
            logger.error(f"Error handling function call: {e}")
            self.metrics["errors"] += 1
            
            # Send error response
            await self.connection.conversation.item.create(
                item={
                    "type": "function_call_output",
                    "call_id": event.call_id,
                    "output": json.dumps({
                        "success": False,
                        "error": f"Function call failed: {str(e)}"
                    })
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
                    "count": len(workouts),
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
                    "count": len(workouts),
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
        """Send audio data to the Realtime API with retry logic"""
        if not self.is_connected:
            logger.warning("Not connected to Realtime API")
            return
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Convert audio to base64
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                
                # Append audio to input buffer
                await self.connection.input_audio_buffer.append(
                    audio=audio_base64
                )
                
                self.metrics["messages_sent"] += 1
                return
                
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Failed to send audio after {max_retries} attempts: {e}")
                    self.metrics["errors"] += 1
                    if self.on_error:
                        self.on_error(e)
                else:
                    await asyncio.sleep(0.1 * retry_count)
    
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
            
            self.metrics["messages_sent"] += 2  # item + response
            
        except Exception as e:
            logger.error(f"Error sending text: {e}")
            self.metrics["errors"] += 1
            if self.on_error:
                self.on_error(e)
    
    async def disconnect(self):
        """Close the WebSocket connection and clean up"""
        logger.info("Disconnecting from Realtime API...")
        self.is_connected = False
        
        # Cancel background tasks
        if self._event_handler_task:
            self._event_handler_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        # Flush any remaining audio
        async with self.audio_buffer_lock:
            if self.audio_buffer and self.on_audio_data:
                self.on_audio_data(bytes(self.audio_buffer))
            self.audio_buffer.clear()
        
        # Close connection
        if self.connection:
            try:
                await self.connection.close()
            except:
                pass
        
        # Notify disconnection
        if self.on_connection_status:
            self.on_connection_status(False)
        
        # Log metrics
        logger.info(f"Session metrics: {self.metrics}")
        logger.info("Disconnected from Realtime API")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if self.metrics["connection_start"]:
            self.metrics["uptime_seconds"] = time.time() - self.metrics["connection_start"]
        return self.metrics.copy()