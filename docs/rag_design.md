# RAG Design

## Chunking Strategy

**Size**: 600 tokens
**Overlap**: 100 tokens

**Rationale**:
- 600 tokens provides sufficient context for semantic understanding
- Smaller chunks (200-300) lose context, larger (1000+) dilute relevance
- 100 token overlap prevents information loss at boundaries
- Trade-off: precision vs. recall

## Embeddings

**Model**: OpenAI `text-embedding-3-small` (1536 dimensions)
**Caching**: File-based to avoid redundant API calls
**Batch Processing**: Multiple texts embedded in single API call

## Retrieval

**Method**: Cosine similarity in ChromaDB
**Top-k**: 8 (configurable)
**Metadata Filters**: doc_type, updated_at, category

## Re-ranking

**Hybrid Scoring**:
- 60% cosine similarity (primary relevance)
- 20% recency (exponential decay, 90-day half-life)
- 20% source quality (doc type hierarchy)

**Source Quality Hierarchy**:
1. Pricing (1.0) - Critical for quotes
2. SOP (0.95) - Authoritative procedures
3. Policy (0.9) - Official policies
4. FAQ (0.8) - Curated Q&A
5. General (0.7) - Other content

**Conflict Detection**: Identifies contradictory sources, halves confidence

## Grounding

- Responses MUST cite sources when using RAG
- Empty retrieval → ask clarifying question or escalate
- Weak sources (score <0.6) → filtered out
- Conflicting sources → confidence degraded

## Conditional Retrieval

RAG is **not always on**. Decision engine determines when retrieval is needed.

**Skip retrieval for**:
- Simple acknowledgments
- Conversational queries
- Tool-only actions

**Trigger retrieval for**:
- Factual queries (pricing, policies, SOPs)
- Technical questions
- Any query requiring authoritative sources
