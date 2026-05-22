"""提示词加载器。从 prompts/ 目录加载 .txt 模板文件。

模板文件使用 Python str.format() 语法，变量用 {variable_name} 占位。
"""

import os
from typing import Dict

_PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_cache: Dict[str, str] = {}


def load_prompt(name: str, **kwargs) -> str:
    """加载提示词模板并填充变量。

    Args:
        name: 模板文件名（不含 .txt 后缀）
        **kwargs: 模板变量

    Returns:
        填充后的提示词文本
    """
    if name not in _cache:
        path = os.path.join(_PROMPTS_DIR, f"{name}.txt")
        if not os.path.exists(path):
            raise FileNotFoundError(f"提示词模板不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            _cache[name] = f.read()

    template = _cache[name]
    if kwargs:
        return template.format(**kwargs)
    return template


def reload_prompt(name: str) -> str:
    """强制重新从磁盘加载提示词（热更新用）。"""
    _cache.pop(name, None)
    return load_prompt(name)
