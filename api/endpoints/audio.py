import base64
import json
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, websockets
import tempfile
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
import io
import whisper
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()


router = APIRouter(prefix="/audio", tags=["audio"])

voice_id = "ruOXgAPEKXx6RHpsL7YE"
class TTSRequest(BaseModel):
    text: str


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # Placeholder: Replace with actual transcription logic (e.g., OpenAI Whisper, Google STT)
    # For now, just return the filename as the transcript
    # You would typically save the file, send it to a transcription API, and return the result
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")
    # Example: transcript = transcribe_with_whisper(file.file)
    # model = whisper.load_model("turbo")
    with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio.flush()
        model = whisper.load_model("turbo")
        result = model.transcribe(temp_audio.name)
    # result = model.transcribe(file)
    return {"transcript": result["text"]}

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