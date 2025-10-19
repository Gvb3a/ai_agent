# https://www.wolframalpha.com/
import re
import requests
from urllib.parse import quote
from .file_utils import download_image
from ...config.logger import logger
from ...config.config import load_config


config = load_config()
WOLFRAM_SIMPLE_API = config.api.wolfram_simple_key
WOLFRAM_SHOW_STEPS_RESULT = config.api.wolfram_full_key

    
def calculator(expression: str) -> str:
    '''Calculates the result of a mathematical expression.'''
    try:
        expression = expression.replace('^', '**')
        logger.info(expression)
        return str(eval(expression))
    
    except Exception as e:
        logger.error(f"Calculator error: {e}", exc_info=True)
        return f"Calculator error: {e}"


def wolfram_short_answer_api(text: str) -> str:
    'https://products.wolframalpha.com/short-answers-api/documentation - Short answer from WolframAlpha'
    query = quote(text)
    url = f'https://api.wolframalpha.com/v1/result?appid={WOLFRAM_SIMPLE_API}&i={query}'
    answer = requests.get(url).text
    logger.info(answer)
    return answer


def wolfram_llm_api(text: str) -> tuple[str, list]:
    'https://products.wolframalpha.com/llm-api/documentation - text version of the WolframAlpha page answer. Returns the text and a list of links to images'
    query = quote(text)
    url = f'https://www.wolframalpha.com/api/v1/llm-api?input={query}&appid={WOLFRAM_SHOW_STEPS_RESULT}'
    answer = requests.get(url).text
    # TODO: improve (add async) and add llm
    answer = answer[:answer.find('Wolfram|Alpha website result for "')]
    links = re.findall(r'https?://\S+', answer)
    answer = re.sub(r'https?://\S+', 'Images will be attached to the answer', answer)
    logger.info(f'{answer}, {links}')
    return answer, links


def wolfram_simple_api(text: str) -> str:
    'https://products.wolframalpha.com/simple-api/documentation - WolframAlpha answer page image'
    query = quote(text)
    link = f'https://api.wolframalpha.com/v1/simple?appid={WOLFRAM_SIMPLE_API}&i={query}%3F'
    file_name = download_image(link)
    logger.info(file_name)
    return file_name


# These two functions are for use by llm
def wolfram_short_answer(query: str) -> str:
    'Short answer from WolframAlpha'
    return wolfram_short_answer_api(query)


def wolfram_full_answer(text: str):  # TODO: async + and [wolfram_simple_api(text)] + full_answer_images 
    'returns the text version of the answer sheet, the image links and the answer sheet as a picture'
    full_answer, full_answer_images = wolfram_llm_api(text)
    images = full_answer_images
    logger.info(f'{full_answer}, {images}')
    return full_answer, images