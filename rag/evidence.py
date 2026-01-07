"""
Evidence objects for RAG retrieval.
Represents retrieved chunks with metadata and scores.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class Evidence:
    """Evidence retrieved from knowledge base."""

    source_id: str  # Unique identifier for the chunk
    doc_title: str  # Document title
    doc_type: str  # sop, faq, pricing, policy, etc.
    chunk_text: str  # The actual text content
    score: float  # Relevance score (0-1)
    chunk_index: int  # Index within source document
    source_file: str  # Original file path
    metadata: Dict[str, Any]  # Additional metadata
    retrieved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_id": self.source_id,
            "doc_title": self.doc_title,
            "doc_type": self.doc_type,
            "chunk_text": self.chunk_text,
            "score": self.score,
            "chunk_index": self.chunk_index,
            "source_file": self.source_file,
            "metadata": self.metadata,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None
        }

    def format_citation(self) -> str:
        """Format as citation for LLM response."""
        return f"[{self.doc_title} - {self.doc_type}]"

    def is_high_quality(self, threshold: float = 0.7) -> bool:
        """Check if evidence meets quality threshold."""
        return self.score >= threshold
