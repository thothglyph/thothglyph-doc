from __future__ import annotations
import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL  # type: ignore # noqa
from logging import Logger, StreamHandler, Formatter  # type: ignore


NAMESPACE = 'thothglyph'


def getLogger(modname) -> Logger:
    logger = logging.getLogger(NAMESPACE + '.' + modname)
    handler = StreamHandler()
    formatter = Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
