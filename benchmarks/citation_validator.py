"""Citation Validator - Enhanced citation validation and analysis.

Provides comprehensive citation validation:
- URL accessibility checking
- Content relevance verification
- Source authority scoring
- Citation format validation
- Duplicate detection
- Citation network analysis
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import re
from typing import Any
from urllib.parse import urlparse

import structlog

# Re-export base class
from .deep_research_bench import CitationValidation as BaseCitationValidation

logger = structlog.get_logger(__name__)


class CitationFormat(str, Enum):
    """Citation format types."""

    URL = "url"
    DOI = "doi"
    ARXIV = "arxiv"
    ISBN = "isbn"
    PMID = "pmid"
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    UNKNOWN = "unknown"


class SourceAuthority(str, Enum):
    """Authority level of citation source."""

    HIGH = "high"  # Academic, government, major publications
    MEDIUM = "medium"  # Reputable news, established blogs
    LOW = "low"  # User-generated, unknown sources
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    """Status of citation validation."""

    VALID = "valid"
    INVALID = "invalid"
    INACCESSIBLE = "inaccessible"
    PENDING = "pending"
    ERROR = "error"


@dataclass
class CitationMetadata:
    """Extracted metadata from a citation."""

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    publication_date: datetime | None = None
    publisher: str | None = None
    doi: str | None = None
    url: str | None = None
    citation_format: CitationFormat = CitationFormat.UNKNOWN


@dataclass
class EnhancedCitationValidation:
    """Enhanced citation validation result."""

    citation: str
    citation_hash: str
    format: CitationFormat
    status: ValidationStatus
    authority: SourceAuthority
    is_accessible: bool
    content_relevance: float
    format_validity: float
    authority_score: float
    overall_score: float
    metadata: CitationMetadata | None = None
    errors: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "citation": self.citation[:200],
            "citation_hash": self.citation_hash,
            "format": self.format.value,
            "status": self.status.value,
            "authority": self.authority.value,
            "is_accessible": self.is_accessible,
            "content_relevance": self.content_relevance,
            "format_validity": self.format_validity,
            "authority_score": self.authority_score,
            "overall_score": self.overall_score,
            "errors": self.errors,
            "validated_at": self.validated_at.isoformat(),
        }

    def to_base(self) -> BaseCitationValidation:
        """Convert to base CitationValidation for compatibility."""
        return BaseCitationValidation(
            citation=self.citation,
            is_valid=self.status == ValidationStatus.VALID,
            source_exists=self.is_accessible,
            content_matches=self.content_relevance > 0.5,
            relevance_score=self.content_relevance,
            notes="; ".join(self.errors) if self.errors else "",
        )


@dataclass
class CitationAnalysis:
    """Analysis of citation set."""

    total_citations: int
    valid_count: int
    invalid_count: int
    inaccessible_count: int
    duplicate_count: int
    avg_relevance: float
    avg_authority: float
    authority_distribution: dict[str, int]
    format_distribution: dict[str, int]
    domain_diversity: float
    unique_domains: list[str]
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_citations": self.total_citations,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "inaccessible_count": self.inaccessible_count,
            "duplicate_count": self.duplicate_count,
            "avg_relevance": self.avg_relevance,
            "avg_authority": self.avg_authority,
            "authority_distribution": self.authority_distribution,
            "format_distribution": self.format_distribution,
            "domain_diversity": self.domain_diversity,
            "unique_domains": self.unique_domains[:10],
            "issues": self.issues,
        }


class EnhancedCitationValidator:
    """Enhanced citation validator with comprehensive checking.

    Features:
    - Multi-format citation detection (URL, DOI, arXiv, etc.)
    - URL accessibility verification
    - Source authority scoring
    - Content relevance analysis
    - Duplicate detection
    - Citation network analysis

    Usage:
        >>> validator = EnhancedCitationValidator()
        >>> result = await validator.validate(
        ...     "https://arxiv.org/abs/2301.12345",
        ...     context="This paper discusses neural networks..."
        ... )
        >>> print(result.overall_score)
    """

    # High authority domains
    HIGH_AUTHORITY_DOMAINS = {
        # Academic
        ".edu",
        ".ac.uk",
        "arxiv.org",
        "pubmed.ncbi",
        "scholar.google",
        "nature.com",
        "science.org",
        "ieee.org",
        "acm.org",
        "springer.com",
        "wiley.com",
        "elsevier.com",
        "jstor.org",
        "researchgate.net",
        # Government
        ".gov",
        ".gov.uk",
        "europa.eu",
        "who.int",
        "un.org",
        # Major publications
        "nytimes.com",
        "washingtonpost.com",
        "bbc.com",
        "reuters.com",
        "apnews.com",
        "economist.com",
        "forbes.com",
        "wsj.com",
    }

    # Medium authority domains
    MEDIUM_AUTHORITY_DOMAINS = {
        "medium.com",
        "substack.com",
        "github.com",
        "stackoverflow.com",
        "wikipedia.org",
        "britannica.com",
    }

    # Citation format patterns
    PATTERNS = {
        CitationFormat.DOI: re.compile(r"10\.\d{4,}/[^\s]+"),
        CitationFormat.ARXIV: re.compile(r"arxiv[:.]\s*(\d{4}\.\d{4,5}|[a-z-]+/\d{7})", re.I),
        CitationFormat.ISBN: re.compile(r"(?:ISBN[:\s]*)?(?:97[89])?\d{9}[\dXx]"),
        CitationFormat.PMID: re.compile(r"PMID[:\s]*\d+", re.I),
        CitationFormat.URL: re.compile(r"https?://[^\s<>\"]+"),
    }

    def __init__(
        self,
        url_checker: Callable[[str], Coroutine[Any, Any, bool]] | None = None,
        content_fetcher: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        timeout: float = 10.0,
        max_concurrent: int = 10,
    ) -> None:
        """Initialize citation validator.

        Args:
            url_checker: Async function to check URL accessibility
            content_fetcher: Async function to fetch URL content
            llm_caller: Async LLM function for relevance analysis
            timeout: Timeout for URL checks
            max_concurrent: Maximum concurrent validations
        """
        self._url_checker = url_checker
        self._content_fetcher = content_fetcher
        self._llm_caller = llm_caller
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Caches
        self._validation_cache: dict[str, EnhancedCitationValidation] = {}
        self._accessibility_cache: dict[str, bool] = {}

        # Stats
        self._stats = {
            "total_validated": 0,
            "cache_hits": 0,
            "valid_count": 0,
            "invalid_count": 0,
        }

        self.logger = logger.bind(component="CitationValidator")

    async def validate(
        self,
        citation: str,
        context: str = "",
        check_accessibility: bool = True,
        check_relevance: bool = True,
    ) -> EnhancedCitationValidation:
        """Validate a single citation.

        Args:
            citation: Citation to validate
            context: Context text for relevance checking
            check_accessibility: Whether to verify URL accessibility
            check_relevance: Whether to check content relevance

        Returns:
            EnhancedCitationValidation result
        """
        citation_hash = self._hash_citation(citation)

        # Check cache
        if citation_hash in self._validation_cache:
            self._stats["cache_hits"] += 1
            return self._validation_cache[citation_hash]

        async with self._semaphore:
            self._stats["total_validated"] += 1

            errors = []

            # Detect format
            citation_format = self._detect_format(citation)

            # Validate format
            format_validity = self._validate_format(citation, citation_format)

            # Determine authority
            authority = self._assess_authority(citation)
            authority_score = self._calculate_authority_score(authority, citation)

            # Check accessibility
            is_accessible = True
            if check_accessibility and citation_format == CitationFormat.URL:
                is_accessible = await self._check_accessibility(citation)
                if not is_accessible:
                    errors.append("URL not accessible")

            # Check relevance
            content_relevance = 0.5  # Default neutral
            if check_relevance and context:
                content_relevance = await self._check_relevance(citation, context)

            # Calculate overall score
            overall_score = self._calculate_overall_score(
                format_validity=format_validity,
                authority_score=authority_score,
                is_accessible=is_accessible,
                content_relevance=content_relevance,
            )

            # Determine status
            if format_validity < 0.3:
                status = ValidationStatus.INVALID
                self._stats["invalid_count"] += 1
            elif not is_accessible:
                status = ValidationStatus.INACCESSIBLE
            elif overall_score >= 0.5:
                status = ValidationStatus.VALID
                self._stats["valid_count"] += 1
            else:
                status = ValidationStatus.INVALID
                self._stats["invalid_count"] += 1

            # Extract metadata
            metadata = self._extract_metadata(citation, citation_format)

            result = EnhancedCitationValidation(
                citation=citation,
                citation_hash=citation_hash,
                format=citation_format,
                status=status,
                authority=authority,
                is_accessible=is_accessible,
                content_relevance=content_relevance,
                format_validity=format_validity,
                authority_score=authority_score,
                overall_score=overall_score,
                metadata=metadata,
                errors=errors,
            )

            # Cache result
            self._validation_cache[citation_hash] = result

            self.logger.debug(
                "citation.validated",
                citation=citation[:50],
                format=citation_format.value,
                status=status.value,
                score=overall_score,
            )

            return result

    async def validate_batch(
        self,
        citations: list[str],
        context: str = "",
        check_accessibility: bool = True,
        deduplicate: bool = True,
    ) -> tuple[list[EnhancedCitationValidation], CitationAnalysis]:
        """Validate multiple citations and analyze the set.

        Args:
            citations: List of citations
            context: Context for relevance checking
            check_accessibility: Whether to check URL accessibility
            deduplicate: Whether to skip duplicates

        Returns:
            Tuple of (validation results, analysis)
        """
        # Deduplicate if requested
        seen_hashes: set[str] = set()
        unique_citations: list[str] = []
        duplicate_count = 0

        for citation in citations:
            hash_val = self._hash_citation(citation)
            if deduplicate and hash_val in seen_hashes:
                duplicate_count += 1
                continue
            seen_hashes.add(hash_val)
            unique_citations.append(citation)

        # Validate all
        tasks = [self.validate(c, context, check_accessibility) for c in unique_citations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(
                    "citation.validation_error",
                    citation=unique_citations[i][:50],
                    error=str(result),
                )
            else:
                valid_results.append(result)

        # Analyze
        analysis = self._analyze_citations(valid_results, duplicate_count)

        return valid_results, analysis

    def _hash_citation(self, citation: str) -> str:
        """Create hash for citation deduplication."""
        normalized = citation.lower().strip()
        return hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()[:12]

    def _detect_format(self, citation: str) -> CitationFormat:
        """Detect citation format."""
        citation = citation.strip()

        # Check specific patterns
        for format_type, pattern in self.PATTERNS.items():
            if pattern.search(citation):
                return format_type

        # Check for URL-like structure
        if citation.startswith(("http://", "https://", "www.")):
            return CitationFormat.URL

        # Default to unknown
        return CitationFormat.UNKNOWN

    def _validate_format(self, citation: str, format_type: CitationFormat) -> float:
        """Validate citation format and return validity score."""
        if not citation or len(citation) < 5:
            return 0.0

        if format_type == CitationFormat.URL:
            try:
                parsed = urlparse(citation)
                if parsed.scheme and parsed.netloc:
                    return 1.0
                return 0.5
            except Exception:
                return 0.3

        elif format_type == CitationFormat.DOI:
            if self.PATTERNS[CitationFormat.DOI].search(citation):
                return 1.0
            return 0.5

        elif format_type == CitationFormat.ARXIV:
            if self.PATTERNS[CitationFormat.ARXIV].search(citation):
                return 1.0
            return 0.5

        elif format_type == CitationFormat.ISBN:
            # Basic ISBN validation
            digits = re.sub(r"[^0-9X]", "", citation.upper())
            if len(digits) in (10, 13):
                return 1.0
            return 0.3

        elif format_type == CitationFormat.PMID:
            if self.PATTERNS[CitationFormat.PMID].search(citation):
                return 1.0
            return 0.5

        # Unknown format
        return 0.4

    def _assess_authority(self, citation: str) -> SourceAuthority:
        """Assess source authority level."""
        citation_lower = citation.lower()

        # Check high authority
        for domain in self.HIGH_AUTHORITY_DOMAINS:
            if domain in citation_lower:
                return SourceAuthority.HIGH

        # Check medium authority
        for domain in self.MEDIUM_AUTHORITY_DOMAINS:
            if domain in citation_lower:
                return SourceAuthority.MEDIUM

        # Check for academic identifiers
        if any(
            pattern.search(citation)
            for fmt, pattern in self.PATTERNS.items()
            if fmt in (CitationFormat.DOI, CitationFormat.ARXIV, CitationFormat.PMID)
        ):
            return SourceAuthority.HIGH

        # Default
        if citation.startswith(("http://", "https://")):
            return SourceAuthority.LOW

        return SourceAuthority.UNKNOWN

    def _calculate_authority_score(
        self,
        authority: SourceAuthority,
        citation: str,
    ) -> float:
        """Calculate numeric authority score."""
        base_scores = {
            SourceAuthority.HIGH: 0.9,
            SourceAuthority.MEDIUM: 0.6,
            SourceAuthority.LOW: 0.3,
            SourceAuthority.UNKNOWN: 0.2,
        }
        return base_scores.get(authority, 0.2)

    async def _check_accessibility(self, url: str) -> bool:
        """Check if URL is accessible."""
        # Check cache
        if url in self._accessibility_cache:
            return self._accessibility_cache[url]

        if self._url_checker:
            try:
                result = await asyncio.wait_for(
                    self._url_checker(url),
                    timeout=self.timeout,
                )
                self._accessibility_cache[url] = result
                return result
            except Exception:
                self._accessibility_cache[url] = False
                return False

        # Default: assume accessible
        return True

    async def _check_relevance(self, citation: str, context: str) -> float:
        """Check citation relevance to context."""
        if self._llm_caller:
            prompt = f"""Rate how relevant this citation is to the given context.
