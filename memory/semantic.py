"""
Semantic memory using ChromaDB vector store.
Stores embeddings for conversation history and knowledge base.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from config import settings
from rag.embeddings import EmbeddingGenerator
from observability import trace_logger


class SemanticMemory:
    """Vector store for semantic memory and knowledge base."""

    def __init__(
        self,
        persist_directory: str = None,
        collection_name: str = "knowledge_base"
    ):
        """
        Initialize semantic memory with ChromaDB.

        Args:
            persist_directory: Directory for persistent storage
            collection_name: Collection name for this memory
        """
        self.persist_directory = persist_directory or settings.chroma_persist_dir

        # Ensure directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Knowledge base and conversation history"}
        )

        # Embedding generator
        self.embedding_generator = EmbeddingGenerator()

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to semantic memory.

        Args:
            documents: List of text documents
            metadatas: List of metadata dicts
            ids: Optional list of IDs (generated if not provided)

        Returns:
            List of document IDs
        """
        if not documents:
            return []

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        # Generate embeddings
        embeddings = self.embedding_generator.embed(documents)

        # Add to collection
        try:
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            trace_logger.info(
                f"Added {len(documents)} documents to semantic memory",
                collection=self.collection.name,
                num_docs=len(documents)
            )

            return ids

        except Exception as e:
            trace_logger.error_occurred(
                error_type="semantic_memory_add_error",
                error_message=str(e),
                context={"num_documents": len(documents)}
            )
            raise

    def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query semantic memory.

        Args:
            query_embeddings: List of query embeddings
            n_results: Number of results to return
            where: Metadata filters

        Returns:
            Query results dictionary
        """
        try:
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where
            )
            return results

        except Exception as e:
            trace_logger.error_occurred(
                error_type="semantic_memory_query_error",
                error_message=str(e),
                context={"n_results": n_results, "where": where}
            )
            raise

    def delete(self, ids: List[str]):
        """Delete documents by IDs."""
        try:
            self.collection.delete(ids=ids)
            trace_logger.info(
                f"Deleted {len(ids)} documents from semantic memory",
                collection=self.collection.name
            )
        except Exception as e:
            trace_logger.error_occurred(
                error_type="semantic_memory_delete_error",
                error_message=str(e)
            )
            raise

    def count(self) -> int:
        """Get document count in collection."""
        return self.collection.count()

    def clear(self):
        """Clear all documents from collection."""
        # Delete collection and recreate
        self.client.delete_collection(name=self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"description": "Knowledge base and conversation history"}
        )
        trace_logger.info(
            "Cleared semantic memory collection",
            collection=self.collection.name
        )


class ConversationMemory(SemanticMemory):
    """Specialized semantic memory for conversation history."""

    def __init__(self, persist_directory: str = None):
        super().__init__(
            persist_directory=persist_directory,
            collection_name="conversation_history"
        )

    def add_conversation_turn(
        self,
        lead_id: str,
        role: str,
        message: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Add a conversation turn to memory.

        Args:
            lead_id: Lead identifier
            role: 'user' or 'agent'
            message: Message text
            metadata: Additional metadata

        Returns:
            Document ID
        """
        turn_id = str(uuid.uuid4())

        meta = {
            "lead_id": lead_id,
            "role": role,
            "type": "conversation_turn",
            **(metadata or {})
        }

        self.add_documents(
            documents=[message],
            metadatas=[meta],
            ids=[turn_id]
        )

        return turn_id

    def get_conversation_history(
        self,
        lead_id: str,
        n_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a lead.

        Args:
            lead_id: Lead identifier
            n_results: Number of messages to retrieve

        Returns:
            List of conversation turns
        """
        # Query with a generic embedding (or could use lead context)
        query_embedding = self.embedding_generator.embed_single(f"conversation history for {lead_id}")

        results = self.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"lead_id": lead_id}
        )

        # Format results
        history = []
        if results and results.get("ids"):
            for i in range(len(results["ids"][0])):
                history.append({
                    "id": results["ids"][0][i],
                    "message": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i]
                })

        return history
