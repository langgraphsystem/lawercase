"""Fact Checker - Verifies factual claims in research outputs.

Provides:
- Claim extraction from text
- Fact verification pipeline
- Source cross-referencing
- Confidence scoring for facts
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ClaimType(str, Enum):
    """Types of claims that can be fact-checked."""

    FACTUAL = "factual"  # Verifiable fact
    STATISTICAL = "statistical"  # Numbers, percentages
    TEMPORAL = "temporal"  # Dates, time-related
    ATTRIBUTION = "attribution"  # Quotes, citations
    CAUSAL = "causal"  # Cause-effect relationships
    COMPARATIVE = "comparative"  # Comparisons
    DEFINITIONAL = "definitional"  # Definitions


class VerificationStatus(str, Enum):
    """Status of fact verification."""

    VERIFIED = "verified"
    REFUTED = "refuted"
    UNVERIFIABLE = "unverifiable"
    PARTIALLY_TRUE = "partially_true"
    NEEDS_CONTEXT = "needs_context"
    PENDING = "pending"


@dataclass
class Claim:
    """A claim extracted from text."""

    claim_id: str
    text: str
    claim_type: ClaimType
    source_text: str  # Original context
    position: int  # Position in source text
    confidence: float = 0.5  # Extraction confidence
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "claim_type": self.claim_type.value,
            "confidence": self.confidence,
        }


@dataclass
class VerificationResult:
    """Result of fact verification."""

    claim: Claim
    status: VerificationStatus
    confidence: float  # Verification confidence
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    sources_checked: list[str] = field(default_factory=list)
    explanation: str = ""
    verified_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "status": self.status.value,
            "confidence": self.confidence,
            "supporting_evidence_count": len(self.supporting_evidence),
            "contradicting_evidence_count": len(self.contradicting_evidence),
            "sources_checked": len(self.sources_checked),
            "explanation": self.explanation,
        }


@dataclass
class FactCheckReport:
    """Complete fact-checking report."""

    report_id: str
    source_text: str
    claims_found: int
    claims_verified: int
    claims_refuted: int
    claims_unverifiable: int
    overall_accuracy: float
    results: list[VerificationResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "claims_found": self.claims_found,
            "claims_verified": self.claims_verified,
            "claims_refuted": self.claims_refuted,
            "claims_unverifiable": self.claims_unverifiable,
            "overall_accuracy": self.overall_accuracy,
            "results": [r.to_dict() for r in self.results],
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FactCheckerConfig:
    """Configuration for fact checker."""

    extract_factual: bool = True
    extract_statistical: bool = True
    extract_temporal: bool = True
    extract_attributions: bool = True
    min_claim_length: int = 10
    max_claims_per_text: int = 50
    verification_timeout: float = 30.0
    require_multiple_sources: bool = True
    min_verification_confidence: float = 0.6


class ClaimExtractor:
    """Extracts claims from text for fact-checking."""

    def __init__(self, config: FactCheckerConfig):
        self.config = config
        self._claim_count = 0

        # Patterns for different claim types
        self._statistical_pattern = re.compile(
            r"\b(\d+(?:\.\d+)?(?:\s*%|\s*percent)?)\b.*?(?:of|is|are|was|were|increased|decreased)",
            re.IGNORECASE,
        )
        self._temporal_pattern = re.compile(
            r"\b(in\s+\d{4}|since\s+\d{4}|before\s+\d{4}|after\s+\d{4}|\d{4}[-/]\d{2}[-/]\d{2})",
            re.IGNORECASE,
        )
        self._attribution_pattern = re.compile(
            r"(?:according\s+to|said|stated|reported|claimed)\s+(?:by\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            re.IGNORECASE,
        )

    def extract_claims(self, text: str) -> list[Claim]:
        """Extract claims from text.

        Args:
            text: Text to extract claims from

        Returns:
            List of extracted claims
        """
        claims = []

        # Split into sentences
        sentences = self._split_sentences(text)

        for i, sentence in enumerate(sentences):
            if len(sentence) < self.config.min_claim_length:
                continue

            # Extract different claim types
            if self.config.extract_statistical:
                statistical_claims = self._extract_statistical_claims(sentence, i)
                claims.extend(statistical_claims)

            if self.config.extract_temporal:
                temporal_claims = self._extract_temporal_claims(sentence, i)
                claims.extend(temporal_claims)

            if self.config.extract_attributions:
                attribution_claims = self._extract_attribution_claims(sentence, i)
                claims.extend(attribution_claims)

            if self.config.extract_factual:
                factual_claims = self._extract_factual_claims(sentence, i)
                claims.extend(factual_claims)

            if len(claims) >= self.config.max_claims_per_text:
                break

        return claims[: self.config.max_claims_per_text]

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_statistical_claims(self, sentence: str, position: int) -> list[Claim]:
        """Extract statistical claims."""
        claims = []
        matches = self._statistical_pattern.findall(sentence)

        if matches and any(char.isdigit() for char in sentence):
            self._claim_count += 1
            claims.append(
                Claim(
                    claim_id=f"claim_stat_{self._claim_count}",
                    text=sentence,
                    claim_type=ClaimType.STATISTICAL,
                    source_text=sentence,
                    position=position,
                    confidence=0.8,
                )
            )

        return claims

    def _extract_temporal_claims(self, sentence: str, position: int) -> list[Claim]:
        """Extract temporal claims."""
        claims = []
        matches = self._temporal_pattern.findall(sentence)

        if matches:
            self._claim_count += 1
            claims.append(
                Claim(
                    claim_id=f"claim_temp_{self._claim_count}",
                    text=sentence,
                    claim_type=ClaimType.TEMPORAL,
                    source_text=sentence,
                    position=position,
                    confidence=0.7,
                    metadata={"temporal_references": matches},
                )
            )

        return claims

    def _extract_attribution_claims(self, sentence: str, position: int) -> list[Claim]:
        """Extract attribution claims."""
        claims = []
        matches = self._attribution_pattern.findall(sentence)

        if matches:
            self._claim_count += 1
            claims.append(
                Claim(
                    claim_id=f"claim_attr_{self._claim_count}",
                    text=sentence,
                    claim_type=ClaimType.ATTRIBUTION,
                    source_text=sentence,
                    position=position,
                    confidence=0.75,
                    metadata={"attributed_to": matches},
                )
            )

        return claims

    def _extract_factual_claims(self, sentence: str, position: int) -> list[Claim]:
        """Extract general factual claims."""
        claims = []

        # Look for definitive statements
        factual_indicators = [
            r"\bis\s+(?:a|an|the)\b",
            r"\bwas\s+(?:a|an|the)\b",
            r"\bare\s+(?:a|an|the)\b",
            r"\bhas\s+been\b",
            r"\bhave\s+been\b",
            r"\bconsists\s+of\b",
            r"\bcontains\b",
        ]

        for indicator in factual_indicators:
            if re.search(indicator, sentence, re.IGNORECASE):
                self._claim_count += 1
                claims.append(
                    Claim(
                        claim_id=f"claim_fact_{self._claim_count}",
                        text=sentence,
                        claim_type=ClaimType.FACTUAL,
                        source_text=sentence,
                        position=position,
                        confidence=0.6,
                    )
                )
                break

        return claims


class FactChecker:
    """Verifies factual claims in research outputs.

    Features:
    - Automatic claim extraction
    - Multi-source verification
    - Confidence scoring
    - Detailed reporting

    Usage:
        >>> checker = FactChecker()
        >>> report = await checker.check(
        ...     text="Machine learning was invented in 1959 by Arthur Samuel.",
        ...     sources=["source1", "source2"]
        ... )
        >>> print(report.overall_accuracy)
    """

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        knowledge_retriever: Callable[[str], Coroutine[Any, Any, list[str]]] | None = None,
        config: FactCheckerConfig | None = None,
    ):
        """Initialize fact checker.

        Args:
            llm_caller: Optional LLM for semantic verification
            knowledge_retriever: Function to retrieve relevant knowledge
            config: Fact checker configuration
        """
        self._llm_caller = llm_caller
        self._knowledge_retriever = knowledge_retriever
        self.config = config or FactCheckerConfig()
        self._extractor = ClaimExtractor(self.config)
        self._check_count = 0

        self.logger = logger.bind(component="FactChecker")

    async def check(
        self,
        text: str,
        sources: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> FactCheckReport:
        """Check facts in text.

        Args:
            text: Text to fact-check
            sources: Optional list of sources to verify against
            context: Additional context

        Returns:
            FactCheckReport with verification results
        """
        self._check_count += 1
        report_id = f"fc_{self._check_count}_{int(datetime.now(UTC).timestamp())}"

        self.logger.info(
            "fact_checker.start",
            report_id=report_id,
            text_length=len(text),
        )

        # Extract claims
        claims = self._extractor.extract_claims(text)

        self.logger.info(
            "fact_checker.claims_extracted",
            count=len(claims),
        )

        # Verify each claim
        results = []
        for claim in claims:
            result = await self._verify_claim(claim, sources)
            results.append(result)

        # Calculate statistics
        verified = sum(1 for r in results if r.status == VerificationStatus.VERIFIED)
        refuted = sum(1 for r in results if r.status == VerificationStatus.REFUTED)
        unverifiable = sum(1 for r in results if r.status == VerificationStatus.UNVERIFIABLE)

        total_verifiable = verified + refuted
        accuracy = verified / max(total_verifiable, 1)

        report = FactCheckReport(
            report_id=report_id,
            source_text=text[:500],
            claims_found=len(claims),
            claims_verified=verified,
            claims_refuted=refuted,
            claims_unverifiable=unverifiable,
            overall_accuracy=accuracy,
            results=results,
        )

        self.logger.info(
            "fact_checker.complete",
            report_id=report_id,
            claims=len(claims),
            verified=verified,
            refuted=refuted,
            accuracy=accuracy,
        )

        return report

    async def _verify_claim(
        self,
        claim: Claim,
        sources: list[str] | None,
    ) -> VerificationResult:
        """Verify a single claim.

        Args:
            claim: Claim to verify
            sources: Sources to check against

        Returns:
            VerificationResult
        """
        supporting = []
        contradicting = []
        sources_checked = []

        # Try knowledge retrieval
        if self._knowledge_retriever:
            try:
                relevant_docs = await asyncio.wait_for(
                    self._knowledge_retriever(claim.text),
                    timeout=self.config.verification_timeout,
                )

                for doc in relevant_docs[:5]:
                    sources_checked.append(f"knowledge_base:{hash(doc) % 10000}")

                    # Simple matching heuristic
                    claim_words = set(claim.text.lower().split())
                    doc_words = set(doc.lower().split())
                    overlap = len(claim_words & doc_words) / max(len(claim_words), 1)

                    if overlap > 0.5:
                        supporting.append(doc[:200])
                    elif overlap > 0.2:
                        # Neutral - could support or contradict
                        pass

            except TimeoutError:
                self.logger.warning("knowledge_retrieval.timeout", claim_id=claim.claim_id)
            except Exception as e:
                self.logger.warning("knowledge_retrieval.failed", error=str(e))

        # LLM-based verification
        if self._llm_caller and not supporting and not contradicting:
            try:
                llm_result = await self._llm_verify(claim)
                if llm_result:
                    status, evidence, explanation = llm_result
                    if status == VerificationStatus.VERIFIED:
                        supporting.append(evidence)
                    elif status == VerificationStatus.REFUTED:
                        contradicting.append(evidence)

                    return VerificationResult(
                        claim=claim,
                        status=status,
                        confidence=0.7,
                        supporting_evidence=supporting,
                        contradicting_evidence=contradicting,
                        sources_checked=[*sources_checked, "llm"],
                        explanation=explanation,
                    )
            except Exception as e:
                self.logger.warning("llm_verification.failed", error=str(e))

        # Heuristic-based verification
        status, confidence, explanation = self._heuristic_verify(claim, supporting, contradicting)

        return VerificationResult(
            claim=claim,
            status=status,
            confidence=confidence,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            sources_checked=sources_checked,
            explanation=explanation,
        )

    async def _llm_verify(
        self,
        claim: Claim,
    ) -> tuple[VerificationStatus, str, str] | None:
        """Use LLM to verify claim."""
        if not self._llm_caller:
            return None

        prompt = f"""Verify this claim. Is it factually accurate?

