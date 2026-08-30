import io

import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment


class SpeechRecognitionError(Exception):
    pass


class SpeechService:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def speech_to_text(self, audio_bytes: bytes) -> str:
        """Decode browser-recorded audio (webm/ogg/etc, via ffmpeg) and transcribe it."""
        try:
            segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        except Exception as exc:
            raise SpeechRecognitionError(f"Could not decode audio: {exc}") from exc

        wav_buffer = io.BytesIO()
        segment.set_channels(1).set_frame_rate(16000).export(wav_buffer, format="wav")
        wav_buffer.seek(0)

        with sr.AudioFile(wav_buffer) as source:
            audio = self.recognizer.record(source)

        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            raise SpeechRecognitionError("Could not understand the audio")
        except sr.RequestError as exc:
            raise SpeechRecognitionError(f"Speech recognition service error: {exc}") from exc

    def text_to_speech(self, text: str, lang: str) -> bytes:
        buffer = io.BytesIO()
        tts = gTTS(text=text, lang=lang)
        tts.write_to_fp(buffer)
        return buffer.getvalue()