Score from 0 (completely irrelevant) to 10 (highly relevant).

Citation: {citation[:200]}
Context: {context[:500]}

Score (just the number):"""
            try:
                result = await self._llm_caller(prompt)
                score = float(result.strip()) / 10
                return min(1.0, max(0.0, score))
            except Exception:
                pass

        # Fallback: keyword overlap
        citation_words = set(re.findall(r"\w+", citation.lower()))
        context_words = set(re.findall(r"\w+", context.lower()))

        if not citation_words:
            return 0.5

        overlap = len(citation_words & context_words)
        return min(overlap / len(citation_words), 1.0)

    def _calculate_overall_score(
        self,
        format_validity: float,
        authority_score: float,
        is_accessible: bool,
        content_relevance: float,
    ) -> float:
        """Calculate overall citation score."""
        accessibility_score = 1.0 if is_accessible else 0.3

        return (
            0.25 * format_validity
            + 0.25 * authority_score
            + 0.25 * accessibility_score
            + 0.25 * content_relevance
        )

    def _extract_metadata(
        self,
        citation: str,
        format_type: CitationFormat,
    ) -> CitationMetadata:
        """Extract metadata from citation."""
        metadata = CitationMetadata(citation_format=format_type)

        if format_type == CitationFormat.URL:
            try:
                parsed = urlparse(citation)
                metadata.url = citation
                metadata.publisher = parsed.netloc
            except Exception:
                pass

        elif format_type == CitationFormat.DOI:
            match = self.PATTERNS[CitationFormat.DOI].search(citation)
            if match:
                metadata.doi = match.group(0)

        elif format_type == CitationFormat.ARXIV:
            match = self.PATTERNS[CitationFormat.ARXIV].search(citation)
            if match:
                metadata.url = f"https://arxiv.org/abs/{match.group(1)}"

        return metadata

    def _analyze_citations(
        self,
        results: list[EnhancedCitationValidation],
        duplicate_count: int,
    ) -> CitationAnalysis:
        """Analyze a set of citation validations."""
        if not results:
            return CitationAnalysis(
                total_citations=0,
                valid_count=0,
                invalid_count=0,
                inaccessible_count=0,
                duplicate_count=duplicate_count,
                avg_relevance=0.0,
                avg_authority=0.0,
                authority_distribution={},
                format_distribution={},
                domain_diversity=0.0,
                unique_domains=[],
                issues=[],
            )

        valid_count = sum(1 for r in results if r.status == ValidationStatus.VALID)
        invalid_count = sum(1 for r in results if r.status == ValidationStatus.INVALID)
        inaccessible_count = sum(1 for r in results if r.status == ValidationStatus.INACCESSIBLE)

        avg_relevance = sum(r.content_relevance for r in results) / len(results)
        avg_authority = sum(r.authority_score for r in results) / len(results)

        # Authority distribution
        authority_dist: dict[str, int] = {}
        for r in results:
            auth = r.authority.value
            authority_dist[auth] = authority_dist.get(auth, 0) + 1

        # Format distribution
        format_dist: dict[str, int] = {}
        for r in results:
            fmt = r.format.value
            format_dist[fmt] = format_dist.get(fmt, 0) + 1

        # Domain diversity
        domains: set[str] = set()
        for r in results:
            if r.metadata and r.metadata.url:
                try:
                    parsed = urlparse(r.metadata.url)
                    domains.add(parsed.netloc)
                except Exception:
                    pass

        # Calculate diversity (0-1 based on unique domains)
        max_expected_domains = min(len(results), 10)
        domain_diversity = len(domains) / max_expected_domains if max_expected_domains > 0 else 0

        # Identify issues
        issues = []
        if valid_count / len(results) < 0.7:
            issues.append(f"Low validity rate: {valid_count}/{len(results)}")
        if avg_authority < 0.5:
            issues.append(f"Low average authority score: {avg_authority:.2f}")
        if avg_relevance < 0.5:
            issues.append(f"Low average relevance: {avg_relevance:.2f}")
        if domain_diversity < 0.3:
            issues.append("Low source diversity")
        if duplicate_count > len(results) * 0.2:
            issues.append(f"High duplicate rate: {duplicate_count} duplicates")

        return CitationAnalysis(
            total_citations=len(results),
            valid_count=valid_count,
            invalid_count=invalid_count,
            inaccessible_count=inaccessible_count,
            duplicate_count=duplicate_count,
            avg_relevance=avg_relevance,
            avg_authority=avg_authority,
            authority_distribution=authority_dist,
            format_distribution=format_dist,
            domain_diversity=domain_diversity,
            unique_domains=sorted(domains),
            issues=issues,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get validator statistics."""
        return {
            **self._stats,
            "cache_size": len(self._validation_cache),
            "accessibility_cache_size": len(self._accessibility_cache),
        }

    def clear_cache(self) -> None:
        """Clear validation caches."""
        self._validation_cache.clear()
        self._accessibility_cache.clear()


# Re-export for compatibility
CitationValidator = EnhancedCitationValidator

__all__ = [
    "CitationAnalysis",
    "CitationFormat",
    "CitationMetadata",
    "CitationValidator",
    "EnhancedCitationValidation",
    "EnhancedCitationValidator",
    "SourceAuthority",
    "ValidationStatus",
]
