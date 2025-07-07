# Arnold.ai - Voice-Powered AI Workout Assistant

Arnold.ai is a voice-powered workout tracking assistant that uses OpenAI for natural language understanding and ElevenLabs for voice synthesis. Track your workouts with simple voice commands!

## Features

- **Voice Commands**: Tell Arnold about your workouts using natural language
- **Speech-to-Text**: Powered by OpenAI Whisper
- **AI Understanding**: OpenAI GPT-4 processes workout commands with workout-specific knowledge
- **Text-to-Speech**: ElevenLabs provides natural voice responses
- **Workout Tracking**: Store and query your workout history
- **Smart Recognition**: Understands various exercise names and variations

## Architecture

```
┌─────────────────────────────┐
│   Voice Input (Audio)       │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│   STT (OpenAI Whisper)      │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│   AI Agent (OpenAI GPT-4)   │
│   - Natural Language        │
│   - Function Calling        │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│   Workout Service Layer     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│   Database (SQLite)         │
└─────────────────────────────┘
               ▼
┌─────────────────────────────┐
│   TTS (ElevenLabs)          │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│   Voice Response (Audio)    │
└─────────────────────────────┘
```

## Quick Start

1. Install system dependencies:
```bash
# macOS
brew install portaudio

# Ubuntu/Debian
sudo apt-get install portaudio19-dev
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys:
# - OPENAI_API_KEY
# - ELEVENLABS_API_KEY
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the server:
```bash
python main.py
```

6. Access API documentation:
- http://localhost:8000/docs

## API Endpoints

### Voice Endpoints
- `POST /audio/process-voice-command` - Process voice command (audio file → AI response)
- `POST /audio/chat` - Text-based chat with the workout agent
- `POST /audio/transcribe` - Convert audio to text (STT only)
- `POST /audio/tts` - Convert text to speech (TTS only)

### Workout Endpoints  
- `POST /workouts/` - Log a new workout set
- `GET /workouts/?exercise={name}&date={date}` - Query workouts by exercise
- `GET /workouts/recent?limit={n}` - Get recent workouts

## Usage Examples

### Voice Command (Audio Upload)
```bash
# Upload an audio file with a workout command
curl -X POST "http://localhost:8000/audio/process-voice-command" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@workout_command.wav"

# Response:
{
  "transcript": "I just did 10 reps of bench press with 135 pounds",
  "ai_response": "Great job! I've logged 10 reps of bench press at 135 pounds. Keep up the good work!",
  "audio_url": "/audio/download/output_123.wav"
}
```

### Text Chat
```bash
curl -X POST "http://localhost:8000/audio/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I just finished 3 sets of squats. First set was 8 reps at 225, second was 6 reps at 245, and third was 4 reps at 265"
  }'

# Response:
{
  "response": "Excellent pyramid set on squats! I've logged all three sets for you:\n- Set 1: 8 reps at 225 lbs\n- Set 2: 6 reps at 245 lbs\n- Set 3: 4 reps at 265 lbs\nThat's some serious weight! Your progressive overload is looking strong."
}
```

### Example Voice Commands Arnold Understands
- "I just did 10 reps of bench press with 135 pounds"
- "Log 3 sets of squats: 8 at 225, 6 at 245, and 4 at 265"
- "What did I bench press last week?"
- "Show me my recent workouts"
- "How much have I been deadlifting lately?"
- "I completed 12 reps of dumbbell curls with 30 pound dumbbells"

## Database Schema

- `id` (INTEGER) - Primary key
- `workout_date` (DATE) - Date of workout
- `exercise` (TEXT) - Exercise name
- `reps` (INTEGER) - Number of repetitions
- `weight_lbs` (REAL) - Weight in pounds
- `created_at` (TIMESTAMP) - Record creation time

## Development Notes

- **Database**: SQLite for local development, configurable via `DATABASE_URL`
- **Migrations**: Alembic handles database schema changes
- **API Docs**: FastAPI auto-generates interactive documentation at `/docs`
- **Voice Models**: 
  - STT: OpenAI Whisper
  - LLM: OpenAI GPT-4 with function calling
  - TTS: ElevenLabs with configurable voice

## Supported Exercises

Arnold recognizes many exercise variations including:
- **Chest**: bench press, incline/decline bench, dumbbell press, flyes
- **Back**: deadlifts, rows, pull-ups, lat pulldowns
- **Legs**: squats, lunges, leg press, calf raises
- **Shoulders**: overhead press, lateral raises, face pulls
- **Arms**: bicep curls, tricep extensions, hammer curls
- **Core**: planks, crunches, leg raises

## Future Enhancements

- User authentication and multi-user support
- Workout program tracking and suggestions
- Progress analytics and visualizations
- Integration with fitness wearables
- Real-time form checking via video