import logging
from colorama import Fore, Style, init
import inspect
from datetime import datetime, timezone
import re


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


def get_logs_text_with_html(characters: int = 12000):
    """
    Reads the last 'characters' from the agent_log.log file,
    formats the log levels in bold HTML tags, and wraps the date/time
    stamp in <code> tags.
    """
    try:
        with open('agent_log.log', 'rb') as file:
            text = file.read()[-characters:].decode('utf-8')

            # Format log levels
            text = text.replace(' INFO ', ' <b>INFO</b> ')
            text = text.replace(' ERROR ', ' <b>ERROR</b> ')
            text = text.replace(' WARNING ', ' <b>WARNING</b> ')

            # Wrap date/time in <code> tags
            def format_date(match):
                return f"<code>{match.group(0)}</code>"

            text = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}", format_date, text)

            return text

    except Exception as e:
        log(f"Error reading log file: {e}", error=True)
        return f"Error reading log file: {e}"
