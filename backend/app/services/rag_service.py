"""RAG 服务 — 基于 ChromaDB 的世界观向量知识库。

每个世界观一个 ChromaDB Collection，存储于 uploads/worlds/{world_id}/rag/
支持：文档添加、文本索引、语义检索、Collection 管理
"""

import os
import uuid
import threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger("worldfish.rag")

# ChromaDB 全局客户端（线程安全）
_chroma_client: Optional[chromadb.PersistentClient] = None
_chroma_lock = threading.Lock()


def _get_chroma_client() -> chromadb.PersistentClient:
    """获取或创建 ChromaDB 持久化客户端（单例）。"""
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                chroma_dir = os.path.join(Config.UPLOAD_FOLDER, "chroma")
                os.makedirs(chroma_dir, exist_ok=True)
                _chroma_client = chromadb.PersistentClient(
                    path=chroma_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                logger.info(f"ChromaDB 已初始化: {chroma_dir}")
    return _chroma_client


def _get_embedding_client() -> OpenAI:
    """获取 Embedding 客户端。
    
    优先使用独立的 Embedding 配置（EMBEDDING_API_KEY / EMBEDDING_BASE_URL），
    未配置时回退到 LLM 配置。
    """
    emb_config = Config.get_embedding_config()
    return OpenAI(api_key=emb_config["api_key"], base_url=emb_config["base_url"])


def _world_collection_name(world_id: str) -> str:
    """世界观对应的 Collection 名称。"""
    return f"world_{world_id}"


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
        self.world_id = world_id
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
            import os
            # 使用 HF 镜像加速下载（中国大陆）
            if not os.environ.get("HF_ENDPOINT"):
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

            from sentence_transformers import SentenceTransformer
            # 使用轻量多语言模型，支持中英文
            model_name = "paraphrase-multilingual-MiniLM-L12-v2"
            logger.info(f"加载本地 Embedding 模型: {model_name}")
            cls._local_model = SentenceTransformer(model_name)
        return cls._local_model

    def _embed(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """将文本列表转为向量。先尝试 API，失败则回退到本地模型。
        
        ModelScope API 请求体限制 6MB，因此分批发送。
        """
        if not texts:
            return []

        emb_config = Config.get_embedding_config()

        def _api_embed_batch(batch: List[str]) -> List[List[float]]:
            response = self._embedding_client.embeddings.create(
                model=emb_config["model_name"],
                input=batch,
                encoding_format="float",
            )
            return [item.embedding for item in response.data]

        all_embeddings = []

        try:
            # 优先使用 API Embedding，分批发送
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                all_embeddings.extend(_api_embed_batch(batch))
            return all_embeddings
        except Exception as e:
            logger.warning(f"API Embedding 失败 ({e})，回退到本地模型")
            try:
                model = self._get_local_embedding_fn()
                embeddings = model.encode(texts, normalize_embeddings=True)
                return [emb.tolist() for emb in embeddings]
            except Exception as local_e:
                logger.error(f"本地 Embedding 也失败: {local_e}")
                raise RuntimeError(f"Embedding 不可用：API({e}) + 本地({local_e})")

    # ------------------------------------------------------------------
    # 文档管理
    # ------------------------------------------------------------------

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        source: str = "manual",
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
            embeddings = self._embed(texts)
            self._collection.add(
                ids=doc_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            logger.info(f"RAG [{self.world_id}]: 添加 {len(texts)} 个文档 ({source})")
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
    ) -> List[str]:
        """将长文本切块后添加到 RAG。

        Args:
            text: 原始文本
            chunk_size: 块大小（默认用配置）
            chunk_overlap: 重叠大小（默认用配置）
            source: 来源标识
            metadata: 附加元数据

        Returns:
            文档 ID 列表
        """
        chunk_size = chunk_size or Config.RAG_CHUNK_SIZE
        chunk_overlap = chunk_overlap or Config.RAG_CHUNK_OVERLAP

        chunks = self._split_text(text, chunk_size, chunk_overlap)
        if not chunks:
            return []

        base_meta = dict(metadata or {})
        metadatas = [
            {**base_meta, "chunk_index": i, "chunk_count": len(chunks)}
            for i in range(len(chunks))
        ]

        return self.add_documents(texts=chunks, metadatas=metadatas, source=source)

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

    def get_stats(self) -> Dict[str, Any]:
        """获取 RAG 统计信息。"""
        doc_count = self.count()
        return {
            "world_id": self.world_id,
            "collection_name": self.collection_name,
            "document_count": doc_count,
            "has_documents": doc_count > 0,
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
