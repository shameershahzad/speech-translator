from deep_translator.constants import GOOGLE_LANGUAGES_TO_CODES

# GOOGLE_LANGUAGES_TO_CODES maps full lowercase name -> code; build the reverse
# lookup once so every supported language gets a real display name, not just
# the raw code, in the dropdown.
CODE_TO_NAME = {code: name.title() for name, code in GOOGLE_LANGUAGES_TO_CODES.items()}

# A few codes (zh-CN, zh-TW, mni-Mtei) aren't all-lowercase and GoogleTranslator
# rejects them if the case doesn't match exactly, so validation is case-insensitive
# but must resolve back to the original casing rather than lowercasing the code.
LOWER_TO_CODE = {code.lower(): code for code in CODE_TO_NAME}

# Languages Google Translate supports but Google's TTS engine has no voice for
# at all (verified against gtts.lang.tts_langs()) - excluded from the dropdown
# so every listed language offers both translation and spoken playback.
NO_TTS_VOICE = {"mni-Mtei"}


class LanguageService:
    def __init__(self):
        self.supported_language_codes = set(CODE_TO_NAME)

    def validate_language_code(self, lang_code: str) -> bool:
        return lang_code.lower() in LOWER_TO_CODE

    def normalize_language_code(self, lang_code: str) -> str:
        return LOWER_TO_CODE.get(lang_code.lower(), lang_code)

    def get_language_name(self, code: str) -> str:
        return CODE_TO_NAME.get(code, code)

    def list_languages(self):
        entries = [
            {"code": code, "name": name}
            for code, name in CODE_TO_NAME.items()
            if code not in NO_TTS_VOICE
        ]
        return sorted(entries, key=lambda entry: entry["name"])
