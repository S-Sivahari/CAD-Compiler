"""RAG module — provides the plug-in interface for semantic template retrieval."""

from rag.provider import RAGResult, RAGProvider, ChromaRAGProvider, NullRAGProvider

__all__ = ["RAGResult", "RAGProvider", "ChromaRAGProvider", "NullRAGProvider"]
