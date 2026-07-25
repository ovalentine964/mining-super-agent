"""
RAG Pipeline for Mining Domain
===============================
Document ingestion, domain-aware chunking, BGE embeddings,
hybrid retrieval (BM25 + dense), cross-encoder re-ranking,
and cited generation.

Every claim in generated responses must have a source citation.
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


# ── Domain-aware chunking ─────────────────────────────────────────────────────
# Geological documents have specific section patterns
GEOLOGICAL_SECTION_PATTERNS = [
    r"^#{1,3}\s+",                          # Markdown headers
    r"^(?:Abstract|Introduction|Conclusion|Results|Discussion|Methodology)",
    r"^(?:STRATIGRAPHY|LITHOLOGY|MINERALOGY|GEOCHEMISTRY|ALTERATION)",
    r"^\d+\.\d*\s+[A-Z]",                   # Numbered sections
    r"^(?:Table|Figure|Plate)\s+\d+",        # Figure/table captions
]

# Sentence boundary patterns for chunking
SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

# Overlap tokens between chunks
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64
DEFAULT_TOP_K = 10
RERANK_TOP_K = 5


@dataclass
class Document:
    """An ingested document."""
    doc_id: str
    title: str
    source: str                    # "pdf", "paper", "report", "web"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List["Chunk"] = field(default_factory=list)


@dataclass
class Chunk:
    """A document chunk with embedding."""
    chunk_id: str
    doc_id: str
    text: str
    start_idx: int
    end_idx: int
    section: Optional[str] = None
    embedding: Optional[np.ndarray] = None
    bm25_score: float = 0.0
    dense_score: float = 0.0
    rerank_score: float = 0.0


@dataclass
class RetrievalResult:
    """A single retrieval result with scores and citation."""
    chunk: Chunk
    final_score: float
    citation: str                  # Formatted citation string


@dataclass
class RAGResponse:
    """RAG pipeline response with citations."""
    answer: str
    citations: List[str]
    sources: List[Dict[str, Any]]
    confidence: float
    retrieval_results: List[RetrievalResult]


class BM25Index:
    """
    BM25 sparse retrieval index.
    Simple in-memory implementation for mining documents.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[Chunk] = []
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.num_docs: int = 0
        self._index_built = False

    def add_chunks(self, chunks: List[Chunk]):
        """Add chunks to the BM25 index."""
        self.chunks.extend(chunks)
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild the BM25 index from all chunks."""
        self.num_docs = len(self.chunks)
        self.doc_freqs.clear()
        self.doc_lengths.clear()

        total_length = 0
        for chunk in self.chunks:
            tokens = self._tokenize(chunk.text)
            self.doc_lengths.append(len(tokens))
            total_length += len(tokens)

            # Document frequency
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_doc_length = total_length / max(self.num_docs, 1)
        self._index_built = True

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Tuple[Chunk, float]]:
        """Search using BM25 scoring."""
        if not self._index_built:
            self._rebuild_index()

        query_tokens = self._tokenize(query)
        scores = []

        for i, chunk in enumerate(self.chunks):
            score = self._score(query_tokens, i)
            scores.append((chunk, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _score(self, query_tokens: List[str], doc_idx: int) -> float:
        """Compute BM25 score for a document."""
        doc_tokens = self._tokenize(self.chunks[doc_idx].text)
        doc_len = self.doc_lengths[doc_idx]
        tf = {}

        for token in doc_tokens:
            tf[token] = tf.get(token, 0) + 1

        score = 0.0
        for qt in query_tokens:
            if qt not in tf:
                continue

            term_freq = tf[qt]
            doc_freq = self.doc_freqs.get(qt, 0)

            # IDF component
            idf = max(0, np.log((self.num_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1))

            # TF component with length normalization
            tf_norm = (term_freq * (self.k1 + 1)) / (
                term_freq + self.k1 * (1 - self.b + self.b * doc_len / max(self.avg_doc_length, 1))
            )
            score += idf * tf_norm

        return score

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenization: lowercase, split on non-alphanumeric."""
        return re.findall(r'[a-z0-9]+', text.lower())


