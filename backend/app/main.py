import logging
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from .services.language_service import LanguageService
from .services.speech_service import SpeechRecognitionError, SpeechService
from .services.translation_service import TranslationError, TranslationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("speech-translator")

app = FastAPI(title="Speech Translator API")

DEFAULT_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
]
# ALLOWED_ORIGINS lets a deployed frontend (e.g. a Vercel URL) reach this API
# without hardcoding it - set it as a comma-separated list on the host.
extra_origins = [origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_ORIGINS + extra_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

language_service = LanguageService()
translation_service = TranslationService()
speech_service = SpeechService()


class TranslateRequest(BaseModel):
    text: str
    target_lang: str


class TranslateResponse(BaseModel):
    translated_text: str


class SpeechToTextResponse(BaseModel):
    text: str


@app.get("/api/languages")
def get_languages():
    return language_service.list_languages()


@app.post("/api/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")
    if not language_service.validate_language_code(payload.target_lang):
        raise HTTPException(status_code=400, detail=f"Unsupported language code: {payload.target_lang}")

    try:
        translated = translation_service.translate_text(payload.text, payload.target_lang)
    except TranslationError as exc:
        logger.error("Translation failed: %s", exc)
        raise HTTPException(status_code=502, detail="Translation service failed") from exc

    return TranslateResponse(translated_text=translated)


@app.post("/api/speech-to-text", response_model=SpeechToTextResponse)
async def speech_to_text(audio: UploadFile = File(...), mime_type: str = Form(None), language: str = Form(None)):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    try:
        text = speech_service.speech_to_text(audio_bytes, mime_type, language)
    except SpeechRecognitionError as exc:
        logger.warning("Speech recognition failed: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SpeechToTextResponse(text=text)


@app.get("/api/text-to-speech")
def text_to_speech(text: str, lang: str = "en"):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")

    try:
        audio_bytes = speech_service.text_to_speech(text, lang)
    except Exception as exc:
        logger.error("Text-to-speech failed: %s", exc)
        raise HTTPException(status_code=502, detail="Text-to-speech service failed") from exc

    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.get("/api/health")
def health():
    return {"status": "ok"}
