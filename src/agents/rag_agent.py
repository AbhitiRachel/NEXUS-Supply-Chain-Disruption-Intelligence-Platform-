"""
rag_agent.py
------------
RAG Agent: retrieves the most relevant documents (contracts, disruption
notices, shipping reports) for a natural-language query.

Two backends behind the same interface, same pattern as graph_agent.py:
  - LocalRAGBackend: TF-IDF retrieval using scikit-learn. No server, no
    API key, no embeddings model needed -- this is what lets retrieval
    quality be tested and demoed right now, and is a legitimate fallback
    if a live ChromaDB/embedding-API connection fails during a demo.
  - ChromaDBBackend: swaps in real vector embeddings (e.g. via a free
    sentence-transformers model or an API embedding) once ChromaDB is
    set up locally -- same .retrieve() interface, so nothing else in the
    codebase needs to change.

Why TF-IDF is a legitimate fallback, not just a shortcut: this document
corpus is small (27 docs) and keyword-rich (entity names, disruption
types) -- exactly the case where TF-IDF performs close to semantic
embeddings anyway. The report should be explicit that the production
path is ChromaDB with real embeddings; TF-IDF is the tested, zero-
dependency baseline.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DOCS_DIR = Path(__file__).parent.parent.parent / "data" / "documents"


@dataclass
class RetrievedDoc:
    filename: str
    doc_type: str
    entity_id: str
    entity_name: str
    score: float
    text: str


class LocalRAGBackend:
    """TF-IDF retrieval over the synthetic document corpus. No server required."""

    def __init__(self, docs_dir: Path = DOCS_DIR):
        self.docs_dir = docs_dir
        index = json.loads((docs_dir / "documents_index.json").read_text())

        self.metadata = index
        self.texts = [
            (docs_dir / doc["filename"]).read_text() for doc in index
        ]

        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.doc_matrix = self.vectorizer.fit_transform(self.texts)

    def retrieve(self, query: str, top_k: int = 3, doc_type: str | None = None) -> list[RetrievedDoc]:
        """
        Returns the top_k most relevant documents for the query, optionally
        filtered to a specific doc_type ('contract', 'disruption_notice',
        'shipping_report').
        """
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.doc_matrix)[0]

        ranked_indices = scores.argsort()[::-1]

        results = []
        for idx in ranked_indices:
            meta = self.metadata[idx]
            if doc_type and meta["doc_type"] != doc_type:
                continue
            if scores[idx] <= 0:
                continue  # no lexical overlap at all -- not a real match
            results.append(
                RetrievedDoc(
                    filename=meta["filename"],
                    doc_type=meta["doc_type"],
                    entity_id=meta["entity_id"],
                    entity_name=meta["entity_name"],
                    score=round(float(scores[idx]), 4),
                    text=self.texts[idx],
                )
            )
            if len(results) >= top_k:
                break

        return results


def connect_chromadb(persist_dir: str = "./chroma_store"):
    """
    Returns a ChromaDBBackend with the same .retrieve() interface, once
    chromadb is installed (`pip install chromadb`). Not implemented in
    this sandbox (no network access to install/test it here) -- swap
    LocalRAGBackend for this once you have it running locally; nothing
    else in the codebase needs to change since the interface matches.
    """
    raise NotImplementedError(
        "ChromaDBBackend requires `pip install chromadb` (needs network "
        "access, unavailable in this build environment). Use LocalRAGBackend "
        "for development and testing; wire this up once ChromaDB is "
        "installed locally."
    )
