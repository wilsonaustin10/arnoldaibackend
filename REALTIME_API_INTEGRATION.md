# OpenAI Realtime API Integration for Arnold AI

## Overview

This document describes the integration of OpenAI's Realtime API into the Arnold AI voice agent application. The integration provides ultra-low latency, natural voice conversations with sub-100ms response times.

## Architecture Changes

### Previous Architecture (Sequential)
```
Audio Input → HTTP → STT (Whisper) → HTTP → LLM (GPT-4) → HTTP → TTS (ElevenLabs) → Audio Output
Total Latency: 300-500ms+
```

### New Architecture (Realtime WebSocket)
```
Audio Input ←→ WebSocket ←→ OpenAI Realtime API (STT + LLM + TTS integrated) ←→ Workout Service
Total Latency: <100ms
```

## Key Features

### 1. **Bidirectional Audio Streaming**
- Continuous WebSocket connection for real-time audio exchange
- PCM16 format at 24kHz sample rate
- Automatic voice activity detection (VAD)

### 2. **Integrated Speech Processing**
- Speech-to-text, LLM processing, and text-to-speech in a single API
- Preserves tonal and inflectional cues
- Natural interruption handling

### 3. **Function Calling**
- Seamless integration with workout logging functions
- Real-time database operations
- Maintains conversation context

### 4. **Robust Error Handling**
- Automatic reconnection with exponential backoff
- Connection health monitoring with heartbeat
- Graceful degradation on failures

## Implementation Details

### Core Components

#### 1. **RealtimeVoiceAgentEnhanced** (`services/realtime_voice_agent_enhanced.py`)
- Main service class for Realtime API integration
- Handles WebSocket connection management
- Implements function calling for workout operations
- Features:
  - Automatic reconnection
  - Performance metrics tracking
  - Audio buffering for smooth playback
  - Event-driven architecture

#### 2. **Realtime Audio Endpoints** (`api/endpoints/realtime_audio.py`)
- WebSocket endpoint: `/realtime/stream`
- Manages bidirectional audio streaming
- Handles both audio and text inputs
- Features:
  - Concurrent audio processing
  - Real-time transcription feedback
  - Low-latency response streaming

#### 3. **Realtime Client** (`realtime_client.py`)
- Python client for testing and demonstration
- PyAudio integration for microphone/speaker access
- WebSocket client implementation
- Features:
  - Real-time audio capture and playback
  - Text fallback support
  - Graceful shutdown handling

### API Endpoints

#### WebSocket: `/realtime/stream`
Establishes a persistent WebSocket connection for real-time audio streaming.

**Client → Server Messages:**
- Binary: PCM16 audio data at 24kHz
- JSON: Control commands (e.g., `{"type": "text_input", "text": "..."}`)

**Server → Client Messages:**
- Binary: PCM16 audio responses
- JSON: Transcripts, response text, errors

#### POST: `/realtime/session/start`
Initiates a new session and returns connection configuration.

**Response:**
```json
{
  "status": "ready",
  "websocket_url": "/realtime/stream",
  "audio_format": {
    "encoding": "pcm16",
    "sample_rate": 24000,
    "channels": 1
  }
}
```

## Usage Examples

### 1. Using the Python Client
```bash
# Make sure the server is running
python main.py

# In another terminal, run the client
python realtime_client.py
```

### 2. WebSocket Connection (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:8000/realtime/stream');

// Send audio data
ws.send(audioBuffer);

// Handle responses
ws.onmessage = (event) => {
  if (event.data instanceof Blob) {
    // Audio response
    playAudio(event.data);
  } else {
    // JSON message
    const data = JSON.parse(event.data);
    console.log(data);
  }
};
```

### 3. Function Calling Examples

The system supports these voice commands:
- "I just did 10 reps of bench press at 185 pounds"
- "Show me my recent workouts"
- "What's my squat progress?"

## Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key
```

### Session Configuration
The Realtime API session is configured with:
- Model: `gpt-4o-realtime-preview`
- Voice: `alloy` (customizable)
- Audio format: PCM16 at 24kHz
- VAD threshold: 0.5
- Silence duration: 200ms

## Performance Optimizations

### 1. **Audio Buffering**
- 100ms audio buffer for smooth playback
- Prevents audio stuttering
- Automatic buffer management

### 2. **Connection Management**
- Persistent WebSocket reduces connection overhead
- Heartbeat monitoring (30s intervals)
- Automatic reconnection on failure

### 3. **Concurrent Processing**
- Asynchronous audio handling
- Non-blocking I/O operations
- Parallel event processing

## Error Handling

### Reconnection Strategy
```python
ReconnectConfig(
    max_retries=5,
    initial_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0
)
```

### Error Types Handled
1. **Connection Errors**: Automatic reconnection
2. **API Errors**: Logged and reported to client
3. **Function Call Errors**: Graceful fallback responses
4. **Audio Processing Errors**: Buffer management and recovery

## Monitoring and Metrics

The system tracks:
- Connection uptime
- Messages sent/received
- Error count
- Reconnection attempts
- Function call count
- Average latency

Access metrics:
```python
metrics = voice_agent.get_metrics()
```

## Migration Guide

### From Old API to Realtime API

1. **Update Dependencies**
   ```bash
   pip install openai>=1.93.2 websockets
   ```

2. **Replace Audio Endpoints**
   - Old: `/audio/process-voice-command`
   - New: `/realtime/stream` (WebSocket)

3. **Update Client Code**
   - Switch from HTTP requests to WebSocket
   - Handle streaming responses
   - Implement continuous audio capture

### Backward Compatibility
The original HTTP endpoints remain available:
- `/audio/transcribe` - STT only
- `/audio/tts` - TTS only
- `/audio/process-voice-command` - Full pipeline (higher latency)

## Best Practices

1. **Audio Quality**
   - Use noise cancellation on client side
   - Maintain consistent audio levels
   - Handle network jitter with buffering

2. **Connection Management**
   - Implement client-side reconnection
   - Monitor connection health
   - Handle graceful shutdowns

3. **Error Handling**
   - Log all errors for debugging
   - Provide user feedback on failures
   - Implement fallback mechanisms

## Troubleshooting

### Common Issues

1. **Connection Drops**
   - Check network stability
   - Verify API key validity
   - Monitor rate limits

2. **Audio Quality Issues**
   - Verify audio format (PCM16, 24kHz)
   - Check microphone permissions
   - Test with different audio devices

3. **High Latency**
   - Check network latency
   - Verify server location
   - Monitor CPU usage

### Debug Mode
Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. **Multi-language Support**
   - Automatic language detection
   - Real-time translation

2. **Advanced Features**
   - Speaker diarization
   - Emotion detection
   - Custom voice models

3. **Performance Improvements**
   - WebRTC integration
   - Edge computing support
   - Adaptive bitrate

## References

- [OpenAI Realtime API Documentation](https://platform.openai.com/docs/guides/realtime)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/docs/)