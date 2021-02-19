import logging
import os
import pathlib
import time

from market_maker import custom_strategy
from market_maker.settings import settings


def setup_custom_logger(name, log_level=settings.LOG_LEVEL):

    logger = logging.getLogger(name)

    if not len(logger.handlers):

        # set api key and secret
        setApi()

        timestr = time.strftime("%m%d-%H%M%S")
        formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

        streamHandler = logging.StreamHandler()
        apiKey = settings.API_KEY[:4]
        script_dir = pathlib.Path(__file__).parent.parent.parent
        rel_path = './log/' + apiKey

        fileHandler = None
        rel_path += '/' + name
        abs_file_path = os.path.join(script_dir, rel_path)
        os.makedirs(abs_file_path, exist_ok = True)

        fileHandler = logging.FileHandler(abs_file_path + '/' + name + '.log')

        streamHandler.setFormatter(formatter)
        fileHandler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(log_level)

        logger.addHandler(streamHandler)
        logger.addHandler(fileHandler)

    return logger

def setApi():
    script_dir = pathlib.Path(__file__).parent.parent.parent

    rel_path = "client_api/bitmex_key_secret.txt"
    abs_file_path = os.path.join(script_dir, rel_path)

    r = open(abs_file_path, mode='rt', encoding='utf-8')
    list = r.read().splitlines()
    key = list[0].split('=')[1]
    secret = list[1].split('=')[1]

    settings.API_KEY = key
    settings.API_SECRET = secret