class DenseRetriever:
    """
    Dense vector retrieval using BGE embeddings.
    Uses BAAI/bge-large-en-v1.5 for embedding.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5",
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._tokenizer = None
        self.embeddings: Optional[np.ndarray] = None
        self.chunks: List[Chunk] = []

    def _load_model(self):
        """Lazy-load the embedding model."""
        if self._model is not None:
            return

        try:
            from transformers import AutoModel, AutoTokenizer
            import torch

            self.device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
            logger.info("Loading BGE embedding model: %s", self.model_name)

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name).to(self.device)
            self._model.eval()

        except ImportError:
            logger.warning("transformers not available, using sentence-transformers fallback")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device or "cpu")
            except ImportError:
                raise ImportError(
                    "Either transformers or sentence-transformers required. "
                    "pip install sentence-transformers"
                )

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts to dense vectors."""
        self._load_model()

        try:
            # Try sentence-transformers first (simpler API)
            from sentence_transformers import SentenceTransformer
            if isinstance(self._model, SentenceTransformer):
                return self._model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        except (ImportError, AttributeError):
            pass

        # HuggingFace transformers path
        import torch

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            inputs = self._tokenizer(
                batch, padding=True, truncation=True,
                max_length=512, return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                outputs = self._model(**inputs)
                # Mean pooling
                attention_mask = inputs["attention_mask"].unsqueeze(-1)
                embeddings = (outputs.last_hidden_state * attention_mask).sum(1)
                embeddings = embeddings / attention_mask.sum(1)
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            all_embeddings.append(embeddings.cpu().numpy())

        return np.vstack(all_embeddings)

    def add_chunks(self, chunks: List[Chunk]):
        """Index chunks with dense embeddings."""
        texts = [c.text for c in chunks]
        self.embeddings = self.encode(texts)
        self.chunks = chunks
        # Store embeddings in chunks
        for chunk, emb in zip(chunks, self.embeddings):
            chunk.embedding = emb

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Tuple[Chunk, float]]:
        """Search using cosine similarity."""
        if self.embeddings is None or len(self.chunks) == 0:
            return []

        query_emb = self.encode([query])[0]

        # Cosine similarity
        similarities = np.dot(self.embeddings, query_emb) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_emb) + 1e-8
        )

        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [(self.chunks[i], float(similarities[i])) for i in top_indices]


