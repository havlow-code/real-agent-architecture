"""
Re-ranking module for retrieved evidence.
Applies hybrid scoring: cosine similarity + recency + source quality.
"""

from typing import List
from datetime import datetime, timezone
import math

from rag.evidence import Evidence
from config import settings


class EvidenceReranker:
    """Re-ranks retrieved evidence using multiple signals."""

    def __init__(
        self,
        cosine_weight: float = 0.6,
        recency_weight: float = 0.2,
        quality_weight: float = 0.2
    ):
        """
        Initialize reranker.

        Args:
            cosine_weight: Weight for cosine similarity score
            recency_weight: Weight for document recency
            quality_weight: Weight for source quality
        """
        self.cosine_weight = cosine_weight
        self.recency_weight = recency_weight
        self.quality_weight = quality_weight

    def rerank(self, evidence_list: List[Evidence]) -> List[Evidence]:
        """
        Re-rank evidence using hybrid scoring.

        Rationale:
        - Cosine similarity (60%): Primary relevance signal
        - Recency (20%): Prefer recently updated documents
        - Source quality (30%): Boost high-authority sources (SOPs, pricing)

        Args:
            evidence_list: List of Evidence objects

        Returns:
            Re-ranked list of Evidence objects
        """
        if not evidence_list:
            return []

        # Calculate composite scores
        for evidence in evidence_list:
            cosine_score = evidence.score

            # Recency score (exponential decay)
            recency_score = self._calculate_recency_score(evidence)

            # Quality score based on doc type
            quality_score = self._calculate_quality_score(evidence)

            # Composite score
            evidence.score = (
                self.cosine_weight * cosine_score +
                self.recency_weight * recency_score +
                self.quality_weight * quality_score
            )

        # Sort by composite score
        evidence_list.sort(key=lambda e: e.score, reverse=True)

        return evidence_list

    def _calculate_recency_score(self, evidence: Evidence) -> float:
        """
        Calculate recency score.

        Uses exponential decay: score = exp(-days_old / half_life)
        """
        # Try to get updated_at from metadata
        updated_at = evidence.metadata.get("updated_at")

        if not updated_at:
            # Default: assume reasonably recent
            return 0.7

        try:
            if isinstance(updated_at, str):
                updated_dt = datetime.fromisoformat(updated_at)
            else:
                updated_dt = updated_at

            now = datetime.now(timezone.utc)
            days_old = (now - updated_dt).days

            # Half-life of 90 days (score drops to 0.5 after 90 days)
            half_life = 90
            recency_score = math.exp(-days_old / half_life)

            return recency_score

        except Exception:
            return 0.7

    def _calculate_quality_score(self, evidence: Evidence) -> float:
        """
        Calculate source quality score based on doc type.

        Hierarchy (highest to lowest):
        - pricing: 1.0 (critical for quotes)
        - sop: 0.95 (authoritative procedures)
        - policy: 0.9 (official policies)
        - faq: 0.8 (curated Q&A)
        - general: 0.7 (other content)
        """
        quality_map = {
            "pricing": 1.0,
            "sop": 0.95,
            "policy": 0.9,
            "faq": 0.8,
            "general": 0.7
        }

        return quality_map.get(evidence.doc_type, 0.7)

    def filter_low_quality(
        self,
        evidence_list: List[Evidence],
        threshold: float = None
    ) -> List[Evidence]:
        """
        Filter out low-quality evidence below threshold.

        Args:
            evidence_list: List of Evidence objects
            threshold: Minimum score (default from settings)

        Returns:
            Filtered list
        """
        threshold = threshold or settings.rag_confidence_threshold
        return [e for e in evidence_list if e.score >= threshold]

    def detect_conflicts(self, evidence_list: List[Evidence]) -> bool:
        """
        Detect if evidence contains conflicting information.

        Simple heuristic: if we have pricing docs with different numbers,
        or policies with contradictory language.

        For PoC, this is a placeholder. In production, would use:
        - NLI models to detect contradictions
        - Semantic similarity to find duplicates with different facts
        - Entity extraction to compare specific values

        Args:
            evidence_list: List of Evidence objects

        Returns:
            True if conflicts detected
        """
        # Group by doc type
        by_type = {}
        for e in evidence_list:
            if e.doc_type not in by_type:
                by_type[e.doc_type] = []
            by_type[e.doc_type].append(e)

        # Check for multiple pricing docs (potential price conflict)
        if "pricing" in by_type and len(by_type["pricing"]) > 1:
            # If multiple pricing sources have different scores,
            # might indicate conflicting info
            scores = [e.score for e in by_type["pricing"]]
            if max(scores) - min(scores) > 0.3:
                return True

        # Check for multiple policies (potential policy conflict)
        if "policy" in by_type and len(by_type["policy"]) > 1:
            scores = [e.score for e in by_type["policy"]]
            if max(scores) - min(scores) > 0.3:
                return True

        return False
