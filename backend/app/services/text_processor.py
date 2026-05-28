"""
轻量文档拆分与预处理
"""

import re
from typing import Dict, List

from ..utils.file_parser import FileParser, split_text_into_chunks


class TextProcessor:

    @staticmethod
    def extract_from_files(paths: List[str]) -> str:
        return FileParser.extract_from_multiple(paths)

    @staticmethod
    def split_text(source: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        return split_text_into_chunks(source, chunk_size, overlap)

    @staticmethod
    def normalize(text: str) -> str:
        """统一换行、去掉多余空行和首尾空白。"""
        cleaned = text.replace('\r\n', '\n').replace('\r', '\n')
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        lines = [line.strip() for line in cleaned.split('\n')]
        return '\n'.join(lines).strip()

    @staticmethod
    def stats(text: str) -> Dict[str, int]:
        return {
            "total_chars": len(text),
            "total_lines": text.count('\n') + 1,
            "total_words": len(text.split()),
        }


# 兼容旧名称
TextProcessor.preprocess_text = staticmethod(TextProcessor.normalize)
TextProcessor.get_text_stats = staticmethod(TextProcessor.stats)
