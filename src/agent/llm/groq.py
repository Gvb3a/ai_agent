# https://groq.com/
from groq import Groq
from typing import Literal
from datetime import datetime
from ..tools.file_utils import files_to_text
from ...config.logger import logger
from ...config.config import load_config


config = load_config()
groq_api_keys = config.api.groq_key
groq_client = [Groq(api_key=key, default_headers={"Groq-Model-Version": "latest"}) for key in groq_api_keys]  # Helps with rate limiting


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
            answer = str(response.choices[0].message.content)
            break
        except Exception as e:
            logger.error(f'Error with {model} on {client.api_key}: {e}', exc_info=True)
            answer = f'Error {e}'
            continue

    logger.info(f'groq_api answer: {answer}, query: {messages[-1]["content"]}, model: {model}')
    return answer


def groq_api_compound(messages: list, model: Literal['groq/compound', 'groq/compound-mini'] = 'groq/compound', files: list = None, only_answer: bool = True, browser_automation: bool = False) -> tuple[str, str, str] | str:
    start_time = datetime.now()
    if type(messages) == str:
        messages = [{"role": "user", "content": messages}]
    if model not in ['groq/compound', 'groq/compound-mini']:
        logger.warning(f'Wrong model: {model}')
        model = 'groq/compound'
    if files:
        file_texts = files_to_text(files)
        messages[-1]["content"] += file_texts

    compound_custom = {
                    "tools": {
                        "enabled_tools": ["web_search", "wolfram_alpha", "code_interpreter", "visit_website"],
                        "wolfram_settings": {"authorization": config.api.wolfram_full_key}
                    }
                }
    
    if browser_automation:
        compound_custom["tools"]["enabled_tools"].append('browser_automation')

    for client in groq_client:
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=model,
                compound_custom=compound_custom
            )
            answer = str(response.choices[0].message.content)
            executed_tools = response.choices[0].message.executed_tools
            break
        except Exception as e:
            logger.error(f'Error with {model} on {client.api_key}: {e}', exc_info=True)
            answer = f'Error {e}'
            executed_tools = []
            continue
    
    if executed_tools:
        tools = [{tool.type: tool.arguments} for tool in executed_tools]
    else:
        tools = []
    seconds = round((datetime.now()-start_time).total_seconds(), 2)
    minutes = int(seconds // 60) 
    time = f"{minutes} min {seconds} s" if minutes else f"{seconds} s"
    logger.info(f'{model} answer: {answer}, query: {messages[-1]["content"]}, tools: {tools}, time: {time}, files: {files}, only_answer: {only_answer}, browser_automation: {browser_automation}')
    if only_answer:
        return answer
    else:
        return answer, tools, time

