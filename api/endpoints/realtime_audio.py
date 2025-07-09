import asyncio
import os
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import pyaudio
import wave
from dotenv import load_dotenv

from services.realtime_voice_agent import RealtimeVoiceAgent
from services.workout_service import WorkoutService

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/realtime", tags=["realtime_audio"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Audio configuration
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000  # OpenAI Realtime API uses 24kHz


class AudioStreamManager:
    """Manages bidirectional audio streaming between client and Realtime API"""
    
    def __init__(self, websocket: WebSocket, voice_agent: RealtimeVoiceAgent):
        self.websocket = websocket
        self.voice_agent = voice_agent
        self.is_active = True
        self.audio_queue = asyncio.Queue()
        
    async def start(self):
        """Start audio streaming tasks"""
        # Set up callbacks
        self.voice_agent.on_audio_data = self._handle_audio_output
        self.voice_agent.on_transcript = self._handle_transcript
        self.voice_agent.on_response_text = self._handle_response_text
        
        # Connect to Realtime API
        await self.voice_agent.connect()
        
        # Start concurrent tasks
        await asyncio.gather(
            self._receive_audio_from_client(),
            self._send_audio_to_client(),
            return_exceptions=True
        )
    
    async def _receive_audio_from_client(self):
        """Receive audio from WebSocket client and forward to Realtime API"""
        try:
            while self.is_active:
                message = await self.websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Audio data received
                        audio_data = message["bytes"]
                        await self.voice_agent.send_audio(audio_data)
                    elif "text" in message:
                        # Handle text messages (control commands)
                        data = json.loads(message["text"])
                        await self._handle_control_message(data)
                        
        except WebSocketDisconnect:
            logger.info("Client disconnected")
            self.is_active = False
        except Exception as e:
            logger.error(f"Error receiving audio: {e}")
            self.is_active = False
    
    async def _send_audio_to_client(self):
        """Send audio from Realtime API to WebSocket client"""
        try:
            while self.is_active:
                audio_data = await self.audio_queue.get()
                if audio_data:
                    await self.websocket.send_bytes(audio_data)
                    
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            self.is_active = False
    
    def _handle_audio_output(self, audio_data: bytes):
        """Callback for audio output from Realtime API"""
        asyncio.create_task(self.audio_queue.put(audio_data))
    
    def _handle_transcript(self, transcript: str):
        """Callback for user transcripts"""
        asyncio.create_task(self.websocket.send_json({
            "type": "transcript",
            "text": transcript
        }))
    
    def _handle_response_text(self, text: str):
        """Callback for assistant response text"""
        asyncio.create_task(self.websocket.send_json({
            "type": "response_text",
            "text": text
        }))
    
    async def _handle_control_message(self, data: dict):
        """Handle control messages from client"""
        message_type = data.get("type")
        
        if message_type == "text_input":
            # Handle text input
            text = data.get("text", "")
            await self.voice_agent.send_text(text)
        elif message_type == "stop":
            # Stop streaming
            self.is_active = False
    
    async def stop(self):
        """Clean up resources"""
        self.is_active = False
        await self.voice_agent.disconnect()


@router.websocket("/stream")
async def websocket_audio_stream(
    websocket: WebSocket,
    workout_service: WorkoutService = Depends()
):
    """
    WebSocket endpoint for real-time audio streaming.
    
    Client sends:
    - Binary messages: PCM16 audio data at 24kHz
    - Text messages: JSON control commands
    
    Server sends:
    - Binary messages: PCM16 audio responses
    - Text messages: JSON with transcripts and response text
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    voice_agent = RealtimeVoiceAgent(OPENAI_API_KEY, workout_service)
    stream_manager = AudioStreamManager(websocket, voice_agent)
    
    try:
        await stream_manager.start()
    except Exception as e:
        logger.error(f"Streaming error: {e}")
    finally:
        await stream_manager.stop()
        await websocket.close()
        logger.info("WebSocket connection closed")


@router.post("/session/start")
async def start_realtime_session(workout_service: WorkoutService = Depends()):
    """
    Start a new Realtime API session and return connection details.
    This can be used for clients that want to manage their own WebSocket connection.
    """
    try:
        # For security, you might want to generate a session token here
        # that clients can use to authenticate their WebSocket connection
        
        return JSONResponse({
            "status": "ready",
            "websocket_url": "/realtime/stream",
            "audio_format": {
                "encoding": "pcm16",
                "sample_rate": 24000,
                "channels": 1
            },
            "instructions": "Connect to the WebSocket endpoint to start streaming audio"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.get("/health")
async def health_check():
    """Check if the Realtime API service is healthy"""
    return {"status": "healthy", "service": "realtime_audio"}