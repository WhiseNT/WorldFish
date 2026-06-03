"""RAG 服务 — 基于 ChromaDB 的世界观向量知识库。

每个世界观一个 ChromaDB Collection，存储于 uploads/worlds/{world_id}/rag/
支持：文档添加、文本索引、语义检索、Collection 管理
"""

import hashlib
import os
import re
import uuid
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..models.world import WorldManager
from ..utils.logger import get_logger

logger = get_logger("worldfish.rag")

def get_rag_text_volume_profile(text_len: int) -> Dict[str, Any]:
    """根据文本量为 RAG 自动选择切块策略。

    RAG 分块不再依赖 LLM/环境变量里的手动块大小配置，而是由程序按文本量分档决定。
    短文本保持较细粒度，超长文本增大块大小以降低 Embedding 与向量写入成本。
    """
    text_len = max(0, int(text_len or 0))
    if text_len <= 15_000:
        profile_name, chunk_size = "short", 800
    elif text_len <= 120_000:
        profile_name, chunk_size = "medium", 1000
    elif text_len <= 500_000:
        profile_name, chunk_size = "long", 1400
    elif text_len <= 1_500_000:
        profile_name, chunk_size = "huge", 1800
    else:
        profile_name, chunk_size = "massive", 2200

    chunk_overlap = max(80, min(260, int(chunk_size * 0.1)))
    return {
        "profile": profile_name,
        "text_length": text_len,
        "rag_chunk_size": chunk_size,
        "rag_chunk_overlap": chunk_overlap,
        "rag_chunk_preset": "novel",
        "strategy": "auto_by_text_volume",
    }


RAG_CHUNK_PRESETS = [
    {
        "id": "novel",
        "name": "小说章节",
        "description": "优先按“第X章/第X节/Chapter X”等章节标题切分，超长章节自动再切块。",
        "default": True,
    },
    {
        "id": "default",
        "name": "通用段落",
        "description": "按段落和句子边界切分，适合设定文档、说明书和短文本。",
        "default": False,
    },
]

CHAPTER_HEADING_RE = re.compile(
    r"(?mi)^\s*(?:#{1,6}\s*)?(?P<title>"
    r"(?:第\s*[零〇一二三四五六七八九十百千万两\d]+\s*[章节卷部回篇集][^\n]{0,80})"
    r"|(?:[零〇一二三四五六七八九十百千万两\d]+\s*[章节卷部回篇集][^\n]{0,80})"
    r"|(?:卷\s*[零〇一二三四五六七八九十百千万两\d]+[^\n]{0,80})"
    r"|(?:Chapter\s+\d+[^\n]{0,80})"
    r"|(?:Part\s+\d+[^\n]{0,80})"
    r"|(?:VOLUME\s*\d+[^\n]{0,80})"
    r"|(?:三体\s*[ⅠⅡⅢIVXivx123一二三]+[^\n]{0,80})"
    r"|(?:(?:序章|楔子|引子|尾声|终章|后记)[^\n]{0,80})"
    r")\s*$"
)

ProgressCallback = Callable[[str, int, str, Optional[Dict[str, Any]]], None]

# ChromaDB 全局客户端（线程安全）
_chroma_client: Optional[Any] = None
_chroma_lock = threading.Lock()


