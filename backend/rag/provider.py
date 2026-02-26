"""RAG Provider Interface — plug-in contract for SynthoCAD.

Implement ``RAGProvider`` (or any class that satisfies the same signature)
and pass an instance to `SynthoCadPipeline` to enable semantic template
retrieval.

The provider is responsible for:
  1. Accepting a natural-language user prompt.
  2. Returning a ranked list of ``RAGResult`` dicts.

Everything else (ChromaDB, embedding model choice, image storage, etc.)
lives **inside** the provider — the pipeline never touches it directly.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ── Result data structure ────────────────────────────────────────────────

@dataclass
class RAGResult:
    """One item returned by a RAG query.

    Only ``description`` and ``json_data`` are required.
    Everything else is optional and used for ranking / display.
    """
    description: str                       # textual description of the template
    json_data:   Dict[str, Any]            # the SCL JSON content
    score:       float            = 0.0    # similarity / relevance score (higher = better)
    json_path:   Optional[str]   = None   # path on disk (if available)
    image_path:  Optional[str]   = None   # preview image (if available)
    source_id:   Optional[str]   = None   # unique identifier inside the store
    metadata:    Dict[str, Any]  = field(default_factory=dict)  # anything extra


# ── Provider protocol (duck-typing-friendly) ─────────────────────────────

@runtime_checkable
class RAGProvider(Protocol):
    """Minimal interface every RAG back-end must satisfy.

    You can implement this as a plain class — no need to inherit from
    anything.  The pipeline only calls ``query()`` and optionally
    ``is_ready()``.

    Example
    -------
    >>> class MyRAG:
    ...     def query(self, prompt, n_results=3):
    ...         return [RAGResult(description="...", json_data={...})]
    ...     def is_ready(self):
    ...         return True
    """

    def query(self, prompt: str, n_results: int = 3) -> List[RAGResult]:
        """Return up to *n_results* ``RAGResult`` objects for *prompt*."""
        ...

    def is_ready(self) -> bool:
        """Return True when the provider has data and can serve queries."""
        ...


# ── Concrete adapter wrapping the existing ChromaDB code ─────────────────

class ChromaRAGProvider:
    """Adapts the existing ``rag.query.query_cad_templates`` to the
    ``RAGProvider`` protocol.

    Instantiate with no arguments — it uses the existing ChromaDB setup.
    """

    def query(self, prompt: str, n_results: int = 3) -> List[RAGResult]:
        from rag.query import query_cad_templates
        raw = query_cad_templates(prompt, n_results=n_results)
        results: List[RAGResult] = []
        for i, item in enumerate(raw):
            results.append(RAGResult(
                description=item.get("description", ""),
                json_data=item.get("json", {}),
                score=1.0 - (i * 0.1),          # approximate ranking
                json_path=item.get("json_path"),
                source_id=item.get("id"),
            ))
        return results

    def is_ready(self) -> bool:
        try:
            from rag.db import get_collection
            col = get_collection()
            return col.count() > 0
        except Exception:
            return False


# ── Null provider (used when no RAG is configured) ───────────────────────

class NullRAGProvider:
    """Stub that returns nothing — allows the pipeline to run without RAG."""

    def query(self, prompt: str, n_results: int = 3) -> List[RAGResult]:
        return []

    def is_ready(self) -> bool:
        return False
