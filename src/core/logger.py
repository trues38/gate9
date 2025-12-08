import logging

def get_logger(name="G9"):
    formatter = logging.Formatter(
        "\033[92m[%(asctime)s] %(levelname)s\033[0m - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

logger = get_logger()