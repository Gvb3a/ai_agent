from deep_translator import GoogleTranslator, single_detection
from ...config.config import load_config

config = load_config()
detect_language_api_key = config.api.detect_language_key


def detect_language(text: str) -> str:
    try:
        return single_detection(text=text, api_key=detect_language_api_key, detailed=False)
    except:
        return 'en'
    

def translate(text: str, target_language: str = 'en', source_language: str = 'auto') -> str:   # TODO: ggcs translator
    translated_text = GoogleTranslator(source=source_language, target=target_language).translate(text)
    return translated_text