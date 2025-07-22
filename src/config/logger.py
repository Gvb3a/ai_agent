import logging
from .config import load_config


config = load_config()


logging.basicConfig(
    level=logging.DEBUG,
    filename=config.logs.log_path,
    filemode="a",
    encoding="utf-8",
    format="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
logger = logging.getLogger()


# All errors will be additionally recorded in a separate file.
error_handler = logging.FileHandler(config.logs.errors_log_path, mode="a", encoding="utf-8")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
))
logger.addHandler(error_handler)
