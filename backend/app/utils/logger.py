"""
应用日志工厂
统一创建带轮转文件和控制台双输出的 logger。
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_LOG_ROOT = os.path.join(_BASE, 'logs')

_CONSOLE_FMT = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', '%H:%M:%S')
_FILE_FMT = logging.Formatter(
    '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
    '%Y-%m-%d %H:%M:%S',
)


def _utf8_stdout():
    """Windows 控制台 UTF-8 兼容。"""
    if sys.platform != 'win32':
        return
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')


def _make_file_handler():
    filename = datetime.now().strftime('%Y-%m-%d') + '.log'
    handler = RotatingFileHandler(
        os.path.join(_LOG_ROOT, filename),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_FILE_FMT)
    return handler


def _make_console_handler():
    _utf8_stdout()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(_CONSOLE_FMT)
    return handler


def setup_logger(name='worldfish', level=logging.DEBUG):
    os.makedirs(_LOG_ROOT, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:
        return logger
    logger.addHandler(_make_file_handler())
    logger.addHandler(_make_console_handler())
    return logger


def get_logger(name='worldfish'):
    target = logging.getLogger(name)
    if not target.handlers:
        return setup_logger(name)
    return target


_default = setup_logger()


def debug(msg, *a, **kw):
    _default.debug(msg, *a, **kw)


def info(msg, *a, **kw):
    _default.info(msg, *a, **kw)


def warning(msg, *a, **kw):
    _default.warning(msg, *a, **kw)


def error(msg, *a, **kw):
    _default.error(msg, *a, **kw)


def critical(msg, *a, **kw):
    _default.critical(msg, *a, **kw)
