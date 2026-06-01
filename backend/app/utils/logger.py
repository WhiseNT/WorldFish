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
_SHARED_FILE_HANDLER = None
_SHARED_CONSOLE_HANDLER = None


class WindowsSafeRotatingFileHandler(RotatingFileHandler):
    """避免 Windows 下日志轮转文件被短暂占用时打断请求线程。"""

    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError:
            if self.stream:
                self.stream.close()
                self.stream = None
            self.mode = 'a'
            self.stream = self._open()


def _utf8_stdout():
    """Windows 控制台 UTF-8 兼容。"""
    if sys.platform != 'win32':
        return
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')


def _make_file_handler():
    filename = datetime.now().strftime('%Y-%m-%d') + '.log'
    handler = WindowsSafeRotatingFileHandler(
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


def _get_shared_file_handler():
    global _SHARED_FILE_HANDLER
    if _SHARED_FILE_HANDLER is None:
        _SHARED_FILE_HANDLER = _make_file_handler()
    return _SHARED_FILE_HANDLER


def _get_shared_console_handler():
    global _SHARED_CONSOLE_HANDLER
    if _SHARED_CONSOLE_HANDLER is None:
        _SHARED_CONSOLE_HANDLER = _make_console_handler()
    return _SHARED_CONSOLE_HANDLER


def _close_owned_handlers(logger):
    shared_handlers = {_SHARED_FILE_HANDLER, _SHARED_CONSOLE_HANDLER}
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        if handler not in shared_handlers:
            handler.close()


def setup_logger(name='worldfish', level=logging.DEBUG):
    os.makedirs(_LOG_ROOT, exist_ok=True)
    base_logger = logging.getLogger('worldfish')
    base_logger.setLevel(level)
    base_logger.propagate = False

    if not base_logger.handlers:
        base_logger.addHandler(_get_shared_file_handler())
        base_logger.addHandler(_get_shared_console_handler())

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if name == 'worldfish':
        return base_logger

    if name.startswith('worldfish.'):
        if logger.handlers:
            _close_owned_handlers(logger)
        logger.propagate = True
        return logger

    if not logger.handlers:
        logger.addHandler(_get_shared_file_handler())
        logger.addHandler(_get_shared_console_handler())
    logger.propagate = False
    return logger


def get_logger(name='worldfish'):
    return setup_logger(name)


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
