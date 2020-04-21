import logging
import time
from market_maker.settings import settings


def setup_custom_logger(name, log_level=settings.LOG_LEVEL):

    logger = logging.getLogger(name)

    if not len(logger.handlers):
        timestr = time.strftime("%m%d-%H%M%S")
        formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

        streamHandler = logging.StreamHandler()
        fileHandler = logging.FileHandler('./log/' + timestr + '.log')

        streamHandler.setFormatter(formatter)
        fileHandler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(log_level)

        logger.addHandler(streamHandler)
        logger.addHandler(fileHandler)

    return logger


