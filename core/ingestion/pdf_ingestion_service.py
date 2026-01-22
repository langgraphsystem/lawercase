"""PDF Ingestion Service for converting PDF documents to semantic memory.

Pipeline: PDF -> Parse (Markitdown) -> Chunk (Semantic) -> Tag (EB-1A) -> Store (Memory)

Phase 3: Hybrid RAG Pipeline Integration
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from core.memory.memory_manager import MemoryManager
from core.memory.models import MemoryRecord
from core.rag.chunking import ChunkingStrategy, DocumentChunk, create_chunker
from core.rag.document_parser import MarkitdownParser, ParsedDocument

logger = structlog.get_logger(__name__)


# EB-1A Criteria keywords for auto-tagging
EB1A_CRITERIA_KEYWORDS: dict[str, list[str]] = {
    "eb1a_awards": [
        "award",
        "prize",
        "recognition",
        "honor",
        "medal",
        "scholarship",
        "grant",
        "fellowship",
        "distinguished",
        "excellence",
        "outstanding",
        "best",
        "winner",
        "recipient",
        "rewarded",
    ],
    "eb1a_membership": [
        "member",
        "fellow",
        "society",
        "association",
        "academy",
        "organization",
        "institute",
        "professional body",
        "elected",
        "inducted",
        "admission",
    ],
    "eb1a_press": [
        "published",
        "featured",
        "interview",
        "article about",
        "media coverage",
        "press",
        "newspaper",
        "magazine",
        "journal featured",
        "profiled",
        "highlighted",
        "reported on",
    ],
    "eb1a_judging": [
        "judge",
        "reviewer",
        "evaluated",
        "assessed",
        "panel",
        "committee",
        "referee",
        "peer review",
        "adjudicator",
        "examiner",
        "appraiser",
    ],
    "eb1a_contribution": [
        "developed",
        "invented",
        "pioneered",
        "breakthrough",
        "innovation",
        "novel",
        "original",
        "first",
        "unique",
        "groundbreaking",
        "revolutionary",
        "created",
        "designed",
        "implemented",
    ],
    "eb1a_scholarly": [
        "publication",
        "journal",
        "paper",
        "research",
        "citation",
        "cited",
        "author",
        "co-author",
        "published in",
        "conference",
        "proceedings",
        "dissertation",
        "thesis",
    ],
    "eb1a_leadership": [
        "director",
        "head",
        "lead",
        "chief",
        "manager",
        "supervisor",
        "president",
        "chairman",
        "founder",
        "co-founder",
        "executive",
        "senior",
        "principal",
        "team lead",
    ],
    "eb1a_salary": [
        "salary",
        "compensation",
        "earnings",
        "income",
        "remuneration",
        "wages",
        "pay",
        "bonus",
        "stock options",
        "total compensation",
    ],
    "eb1a_commercial": [
        "revenue",
        "sales",
        "market",
        "commercial",
        "profit",
        "business",
        "product",
        "customers",
        "clients",
        "adoption",
        "deployment",
        "implementation",
        "success",
    ],
}


@dataclass
class IngestionResult:
    """Result of PDF ingestion operation.

    Attributes:
        document_id: Unique identifier for the ingested document
        file_name: Original file name
        page_count: Number of pages in PDF (if available)
        chunks_count: Number of chunks created
        records_created: Number of memory records stored
        detected_criteria: List of detected EB-1A criteria tags
        criteria_counts: Count of mentions per criterion
        errors: List of any errors encountered
    """

    document_id: str
    file_name: str
    page_count: int = 0
    chunks_count: int = 0
    records_created: int = 0
    detected_criteria: list[str] = field(default_factory=list)
    criteria_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class PDFIngestionService:
    """Service for ingesting PDF documents into semantic memory.

    Orchestrates the complete pipeline:
    1. Parse PDF using Markitdown
    2. Chunk content using semantic chunking
    3. Auto-tag chunks by EB-1A criteria
    4. Generate embeddings and store in memory

    Example:
        >>> service = PDFIngestionService(memory_manager=memory)
        >>> result = await service.ingest_pdf(
        ...     file_path="/tmp/petition.pdf",
        ...     user_id="user123",
        ...     case_id="case456",
        ...     auto_tag_eb1a=True,
        ... )
        >>> print(f"Created {result.chunks_count} chunks")
    """

    def __init__(
        self,
        memory_manager: MemoryManager,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        """Initialize PDF ingestion service.

        Args:
            memory_manager: Memory manager for storing records
            chunk_size: Target size for chunks (characters)
            chunk_overlap: Overlap between chunks (characters)
        """
        self.memory = memory_manager
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parser = MarkitdownParser(use_mcp=False)

    async def ingest_pdf(
        self,
        file_path: str | Path,
        user_id: str,
        case_id: str | None = None,
        auto_tag_eb1a: bool = True,
        additional_tags: list[str] | None = None,
        original_file_name: str | None = None,
    ) -> IngestionResult:
        """Ingest PDF document into semantic memory.

        Args:
            file_path: Path to PDF file
            user_id: User ID for the records
            case_id: Optional case ID to associate with records
            auto_tag_eb1a: Whether to auto-tag by EB-1A criteria
            additional_tags: Additional tags to apply to all chunks
            original_file_name: Original filename (for temp files from uploads)

        Returns:
            IngestionResult with statistics

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format not supported
        """
        file_path = Path(file_path)
        document_id = str(uuid.uuid4())
        # Use original filename if provided (for temp file uploads)
        display_name = original_file_name or file_path.name
        result = IngestionResult(
            document_id=document_id,
            file_name=display_name,
        )

        logger.info(
            "pdf_ingestion.start",
            document_id=document_id,
            file_path=str(file_path),
            user_id=user_id,
            case_id=case_id,
        )

        try:
            # Step 1: Parse PDF
            parsed_doc = await self._parse_document(file_path)
            result.page_count = parsed_doc.metadata.get("page_count", 0)

            logger.info(
                "pdf_ingestion.parsed",
                document_id=document_id,
                content_length=len(parsed_doc.content),
                page_count=result.page_count,
            )

            # Step 2: Chunk content
            chunks = self._chunk_content(parsed_doc, document_id)
            result.chunks_count = len(chunks)

            logger.info(
                "pdf_ingestion.chunked",
                document_id=document_id,
                chunks_count=result.chunks_count,
            )

            # Step 3: Create memory records with tags
            base_tags = ["document", "pdf"]
            if additional_tags:
                base_tags.extend(additional_tags)

            memory_records = []
            all_detected_criteria: set[str] = set()
            criteria_counts: dict[str, int] = {}

            for chunk in chunks:
                # Auto-tag by EB-1A criteria
                chunk_tags = base_tags.copy()

                if auto_tag_eb1a:
                    eb1a_tags = self._classify_eb1a_criteria(chunk.content)
                    chunk_tags.extend(eb1a_tags)
                    all_detected_criteria.update(eb1a_tags)

                    # Count criteria mentions
                    for tag in eb1a_tags:
                        criteria_counts[tag] = criteria_counts.get(tag, 0) + 1

                # Create memory record
                record = MemoryRecord(
                    text=chunk.content,
                    user_id=user_id,
                    case_id=case_id,
                    type="semantic",
                    source=f"pdf://{display_name}",
                    tags=chunk_tags,
                    metadata={
                        "document_id": document_id,
                        "document_source": str(file_path),
                        "original_filename": display_name,
                        "chunk_id": chunk.chunk_id,
                        "chunk_index": chunk.metadata.get("chunk_index", 0),
                        "start_pos": chunk.start_pos,
                        "end_pos": chunk.end_pos,
                        "pdf_metadata": parsed_doc.metadata,
                    },
                )
                memory_records.append(record)

            result.detected_criteria = sorted(all_detected_criteria)
            result.criteria_counts = criteria_counts

            # Step 4: Store in memory
            await self.memory.awrite(memory_records)
            result.records_created = len(memory_records)

            logger.info(
                "pdf_ingestion.complete",
                document_id=document_id,
                records_created=result.records_created,
                detected_criteria=result.detected_criteria,
                criteria_counts=result.criteria_counts,
            )

        except FileNotFoundError as e:
            result.errors.append(f"File not found: {e}")
            logger.error("pdf_ingestion.file_not_found", error=str(e))
            raise

        except ValueError as e:
            result.errors.append(f"Invalid format: {e}")
            logger.error("pdf_ingestion.invalid_format", error=str(e))
            raise

        except Exception as e:
            result.errors.append(f"Ingestion failed: {e}")
            logger.exception("pdf_ingestion.failed", error=str(e))
            raise

        return result

    async def _parse_document(self, file_path: Path) -> ParsedDocument:
        """Parse document using Markitdown.

        Args:
            file_path: Path to document

        Returns:
            ParsedDocument with content and metadata
        """
        return await self.parser.parse_file(file_path, extract_metadata=True)

    def _chunk_content(
        self,
        parsed_doc: ParsedDocument,
        doc_id: str,
    ) -> list[DocumentChunk]:
        """Chunk document content using semantic chunking.

        Args:
            parsed_doc: Parsed document
            doc_id: Document identifier

        Returns:
            List of DocumentChunk objects
        """
        chunker = create_chunker(
            strategy=ChunkingStrategy.SEMANTIC,
            chunk_size=self.chunk_size,
            min_chunk_size=100,
        )

        return chunker.chunk_text(
            text=parsed_doc.content,
            doc_id=doc_id,
            base_metadata={
                "source": parsed_doc.file_path,
                "format": parsed_doc.format.value,
            },
        )

    def _classify_eb1a_criteria(self, text: str) -> list[str]:
        """Classify text by EB-1A criteria using keyword matching.

        Args:
            text: Text to classify

        Returns:
            List of matching EB-1A criterion tags
        """
        text_lower = text.lower()
        matched_criteria: list[str] = []

        for criterion_tag, keywords in EB1A_CRITERIA_KEYWORDS.items():
            for keyword in keywords:
                # Use word boundary matching for better accuracy
                pattern = rf"\b{re.escape(keyword)}\b"
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matched_criteria.append(criterion_tag)
                    break  # One match per criterion is enough

        return matched_criteria

    async def ingest_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        user_id: str,
        case_id: str | None = None,
        auto_tag_eb1a: bool = True,
        additional_tags: list[str] | None = None,
    ) -> IngestionResult:
        """Ingest PDF from bytes (useful for Telegram uploads).

        Args:
            file_bytes: Document bytes
            file_name: Original filename
            user_id: User ID
            case_id: Optional case ID
            auto_tag_eb1a: Whether to auto-tag by EB-1A criteria
            additional_tags: Additional tags

        Returns:
            IngestionResult with statistics
        """
        import tempfile

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=Path(file_name).suffix, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(file_bytes)

        try:
            result = await self.ingest_pdf(
                file_path=temp_path,
                user_id=user_id,
                case_id=case_id,
                auto_tag_eb1a=auto_tag_eb1a,
                additional_tags=additional_tags,
                original_file_name=file_name,  # Pass original filename
            )
            return result
        finally:
            # Cleanup temp file
            temp_path.unlink(missing_ok=True)


# Factory function
def create_pdf_ingestion_service(
    memory_manager: MemoryManager,
    chunk_size: int = 1000,
) -> PDFIngestionService:
    """Create PDFIngestionService instance.

    Args:
        memory_manager: Memory manager instance
        chunk_size: Target chunk size

    Returns:
        Configured PDFIngestionService
    """
    return PDFIngestionService(
        memory_manager=memory_manager,
        chunk_size=chunk_size,
    )
