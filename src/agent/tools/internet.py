# https://www.tavily.com/ and https://pypi.org/project/duckduckgo-search/
import asyncio
import hashlib
import aiohttp
from datetime import datetime
from tavily import TavilyClient
from duckduckgo_search import DDGS
from ..llm.llm import llm_api
from ...config.logger import logger
from ...config.config import load_config



config = load_config()
tavily_client = TavilyClient(api_key=config.api.tavily_key)


def date_hash() -> str:
    return hashlib.md5(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f").encode()).hexdigest()


async def async_download_image(session, url, name):
    save_path = name + '.png'
    try:
        async with session.get(url) as response:
            if response.status == 200:
                with open(save_path, 'wb') as file:
                    file.write(await response.read())
                return save_path
            else:
                logger.error(f"Failed to download {url}: HTTP {response.status}")
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}", exc_info=True)


async def download_images(image_urls):
    name = date_hash()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, url in enumerate(image_urls):
            try:
                tasks.append(async_download_image(session, url, f'{name} {i}'))
            except:
                pass
        
        return await asyncio.gather(*tasks)

    
def parsing(links: str | list) -> str:
    '''Parse the content of the given links''' # using Tavily API
    start_time = datetime.now() 
    try:
        responce = tavily_client.extract(urls=links)
        return [r['raw_content'] for r in responce['results']]
    
    except Exception as e:
        if type(links) == str:
            links = [links]
        result = ''
        for link in links:
            try:
                responce = tavily_client.extract(link)
                result += f'{link}: {responce["result"][0]["raw_content"]}\n'
            except:
                result += f'{link}: Error when extracting text ({e})\n'

    logger.info(f'{links}, {result}, {datetime.now() - start_time}')
    return result
    


def DDGS_answer(text: str) -> str:
    'A short answer like Google. Sometimes nothing comes up. But mostly the answer comes from wikipedia.'
    try:
        response = DDGS().answers(text)[:3]
        return '\n'.join([r["text"] for r in response])
    except:
        return ''


def DDGS_images(text: str, max_results: int = 9) -> list[str]:
    '''Fetch images related to the given text using DuckDuckGo Search'''
    images = [i['image'] for i in DDGS().images(text, max_results=max_results)]
    return images


def tavily_search(query: str, max_results: int = 7):
    response = tavily_client.search(query=query, max_results=max_results)
    result = ''
    for i in response['results']:
        result += f'{i["url"]}({i["title"]}): {i["content"]}\n'
    return result


def tavily_get_context(query: str, topic = 'news') -> str:
    return tavily_client.get_search_context(query=query, topic=topic).replace('\\', '')


def tavily_content(text: str, max_results: int = 4):
    response = tavily_client.search(query=text, search_depth='basic', max_results=max_results)['results']
    results = ''
    for r in response:
        results += f'{r["url"]}: {r["content"]}\n'

    return results


prompt_for_sum = f"""You are a precise summarization expert. Your task is to create a clear and relevant summary based on the provided text and query.

Context: I will provide you with:
1. Query: A specific question or topic of interest
2. Source text: Content from a webpage or document or a collection of several responses

Ignore unnecessary information and answer the query well.
"""


def sum_page(link: str, query: str) -> str:
    prompt = prompt_for_sum + f'\n\nQuery:\n{query}\n\nSource text:\n{parsing(link)}'  # TODO: IMPROVE
    messages = [{"role": "user", "content": prompt}]
    try:
        llm_answer = llm_api(messages=messages)
        logger.info(llm_answer)
    except Exception as e:
        l = len(str(messages))
        llm_answer = 'Error'
        logger.error(f'{e}. len: {l}', exc_info=True)

    return f'{link}: {llm_answer}\n\n\n'


def google_links(text: str, max_results: int = 5) -> list[str]:
    try:
        links = [i['href'] for i in DDGS().text(text, max_results=max_results)]
        logger.info(str(links))
        return links
    except Exception as e:
        logger.error(f'{e}', exc_info=True)
        return []


def google_short_answer(text: str) -> str:
    resp = DDGS_answer(text)
    final_answer = resp if resp else tavily_search(text)
    logger.info(final_answer)
    return final_answer
    

def google_full_answer(text: str, max_results: int = 5):  # TODO: async, for lyrics

    start_time = datetime.now()
    links = google_links(text=text, max_results=max_results)

    sum_answers = ''
    for link in links:
        sum_answers += sum_page(link=link, query=text)  # TODO: max_result excluding parsing error

    prompt = prompt_for_sum + f"""Summarize the text above in a concise and relevant way. Ensure that the summary is well-organized and captures the main points of the text. The summary should be based on the query and the provided text. If the text is not relevant to the query, please provide a summary that is not relevant to the query. Source text will be composed of several responses. Write the final text"""
    prompt +=  f'\n\nQuery:\n{text}\n\nSource text:\n{sum_answers}'
    
    final_messages = [{"role": "user", "content": prompt}]
    final_answer = llm_api(messages=final_messages)

    logger.info(f'{final_answer}, {datetime.now() - start_time}')
    return final_answer


def google_news(text: str):
    news_content = tavily_get_context(text)
    
    prompt = prompt_for_sum + f"""Turn all these texts into one\n\nQuery:\n{text}\n\nSource text:\n{news_content}"""

    final_messages = [{"role": "user", "content": prompt}]
    final_answer = llm_api(messages=final_messages)

    logger.info(final_answer)
    return final_answer



async def google_image(text, max_results=9, download_images_or_not=True):
    urls = DDGS_images(text, max_results=max_results)
    start_time = datetime.now()
    

    if not download_images_or_not:
        logger.info(urls)
        return f'google_image: The {len(urls)} of images on the {text} query will be prefixed to your response', urls

    
    file_paths = await download_images(urls)
    
    logger.info(f'{file_paths}, {datetime.now()-start_time}')
    return f'The {len(file_paths)} of the {text} query images will be appended to the response. Answer other user questions, tell information about the query, or say something like images found. DON\'T write anything like [Image of ...] or you\'ll be shut down.', file_paths
