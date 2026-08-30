import speech_recognition as sr
from deep_translator.constants import GOOGLE_LANGUAGES_TO_CODES
from deep_translator import GoogleTranslator
from gtts import gTTS
import pygame
import tempfile
import pyttsx3
import os
import sys
import uuid
import logging
import json
import threading
import time
from typing import Dict, Optional, Any, List, Set, Tuple
from enum import Enum
from functools import lru_cache

# ============================================================================
# Configuration
# ============================================================================

# Force UTF-8 output so emoji in menus/messages don't crash on terminals
# that default to a non-UTF-8 codepage (e.g. Windows cp1252).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("speech_assistant.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("SpeechAssistant")

# ============================================================================
# Constants & Enums
# ============================================================================

class MenuOption(Enum):
    """Enum for menu options to avoid magic strings"""
    TRANSLATE = "1"
    EXIT = "2"
    VIEW_LANGUAGES = "1"
    SELECT_LANGUAGE = "2"
    RETURN = "3"
    EXIT_CODE = "4"
    
# ============================================================================
# Service Classes
# ============================================================================

class LanguageService:
    """Encapsulates language-related functionality"""
    
    def __init__(self):
        """Initialize language service with supported languages"""
        self.supported_languages = GOOGLE_LANGUAGES_TO_CODES
        self.supported_language_codes = set(GOOGLE_LANGUAGES_TO_CODES.values())
        self.language_names = {
            'en': 'English', 'ar': 'Arabic', 'es': 'Spanish', 'fr': 'French',
            'de': 'German', 'hi': 'Hindi', 'it': 'Italian', 'ja': 'Japanese',
            'ko': 'Korean', 'ru': 'Russian', 'zh-CN': 'Chinese (Simplified)',
            'zh-TW': 'Chinese (Traditional)'
        }
    
    def validate_language_code(self, lang_code: str) -> bool:
        """Validate if the language code is supported."""
        return lang_code.lower() in self.supported_language_codes
    
    def get_language_name(self, code: str) -> str:
        """Get language name from code with fallback"""
        return self.language_names.get(code.lower(), code)
    
    def display_available_languages(self) -> None:
        """Display languages in a formatted way"""
        print("\n" + "=" * 50)
        print("📋 AVAILABLE LANGUAGES 📋".center(50))
        print("=" * 50)
        
        # Create a sorted list of tuples (code, name) for display
        lang_list = sorted([(code, name) for code, name in self.language_names.items()], 
                           key=lambda x: x[1])  # Sort by language name
        
        # Display in a cleaner format with columns
        for i, (code, name) in enumerate(lang_list):
            print(f"  {code:<6}: {name:<20}", end="")
            if (i + 1) % 3 == 0 or i == len(lang_list) - 1:  # 3 columns or last item
                print()
        print("-" * 50)


class TranslationService:
    """Handles translation functionality"""
    
    def __init__(self, language_service: LanguageService):
        """Initialize with dependency on language service"""
        self.language_service = language_service
        
    @lru_cache(maxsize=100)  # Cache recent translations
    def translate_text(self, text: str, target_lang: str) -> Optional[str]:
        """Translate text to target language with caching"""
        try:
            translator = GoogleTranslator(source='auto', target=target_lang.lower())
            translated = translator.translate(text)
            return translated
        except Exception as e:
            logger.error(f"Translation error: {e}")
            print(f"❌ Translation error: {e}")
            return None


