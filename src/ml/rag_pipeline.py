"""
RAG Pipeline — Document ingestion, domain-aware chunking, BGE embeddings,
hybrid retrieval (BM25 + dense), cross-encoder re-ranking, cited generation.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64
DEFAULT_TOP_K = 10
RERANK_TOP_K = 5
SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


@dataclass
class Document:
    doc_id: str
    title: str
    source: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List["Chunk"] = field(default_factory=list)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    start_idx: int
    end_idx: int
    section: Optional[str] = None
    embedding: Optional[np.ndarray] = None


@dataclass
class RetrievalResult:
    chunk: Chunk
    final_score: float
    citation: str


@dataclass
class RAGResponse:
    answer: str
    citations: List[str]
    sources: List[Dict[str, Any]]
    confidence: float
    retrieval_results: List[RetrievalResult]


class BM25Index:
    """BM25 sparse retrieval index."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[Chunk] = []
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.num_docs: int = 0

    def add_chunks(self, chunks: List[Chunk]):
        self.chunks.extend(chunks)
        self._rebuild_index()

    def _rebuild_index(self):
        self.num_docs = len(self.chunks)
        self.doc_freqs.clear()
        self.doc_lengths.clear()
        total_length = 0
        for chunk in self.chunks:
            tokens = self._tokenize(chunk.text)
            self.doc_lengths.append(len(tokens))
            total_length += len(tokens)
            for token in set(tokens):
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1
        self.avg_doc_length = total_length / max(self.num_docs, 1)

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Tuple[Chunk, float]]:
        query_tokens = self._tokenize(query)
        scores = [(chunk, self._score(query_tokens, i)) for i, chunk in enumerate(self.chunks)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _score(self, query_tokens: List[str], doc_idx: int) -> float:
        doc_tokens = self._tokenize(self.chunks[doc_idx].text)
        tf = {}
        for t in doc_tokens:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        doc_len = self.doc_lengths[doc_idx]
        for qt in query_tokens:
            if qt not in tf:
                continue
            df = self.doc_freqs.get(qt, 0)
            idf = max(0, np.log((self.num_docs - df + 0.5) / (df + 0.5) + 1))
            tf_norm = (tf[qt] * (self.k1 + 1)) / (tf[qt] + self.k1 * (1 - self.b + self.b * doc_len / max(self.avg_doc_length, 1)))
            score += idf * tf_norm
        return score

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r'[a-z0-9]+', text.lower())


class DenseRetriever:
    """Dense vector retrieval using BGE embeddings."""

    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device
        self._model = None
        self.embeddings: Optional[np.ndarray] = None
        self.chunks: List[Chunk] = []

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device or "cpu")
        except ImportError:
            raise ImportError("sentence-transformers required: pip install sentence-transformers")

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        self._load_model()
        return self._model.encode(texts, batch_size=batch_size, show_progress_bar=False)

    def add_chunks(self, chunks: List[Chunk]):
        texts = [c.text for c in chunks]
        self.embeddings = self.encode(texts)
        self.chunks = chunks
        for chunk, emb in zip(chunks, self.embeddings):
            chunk.embedding = emb

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Tuple[Chunk, float]]:
        if self.embeddings is None or len(self.chunks) == 0:
            return []
        query_emb = self.encode([query])[0]
        similarities = np.dot(self.embeddings, query_emb) / (np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_emb) + 1e-8)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [(self.chunks[i], float(similarities[i])) for i in top_indices]


