from typing import Literal
from datetime import datetime
from .groq import groq_api
from .google import genai_api
from ..tools.file_utils import files_to_text
from ...config.logger import logger


def llm_api(messages: list[dict] | str, files: str | list = [], provider: Literal['groq', 'google'] = 'groq'):
    if type(messages) == str:
        messages = [{'role': 'user', 'content': messages}]

    if type(files) == str:
        files = [files]

    messages[-1]["content"] += files_to_text([file for file in files if not file.endswith(('.png', '.jpg', '.jpeg', '.webp'))])
    files = list(filter(lambda x: x.endswith(('.png', '.jpg', '.jpeg', '.webp')), files))
    start_time = datetime.now()

    
    if provider == 'google' or files:
        try:
            answer = genai_api(messages, files)
        except Exception as e:
            logger.error(f'google error: {e}', exc_info=True)
            answer = groq_api(messages)
    
    else:
        try:
            answer = groq_api(messages)
        except Exception as e:
            logger.error(f'groq error: {e}', exc_info=True)
            answer = genai_api(messages)

    logger.info(f'answer: {answer}, messages: {messages[-1]["content"]}, files: {files}, provider: {provider}, time: {datetime.now()-start_time}')
    return answer
