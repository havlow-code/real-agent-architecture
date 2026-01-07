"""
Script to ingest knowledge base documents into vector store.
Run this after setting up the environment to populate the RAG system.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag import DocumentChunker
from memory import SemanticMemory
from observability import trace_logger


def ingest_knowledge_base(knowledge_base_dir: str = "./knowledge_base"):
    """
    Ingest all documents from knowledge base directory.

    Args:
        knowledge_base_dir: Path to knowledge base directory
    """
    kb_path = Path(knowledge_base_dir)

    if not kb_path.exists():
        print(f"Error: Knowledge base directory not found: {knowledge_base_dir}")
        return False

    print("Initializing ingestion...")
    print(f"Knowledge base directory: {kb_path.absolute()}")

    # Initialize components
    chunker = DocumentChunker()
    semantic_memory = SemanticMemory(collection_name="knowledge_base")

    # Clear existing knowledge base
    print("\nClearing existing knowledge base...")
    semantic_memory.clear()

    # Chunk all documents
    print("\nChunking documents...")
    all_chunks = chunker.chunk_directory(
        directory_path=kb_path,
        recursive=True,
        file_extensions=[".md", ".txt"]
    )

    print(f"Generated {len(all_chunks)} chunks from knowledge base")

    if not all_chunks:
        print("Warning: No chunks generated. Check that documents exist in knowledge_base/")
        return False

    # Prepare for ingestion
    documents = [chunk["text"] for chunk in all_chunks]
    metadatas = [chunk["metadata"] for chunk in all_chunks]
    ids = [f"{chunk['metadata']['source_file']}_{chunk['chunk_index']}" for chunk in all_chunks]

    # Ingest into vector store
    print("\nIngesting into vector store...")
    print("This may take a few minutes depending on the number of documents...")

    try:
        semantic_memory.add_documents(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"\n✓ Successfully ingested {len(all_chunks)} chunks")
        print(f"✓ Vector store document count: {semantic_memory.count()}")

        # Display summary by document type
        doc_types = {}
        for chunk in all_chunks:
            doc_type = chunk["metadata"].get("doc_type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

        print("\nIngestion summary by document type:")
        for doc_type, count in sorted(doc_types.items()):
            print(f"  {doc_type}: {count} chunks")

        return True

    except Exception as e:
        print(f"\n✗ Error during ingestion: {str(e)}")
        trace_logger.error_occurred(
            error_type="ingestion_error",
            error_message=str(e)
        )
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Knowledge Base Ingestion Script")
    print("=" * 60)

    success = ingest_knowledge_base()

    if success:
        print("\n✓ Knowledge base ingestion completed successfully!")
        print("\nYou can now start the agent with:")
        print("  uvicorn api.app:app --host 0.0.0.0 --port 8000")
    else:
        print("\n✗ Knowledge base ingestion failed. Check errors above.")
        sys.exit(1)
