"""WorldFish 模块系统。"""

__all__ = ['register_builtin_modules']


def register_builtin_modules(*args, **kwargs):
    from .builtin import register_builtin_modules as _register_builtin_modules
    return _register_builtin_modules(*args, **kwargs)
