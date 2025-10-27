import os
import PIL.Image
from typing import Literal
from google import genai, generativeai
from ..tools.file_utils import files_to_text
from ...config.config import load_config
from ...config.logger import logger


config = load_config()

os.environ["GOOGLE_API_KEY"] = config.api.gemini_key
os.environ['GRPC_DNS_RESOLVER'] = 'native'
generativeai.configure(api_key=os.environ['GOOGLE_API_KEY'])

google_models = {
    "gemini-2.5-flash": generativeai.GenerativeModel("gemini-2.5-flash"),
    "gemini-2.5-pro": generativeai.GenerativeModel("gemini-2.5-pro"),
    "gemini-2.5-flash-lite": generativeai.GenerativeModel("gemini-2.5-flash-lite")
}
google_model_flash = generativeai.GenerativeModel("gemini-2.5-flash")

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def genai_api(messages: list[dict] | str, files: list | str = [], model: Literal["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"] = "gemini-2.5-flash") -> str:
    if type(messages) == str:
        user_message = messages
        formatted_history = []

    else:  # google is a bit special and to keep everything in the same style I do the transformation here.
        user_message = messages[-1]['content']
        history = messages[:-1]

        formatted_history = []
        for message in history:
            role = 'user' if message['role'] in ['user', 'system'] else 'model' 
            content = message['content']
            formatted_history.append({"role": role, "parts": content})

    google_model = google_models.get(model, google_model_flash)
    chat = google_model.start_chat(history=formatted_history)
    
    image_files = []
    for file_path in files:
        if file_path.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            image_files.append(PIL.Image.open(file_path))
        else:
            user_message += files_to_text(file_path)

    if image_files:
        response = chat.send_message([user_message] + image_files)
    else:
        response = chat.send_message(user_message)

    logger.info(f"Query: {user_message}, Response: {response.text}")
    return response.text

