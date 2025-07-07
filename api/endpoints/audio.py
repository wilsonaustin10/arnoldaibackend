import base64
import json
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, websockets, Depends
import tempfile
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
import io
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from typing import List, Dict, Optional

from services.voice_agent import VoiceAgent
from services.workout_service import WorkoutService

load_dotenv()


router = APIRouter(prefix="/audio", tags=["audio"])

voice_id = "ruOXgAPEKXx6RHpsL7YE"
class TTSRequest(BaseModel):
    text: str

class ConversationRequest(BaseModel):
    conversation_history: Optional[List[Dict]] = None


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client with workaround for compatibility issues
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except TypeError:
    # Fallback for compatibility issues
    import openai
    openai.api_key = OPENAI_API_KEY
    # Create a wrapper to maintain compatibility
    class OpenAIWrapper:
        class Audio:
            class Transcriptions:
                @staticmethod
                def create(model, file, response_format):
                    # Use the older API format
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                        tmp.write(file.read())
                        tmp_path = tmp.name
                    
                    with open(tmp_path, 'rb') as audio_file:
                        transcript = openai.Audio.transcribe(model, audio_file)
                    
                    return transcript.get('text', '')
            
            transcriptions = Transcriptions()
        
        class Chat:
            class Completions:
                @staticmethod
                def create(**kwargs):
                    response = openai.ChatCompletion.create(**kwargs)
                    return response
            
            completions = Completions()
        
        audio = Audio()
        chat = Chat()
    
    openai_client = OpenAIWrapper()

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # Use OpenAI's Whisper API for transcription
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")
    
    try:
        # Read the audio file
        audio_data = await file.read()
        
        # Create a file-like object for OpenAI API
        audio_file = io.BytesIO(audio_data)
        audio_file.name = file.filename or "audio.wav"
        
        # Use OpenAI's Whisper API
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
        
        return {"transcript": transcript}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/tts")
async def generate_audio(request: TTSRequest):
    elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    # # Generate speech from text
    audio_iter = elevenlabs.text_to_speech.convert(
        text=request.text,
        voice_id=voice_id,
        model_id="eleven_flash_v2_5",  # or another model if you prefer
        # output_format="wav_44100"
    )

    # Return the file as a response
    # temp_audio_path = "assets/sample.wav"
    # with open(temp_audio_path, "rb") as f:
    #     audio_bytes = f.read()
    # # Save to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:

        for chunk in audio_iter:
            temp_audio.write(chunk)
        temp_audio_path = temp_audio.name
        
    headers = {"Content-Disposition": "attachment; filename=output.wav"}
    return FileResponse(temp_audio_path, media_type="audio/wav", headers=headers)

@router.post("/process-voice-command")
async def process_voice_command(
    file: UploadFile = File(...),
    workout_service: WorkoutService = Depends()
):
    """Process voice command: STT -> AI Processing -> TTS"""
    
    # Step 1: Transcribe the audio
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")
    
    try:
        # Transcribe audio
        audio_data = await file.read()
        audio_file = io.BytesIO(audio_data)
        audio_file.name = file.filename or "audio.wav"
        
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
        
        # Step 2: Process with AI agent
        voice_agent = VoiceAgent(openai_client, workout_service)
        ai_response = voice_agent.process_voice_command(transcript)
        
        # Step 3: Convert response to speech
        elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio_iter = elevenlabs.text_to_speech.convert(
            text=ai_response,
            voice_id=voice_id,
            model_id="eleven_flash_v2_5"
        )
        
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            for chunk in audio_iter:
                temp_audio.write(chunk)
            temp_audio_path = temp_audio.name
        
        # Return both transcript and audio response
        return JSONResponse(
            content={
                "transcript": transcript,
                "ai_response": ai_response,
                "audio_url": f"/audio/download/{temp_audio_path.split('/')[-1]}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.post("/chat")
async def chat_with_agent(
    request: dict,
    workout_service: WorkoutService = Depends()
):
    """Text-based chat with the workout agent"""
    
    try:
        text = request.get("text", "")
        conversation_history = request.get("conversation_history", [])
        
        voice_agent = VoiceAgent(openai_client, workout_service)
        response = voice_agent.process_voice_command(
            text, 
            conversation_history=conversation_history
        )
        
        return {"response": response}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")