class CrossEncoderReranker:
    """
    Cross-encoder re-ranking using BAAI/bge-reranker-v2-m3.
    Re-ranks retrieval results for higher precision.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """Lazy-load the reranker model."""
        if self._model is not None:
            return

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch

            self.device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
            logger.info("Loading cross-encoder reranker: %s", self.model_name)

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            ).to(self.device)
            self._model.eval()
        except ImportError:
            raise ImportError("transformers required for cross-encoder reranking")

    def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int = RERANK_TOP_K,
    ) -> List[Tuple[Chunk, float]]:
        """Re-rank chunks by relevance to query."""
        self._load_model()

        import torch

        # Score each query-document pair
        scores = []
        pairs = [(query, chunk.text) for chunk in chunks]

        for pair in pairs:
            inputs = self._tokenizer(
                pair[0], pair[1],
                padding=True, truncation=True,
                max_length=512, return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                outputs = self._model(**inputs)
                score = outputs.logits.squeeze().item()

            scores.append(score)

        # Sort by rerank score
        scored = list(zip(chunks, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:top_k]


class RAGPipeline:
    """
    Complete RAG pipeline for mining domain.

    Pipeline: Ingest → Chunk → Embed → Retrieve (hybrid) → Re-rank → Generate (cited)
    """

    def __init__(
        self,
        embedding_model: str = "BAAI/bge-large-en-v1.5",
        reranker_model: str = "BAAI/bge-reranker-v2-m3",
        device: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize retrieval components
        self.bm25 = BM25Index()
        self.dense = DenseRetriever(model_name=embedding_model, device=device)
        self.reranker = CrossEncoderReranker(model_name=reranker_model, device=device)

        # Document store
        self.documents: Dict[str, Document] = {}
        self.all_chunks: List[Chunk] = []

        logger.info("RAGPipeline initialized (chunk_size=%d, overlap=%d)", chunk_size, chunk_overlap)

    def ingest_document(
        self,
        content: str,
        title: str = "",
        source: str = "unknown",
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """
        Ingest a document: chunk it and add to retrieval indices.
        """
        if not doc_id:
            doc_id = hashlib.md5(content[:1000].encode()).hexdigest()[:12]

        doc = Document(
            doc_id=doc_id,
            title=title,
            source=source,
            content=content,
            metadata=metadata or {},
        )

        # Chunk with domain-aware splitting
        doc.chunks = self._chunk_document(doc)
        self.documents[doc_id] = doc
        self.all_chunks.extend(doc.chunks)

        # Add to indices
        self.bm25.add_chunks(doc.chunks)
        self.dense.add_chunks(doc.chunks)

        logger.info("Ingested document '%s' (%d chunks)", title or doc_id, len(doc.chunks))
        return doc

    def ingest_file(self, path: Union[str, Path], **kwargs) -> Document:
        """Ingest a file (PDF, text, markdown)."""
        path = Path(path)

        if path.suffix.lower() == ".pdf":
            content = self._extract_pdf(path)
        elif path.suffix.lower() in {".txt", ".md", ".markdown"}:
            content = path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        return self.ingest_document(
            content=content,
            title=path.stem,
            source=str(path),
            **kwargs,
        )

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        rerank: bool = True,
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval: BM25 + dense vector, then cross-encoder re-ranking.
        """
        # BM25 retrieval
        bm25_results = self.bm25.search(query, top_k=top_k)

        # Dense retrieval
        dense_results = self.dense.search(query, top_k=top_k)

        # Merge results (Reciprocal Rank Fusion)
        merged = self._merge_results(bm25_results, dense_results, top_k=top_k)

        # Re-rank with cross-encoder
        if rerank:
            try:
                reranked = self.reranker.rerank(query, [c for c, _ in merged], top_k=RERANK_TOP_K)
            except Exception as exc:
                logger.warning("Reranking failed, using merged results: %s", exc)
                reranked = merged[:RERANK_TOP_K]
        else:
            reranked = merged[:RERANK_TOP_K]

        # Build results with citations
        results = []
        for chunk, score in reranked:
            citation = self._format_citation(chunk)
            results.append(RetrievalResult(
                chunk=chunk,
                final_score=score,
                citation=citation,
            ))

        return results

    def query(
        self,
        question: str,
        top_k: int = DEFAULT_TOP_K,
        rerank: bool = True,
    ) -> RAGResponse:
        """
        Full RAG query: retrieve → format → return with citations.
        Generation is handled by the caller (LLM) with the retrieved context.
        """
        results = self.retrieve(question, top_k=top_k, rerank=rerank)

        # Build context for generation
        context_parts = []
        citations = []
        sources = []

        for i, result in enumerate(results, 1):
            context_parts.append(f"[{i}] {result.chunk.text}")
            citations.append(result.citation)
            sources.append({
                "doc_id": result.chunk.doc_id,
                "title": self.documents.get(result.chunk.doc_id, Document("", "", "", "")).title,
                "citation": result.citation,
                "score": round(result.final_score, 4),
                "text_preview": result.chunk.text[:200],
            })

        # Confidence based on retrieval quality
        avg_score = np.mean([r.final_score for r in results]) if results else 0.0
        confidence = min(1.0, max(0.0, avg_score))

        # Format the context for the LLM
        context = "\n\n".join(context_parts)

        return RAGResponse(
            answer=context,  # Raw context for LLM to generate from
            citations=citations,
            sources=sources,
            confidence=float(confidence),
            retrieval_results=results,
        )

    def _chunk_document(self, doc: Document) -> List[Chunk]:
        """
        Domain-aware document chunking.
        Splits on geological section boundaries, then falls back to sentence boundaries.
        """
        text = doc.content
        chunks = []

        # Try to split on section boundaries first
        sections = self._split_on_sections(text)

        for section_text, section_name in sections:
            # Further split long sections
            sub_chunks = self._split_text(section_text)
            for chunk_text, start, end in sub_chunks:
                chunk_id = f"{doc.doc_id}_{start}_{end}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc.doc_id,
                    text=chunk_text,
                    start_idx=start,
                    end_idx=end,
                    section=section_name,
                ))

        # If no sections found, fall back to simple chunking
        if not chunks:
            for chunk_text, start, end in self._split_text(text):
                chunk_id = f"{doc.doc_id}_{start}_{end}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc.doc_id,
                    text=chunk_text,
                    start_idx=start,
                    end_idx=end,
                ))

        return chunks

    def _split_on_sections(self, text: str) -> List[Tuple[str, str]]:
        """Split text on geological section headers."""
        sections = []
        current_start = 0
        current_section = "preamble"

        for match in re.finditer(r'^(#{1,3}\s+.+|[A-Z][A-Z\s]{3,}:?)\s*$', text, re.MULTILINE):
            section_text = text[current_start:match.start()].strip()
            if section_text:
                sections.append((section_text, current_section))
            current_section = match.group().strip()
            current_start = match.start()

        # Last section
        remaining = text[current_start:].strip()
        if remaining:
            sections.append((remaining, current_section))

        return sections

    def _split_text(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text into chunks with overlap."""
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence boundary near the end
                search_start = max(start + self.chunk_size - self.chunk_overlap * 2, start)
                segment = text[search_start:end]
                boundaries = list(SENTENCE_BOUNDARY.finditer(segment))
                if boundaries:
                    last_boundary = boundaries[-1]
                    end = search_start + last_boundary.end()

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append((chunk_text, start, end))

            # Move start with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break

        return chunks

    def _merge_results(
        self,
        bm25_results: List[Tuple[Chunk, float]],
        dense_results: List[Tuple[Chunk, float]],
        top_k: int = DEFAULT_TOP_K,
    ) -> List[Tuple[Chunk, float]]:
        """
        Merge BM25 and dense results using Reciprocal Rank Fusion (RRF).
        """
        k = 60  # RRF constant
        scores: Dict[str, float] = {}
        chunk_map: Dict[str, Chunk] = {}

        # BM25 scores
        for rank, (chunk, _) in enumerate(bm25_results):
            rrf = 1.0 / (k + rank + 1)
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + rrf
            chunk_map[chunk.chunk_id] = chunk

        # Dense scores
        for rank, (chunk, _) in enumerate(dense_results):
            rrf = 1.0 / (k + rank + 1)
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + rrf
            chunk_map[chunk.chunk_id] = chunk

        # Sort by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [(chunk_map[cid], scores[cid]) for cid in sorted_ids[:top_k]]

    def _format_citation(self, chunk: Chunk) -> str:
        """Format a citation for a chunk."""
        doc = self.documents.get(chunk.doc_id)
        if doc:
            return f"[{doc.title}] (section: {chunk.section or 'N/A'}, chars {chunk.start_idx}-{chunk.end_idx})"
        return f"[doc:{chunk.doc_id}] (chars {chunk.start_idx}-{chunk.end_idx})"

    @staticmethod
    def _extract_pdf(path: Path) -> str:
        """Extract text from PDF."""
        try:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            return text
        except ImportError:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(path))
                text = "\n\n".join(page.get_text() for page in doc)
                return text
            except ImportError:
                raise ImportError("PDF extraction requires PyPDF2 or PyMuPDF: pip install PyPDF2")
