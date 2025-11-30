"""Document parsing with Markitdown MCP integration.

Converts PDF, DOCX, HTML, and other formats to Markdown for RAG ingestion.
Integrates with Markitdown MCP server for robust document processing.

Phase 3: Hybrid RAG Pipeline
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
import mimetypes
from pathlib import Path
from typing import Any

# Type aliases
ParsedContent = str
DocumentMetadata = dict[str, Any]


class DocumentFormat(Enum):
    """Supported document formats."""

    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    HTML = "html"
    HTM = "htm"
    MARKDOWN = "md"
    TXT = "txt"
    RTF = "rtf"
    XLSX = "xlsx"
    XLS = "xls"
    PPTX = "pptx"
    PPT = "ppt"


@dataclass
class ParsedDocument:
    """Parsed document with metadata.

    Attributes:
        content: Parsed content in Markdown format
        format: Original document format
        metadata: Document metadata (title, author, page_count, etc.)
        file_path: Original file path

    Example:
        >>> doc = ParsedDocument(
        ...     content="# Document Title\\n\\nContent...",
        ...     format=DocumentFormat.PDF,
        ...     metadata={"page_count": 10, "title": "Example"},
        ...     file_path="document.pdf"
        ... )
    """

    content: ParsedContent
    format: DocumentFormat
    metadata: DocumentMetadata
    file_path: str


class MarkitdownParser:
    """Document parser using Markitdown library.

    Converts various document formats to Markdown using the markitdown library.
    Provides fallback for MCP integration.

    Attributes:
        use_mcp: Whether to use MCP server (if available)

    Example:
        >>> parser = MarkitdownParser()
        >>> doc = await parser.parse_file("document.pdf")
        >>> print(doc.content)  # Markdown content
    """

    def __init__(
        self,
        use_mcp: bool = False,
    ) -> None:
        """Initialize Markitdown parser.

        Args:
            use_mcp: If True, attempt to use MCP server integration.
                     Falls back to direct library if MCP unavailable.

        Example:
            >>> # Direct library usage
            >>> parser = MarkitdownParser(use_mcp=False)
            >>>
            >>> # MCP server usage (if available)
            >>> parser = MarkitdownParser(use_mcp=True)
        """
        self.use_mcp = use_mcp
        self._markitdown = None  # Lazy loading

    def _load_markitdown(self) -> None:
        """Lazy load markitdown library."""
        if self._markitdown is not None:
            return

        try:
            from markitdown import MarkItDown

            self._markitdown = MarkItDown()
        except ImportError:
            raise ImportError(
                "markitdown library required for document parsing. "
                "Install with: pip install markitdown"
            )

    async def parse_file(
        self,
        file_path: str | Path,
        extract_metadata: bool = True,
    ) -> ParsedDocument:
        """Parse document file to Markdown.

        Args:
            file_path: Path to document file
            extract_metadata: Whether to extract document metadata

        Returns:
            ParsedDocument with content and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format not supported

        Example:
            >>> doc = await parser.parse_file("contract.pdf")
            >>> print(f"Parsed {len(doc.content)} characters")
            >>> print(f"Metadata: {doc.metadata}")
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Detect format
        doc_format = self._detect_format(file_path)

        # Parse content
        if self.use_mcp:
            content = await self._parse_with_mcp(file_path)
        else:
            content = await self._parse_with_library(file_path)

        # Extract metadata
        metadata = {}
        if extract_metadata:
            metadata = await self._extract_metadata(file_path, doc_format)

        return ParsedDocument(
            content=content,
            format=doc_format,
            metadata=metadata,
            file_path=str(file_path),
        )

    async def parse_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        extract_metadata: bool = True,
    ) -> ParsedDocument:
        """Parse document from bytes.

        Args:
            file_bytes: Document bytes
            filename: Original filename (for format detection)
            extract_metadata: Whether to extract metadata

        Returns:
            ParsedDocument with content and metadata

        Example:
            >>> with open("document.pdf", "rb") as f:
            ...     content = f.read()
            >>> doc = await parser.parse_bytes(content, "document.pdf")
        """
        # Write to temp file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(file_bytes)

        try:
            # Parse temp file
            doc = await self.parse_file(temp_path, extract_metadata)
            # Update file_path to original filename
            doc.file_path = filename
            return doc
        finally:
            # Cleanup
            temp_path.unlink(missing_ok=True)

    async def parse_batch(
        self,
        file_paths: list[str | Path],
        extract_metadata: bool = True,
    ) -> list[ParsedDocument]:
        """Parse multiple documents in batch.

        Args:
            file_paths: List of file paths
            extract_metadata: Whether to extract metadata

        Returns:
            List of ParsedDocument objects

        Example:
            >>> files = ["doc1.pdf", "doc2.docx", "doc3.html"]
            >>> docs = await parser.parse_batch(files)
            >>> len(docs)
            3
        """
        tasks = [self.parse_file(path, extract_metadata) for path in file_paths]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def _parse_with_library(self, file_path: Path) -> str:
        """Parse using markitdown library directly.

        Args:
            file_path: Path to document

        Returns:
            Markdown content
        """
        self._load_markitdown()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._markitdown.convert,
            str(file_path),
        )

        return result.text_content

    async def _parse_with_mcp(self, file_path: Path) -> str:
        """Parse using Markitdown MCP server.

        Args:
            file_path: Path to document

        Returns:
            Markdown content

        Note:
            This is a placeholder for MCP integration.
            Actual implementation would use MCP client to call server.
        """
        # TODO: Implement MCP client integration
        # For now, fall back to direct library
        return await self._parse_with_library(file_path)

    def _detect_format(self, file_path: Path) -> DocumentFormat:
        """Detect document format from file extension.

        Args:
            file_path: Path to document

        Returns:
            DocumentFormat enum value

        Raises:
            ValueError: If format not supported
        """
        suffix = file_path.suffix.lower().lstrip(".")

        try:
            return DocumentFormat(suffix)
        except ValueError:
            raise ValueError(
                f"Unsupported document format: {suffix}. "
                f"Supported: {', '.join(f.value for f in DocumentFormat)}"
            )

    async def _extract_metadata(
        self,
        file_path: Path,
        doc_format: DocumentFormat,
    ) -> DocumentMetadata:
        """Extract metadata from document.

        Args:
            file_path: Path to document
            doc_format: Document format

        Returns:
            Dictionary with metadata

        Example metadata:
            - file_size: File size in bytes
            - created_at: Creation timestamp
            - modified_at: Modification timestamp
            - mime_type: MIME type
            - page_count: Number of pages (PDF only)
            - title: Document title (if available)
        """
        metadata: DocumentMetadata = {
            "file_size": file_path.stat().st_size,
            "created_at": file_path.stat().st_ctime,
            "modified_at": file_path.stat().st_mtime,
            "mime_type": mimetypes.guess_type(str(file_path))[0],
        }

        # Format-specific metadata extraction
        if doc_format == DocumentFormat.PDF:
            try:
                pdf_metadata = await self._extract_pdf_metadata(file_path)
                metadata.update(pdf_metadata)
            except Exception:
                pass  # nosec B110 - PDF metadata extraction is optional

        return metadata

    async def _extract_pdf_metadata(self, file_path: Path) -> DocumentMetadata:
        """Extract PDF-specific metadata.

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary with PDF metadata
        """
        try:
            import PyPDF2
        except ImportError:
            return {}

        loop = asyncio.get_event_loop()

        def extract():
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                metadata = {
                    "page_count": len(reader.pages),
                }

                # Add PDF info if available
                if reader.metadata:
                    if reader.metadata.title:
                        metadata["title"] = reader.metadata.title
                    if reader.metadata.author:
                        metadata["author"] = reader.metadata.author
                    if reader.metadata.subject:
                        metadata["subject"] = reader.metadata.subject

                return metadata

        return await loop.run_in_executor(None, extract)