def _get_chroma_client() -> Any:
    """获取或创建 ChromaDB 持久化客户端（单例）。"""
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                try:
                    import chromadb
                    from chromadb.config import Settings as ChromaSettings
                except ModuleNotFoundError as exc:
                    raise RuntimeError('ChromaDB 未安装，无法使用 RAG 知识库功能。请安装 chromadb 后重试。') from exc
                chroma_dir = os.path.join(Config.UPLOAD_FOLDER, "chroma")
                os.makedirs(chroma_dir, exist_ok=True)
                _chroma_client = chromadb.PersistentClient(
                    path=chroma_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                logger.info(f"ChromaDB 已初始化: {chroma_dir}")
    return _chroma_client


def _get_embedding_client():
    """获取 API Embedding 客户端；本地 provider 不创建 API client。"""
    emb_config = Config.get_embedding_config()
    if emb_config.get("provider") == "local":
        return None
    if not emb_config.get("api_key"):
        raise RuntimeError(Config.EMBEDDING_REQUIRED_MESSAGE)
    return OpenAI(api_key=emb_config["api_key"], base_url=emb_config["base_url"] or None)


def _world_collection_name(world_id: str) -> str:
    """世界观对应的 Collection 名称。"""
    world_id = str(world_id or "").strip()
    if not WorldManager.is_valid_world_id(world_id):
        raise ValueError(f"非法世界观 ID: {world_id}")
    collection_name = f"world_{world_id}"
    if len(collection_name) > 63:
        digest = hashlib.sha256(world_id.encode("utf-8")).hexdigest()[:16]
        collection_name = f"world_{digest}"
    return collection_name


@dataclass
class RagDocument:
    """RAG 文档。"""
    doc_id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "text": self.text[:200] + "..." if len(self.text) > 200 else self.text,
            "text_length": len(self.text),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class RagSearchResult:
    """RAG 检索结果。"""
    doc_id: str
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "text": self.text,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


class RagService:
    """世界观 RAG 服务。

    每个世界观一个独立的 ChromaDB Collection。
    Embedding 可通过 EMBEDDING_* 环境变量独立配置（不填则复用 LLM API）。
    """

    def __init__(self, world_id: str):
        if not WorldManager.is_valid_world_id(world_id):
            raise ValueError(f"非法世界观 ID: {world_id}")
        self.world_id = str(world_id).strip()
        self.collection_name = _world_collection_name(world_id)
        self._client = _get_chroma_client()
        self._embedding_client = _get_embedding_client()
        self._collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """获取或创建 Collection（数据安全模式）。

        优先使用 get_or_create_collection，确保不会因任意异常
        而意外创建空集合覆盖已有数据。逐级回退保证兼容性。
        """
        # 方案 A：标准 API（ChromaDB >= 0.4）
        try:
            return self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"world_id": self.world_id, "hnsw:space": "cosine"},
            )
        except Exception as e1:
            logger.warning(f"get_or_create_collection 失败 [{self.collection_name}]: {e1}")

        # 方案 B：get_collection（已存在）
        try:
            coll = self._client.get_collection(name=self.collection_name)
            logger.info(f"通过 get_collection 获取到已有 Collection: {self.collection_name}")
            return coll
        except Exception as e2:
            logger.warning(f"get_collection 也失败 [{self.collection_name}]: {e2}")

        # 方案 C：纯新建（仅在 Collection 确实不存在时）
        logger.info(f"创建新 RAG Collection: {self.collection_name}")
        return self._client.create_collection(
            name=self.collection_name,
            metadata={"world_id": self.world_id, "hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # 嵌入
    # ------------------------------------------------------------------

    _local_model = None  # 本地 sentence-transformers 模型缓存

    @classmethod
    def _get_local_embedding_fn(cls):
        """获取本地 Embedding 函数（懒加载，首次使用时下载模型）。"""
        if cls._local_model is None:
            from sentence_transformers import SentenceTransformer
            model_name = Config.LOCAL_EMBEDDING_MODEL_NAME
            logger.info(f"加载本地 Embedding 模型: {model_name} ({Config.LOCAL_EMBEDDING_MODEL_SOURCE})")
            cls._local_model = SentenceTransformer(model_name, trust_remote_code=True)
        return cls._local_model


    def _emit_progress(
        self,
        progress_callback: Optional[ProgressCallback],
        stage: str,
        progress: int,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        if progress_callback:
            progress_callback(stage, max(0, min(int(progress), 100)), message, detail or {})

    @classmethod
    def get_chunk_presets(cls) -> List[Dict[str, Any]]:
        return [dict(item) for item in RAG_CHUNK_PRESETS]

    def _embed(
        self,
        texts: List[str],
        batch_size: int = 20,
        progress_callback: Optional[ProgressCallback] = None,
        progress_start: int = 25,
        progress_end: int = 80,
    ) -> List[List[float]]:
        """将文本列表转为向量。根据显式 provider 使用 API 或本地模型。"""
        if not texts:
            return []

        emb_config = Config.get_embedding_config()
        if not emb_config.get("available"):
            raise RuntimeError(Config.EMBEDDING_REQUIRED_MESSAGE)

        total = len(texts)
        batch_count = max(1, (total + batch_size - 1) // batch_size)

        if emb_config.get("provider") == "local":
            self._emit_progress(progress_callback, "embedding", progress_start, f"正在使用本地模型生成向量：{Config.LOCAL_EMBEDDING_MODEL_NAME}", {
                "total_chunks": total,
                "embedding_provider": "local",
                "model": Config.LOCAL_EMBEDDING_MODEL_NAME,
                "model_source": Config.LOCAL_EMBEDDING_MODEL_SOURCE,
            })
            model = self._get_local_embedding_fn()
            embeddings = model.encode(texts, normalize_embeddings=True)
            self._emit_progress(progress_callback, "embedding", progress_end, f"本地向量生成完成：{total}/{total} 个文本块", {
                "total_chunks": total,
                "processed_chunks": total,
                "embedding_provider": "local",
            })
            return [emb.tolist() if hasattr(emb, "tolist") else list(emb) for emb in embeddings]

        if self._embedding_client is None:
            raise RuntimeError(Config.EMBEDDING_REQUIRED_MESSAGE)

        def _api_embed_batch(batch: List[str]) -> List[List[float]]:
            response = self._embedding_client.embeddings.create(
                model=emb_config["model_name"],
                input=batch,
                encoding_format="float",
            )
            return [item.embedding for item in response.data]

        all_embeddings = []
        self._emit_progress(progress_callback, "embedding", progress_start, f"正在生成向量：共 {total} 个文本块，{batch_count} 个批次", {
            "total_chunks": total,
            "batch_count": batch_count,
            "embedding_provider": "api",
        })
        for batch_index, i in enumerate(range(0, len(texts), batch_size), start=1):
            batch = texts[i:i + batch_size]
            all_embeddings.extend(_api_embed_batch(batch))
            processed = min(i + len(batch), total)
            progress = progress_start + int((progress_end - progress_start) * processed / max(total, 1))
            self._emit_progress(progress_callback, "embedding", progress, f"正在生成向量：第 {batch_index}/{batch_count} 批，已处理 {processed}/{total} 个文本块", {
                "total_chunks": total,
                "processed_chunks": processed,
                "batch_index": batch_index,
                "batch_count": batch_count,
                "embedding_provider": "api",
            })
        return all_embeddings

    # ------------------------------------------------------------------
    # 文档管理
    # ------------------------------------------------------------------

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        source: str = "manual",
        progress_callback: Optional[ProgressCallback] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> List[str]:
        """批量添加文档到 RAG。

        Args:
            texts: 文本列表
            metadatas: 元数据列表（与 texts 一一对应）
            source: 来源标识（manual / extraction / file）

        Returns:
            文档 ID 列表
        """
        if not texts:
            return []

        doc_ids = [f"rag_{uuid.uuid4().hex[:12]}" for _ in texts]
        if metadatas is None:
            metadatas = [{} for _ in texts]
        for meta in metadatas:
            meta.setdefault("source", source)
            meta.setdefault("indexed_at", datetime.now().isoformat())

        try:
            if should_stop and should_stop():
                self._emit_progress(progress_callback, "skipped", 100, "索引已暂停/中断，未写入向量数据库", {
                    "total_chunks": len(texts),
                })
                return []
            embeddings = self._embed(texts, progress_callback=progress_callback)
            if should_stop and should_stop():
                self._emit_progress(progress_callback, "skipped", 100, "索引已暂停/中断，未写入向量数据库", {
                    "total_chunks": len(texts),
                })
                return []
            self._emit_progress(progress_callback, "writing", 85, f"正在写入向量数据库：{len(texts)} 个文本块", {
                "total_chunks": len(texts),
            })
            self._collection.add(
                ids=doc_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            logger.info(f"RAG [{self.world_id}]: 添加 {len(texts)} 个文档 ({source})")
            self._emit_progress(progress_callback, "done", 100, f"索引完成：已写入 {len(texts)} 个文本块", {
                "total_chunks": len(texts),
                "doc_ids": doc_ids,
            })
            return doc_ids
        except Exception as e:
            logger.error(f"RAG 添加文档失败: {e}")
            raise

    def add_text_chunks(
        self,
        text: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
        source: str = "manual",
        metadata: Optional[Dict[str, Any]] = None,
        chunk_preset: str = "default",
        progress_callback: Optional[ProgressCallback] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> List[str]:
        """将长文本切块后添加到 RAG。

        Args:
            text: 原始文本
            chunk_size: 兼容旧接口参数；实际会被按文本量自动策略覆盖
            chunk_overlap: 兼容旧接口参数；实际会被按文本量自动策略覆盖
            source: 来源标识
            metadata: 附加元数据

        Returns:
            文档 ID 列表
        """
        text_len = len(text or "")
        rag_profile = get_rag_text_volume_profile(text_len)
        requested_chunk_size = chunk_size
        requested_chunk_overlap = chunk_overlap
        chunk_size = int(rag_profile["rag_chunk_size"])
        chunk_overlap = int(rag_profile["rag_chunk_overlap"])
        preset = str(chunk_preset or rag_profile["rag_chunk_preset"] or "default").strip().lower()
        if preset not in {item["id"] for item in RAG_CHUNK_PRESETS}:
            preset = "default"
        base_meta = dict(metadata or {})
        source_hash = base_meta.get("source_hash") or hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest()

        if should_stop and should_stop():
            self._emit_progress(progress_callback, "skipped", 100, "索引已暂停/中断，未开始写入向量数据库", {
                "text_length": text_len,
            })
            return []

        existing_doc_ids = self.find_document_ids_by_source_hash(source_hash, source=source)
        if existing_doc_ids:
            self._emit_progress(progress_callback, "done", 100, f"该文本已索引，跳过重复写入：{len(existing_doc_ids)} 个文本块", {
                "total_chunks": len(existing_doc_ids),
                "deduplicated": True,
                "source_hash": source_hash,
            })
            logger.info(f"RAG [{self.world_id}]: source_hash 已存在，跳过重复索引 ({len(existing_doc_ids)} 文档)")
            return existing_doc_ids

        self._emit_progress(progress_callback, "preprocessing", 5, f"正在预处理文本：{text_len} 字符（自动 {rag_profile['profile']} RAG策略，{chunk_size} 字/块）", {
            "chunk_preset": preset,
            "text_length": text_len,
            "rag_volume_profile": rag_profile,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "chunk_strategy": rag_profile.get("strategy"),
            "requested_chunk_size_ignored": requested_chunk_size,
            "requested_chunk_overlap_ignored": requested_chunk_overlap,
        })
        chunks_with_meta = self._split_text_by_preset(text, preset, chunk_size, chunk_overlap)
        if not chunks_with_meta:
            return []

        chunks = [item[0] for item in chunks_with_meta]
        if should_stop and should_stop():
            self._emit_progress(progress_callback, "skipped", 100, "索引已暂停/中断，未写入向量数据库", {
                "chunk_count": len(chunks),
            })
            return []
        self._emit_progress(progress_callback, "splitting", 18, f"切分完成：使用{self._preset_name(preset)}，生成 {len(chunks)} 个文本块", {
            "chunk_preset": preset,
            "chunk_count": len(chunks),
            "chapter_count": len({meta.get("chapter_index") for _, meta in chunks_with_meta if meta.get("chapter_index") is not None}),
            "rag_volume_profile": rag_profile,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "chunk_strategy": rag_profile.get("strategy"),
        })

        cursor = 0
        metadatas = []
        for i, (chunk_text, chunk_meta) in enumerate(chunks_with_meta):
            found = (text or "").find(chunk_text[: min(len(chunk_text), 200)], cursor)
            start = found if found >= 0 else cursor
            end = start + len(chunk_text)
            cursor = max(cursor, end)
            metadatas.append({
                **base_meta,
                **chunk_meta,
                "source": source,
                "source_hash": source_hash,
                "cache_key": base_meta.get("cache_key", ""),
                "rag_profile": preset,
                "rag_chunk_index": i,
                "rag_chunk_count": len(chunks),
                "char_range": [start, end],
                "chapter_title": chunk_meta.get("chapter_title", ""),
                "source_text_length": text_len,
                "indexed_at": datetime.now().isoformat(),
                "chunk_index": i,
                "chunk_count": len(chunks),
                "chunk_preset": preset,
                "rag_volume_profile": rag_profile["profile"],
                "rag_chunk_size": chunk_size,
                "rag_chunk_overlap": chunk_overlap,
                "text_length": len(chunk_text),
            })

        return self.add_documents(
            texts=chunks,
            metadatas=metadatas,
            source=source,
            progress_callback=progress_callback,
            should_stop=should_stop,
        )

    def _preset_name(self, preset: str) -> str:
        for item in RAG_CHUNK_PRESETS:
            if item["id"] == preset:
                return item["name"]
        return preset

    def _split_text_by_preset(self, text: str, preset: str, chunk_size: int, chunk_overlap: int) -> List[Tuple[str, Dict[str, Any]]]:
        if preset == "novel":
            chunks = self._split_novel_chapters(text, chunk_size, chunk_overlap)
            if chunks:
                return chunks
        return [(chunk, {}) for chunk in self._split_text(text, chunk_size, chunk_overlap)]

    def _split_novel_chapters(self, text: str, chunk_size: int, chunk_overlap: int) -> List[Tuple[str, Dict[str, Any]]]:
        clean_text = text.strip()
        if not clean_text:
            return []
        matches = list(CHAPTER_HEADING_RE.finditer(clean_text))
        if not matches:
            return [(chunk, {}) for chunk in self._split_text(clean_text, chunk_size, chunk_overlap)]

        results: List[Tuple[str, Dict[str, Any]]] = []
        for chapter_index, match in enumerate(matches):
            start = match.start()
            end = matches[chapter_index + 1].start() if chapter_index + 1 < len(matches) else len(clean_text)
            chapter_text = clean_text[start:end].strip()
            title = match.group("title").strip()
            if not chapter_text:
                continue
            if len(chapter_text) <= chunk_size:
                results.append((chapter_text, {
                    "chapter_title": title,
                    "chapter_index": chapter_index,
                    "chapter_chunk_index": 0,
                    "chapter_chunk_count": 1,
                }))
                continue

            sub_chunks = self._split_text(chapter_text, chunk_size, chunk_overlap)
            for sub_index, sub_chunk in enumerate(sub_chunks):
                results.append((sub_chunk, {
                    "chapter_title": title,
                    "chapter_index": chapter_index,
                    "chapter_chunk_index": sub_index,
                    "chapter_chunk_count": len(sub_chunks),
                }))
        return results

    def _split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """按段落边界智能切分。优先在空行处断句。"""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) + 2 <= chunk_size:
                current = current + "\n\n" + para if current else para
            else:
                if current:
                    chunks.append(current)
                if len(para) <= chunk_size:
                    current = para
                else:
                    # 单个段落超过 chunk_size，按句子切分
                    if current:
                        chunks.append(current)
                    current = ""
                    sub_chunks = self._split_long_paragraph(para, chunk_size, chunk_overlap)
                    chunks.extend(sub_chunks)

        if current:
            chunks.append(current)

        return chunks

    def _split_long_paragraph(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """按句子边界切分超长段落。"""
        import re
        sentences = re.split(r"(?<=[。！？.!?])\s*", text)
        chunks = []
        current = ""
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(current) + len(sent) <= chunk_size:
                current = current + sent if current else sent
            else:
                if current:
                    chunks.append(current)
                current = sent
        if current:
            chunks.append(current)
        return chunks

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[RagSearchResult]:
        """语义检索。

        Args:
            query: 查询文本
            top_k: 返回条数（默认用配置）
            where: ChromaDB 过滤条件

        Returns:
            检索结果列表（按相似度降序）
        """
        top_k = top_k or Config.RAG_TOP_K
        try:
            query_embedding = self._embed([query])[0]
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            search_results = []
            if results and results.get("ids") and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    search_results.append(RagSearchResult(
                        doc_id=results["ids"][0][i],
                        text=results["documents"][0][i] if results.get("documents") else "",
                        score=1.0 - results["distances"][0][i] if results.get("distances") else 0.0,
                        metadata=results["metadatas"][0][i] if results.get("metadatas") else {},
                    ))

            logger.debug(f"RAG [{self.world_id}]: 检索 '{query[:50]}...' -> {len(search_results)} 结果")
            return search_results

        except Exception as e:
            logger.error(f"RAG 检索失败: {e}")
            return []

    def search_text(self, query: str, top_k: int = None) -> str:
        """检索并返回拼接后的上下文文本，供 LLM 注入。

        Args:
            query: 查询文本
            top_k: 返回条数

        Returns:
            格式化的上下文字符串
        """
        results = self.search(query, top_k=top_k)
        if not results:
            return ""

        parts = ["## 相关知识库内容\n"]
        for i, r in enumerate(results):
            source = r.metadata.get("source", "未知")
            parts.append(f"[{i + 1}] (来源: {source}, 相关度: {r.score:.2f})\n{r.text}\n")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Collection 管理
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Collection 中文档数量。"""
        try:
            return self._collection.count()
        except Exception:
            return 0

    def find_document_ids_by_source_hash(self, source_hash: str, source: str = "extraction") -> List[str]:
        """按原文 hash 查找已有文档，用于避免重复索引同一份扫描输入。"""
        source_hash = str(source_hash or "").strip()
        if not source_hash:
            return []
        try:
            result = self._collection.get(
                where={"source_hash": source_hash},
                include=["metadatas"],
                limit=100000,
            )
        except Exception as e:
            logger.warning(f"RAG [{self.world_id}]: 查询 source_hash 去重失败: {e}")
            return []

        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []
        if not source:
            return list(ids)
        matched = []
        for doc_id, metadata in zip(ids, metadatas):
            if not isinstance(metadata, dict) or metadata.get("source") == source:
                matched.append(doc_id)
        return matched

    def get_stats(self) -> Dict[str, Any]:
        """获取 RAG 统计信息。"""
        doc_count = self.count()
        return {
            "world_id": self.world_id,
            "collection_name": self.collection_name,
            "document_count": doc_count,
            "has_documents": doc_count > 0,
        }

    def export_documents_for_scan(self, limit: int = 100000) -> Dict[str, Any]:
        """导出当前知识库文本，作为世界观扫描输入。"""
        total = self.count()
        if total <= 0:
            return {"text": "", "document_count": 0, "text_length": 0}

        def _coerce_int(value: Any, default: int = 0) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _parse_char_range(value: Any) -> Tuple[int, int]:
            if isinstance(value, (list, tuple)) and len(value) >= 2:
                return _coerce_int(value[0], 0), _coerce_int(value[1], 0)
            if isinstance(value, str):
                matches = re.findall(r"\d+", value)
                if len(matches) >= 2:
                    return _coerce_int(matches[0], 0), _coerce_int(matches[1], 0)
            return 0, 0

        fetch_limit = max(1, min(int(limit or total), total))
        page_size = min(500, fetch_limit)
        records = []
        offset = 0
        fetched = 0
        try:
            while fetched < fetch_limit:
                batch_size = min(page_size, fetch_limit - fetched)
                docs = self.list_documents(limit=batch_size, offset=offset)
                if not docs:
                    break
                for index, doc in enumerate(docs, start=fetched):
                    text = str(doc.text or "").strip()
                    if not text:
                        continue
                    metadata = doc.metadata if isinstance(doc.metadata, dict) else {}
                    char_start, char_end = _parse_char_range(metadata.get("char_range"))
                    records.append({
                        "doc_id": doc.doc_id,
                        "text": text,
                        "metadata": metadata,
                        "source_hash": str(metadata.get("source_hash") or ""),
                        "source": str(metadata.get("source") or "rag"),
                        "source_label": str(metadata.get("filename") or metadata.get("source_label") or metadata.get("source") or "rag").strip(),
                        "source_text_length": _coerce_int(metadata.get("source_text_length"), len(text)),
                        "chapter_title": str(metadata.get("chapter_title") or "").strip(),
                        "chapter_index": _coerce_int(metadata.get("chapter_index"), 0),
                        "chunk_index": _coerce_int(
                            metadata.get("rag_chunk_index")
                            if metadata.get("rag_chunk_index") is not None
                            else metadata.get("chunk_index"),
                            index,
                        ),
                        "char_start": char_start,
                        "char_end": char_end,
                    })
                batch_count = len(docs)
                fetched += batch_count
                offset += batch_count
                if batch_count < batch_size:
                    break
        except Exception as e:
            logger.error(f"导出 RAG 扫描文本失败 [{self.world_id}]: {e}", exc_info=True)
            return {"text": "", "document_count": 0, "text_length": 0, "error": str(e)}

        records.sort(key=lambda item: (
            item["source_text_length"],
            item["source_hash"],
            item["chunk_index"],
            item["chapter_index"],
            item["char_start"],
            item["doc_id"],
        ))

        parts = []
        for idx, record in enumerate(records, start=1):
            title_bits = [f"RAG文档 {idx}"]
            if record["source_label"]:
                title_bits.append(f"来源:{record['source_label']}")
            if record["chapter_title"]:
                title_bits.append(f"章节:{record['chapter_title']}")
            elif record["chapter_index"] > 0:
                title_bits.append(f"章节序号:{record['chapter_index'] + 1}")
            if record["char_end"] > record["char_start"]:
                title_bits.append(f"位置:{record['char_start']}-{record['char_end']}")
            parts.append(f"【{' | '.join(title_bits)}】\n{record['text']}")

        text = "\n\n".join(parts)
        return {
            "text": text,
            "document_count": len(records),
            "text_length": len(text),
            "total_count": total,
        }

    def list_documents(self, limit: int = 100, offset: int = 0) -> List[RagDocument]:
        """列出 Collection 中的文档（分页）。"""
        try:
            result = self._collection.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"],
            )
            docs = []
            if result and result.get("ids"):
                for i in range(len(result["ids"])):
                    docs.append(RagDocument(
                        doc_id=result["ids"][i],
                        text=result["documents"][i] if result.get("documents") else "",
                        metadata=result["metadatas"][i] if result.get("metadatas") else {},
                    ))
            return docs
        except Exception as e:
            logger.error(f"列出文档失败 [{self.world_id}]: {e}", exc_info=True)
            return []

    def delete_document(self, doc_id: str) -> bool:
        """删除单个文档。"""
        try:
            self._collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def delete_all(self) -> bool:
        """清空 Collection（删除后重建以彻底清除向量数据）。"""
        try:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.create_collection(
                name=self.collection_name,
                metadata={"world_id": self.world_id, "hnsw:space": "cosine"},
            )
            logger.info(f"RAG [{self.world_id}]: Collection 已清空重建")
            return True
        except Exception as e:
            logger.error(f"清空 Collection 失败: {e}")
            return False

    @classmethod
    def delete_world_rag(cls, world_id: str) -> bool:
        """删除世界观对应的 RAG Collection（世界观删除时调用）。"""
        try:
            client = _get_chroma_client()
            collection_name = _world_collection_name(world_id)
            client.delete_collection(collection_name)
            logger.info(f"RAG Collection 已删除: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"删除 RAG Collection 失败: {e}")
            return False
