import logging
from colorama import Fore, Style, init
import inspect
from datetime import datetime, timezone


logging.basicConfig(level=20, filename="agent_log.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s")

def utc_time():
    return datetime.now(timezone.utc).strftime('%Y.%m.%d %H:%M:%S')

init()

def log(text: str = '', error=False):

    t = utc_time()

    func_name = inspect.stack()[1].function
    if func_name == '<module>':
        func_name = text
        text = ''

    color = Fore.RED if error else Fore.GREEN
    print(t, f'{color}{Style.BRIGHT}{func_name}{Style.RESET_ALL}', text)

    if error:
        logging.error(f'{func_name} {text}')
    else:
        logging.info(f'{func_name} {text}')

