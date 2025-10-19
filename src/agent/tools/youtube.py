# !!! DIDNT WORK !!!
import re
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from .translate import detect_language
from ...config.logger import logger
from ...agent.llm.llm import llm_api


def transcript2text(transcript: list[dict], sep='\n') -> str:
    result = []
    current_minute = -1

    for t in transcript:
        minute = int(t["start"] // 60)
        if minute != current_minute:
            result.append(f"{minute} minute:")
            current_minute = minute
        
        result.append(t["text"])

    return sep.join(result)



def get_youtube_transcripts(link: str, language: str = 'en'):

    if 'youtube.com' in link:
        pattern_for_youtube_video = r"(?:v=|\/)([a-zA-Z0-9_-]{11})"  # https://www.youtube.com/watch?v=xxxxxxxxxxx -> xxxxxxxxxxx
        match = re.search(pattern_for_youtube_video, link)
        if match:
            video_id = match.group(1)
        else:
            return 'Error: incorrect link'
    else:
        video_id = link

    
    # get title
    response = requests.get(link)
    soup = BeautifulSoup(response.text, 'html.parser')
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.text.replace(" - YouTube", "")
    else:
        title = 'Error: title not found'

    # get transcript: [{'text': str, 'start': float, 'duration': float}, ...]
    try:  
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        logger.info(f'1 (defult language): {language}, {link}({title})')
        return transcript2text(transcript), title
    except:
        pass


    try:
        language = detect_language(title)
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        logger.info(f'2 (detect language): {language}, {link}({title})')
        return transcript2text(transcript), title
    except:
        pass


    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcripts:
            transcript = transcript.translate('en').fetch()
            break
        logger.info(f'3 (translate). {link}({title})')
    except Exception as e:
        logger.error(f'error: {e}', exc_info=True)
        transcript = [{'text': f'Subtitles are not available', 'start': 0.0}]
    
    return transcript2text(transcript), title


def youtube_sum(link: str, question: str | None = None, language: str = 'en') -> str: 
    # make it possible to ask questions.
    text, title = get_youtube_transcripts(link, language)

    if question:
        content = f'Answer the question "{question}" based on this YouTube video "{title}": {text}'
    else:
        content = f'Summarize this YouTube video "{title}": {text}'

    try:
        answer = llm_api(messages=[{'role': 'user', 'content': content}], provider='google')
        logger.info(f'{link} ({question}): {answer}')
        return answer
    except Exception as e:
        logger.error(f'{link} error ({e})', exc_info=True)
        return f'Error({e}). Most like too much text or a completely incomprehensible error that cannot be fixed (or subtitles are not available). Tell the user to try again later'