class SpeechService:
    """Handles speech recognition and text-to-speech"""
    
    def __init__(self):
        """Initialize speech recognition and TTS engines"""
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')
        
    def recognize_speech(self, timeout: int = 5) -> Optional[str]:
        """Record and recognize speech with progress indicator"""
        try:
            with sr.Microphone() as source:
                print("\nAdjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Add a progress indicator while listening
                print("🎤 Speak now...")
                
                # Start a thread for the spinner
                stop_spinner = threading.Event()
                spinner_thread = threading.Thread(
                    target=self._show_spinner, 
                    args=(stop_spinner,)
                )
                spinner_thread.daemon = True
                spinner_thread.start()
                
                try:
                    audio = self.recognizer.listen(source, timeout=timeout)
                finally:
                    stop_spinner.set()  # Stop the spinner
                    spinner_thread.join(timeout=1)
                
                text = self.recognizer.recognize_google(audio)
                print(f"Recognized Text: {text}")
                return text
        except sr.WaitTimeoutError:
            logger.warning("No speech detected within timeout period")
            print("❌ No speech detected within timeout period")
        except sr.UnknownValueError:
            logger.warning("Could not understand the audio")
            print("❌ Could not understand the audio")
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            print(f"❌ Speech recognition error: {e}")
        except Exception as e:
            logger.error(f"An error occurred during speech recognition: {e}")
            print(f"❌ An error occurred: {e}")
        return None
    
    def _show_spinner(self, stop_event):
        """Shows a spinner while recording"""
        spinner = "|/-\\"
        i = 0
        while not stop_event.is_set():
            i = (i + 1) % len(spinner)
            print(f"\rListening... {spinner[i]}", end="", flush=True)
            time.sleep(0.1)
        print("\r", end="")  # Clear the spinner line
    
    def speak_text(self, text: str, lang: str = 'en') -> bool:
        """Text-to-speech with status indicator"""
        try:
            filename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.mp3")
            tts = gTTS(text=text, lang=lang.lower())
            print("🔊 Generating speech...", end="", flush=True)
            tts.save(filename)
            print("\r🔊 Playing speech...      ", end="", flush=True)
            
            pygame.mixer.init()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                continue

            print("\r✅ Speech completed       ")
            pygame.mixer.quit()  # cleanup
            os.remove(filename)  # manually delete temp file after playing
            return True
        except Exception as e:
            logger.error(f"Text-to-speech error: {e}")
            print(f"\r❌ Text-to-speech error: {e}")
            return False


class UserInterface:
    """Handles all user interaction"""
    
    def __init__(self):
        """Initialize UI with required services"""
        self.language_service = LanguageService()
        self.translation_service = TranslationService(self.language_service)
        self.speech_service = SpeechService()
    
    def display_main_menu(self) -> None:
        """Display the main menu with styling"""
        print("\n" + "=" * 50)
        print("📱 MAIN MENU 📱".center(50))
        print("=" * 50)
        print("  1. Real-Time Speech Translation")
        print("  2. Exit")
        print("-" * 50)
    
    def display_translator_menu(self) -> None:
        """Display the translator menu with styling"""
        print("\n" + "=" * 50)
        print("🌐 TRANSLATOR OPTIONS 🌐".center(50))
        print("=" * 50)
        print("  1. View all available languages")
        print("  2. Select language for translation")
        print("  3. Return to main menu")
        print("  4. Exit application")
        print("-" * 50)
    
    def get_user_choice(self, prompt: str = "Enter your choice: ") -> str:
        """Get user input with consistent styling"""
        return input(f"➤ {prompt}")
    
    def show_message(self, message: str, message_type: str = "info") -> None:
        """Display a message with appropriate styling"""
        if message_type == "error":
            print(f"❌ {message}")
        elif message_type == "success":
            print(f"✅ {message}")
        elif message_type == "warning":
            print(f"⚠️ {message}")
        else:
            print(f"ℹ️ {message}")


# ============================================================================
# Main Application Class
# ============================================================================

class SpeechAssistant:
    """Main application class with improved organization"""
    
    def __init__(self):
        """Initialize speech assistant with required components"""
        self.ui = UserInterface()
        self.language_service = self.ui.language_service
        self.translation_service = self.ui.translation_service
        self.speech_service = self.ui.speech_service
        
        # Load config if it exists
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file if it exists"""
        config_path = "speech_assistant_config.json"
        default_config = {
            "default_language": "en",
            "speech_rate": 150,
            "timeout": 5
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return default_config
    
    def available_languages(self) -> None:
        """Display languages and proceed to translation"""
        self.language_service.display_available_languages()
        self.translate()
    
    def translate(self) -> None:
        """Enhanced translation workflow"""
        target_lang = self.ui.get_user_choice("Enter target language code (or 'b' to go back): ").lower()
        if target_lang == 'b':
            return
                
        if not self.language_service.validate_language_code(target_lang):
            self.ui.show_message(f"Invalid language code: {target_lang}", "error")
            return
            
        language_name = self.language_service.get_language_name(target_lang)
        self.ui.show_message(f"Selected language: {language_name}", "success")
        print("Speak in any language, and I'll translate to your selected language.")
        
        while True:
            spoken_text = self.speech_service.recognize_speech(timeout=self.config["timeout"])
            
            if spoken_text:
                # Show "Translating..." message with spinner
                print("🔄 Translating...", end="", flush=True)
                translated_text = self.translation_service.translate_text(spoken_text, target_lang)
                print("\r" + " " * 30, end="\r")  # Clear the line properly
                
                if translated_text:
                    language_name = self.language_service.get_language_name(target_lang)
                    print(f"📝 Translated ({language_name}): {translated_text}")
                    self.speech_service.speak_text(translated_text, target_lang)
                    
                    continue_translating = True
                    while continue_translating:
                        # Display options with clear instruction to enter a single character
                        print("\nFor Next Step:")
                        print("  (c) Change language")
                        print("  (n) New translation")
                        print("  (p) Pronounce again")
                        print("  (g) Go back")
                        print("  (e) Exit")
                        
                        # Use strip() to remove any whitespace and handle empty inputs
                        action = self.ui.get_user_choice("Enter option [c/n/p/g/e]: ").strip().lower()
                        
                        # If empty input, prompt again
                        if not action:
                            print("Please enter an option.")
                            continue
                            
                        # Only use the first character if multiple characters entered
                        action = action[0]
                        
                        if action == 'c':
                            return self.translate()
                        elif action == 'g':
                            return
                        elif action == 'n':
                            continue_translating = False
                        elif action == 'e':
                            self.ui.show_message("Thank you for using Speech Translator!", "success")
                            sys.exit(0)
                        elif action == 'p':
                            self.speech_service.speak_text(translated_text, target_lang)
                        else:
                            self.ui.show_message(f"Invalid option '{action}'! Please try again.", "warning")
            else:
                retry = self.ui.get_user_choice("Would you like to try speaking again? (y/n): ").lower()
                if retry != 'y':
                    return
        
    def translator(self) -> None:
        """Enhanced translator menu"""
        while True:
            self.ui.display_translator_menu()
            choice = self.ui.get_user_choice()
            
            if choice == MenuOption.VIEW_LANGUAGES.value:
                self.available_languages()
            elif choice == MenuOption.SELECT_LANGUAGE.value:
                self.translate()
            elif choice == MenuOption.RETURN.value:
                return
            elif choice == MenuOption.EXIT_CODE.value:
                self.ui.show_message("Thank you for using Speech Translator!", "success")
                sys.exit(0)
            else:
                self.ui.show_message("Invalid choice. Please try again.", "warning")
                                                  
    def start(self) -> None:
        """Application entry point with welcome message"""
        print("\n" + "*" * 60)
        print("🌍 Welcome to Real-Time Speech Translation 🌍".center(60))
        print("*" * 60)
        
        while True:
            self.ui.display_main_menu()
            choice = self.ui.get_user_choice()
            
            if choice == MenuOption.TRANSLATE.value:
                self.translator()
            elif choice == MenuOption.EXIT.value:
                self.ui.show_message("Thank you for using Speech Translator!", "success")
                sys.exit(0)
            else:
                self.ui.show_message("Invalid choice. Please try again.", "warning")


# ============================================================================
# Application Entry Point
# ============================================================================

def main():
    """Application entry point with improved error handling"""
    try:
        # Check for required dependencies
        required_modules = ["speech_recognition", "deep_translator", "gtts", "pygame"]
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            print("❌ The following required modules are not installed:")
            for module in missing_modules:
                print(f"   - {module}")
            print("\nPlease install them using:")
            print(f"pip install {' '.join(missing_modules)}")
            sys.exit(1)
                
        # Start the application
        assistant = SpeechAssistant()
        assistant.start()
        
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        print(f"\nAn unexpected error occurred: {e}")
        print("Check the log file for more details.")
    finally:
        print("\nExiting Speech Assistant...")
        try:
            pygame.mixer.quit()  # Ensure pygame is properly closed
        except:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()