# https://groq.com/
from typing import Literal
from groq import Groq, AsyncGroq
from ..tools.file_utils import files_to_text
from ...config.logger import logger
from ...config.config import load_config


config = load_config()
groq_api_keys = config.api.groq_key
groq_client = [Groq(api_key=key) for key in groq_api_keys]  # Helps with rate limiting
groq_client_async = [AsyncGroq(api_key=key) for key in groq_api_keys]



def groq_api(messages: list, files: list = None, model: Literal['openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'groq/compound', 'groq/compound-mini'] = 'openai/gpt-oss-120b') -> str:
    # https://console.groq.com/docs/models
    if type(messages) == str:
        messages = [{"role": "user", "content": messages}]

    if files:
        file_texts = files_to_text(files)
        messages[-1]["content"] += file_texts

    for client in groq_client:
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=model)
            logger.info(f'Success: {response.choices[0].message.content}')
            answer = str(response.choices[0].message.content)
            break
        except Exception as e:
            logger.error(f'Error with {model} on {client.api_key}: {e}', exc_info=True)
            answer = f'Error {e}'
            continue

    logger.info(f'groq_api answer: {answer}, query: {messages[-1]["content"]}, model: {model}')
    return answer


async def groq_api_stream(messages, model="openai/gpt-oss-120b"):
    error = False
    for client in groq_client_async:
        try:    
            stream = await client.chat.completions.create(
                messages=messages,
                model=model,
                stream=True,
            )
            
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
                return
        except Exception as e:
            logger.error(f'Error with {model} on {client.api_key}: {e}', exc_info=True)
            error = True
            continue
    if error:
        yield 'Error'
        return

def groq_api_compound(messages: list, model: Literal['groq/compound', 'groq/compound-mini'] = 'groq/compound', files: list = None) -> str:
    return groq_api(messages, model=model, files=files)