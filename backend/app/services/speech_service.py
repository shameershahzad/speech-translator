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

# recognize_google needs a full BCP-47 locale, not a bare language code -
# without one it silently assumes en-US, which is why speech in any other
# language came back empty, garbled, or transliterated into English. This
# used to only cover ~65 of the 133 languages in the "Speak in" dropdown;
# anything outside that set (e.g. Sindhi, Yoruba, Pashto, Somali) fell
# through to the bare 2-letter code, which Google's speech API rejects -
# so the bug wasn't Urdu-specific, it affected every unmapped language.
# Covers every code the language picker offers.
SPEECH_RECOGNITION_LOCALES = {
    "en": "en-US", "ur": "ur-PK", "hi": "hi-IN", "ar": "ar-SA", "es": "es-ES",
    "fr": "fr-FR", "de": "de-DE", "it": "it-IT", "pt": "pt-PT", "ru": "ru-RU",
    "zh-CN": "zh-CN", "zh-TW": "zh-TW", "ja": "ja-JP", "ko": "ko-KR", "tr": "tr-TR",
    "bn": "bn-BD", "ta": "ta-IN", "te": "te-IN", "ml": "ml-IN", "mr": "mr-IN",
    "gu": "gu-IN", "kn": "kn-IN", "pa": "pa-IN", "th": "th-TH", "vi": "vi-VN",
    "id": "id-ID", "ms": "ms-MY", "nl": "nl-NL", "pl": "pl-PL", "uk": "uk-UA",
    "el": "el-GR", "iw": "iw-IL", "fa": "fa-IR", "sw": "sw-KE", "am": "am-ET",
    "af": "af-ZA", "sv": "sv-SE", "no": "nb-NO", "da": "da-DK", "fi": "fi-FI",
    "cs": "cs-CZ", "sk": "sk-SK", "ro": "ro-RO", "hu": "hu-HU", "bg": "bg-BG",
    "hr": "hr-HR", "sr": "sr-RS", "sl": "sl-SI", "lt": "lt-LT", "lv": "lv-LV",
    "et": "et-EE", "is": "is-IS", "ga": "ga-IE", "cy": "cy-GB", "km": "km-KH",
    "ne": "ne-NP", "si": "si-LK", "mn": "mn-MN", "kk": "kk-KZ", "uz": "uz-UZ",
    "az": "az-AZ", "ka": "ka-GE", "hy": "hy-AM", "sq": "sq-AL", "mk": "mk-MK",
    "bs": "bs-BA", "zu": "zu-ZA",
    "ak": "ak-GH", "as": "as-IN", "ay": "ay-BO", "be": "be-BY", "bho": "hi-IN",
    "bm": "fr-ML", "ca": "ca-ES", "ceb": "fil-PH", "ckb": "ar-IQ", "co": "fr-FR",
    "doi": "hi-IN", "dv": "dv-MV", "ee": "ee-GH", "eo": "eo", "eu": "eu-ES",
    "fy": "fy-NL", "gd": "gd-GB", "gl": "gl-ES", "gn": "gn-PY", "gom": "hi-IN",
    "ha": "ha-NG", "haw": "haw-US", "hmn": "hmn", "ht": "fr-HT", "ig": "ig-NG",
    "ilo": "fil-PH", "jw": "jv-ID", "kri": "en-SL", "ku": "ku-TR", "ky": "ky-KG",
    "la": "la", "lb": "lb-LU", "lg": "lg-UG", "ln": "ln-CD", "lo": "lo-LA",
    "lus": "hi-IN", "mai": "hi-IN", "mg": "mg-MG", "mi": "mi-NZ", "mni-Mtei": "hi-IN",
    "mt": "mt-MT", "my": "my-MM", "nso": "en-ZA", "ny": "en-MW", "om": "om-ET",
    "or": "or-IN", "ps": "ps-AF", "qu": "qu-PE", "rw": "rw-RW", "sa": "sa-IN",
    "sd": "sd-PK", "sm": "sm-WS", "sn": "sn-ZW", "so": "so-SO", "st": "en-ZA",
    "su": "su-ID", "tg": "tg-TJ", "ti": "ti-ET", "tk": "tk-TM", "tl": "fil-PH",
    "ts": "en-ZA", "tt": "tt-RU", "ug": "ug-CN", "xh": "xh-ZA", "yi": "yi",
    "yo": "yo-NG",
}


def _resolve_locale(language: Optional[str]) -> Optional[str]:
    if not language:
        return None
    return SPEECH_RECOGNITION_LOCALES.get(language, language)


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

    def speech_to_text(self, audio_bytes: bytes, mime_type: Optional[str] = None, language: Optional[str] = None) -> str:
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
            return self.recognizer.recognize_google(audio, language=_resolve_locale(language) or "en-US")
        except sr.UnknownValueError:
            raise SpeechRecognitionError("Could not understand the audio")
        except sr.RequestError as exc:
            raise SpeechRecognitionError(f"Speech recognition service error: {exc}") from exc

    def text_to_speech(self, text: str, lang: str) -> bytes:
        buffer = io.BytesIO()
        tts = gTTS(text=text, lang=lang)
        tts.write_to_fp(buffer)
        return buffer.getvalue()
