import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.endpoints import audio, workouts, realtime_audio
from db.database import engine, Base
from dotenv import load_dotenv

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Arnold.ai Workout Tracker API",
    description="MVP API for tracking workout sets with voice integration",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workouts.router)
app.include_router(audio.router)
app.include_router(realtime_audio.router)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to Arnold.ai Workout Tracker API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    PORT = 8000
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)