class DocumentIngestionPipeline:
    """Complete document ingestion pipeline.

    Combines parsing, chunking, and embedding for RAG ingestion.

    Attributes:
        parser: Document parser
        chunker: Text chunker
        embed_fn: Embedding function (optional)

    Example:
        >>> from core.rag.chunking import create_chunker, ChunkingStrategy
        >>>
        >>> parser = MarkitdownParser()
        >>> chunker = create_chunker(ChunkingStrategy.SEMANTIC)
        >>> pipeline = DocumentIngestionPipeline(parser, chunker)
        >>>
        >>> chunks = await pipeline.ingest_file("document.pdf")
        >>> print(f"Created {len(chunks)} chunks")
    """

    def __init__(
        self,
        parser: MarkitdownParser,
        chunker: Any,  # One of the chunker types
        embed_fn: Any = None,
    ) -> None:
        """Initialize ingestion pipeline.

        Args:
            parser: Document parser
            chunker: Text chunker
            embed_fn: Optional embedding function for chunks

        Example:
            >>> pipeline = DocumentIngestionPipeline(
            ...     parser=MarkitdownParser(),
            ...     chunker=create_chunker(ChunkingStrategy.SEMANTIC)
            ... )
        """
        self.parser = parser
        self.chunker = chunker
        self.embed_fn = embed_fn

    async def ingest_file(
        self,
        file_path: str | Path,
    ) -> list[Any]:  # Returns DocumentChunk or embedded chunks
        """Ingest document file into RAG system.

        Args:
            file_path: Path to document file

        Returns:
            List of chunks (with embeddings if embed_fn provided)

        Example:
            >>> chunks = await pipeline.ingest_file("contract.pdf")
            >>> for chunk in chunks:
            ...     print(f"Chunk {chunk.chunk_id}: {len(chunk.content)} chars")
        """
        # Step 1: Parse document
        parsed_doc = await self.parser.parse_file(file_path)

        # Step 2: Chunk content
        chunks = self.chunker.chunk_text(
            text=parsed_doc.content,
            doc_id=Path(file_path).stem,
            base_metadata={
                "source": str(file_path),
                "format": parsed_doc.format.value,
                **parsed_doc.metadata,
            },
        )

        # Step 3: Embed chunks (if embed function provided)
        if self.embed_fn:
            chunks = await self._embed_chunks(chunks)

        return chunks

    async def ingest_batch(
        self,
        file_paths: list[str | Path],
    ) -> list[list[Any]]:
        """Ingest multiple documents in batch.

        Args:
            file_paths: List of file paths

        Returns:
            List of chunk lists (one per document)

        Example:
            >>> files = ["doc1.pdf", "doc2.docx"]
            >>> all_chunks = await pipeline.ingest_batch(files)
            >>> total_chunks = sum(len(chunks) for chunks in all_chunks)
        """
        tasks = [self.ingest_file(path) for path in file_paths]
        return await asyncio.gather(*tasks)

    async def _embed_chunks(self, chunks: list[Any]) -> list[Any]:
        """Embed chunks using provided embedding function.

        Args:
            chunks: List of DocumentChunk objects

        Returns:
            List of chunks with embeddings attached
        """
        # TODO: Implement embedding integration
        # This would call the embed_fn on each chunk's content
        return chunks


async def create_document_parser(
    use_mcp: bool = False,
) -> MarkitdownParser:
    """Factory function to create document parser.

    Args:
        use_mcp: Whether to use MCP server integration

    Returns:
        Initialized MarkitdownParser instance

    Example:
        >>> parser = await create_document_parser()
        >>> doc = await parser.parse_file("document.pdf")
    """
    return MarkitdownParser(use_mcp=use_mcp)


__all__ = [
    "DocumentFormat",
    "DocumentIngestionPipeline",
    "MarkitdownParser",
    "ParsedDocument",
    "create_document_parser",
]
