import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL  # noqa


NAMESPACE = 'thothglyph'


def getLogger(modname):
    logger = logging.getLogger(NAMESPACE + '.' + modname)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