Claim: {claim.text}
Claim Type: {claim.claim_type.value}

Respond with:
STATUS: VERIFIED/REFUTED/UNVERIFIABLE
EVIDENCE: Brief supporting or contradicting evidence
EXPLANATION: Why you determined this status"""

        try:
            response = await self._llm_caller(prompt)

            status = VerificationStatus.UNVERIFIABLE
            evidence = ""
            explanation = ""

            for line in response.split("\n"):
                stripped = line.strip()
                if stripped.startswith("STATUS:"):
                    status_str = stripped.replace("STATUS:", "").strip().upper()
                    if "VERIFIED" in status_str:
                        status = VerificationStatus.VERIFIED
                    elif "REFUTED" in status_str:
                        status = VerificationStatus.REFUTED
                elif stripped.startswith("EVIDENCE:"):
                    evidence = stripped.replace("EVIDENCE:", "").strip()
                elif stripped.startswith("EXPLANATION:"):
                    explanation = stripped.replace("EXPLANATION:", "").strip()

            return status, evidence, explanation

        except Exception:
            return None

    def _heuristic_verify(
        self,
        claim: Claim,
        supporting: list[str],
        contradicting: list[str],
    ) -> tuple[VerificationStatus, float, str]:
        """Heuristic-based claim verification."""

        # Based on evidence balance
        if supporting and not contradicting:
            return (
                VerificationStatus.VERIFIED,
                min(0.5 + len(supporting) * 0.1, 0.8),
                f"Supported by {len(supporting)} sources",
            )

        if contradicting and not supporting:
            return (
                VerificationStatus.REFUTED,
                min(0.5 + len(contradicting) * 0.1, 0.8),
                f"Contradicted by {len(contradicting)} sources",
            )

        if supporting and contradicting:
            if len(supporting) > len(contradicting):
                return (
                    VerificationStatus.PARTIALLY_TRUE,
                    0.5,
                    "Mixed evidence, leaning toward verified",
                )
            return (
                VerificationStatus.NEEDS_CONTEXT,
                0.4,
                "Conflicting evidence found",
            )

        # No evidence either way
        return (
            VerificationStatus.UNVERIFIABLE,
            0.3,
            "Insufficient evidence to verify",
        )

    async def quick_check(
        self,
        claim_text: str,
    ) -> VerificationResult:
        """Quick verification of a single claim.

        Args:
            claim_text: Claim text to verify

        Returns:
            VerificationResult
        """
        claim = Claim(
            claim_id=f"quick_{int(datetime.now(UTC).timestamp())}",
            text=claim_text,
            claim_type=ClaimType.FACTUAL,
            source_text=claim_text,
            position=0,
        )

        return await self._verify_claim(claim, None)


def create_fact_checker(
    llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    knowledge_retriever: Callable[[str], Coroutine[Any, Any, list[str]]] | None = None,
) -> FactChecker:
    """Create a fact checker with default configuration."""
    return FactChecker(
        llm_caller=llm_caller,
        knowledge_retriever=knowledge_retriever,
    )


__all__ = [
    "Claim",
    "ClaimExtractor",
    "ClaimType",
    "FactCheckReport",
    "FactChecker",
    "FactCheckerConfig",
    "VerificationResult",
    "VerificationStatus",
    "create_fact_checker",
]
