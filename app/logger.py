"""日志系统：按日期切分，保留 30 天，级别 INFO/WARNING/ERROR。"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler

from . import paths

_LOGGER_NAME = "aiworkbench"

_logger: logging.Logger | None = None


def setup_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    log_dir = paths.logs_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
    )

    # 按天切分，保留 30 个日志文件
    file_handler = TimedRotatingFileHandler(
        log_dir / "aiworkbench.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    # 开发环境下同时输出到控制台
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    if _logger is None:
        return setup_logger()
    return _logger