"""Tests for Document Parser with MCP and Embedding Integration.

This module tests the document parser including:
- File parsing with markitdown
- MCP server integration
- Embedding integration for chunks
- Batch processing
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.rag.document_parser import (
    DocumentFormat,
    DocumentIngestionPipeline,
    MarkitdownParser,
    ParsedDocument,
    create_document_parser,
)


class TestDocumentFormat:
    """Tests for DocumentFormat enum."""

    def test_all_formats_exist(self):
        """Test that all expected formats are defined."""
        expected_formats = ["pdf", "docx", "doc", "html", "md", "txt"]
        actual_formats = [f.value for f in DocumentFormat]

        for fmt in expected_formats:
            assert fmt in actual_formats, f"Missing format: {fmt}"

    def test_format_values_lowercase(self):
        """Test that all format values are lowercase."""
        for fmt in DocumentFormat:
            assert fmt.value == fmt.value.lower()


class TestParsedDocument:
    """Tests for ParsedDocument dataclass."""

    def test_parsed_document_creation(self):
        """Test basic ParsedDocument creation."""
        doc = ParsedDocument(
            content="# Test Document\n\nContent here.",
            format=DocumentFormat.MARKDOWN,
            metadata={"page_count": 1},
            file_path="test.md",
        )
        assert doc.content.startswith("# Test Document")
        assert doc.format == DocumentFormat.MARKDOWN
        assert doc.metadata["page_count"] == 1
        assert doc.file_path == "test.md"


class TestMarkitdownParser:
    """Tests for MarkitdownParser."""

    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = MarkitdownParser(use_mcp=False)
        assert parser.use_mcp is False

    def test_parser_initialization_with_mcp(self):
        """Test parser initialization with MCP enabled."""
        parser = MarkitdownParser(use_mcp=True)
        assert parser.use_mcp is True

    def test_detect_format_pdf(self):
        """Test format detection for PDF."""
        parser = MarkitdownParser()
        fmt = parser._detect_format(Path("document.pdf"))
        assert fmt == DocumentFormat.PDF

    def test_detect_format_docx(self):
        """Test format detection for DOCX."""
        parser = MarkitdownParser()
        fmt = parser._detect_format(Path("document.docx"))
        assert fmt == DocumentFormat.DOCX

    def test_detect_format_unsupported(self):
        """Test format detection raises for unsupported format."""
        parser = MarkitdownParser()
        with pytest.raises(ValueError, match="Unsupported document format"):
            parser._detect_format(Path("document.xyz"))

    @pytest.mark.asyncio
    async def test_parse_file_not_found(self):
        """Test parsing non-existent file raises error."""
        parser = MarkitdownParser()
        with pytest.raises(FileNotFoundError):
            await parser.parse_file("non_existent_file.pdf")

    @pytest.mark.asyncio
    async def test_parse_text_file(self):
        """Test parsing a text file."""
        parser = MarkitdownParser(use_mcp=False)

        # Create temp text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is test content.\nLine 2.")
            temp_path = f.name

        try:
            # Mock markitdown library
            with patch.object(parser, "_load_markitdown"):
                parser._markitdown = MagicMock()
                parser._markitdown.convert = MagicMock(
                    return_value=MagicMock(text_content="This is test content.\nLine 2.")
                )

                doc = await parser.parse_file(temp_path)

                assert doc.format == DocumentFormat.TXT
                assert "test content" in doc.content
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_parse_bytes(self):
        """Test parsing document from bytes."""
        parser = MarkitdownParser(use_mcp=False)

        # Mock markitdown
        with patch.object(parser, "_load_markitdown"):
            parser._markitdown = MagicMock()
            parser._markitdown.convert = MagicMock(
                return_value=MagicMock(text_content="Parsed from bytes")
            )

            doc = await parser.parse_bytes(
                b"Test content bytes",
                "document.txt",
            )

            assert doc.file_path == "document.txt"
            assert "Parsed from bytes" in doc.content


class TestMCPIntegration:
    """Tests for MCP server integration."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create mock MCP client manager."""
        manager = MagicMock()
        manager.connect = AsyncMock(return_value=[])
        manager.disconnect = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_mcp_fallback_on_connection_error(self, mock_mcp_manager):
        """Test fallback to library when MCP connection fails."""
        parser = MarkitdownParser(use_mcp=True)

        mock_mcp_manager.connect = AsyncMock(side_effect=ConnectionError("No MCP server"))

        with (
            patch(
                "core.mcp.client.MCPClientManager",
                return_value=mock_mcp_manager,
            ),
            patch.object(parser, "_parse_with_library", new_callable=AsyncMock) as mock_lib,
        ):
            mock_lib.return_value = "Fallback content"

            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                f.write(b"Test")
                temp_path = f.name

            try:
                result = await parser._parse_with_mcp(Path(temp_path))
                assert result == "Fallback content"
                mock_lib.assert_called_once()
            finally:
                Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_mcp_with_available_tool(self, mock_mcp_manager):
        """Test MCP parsing when tool is available."""
        parser = MarkitdownParser(use_mcp=True)

        # Create mock tool
        mock_tool = MagicMock()
        mock_tool.name = "markitdown_convert"
        mock_tool.ainvoke = AsyncMock(return_value="MCP parsed content")

        mock_mcp_manager.connect = AsyncMock(return_value=[mock_tool])

        with patch(
            "core.mcp.client.MCPClientManager",
            return_value=mock_mcp_manager,
        ):
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                f.write(b"Test")
                temp_path = f.name

            try:
                result = await parser._parse_with_mcp(Path(temp_path))
                assert result == "MCP parsed content"
            finally:
                Path(temp_path).unlink()


class TestDocumentIngestionPipeline:
    """Tests for DocumentIngestionPipeline."""

    @pytest.fixture
    def mock_parser(self):
        """Create mock parser."""
        parser = MagicMock()
        parser.parse_file = AsyncMock(
            return_value=ParsedDocument(
                content="# Document\n\nContent here.",
                format=DocumentFormat.MARKDOWN,
                metadata={"file_size": 100},
                file_path="test.md",
            )
        )
        return parser

    @pytest.fixture
    def mock_chunker(self):
        """Create mock chunker."""
        chunker = MagicMock()
        chunker.chunk_text = MagicMock(
            return_value=[
                MagicMock(content="Chunk 1", metadata={}),
                MagicMock(content="Chunk 2", metadata={}),
            ]
        )
        return chunker

    def test_pipeline_initialization(self, mock_parser, mock_chunker):
        """Test pipeline initialization."""
        pipeline = DocumentIngestionPipeline(
            parser=mock_parser,
            chunker=mock_chunker,
        )
        assert pipeline.parser is not None
        assert pipeline.chunker is not None
        assert pipeline.embed_fn is None

    @pytest.mark.asyncio
    async def test_ingest_file(self, mock_parser, mock_chunker):
        """Test file ingestion creates chunks."""
        pipeline = DocumentIngestionPipeline(
            parser=mock_parser,
            chunker=mock_chunker,
        )

        chunks = await pipeline.ingest_file("test.md")

        assert len(chunks) == 2
        mock_parser.parse_file.assert_called_once()
        mock_chunker.chunk_text.assert_called_once()


class TestEmbeddingIntegration:
    """Tests for embedding integration in ingestion pipeline."""

    @pytest.fixture
    def mock_embed_fn(self):
        """Create mock embedding function."""

        async def embed(text):
            return [0.1, 0.2, 0.3]

        return embed

    @pytest.fixture
    def mock_embed_object(self):
        """Create mock embedding object with aembed method."""
        # Use spec=[] to prevent MagicMock from auto-generating attributes
        obj = MagicMock(spec=[])
        obj.aembed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        return obj

    @pytest.mark.asyncio
    async def test_embed_chunks_with_async_function(self, mock_embed_fn):
        """Test embedding chunks with async function."""
        mock_parser = MagicMock()
        mock_chunker = MagicMock()

        pipeline = DocumentIngestionPipeline(
            parser=mock_parser,
            chunker=mock_chunker,
            embed_fn=mock_embed_fn,
        )

        # Create test chunks
        chunks = [
            MagicMock(content="Chunk 1"),
            MagicMock(content="Chunk 2"),
        ]

        embedded = await pipeline._embed_chunks(chunks)

        assert len(embedded) == 2

    @pytest.mark.asyncio
    async def test_embed_chunks_with_object(self, mock_embed_object):
        """Test embedding chunks with object that has aembed method."""
        mock_parser = MagicMock()
        mock_chunker = MagicMock()

        pipeline = DocumentIngestionPipeline(
            parser=mock_parser,
            chunker=mock_chunker,
            embed_fn=mock_embed_object,
        )

        # Create chunk with proper content attribute (not MagicMock)
        class FakeChunk:
            def __init__(self, content: str):
                self.content = content
                self.metadata = {}
                self.embedding = None

        chunks = [FakeChunk("Chunk 1")]

        embedded = await pipeline._embed_chunks(chunks)

        assert len(embedded) == 1
        # Verify aembed was called and embedding was set
        mock_embed_object.aembed.assert_called_once_with("Chunk 1")
        assert embedded[0].embedding == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_chunks_batch(self):
        """Test batch embedding of chunks."""
        mock_parser = MagicMock()
        mock_chunker = MagicMock()

        # Create embedder with batch method
        mock_embedder = MagicMock()
        mock_embedder.aembed_batch = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])

        pipeline = DocumentIngestionPipeline(
            parser=mock_parser,
            chunker=mock_chunker,
            embed_fn=mock_embedder,
        )

        chunks = [
            MagicMock(content="Chunk 1", metadata={}),
            MagicMock(content="Chunk 2", metadata={}),
            MagicMock(content="Chunk 3", metadata={}),
        ]

        embedded = await pipeline._embed_chunks_batch(chunks)

        assert len(embedded) == 3
        mock_embedder.aembed_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_chunks_no_embed_fn(self):
        """Test that chunks are returned as-is when no embed function."""
        mock_parser = MagicMock()
        mock_chunker = MagicMock()

        pipeline = DocumentIngestionPipeline(
            parser=mock_parser,
            chunker=mock_chunker,
            embed_fn=None,
        )

        chunks = [MagicMock(content="Chunk 1")]

        embedded = await pipeline._embed_chunks(chunks)

        assert embedded == chunks


class TestCreateDocumentParser:
    """Tests for factory function."""

    @pytest.mark.asyncio
    async def test_create_parser_default(self):
        """Test creating parser with defaults."""
        parser = await create_document_parser()
        assert isinstance(parser, MarkitdownParser)
        assert parser.use_mcp is False

    @pytest.mark.asyncio
    async def test_create_parser_with_mcp(self):
        """Test creating parser with MCP enabled."""
        parser = await create_document_parser(use_mcp=True)
        assert parser.use_mcp is True


class TestMetadataExtraction:
    """Tests for document metadata extraction."""

    @pytest.mark.asyncio
    async def test_extract_basic_metadata(self):
        """Test basic metadata extraction from file."""
        parser = MarkitdownParser()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Test content")
            temp_path = Path(f.name)

        try:
            metadata = await parser._extract_metadata(temp_path, DocumentFormat.TXT)

            assert "file_size" in metadata
            assert "created_at" in metadata
            assert "modified_at" in metadata
            assert "mime_type" in metadata
            assert metadata["file_size"] > 0
        finally:
            temp_path.unlink()
