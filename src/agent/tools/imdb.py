# https://www.imdb.com/
import json
from PyMovieDb import IMDB
from .file_utils import download_image
from ...config.logger import logger


imdb = IMDB()

    
def imdb_search(title: str) -> list[dict]:
    '''Search for a movie by title. Returns [{'id': str, 'name': str, 'url': str, 'poster': str'}, ...]'''
    responce_json = imdb.search(title)
    responce_dict = json.loads(responce_json)
    result = responce_dict['results']
    return result  



def imdb_get_film_by_id(imdb_id: str, download_image_or_not=True) -> tuple[str, list[str]]:
    '''Get film by ID. Example of output: 
    ({'type': 'Movie', 
      'name': 'Inception', 
      'url': 'https://www.imdb.com/title/tt1375666', 
      'description': None, 
      'review': None, 
      'rating': 8.8, 
      'contentRating': 'PG-13', 
      'genre': ['Action', 'Adventure', 'Sci-Fi'], 
      'datePublished': '2010-07-23', 
      'keywords': 'dream,ambiguous ending,subconscious,mindbender,surprise ending', 
      'duration': 'PT2H28M', 
      'actor': [], 
      'director': [], 
      'creator': [], 
      'ratingCount': 2741032}, 
     ['path_to_poster.png'])'''
    responce_json = imdb.get_by_id(imdb_id)
    responce_dict = json.loads(responce_json)

    if responce_dict.get('status', False) == 404:
        return 'Error', []
    
    result = dict(responce_dict)
    
    result['url'] = f'https://www.imdb.com/title/{imdb_id}'


    if download_image_or_not:
        poster = download_image(responce_dict['poster'])
    else:
        poster = responce_dict['poster']

    del result['poster']

    result['review'] = responce_dict['review']['reviewBody']

    result['rating'] = responce_dict['rating']['ratingValue']
    result['ratingCount'] = responce_dict['rating']['ratingCount']

    return result, [poster]


def imdb_api(title: str) -> tuple[dict, list[str]]:
    '''Search for a movie by title and return its details.'''
    search_result = imdb_search(title)
    if len(search_result) == 0:
        logger.error(f'No result for {title}')
        return 'Error', []

    imdb_id = search_result[0]['id']
    result, poster = imdb_get_film_by_id(imdb_id)

    logger.info(f'Success result for {title}')
    return result