class CrossEncoderReranker:
    """Cross-encoder re-ranking using BAAI/bge-reranker-v2-m3."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        if self._model is not None:
            return
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch
        self.device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name).to(self.device)
        self._model.eval()

    def rerank(self, query: str, chunks: List[Chunk], top_k: int = RERANK_TOP_K) -> List[Tuple[Chunk, float]]:
        self._load_model()
        import torch
        scores = []
        for chunk in chunks:
            inputs = self._tokenizer(query, chunk.text, padding=True, truncation=True, max_length=512, return_tensors="pt").to(self.device)
            with torch.no_grad():
                score = self._model(**inputs).logits.squeeze().item()
            scores.append(score)
        scored = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
        return scored[:top_k]


class RAGPipeline:
    """Complete RAG pipeline for mining domain."""

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.bm25 = BM25Index()
        self.dense = DenseRetriever()
        self.reranker = CrossEncoderReranker()
        self.documents: Dict[str, Document] = {}
        self.all_chunks: List[Chunk] = []

    def ingest_document(self, content: str, title: str = "", source: str = "unknown", doc_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Document:
        if not doc_id:
            doc_id = hashlib.md5(content[:1000].encode()).hexdigest()[:12]
        doc = Document(doc_id=doc_id, title=title, source=source, content=content, metadata=metadata or {})
        doc.chunks = self._chunk_document(doc)
        self.documents[doc_id] = doc
        self.all_chunks.extend(doc.chunks)
        self.bm25.add_chunks(doc.chunks)
        self.dense.add_chunks(doc.chunks)
        logger.info("Ingested '%s' (%d chunks)", title or doc_id, len(doc.chunks))
        return doc

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K, rerank: bool = True) -> List[RetrievalResult]:
        bm25_results = self.bm25.search(query, top_k=top_k)
        dense_results = self.dense.search(query, top_k=top_k)
        merged = self._merge_results(bm25_results, dense_results, top_k=top_k)

        if rerank:
            try:
                reranked = self.reranker.rerank(query, [c for c, _ in merged], top_k=RERANK_TOP_K)
            except Exception:
                reranked = merged[:RERANK_TOP_K]
        else:
            reranked = merged[:RERANK_TOP_K]

        results = []
        for chunk, score in reranked:
            citation = self._format_citation(chunk)
            results.append(RetrievalResult(chunk=chunk, final_score=score, citation=citation))
        return results

    def query(self, question: str, top_k: int = DEFAULT_TOP_K, rerank: bool = True) -> RAGResponse:
        results = self.retrieve(question, top_k=top_k, rerank=rerank)
        context_parts, citations, sources = [], [], []
        for i, result in enumerate(results, 1):
            context_parts.append(f"[{i}] {result.chunk.text}")
            citations.append(result.citation)
            sources.append({
                "doc_id": result.chunk.doc_id,
                "title": self.documents.get(result.chunk.doc_id, Document("", "", "")).title,
                "citation": result.citation,
                "score": round(result.final_score, 4),
            })
        avg_score = np.mean([r.final_score for r in results]) if results else 0.0
        return RAGResponse(
            answer="\n\n".join(context_parts), citations=citations, sources=sources,
            confidence=float(min(1.0, max(0.0, avg_score))), retrieval_results=results,
        )

    def _chunk_document(self, doc: Document) -> List[Chunk]:
        text = doc.content
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                search_start = max(start + self.chunk_size - self.chunk_overlap * 2, start)
                segment = text[search_start:end]
                boundaries = list(SENTENCE_BOUNDARY.finditer(segment))
                if boundaries:
                    end = search_start + boundaries[-1].end()
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_id = f"{doc.doc_id}_{start}_{end}"
                chunks.append(Chunk(chunk_id=chunk_id, doc_id=doc.doc_id, text=chunk_text, start_idx=start, end_idx=end))
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        return chunks

    def _merge_results(self, bm25_results, dense_results, top_k=DEFAULT_TOP_K):
        k = 60
        scores, chunk_map = {}, {}
        for rank, (chunk, _) in enumerate(bm25_results):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + 1.0 / (k + rank + 1)
            chunk_map[chunk.chunk_id] = chunk
        for rank, (chunk, _) in enumerate(dense_results):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + 1.0 / (k + rank + 1)
            chunk_map[chunk.chunk_id] = chunk
        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [(chunk_map[cid], scores[cid]) for cid in sorted_ids[:top_k]]

    def _format_citation(self, chunk: Chunk) -> str:
        doc = self.documents.get(chunk.doc_id)
        if doc:
            return f"[{doc.title}] (chars {chunk.start_idx}-{chunk.end_idx})"
        return f"[doc:{chunk.doc_id}] (chars {chunk.start_idx}-{chunk.end_idx})"
