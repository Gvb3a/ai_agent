from dataclasses import dataclass
from environs import Env
from colorama import Fore, Style, init
import os


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@dataclass
class TgBot:
    token: str
    admin_ids: list[int]


@dataclass
class Database:
    path: str


@dataclass
class Logs:
    log_path: str
    errors_log_path: str


@dataclass
class API:
    gemini_key: str
    huggingface_key: str
    groq_key: str
    tavily_key: str
    wolfram_simple_key: str
    wolfram_full_key: str
    todoist_key: str
    detect_language_key: str
    e2b_key: str


@dataclass
class Config:
    tg_bot: TgBot
    database: Database
    logs: Logs
    api: API


def load_config(path: str | None = None) -> Config:

    env = Env()
    env.read_env(path)

    init(autoreset=True)

    for key in ['BOT_TOKEN', 'GEMINI_API_KEY', 'HUGGINGFACE_API_KEY', 'GROQ_API_KEY',
                'TAVILY_API_KEY', 'WOLFRAM_SIMPLE_API_KEY', 'WOLFRAM_FULL_API_KEY',
                'TODOIST_API_KEY', 'DETECT_LANGUAGE_API_KEY', 'E2B_API_KEY']:
        if not env.str(key, default=''):
            print(Fore.RED + Style.BRIGHT + f"WARNING: '{key}' is not found in the environment. Functionality can be limited.")

    
    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN", default=""),
            admin_ids=env.list("ADMINS", subcast=int, default=[])
        ),
        database=Database(
            path=os.path.join(BASE_DIR, "src", "bot", "database.db")
        ),
        logs=Logs(
            log_path=os.path.join(BASE_DIR, "src", "logs", "agent.log"),
            errors_log_path=os.path.join(BASE_DIR, "src", "logs", "agent_errors.log")
        ),
        api=API(
            gemini_key=env.str("GEMINI_API_KEY", default=""),
            huggingface_key=env.str("HUGGINGFACE_API_KEY", default=""),
            groq_key=env.str("GROQ_API_KEY", default=""),
            tavily_key=env.str("TAVILY_API_KEY", default=""),
            wolfram_simple_key=env.str("WOLFRAM_SIMPLE_API_KEY", default=""),
            wolfram_full_key=env.str("WOLFRAM_FULL_API_KEY", default=""),
            todoist_key=env.str("TODOIST_API_KEY", default=""),
            detect_language_key=env.str("DETECT_LANGUAGE_API_KEY", default=""),
            e2b_key=env.str("E2B_API_KEY", default="")
        )
    )


if __name__ == "__main__":
    config = load_config()
    print(config)