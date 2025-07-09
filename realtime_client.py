#!/usr/bin/env python3
"""
Realtime Voice Client for Arnold AI
Demonstrates bidirectional audio streaming with the Realtime API
"""

import asyncio
import json
import logging
import pyaudio
import websockets
import numpy as np
from typing import Optional
import threading
import queue
import signal
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Audio configuration matching Realtime API requirements
CHUNK_SIZE = 960  # 20ms at 24kHz
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000
RECORD_SECONDS = 0.02  # 20ms chunks


class RealtimeVoiceClient:
    """Client for real-time voice interaction with Arnold AI"""
    
    def __init__(self, websocket_url: str = "ws://localhost:8000/realtime/stream"):
        self.websocket_url = websocket_url
        self.websocket = None
        self.is_running = False
        
        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        
        # Queues for audio data
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        
        # Event for graceful shutdown
        self.stop_event = threading.Event()
    
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            logger.info(f"Connected to {self.websocket_url}")
            self.is_running = True
            
            # Start audio streams
            self._start_audio_streams()
            
            # Start concurrent tasks
            await asyncio.gather(
                self._send_audio_task(),
                self._receive_task(),
                self._input_audio_task(),
                self._output_audio_task(),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise
        finally:
            await self.disconnect()
    
    def _start_audio_streams(self):
        """Initialize PyAudio streams"""
        # Input stream (microphone)
        self.input_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self._input_callback
        )
        
        # Output stream (speaker)
        self.output_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self._output_callback
        )
        
        self.input_stream.start_stream()
        self.output_stream.start_stream()
        logger.info("Audio streams started")
    
    def _input_callback(self, in_data, frame_count, time_info, status):
        """Callback for microphone input"""
        if self.is_running:
            self.input_queue.put(in_data)
        return (in_data, pyaudio.paContinue)
    
    def _output_callback(self, in_data, frame_count, time_info, status):
        """Callback for speaker output"""
        try:
            data = self.output_queue.get_nowait()
            return (data, pyaudio.paContinue)
        except queue.Empty:
            # Return silence if no data available
            return (b'\x00' * CHUNK_SIZE * 2, pyaudio.paContinue)
    
    async def _input_audio_task(self):
        """Read audio from microphone queue"""
        loop = asyncio.get_event_loop()
        while self.is_running:
            try:
                # Get audio data from queue in a non-blocking way
                audio_data = await loop.run_in_executor(
                    None, 
                    self.input_queue.get, 
                    True,  # block
                    0.1    # timeout
                )
                # Put it in send queue for WebSocket
                self.input_queue.task_done()
            except queue.Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Input audio error: {e}")
    
    async def _output_audio_task(self):
        """Write audio to speaker queue"""
        while self.is_running:
            await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
    
    async def _send_audio_task(self):
        """Send audio data to WebSocket server"""
        while self.is_running:
            try:
                # Get audio from input queue
                if not self.input_queue.empty():
                    audio_data = self.input_queue.get_nowait()
                    if self.websocket:
                        await self.websocket.send(audio_data)
                else:
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"Send error: {e}")
                self.is_running = False
    
    async def _receive_task(self):
        """Receive data from WebSocket server"""
        try:
            async for message in self.websocket:
                if isinstance(message, bytes):
                    # Audio data - add to output queue
                    self.output_queue.put(message)
                else:
                    # JSON message (transcript, response text, etc.)
                    data = json.loads(message)
                    await self._handle_json_message(data)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Receive error: {e}")
        finally:
            self.is_running = False
    
    async def _handle_json_message(self, data: dict):
        """Handle JSON messages from server"""
        message_type = data.get("type")
        
        if message_type == "transcript":
            print(f"\n[You said]: {data.get('text', '')}")
        elif message_type == "response_text":
            print(f"[Arnold]: {data.get('text', '')}", end='', flush=True)
        elif message_type == "error":
            logger.error(f"Server error: {data.get('message', 'Unknown error')}")
    
    async def send_text(self, text: str):
        """Send text input to the server"""
        if self.websocket:
            await self.websocket.send(json.dumps({
                "type": "text_input",
                "text": text
            }))
    
    async def disconnect(self):
        """Disconnect and clean up resources"""
        logger.info("Disconnecting...")
        self.is_running = False
        
        # Stop audio streams
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        
        self.audio.terminate()
        
        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
        
        logger.info("Disconnected")


async def main():
    """Main function with keyboard interrupt handling"""
    client = RealtimeVoiceClient()
    
    print("🎙️  Arnold AI - Realtime Voice Assistant")
    print("=" * 50)
    print("Speak naturally to log workouts or ask questions.")
    print("Examples:")
    print("  - 'I just did 10 reps of bench press at 185 pounds'")
    print("  - 'What's my recent workout history?'")
    print("  - 'Show me my squat progress'")
    print("\nPress Ctrl+C to exit")
    print("=" * 50)
    print("\nConnecting to Arnold AI...\n")
    
    try:
        await client.connect()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        await client.disconnect()
    except Exception as e:
        logger.error(f"Error: {e}")
        await client.disconnect()


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\nReceived interrupt signal. Shutting down...")
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass