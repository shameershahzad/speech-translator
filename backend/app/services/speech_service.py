import io
from typing import Optional

import imageio_ffmpeg
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment

# Vercel's serverless Python runtime has no system ffmpeg/ffprobe and no
# apt-get. imageio-ffmpeg ships a portable ffmpeg binary inside the pip
# package itself, so pydub can decode audio without any OS-level install.
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

# pydub normally auto-detects the input codec by shelling out to ffprobe,
# which imageio-ffmpeg doesn't provide. Passing format+codec explicitly skips
# that probe entirely, so the browser must tell us what it actually recorded.
MIME_TYPE_TO_FORMAT_CODEC = {
    "audio/webm": ("webm", "opus"),
    "audio/ogg": ("ogg", "opus"),
    "audio/mp4": ("mp4", "aac"),
    "audio/mpeg": ("mp3", None),
    "audio/wav": ("wav", None),
    "audio/x-wav": ("wav", None),
}


def _resolve_format_and_codec(mime_type: Optional[str]):
    if not mime_type:
        return None, None
    base_type = mime_type.split(";")[0].strip().lower()
    return MIME_TYPE_TO_FORMAT_CODEC.get(base_type, (None, None))


class SpeechRecognitionError(Exception):
    pass


class SpeechService:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def speech_to_text(self, audio_bytes: bytes, mime_type: Optional[str] = None) -> str:
        """Decode browser-recorded audio (via the bundled ffmpeg binary) and transcribe it."""
        audio_format, codec = _resolve_format_and_codec(mime_type)
        try:
            if audio_format == "wav":
                segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
            elif audio_format and codec:
                segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=audio_format, codec=codec)
            elif audio_format:
                segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=audio_format)
            else:
                raise SpeechRecognitionError(f"Unrecognized audio format: {mime_type!r}")
        except SpeechRecognitionError:
            raise
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
