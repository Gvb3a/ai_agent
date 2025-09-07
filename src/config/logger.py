import logging
from .config import load_config
import os


config = load_config()


log_dir = os.path.dirname(config.logs.log_path)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)

errors_log_dir = os.path.dirname(config.logs.errors_log_path)
if errors_log_dir and not os.path.exists(errors_log_dir):
    os.makedirs(errors_log_dir)
    

logging.basicConfig(
    level=logging.INFO,
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


# Console handler for real-time logging output.
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
))
logger.addHandler(console_handler)
