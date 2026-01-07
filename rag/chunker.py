"""
Document chunking for RAG pipeline.
Splits documents into semantic chunks with overlap.
"""

import tiktoken
from typing import List, Dict, Any
from pathlib import Path

from config import settings


class DocumentChunker:
    """Chunks documents into overlapping segments for RAG."""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize chunker.

        Args:
            chunk_size: Token size for chunks (default from settings)
            chunk_overlap: Overlap between chunks (default from settings)
            encoding_name: Tiktoken encoding name
        """
        self.chunk_size = chunk_size or settings.rag_chunk_size
        self.chunk_overlap = chunk_overlap or settings.rag_chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)

    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk a single text document.

        Rationale for chunk size (600 tokens) and overlap (100 tokens):
        - 600 tokens provides enough context for semantic understanding
        - 100 token overlap ensures no information loss at boundaries
        - Balances retrieval precision with context completeness

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of chunk dictionaries with text and metadata
        """
        # Encode text to tokens
        tokens = self.encoding.encode(text)

        chunks = []
        start_idx = 0

        while start_idx < len(tokens):
            # Extract chunk
            end_idx = start_idx + self.chunk_size
            chunk_tokens = tokens[start_idx:end_idx]

            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)

            # Create chunk object
            chunk = {
                "text": chunk_text,
                "token_count": len(chunk_tokens),
                "chunk_index": len(chunks),
                "metadata": metadata or {}
            }
            chunks.append(chunk)

            # Move to next chunk with overlap
            start_idx += self.chunk_size - self.chunk_overlap

        return chunks

    def chunk_file(
        self,
        file_path: Path,
        doc_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk a file from the knowledge base.

        Args:
            file_path: Path to file
            doc_type: Document type (sop, faq, pricing, policy)

        Returns:
            List of chunks with metadata
        """
        # Read file
        text = file_path.read_text(encoding="utf-8")

        # Determine doc_type from path if not provided
        if not doc_type:
            if "sops" in str(file_path):
                doc_type = "sop"
            elif "faqs" in str(file_path):
                doc_type = "faq"
            elif "pricing" in str(file_path):
                doc_type = "pricing"
            elif "policies" in str(file_path):
                doc_type = "policy"
            else:
                doc_type = "general"

        # Create metadata
        metadata = {
            "source_file": str(file_path),
            "doc_title": file_path.stem,
            "doc_type": doc_type,
            "file_extension": file_path.suffix
        }

        # Chunk the text
        chunks = self.chunk_text(text, metadata)

        return chunks

    def chunk_directory(
        self,
        directory_path: Path,
        recursive: bool = True,
        file_extensions: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk all files in a directory.

        Args:
            directory_path: Path to directory
            recursive: Whether to recurse into subdirectories
            file_extensions: List of file extensions to process

        Returns:
            List of all chunks from all files
        """
        if file_extensions is None:
            file_extensions = [".md", ".txt", ".rst"]

        all_chunks = []

        # Get files
        if recursive:
            files = [
                f for f in directory_path.rglob("*")
                if f.is_file() and f.suffix in file_extensions
            ]
        else:
            files = [
                f for f in directory_path.iterdir()
                if f.is_file() and f.suffix in file_extensions
            ]

        # Chunk each file
        for file_path in files:
            chunks = self.chunk_file(file_path)
            all_chunks.extend(chunks)

        return all_chunks
