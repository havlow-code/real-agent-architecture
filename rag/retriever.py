"""
RAG retrieval from vector store.
Queries ChromaDB and returns relevant chunks.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from rag.evidence import Evidence
from rag.embeddings import EmbeddingGenerator
from config import settings
from observability import trace_logger


class RAGRetriever:
    """Retrieves relevant chunks from vector store."""

    def __init__(self, vector_store):
        """
        Initialize retriever.

        Args:
            vector_store: SemanticMemory instance with ChromaDB
        """
        self.vector_store = vector_store
        self.embedding_generator = EmbeddingGenerator()
        self.top_k = settings.rag_top_k

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        doc_type_filter: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Evidence]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: Search query
            top_k: Number of results (default from settings)
            doc_type_filter: Filter by document type
            metadata_filter: Additional metadata filters

        Returns:
            List of Evidence objects
        """
        k = top_k or self.top_k

        # Generate query embedding
        query_embedding = self.embedding_generator.embed_single(query)

        # Build metadata filter
        where_filter = metadata_filter or {}
        if doc_type_filter:
            where_filter["doc_type"] = doc_type_filter

        # Query vector store
        try:
            results = self.vector_store.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where_filter if where_filter else None
            )

            # Convert to Evidence objects
            evidence_list = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][i]
                    evidence = Evidence(
                        source_id=results["ids"][0][i],
                        doc_title=metadata.get("doc_title", "unknown"),
                        doc_type=metadata.get("doc_type", "unknown"),
                        chunk_text=results["documents"][0][i],
                        score=1.0 - results["distances"][0][i],  # Convert distance to similarity
                        chunk_index=metadata.get("chunk_index", 0),
                        source_file=metadata.get("source_file", "unknown"),
                        metadata=metadata,
                        retrieved_at=datetime.utcnow()
                    )
                    evidence_list.append(evidence)

            # Log retrieval
            trace_logger.retrieval_performed(
                query=query,
                sources=[e.to_dict() for e in evidence_list],
                top_k=k,
                doc_type_filter=doc_type_filter
            )

            return evidence_list

        except Exception as e:
            trace_logger.error_occurred(
                error_type="retrieval_error",
                error_message=str(e),
                context={"query": query, "top_k": k}
            )
            # Return empty list on error rather than failing
            return []

    def retrieve_by_doc_type(
        self,
        query: str,
        doc_types: List[str],
        top_k_per_type: int = 3
    ) -> Dict[str, List[Evidence]]:
        """
        Retrieve from multiple document types.

        Useful for complex queries that might need multiple sources.

        Args:
            query: Search query
            doc_types: List of document types to search
            top_k_per_type: Results per type

        Returns:
            Dictionary mapping doc_type to evidence list
        """
        results = {}
        for doc_type in doc_types:
            evidence = self.retrieve(
                query=query,
                top_k=top_k_per_type,
                doc_type_filter=doc_type
            )
            if evidence:
                results[doc_type] = evidence

        return results

    def retrieve_with_context(
        self,
        query: str,
        conversation_history: List[str],
        top_k: Optional[int] = None
    ) -> List[Evidence]:
        """
        Retrieve with conversation context.

        Combines current query with recent conversation for better retrieval.

        Args:
            query: Current query
            conversation_history: Recent messages
            top_k: Number of results

        Returns:
            List of Evidence objects
        """
        # Build contextualized query
        context = " ".join(conversation_history[-3:])  # Last 3 messages
        contextualized_query = f"{context}\n\nCurrent query: {query}"

        return self.retrieve(query=contextualized_query, top_k=top_k)
