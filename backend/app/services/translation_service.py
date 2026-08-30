import time
from functools import lru_cache

from deep_translator import GoogleTranslator

# When Google Translate's web frontend is rate-limiting/blocking scraped
# requests, it serves a generic HTTP 200 error page instead of a translation.
# deep_translator doesn't detect this as a failure, so we have to.
_ERROR_PAGE_MARKERS = ("that's an error", "please try again later")


class TranslationError(Exception):
    pass


def _looks_like_error_page(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _ERROR_PAGE_MARKERS)


class TranslationService:
    @lru_cache(maxsize=200)
    def translate_text(self, text: str, target_lang: str) -> str:
        last_error = None
        for attempt in range(2):
            try:
                translator = GoogleTranslator(source="auto", target=target_lang)
                translated = translator.translate(text)
            except Exception as exc:
                last_error = exc
            else:
                if translated and not _looks_like_error_page(translated):
                    return translated
                last_error = TranslationError("Translator returned an error page instead of a translation")

            if attempt == 0:
                time.sleep(0.6)

        raise TranslationError(str(last_error))
