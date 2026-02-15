"""Entity Linker for Knowledge Graph Integration.

Links extracted entities to knowledge graph nodes with:
- Entity disambiguation for same-name entities
- Coreference resolution
- Entity normalization
- Confidence scoring
- Batch processing support
- EB-1A specific entity handling
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum
import hashlib
import logging
import re
from typing import Any

from .graph_constructor import Entity, EntityType, KnowledgeGraph

logger = logging.getLogger(__name__)


class LinkConfidence(str, Enum):
    """Confidence levels for entity links."""

    HIGH = "high"  # >0.9 confidence
    MEDIUM = "medium"  # 0.7-0.9 confidence
    LOW = "low"  # 0.5-0.7 confidence
    UNCERTAIN = "uncertain"  # <0.5 confidence


class DisambiguationMethod(str, Enum):
    """Methods used for disambiguation."""

    EXACT_MATCH = "exact_match"
    ALIAS_MATCH = "alias_match"
    EMBEDDING_SIMILARITY = "embedding_similarity"
    CONTEXT_ANALYSIS = "context_analysis"
    TYPE_CONSTRAINT = "type_constraint"
    LLM_DISAMBIGUATION = "llm_disambiguation"
    COREFERENCE = "coreference"
    COMBINED = "combined"


@dataclass
class EntityCandidate:
    """A potential entity match from the knowledge graph."""

    entity_id: str
    entity_name: str
    entity_type: EntityType
    score: float  # 0-1 similarity/confidence score
    method: DisambiguationMethod
    context_features: dict[str, Any] = field(default_factory=dict)
    aliases: set[str] = field(default_factory=set)
    source_docs: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        # Ensure aliases and source_docs are sets
        if isinstance(self.aliases, list):
            self.aliases = set(self.aliases)
        if isinstance(self.source_docs, list):
            self.source_docs = set(self.source_docs)

    @property
    def confidence_level(self) -> LinkConfidence:
        """Get confidence level based on score."""
        if self.score >= 0.9:
            return LinkConfidence.HIGH
        if self.score >= 0.7:
            return LinkConfidence.MEDIUM
        if self.score >= 0.5:
            return LinkConfidence.LOW
        return LinkConfidence.UNCERTAIN

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type.value,
            "score": self.score,
            "method": self.method.value,
            "confidence_level": self.confidence_level.value,
            "context_features": self.context_features,
            "aliases": list(self.aliases),
        }


@dataclass
class EntityMention:
    """An entity mention in text to be linked."""

    text: str
    start_pos: int
    end_pos: int
    entity_type: EntityType | None = None
    context: str = ""  # Surrounding text for disambiguation
    doc_id: str = ""
    sentence_id: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "entity_type": self.entity_type.value if self.entity_type else None,
            "context": self.context,
            "doc_id": self.doc_id,
            "sentence_id": self.sentence_id,
        }


@dataclass
class EntityLink:
    """A resolved link between a mention and a knowledge graph entity."""

    mention: EntityMention
    candidate: EntityCandidate | None
    linked: bool
    confidence: float
    disambiguation_details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def entity_id(self) -> str | None:
        return self.candidate.entity_id if self.candidate else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mention": self.mention.to_dict(),
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "linked": self.linked,
            "confidence": self.confidence,
            "entity_id": self.entity_id,
            "disambiguation_details": self.disambiguation_details,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CorefCluster:
    """A cluster of coreferent mentions."""

    cluster_id: str
    mentions: list[EntityMention] = field(default_factory=list)
    representative: EntityMention | None = None
    linked_entity_id: str | None = None
    confidence: float = 0.0

    def add_mention(self, mention: EntityMention) -> None:
        self.mentions.append(mention)
        # Update representative if this mention is more specific
        if self.representative is None or len(mention.text) > len(self.representative.text):
            self.representative = mention

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "mentions": [m.to_dict() for m in self.mentions],
            "representative": self.representative.to_dict() if self.representative else None,
            "linked_entity_id": self.linked_entity_id,
            "confidence": self.confidence,
        }


class DisambiguationStrategy(ABC):
    """Abstract base class for disambiguation strategies."""

    @abstractmethod
    async def disambiguate(
        self,
        mention: EntityMention,
        candidates: list[EntityCandidate],
        context: dict[str, Any] | None = None,
    ) -> list[EntityCandidate]:
        """
        Rank and filter candidates for a mention.

        Args:
            mention: The entity mention to disambiguate
            candidates: List of candidate entities from the knowledge graph
            context: Additional context for disambiguation

        Returns:
            Ranked and filtered list of candidates
        """


class ExactMatchStrategy(DisambiguationStrategy):
    """Exact string matching strategy."""

    async def disambiguate(
        self,
        mention: EntityMention,
        candidates: list[EntityCandidate],
        context: dict[str, Any] | None = None,
    ) -> list[EntityCandidate]:
        results = []
        mention_text = mention.text.lower().strip()

        for candidate in candidates:
            candidate_name = candidate.entity_name.lower().strip()

            if mention_text == candidate_name:
                candidate.score = 1.0
                candidate.method = DisambiguationMethod.EXACT_MATCH
                results.append(candidate)
            elif mention_text in candidate.aliases or any(
                mention_text == alias.lower() for alias in candidate.aliases
            ):
                candidate.score = 0.95
                candidate.method = DisambiguationMethod.ALIAS_MATCH
                results.append(candidate)

        return sorted(results, key=lambda x: x.score, reverse=True)


class FuzzyMatchStrategy(DisambiguationStrategy):
    """Fuzzy string matching using sequence similarity."""

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    async def disambiguate(
        self,
        mention: EntityMention,
        candidates: list[EntityCandidate],
        context: dict[str, Any] | None = None,
    ) -> list[EntityCandidate]:
        results = []
        mention_text = mention.text.lower().strip()

        for candidate in candidates:
            candidate_name = candidate.entity_name.lower().strip()

            # Calculate similarity
            similarity = SequenceMatcher(None, mention_text, candidate_name).ratio()

            # Check aliases too
            best_alias_sim = 0.0
            for alias in candidate.aliases:
                alias_sim = SequenceMatcher(None, mention_text, alias.lower()).ratio()
                best_alias_sim = max(best_alias_sim, alias_sim)

            best_score = max(similarity, best_alias_sim)

            if best_score >= self.threshold:
                candidate.score = best_score
                candidate.method = (
                    DisambiguationMethod.ALIAS_MATCH
                    if best_alias_sim > similarity
                    else DisambiguationMethod.EXACT_MATCH
                )
                results.append(candidate)

        return sorted(results, key=lambda x: x.score, reverse=True)


class TypeConstraintStrategy(DisambiguationStrategy):
    """Filter candidates by entity type constraints."""

    def __init__(self, type_compatibility: dict[EntityType, set[EntityType]] | None = None):
        # Default type compatibility rules
        self.type_compatibility = type_compatibility or {
            EntityType.PERSON: {EntityType.PERSON},
            EntityType.ORGANIZATION: {EntityType.ORGANIZATION},
            EntityType.LOCATION: {EntityType.LOCATION},
            EntityType.CASE: {EntityType.CASE, EntityType.DOCUMENT},
            EntityType.LAW: {EntityType.LAW, EntityType.REGULATION},
            EntityType.REGULATION: {EntityType.LAW, EntityType.REGULATION},
            EntityType.CRITERION: {EntityType.CRITERION, EntityType.CONCEPT},
            EntityType.EVIDENCE: {EntityType.EVIDENCE, EntityType.DOCUMENT},
            EntityType.CONCEPT: {EntityType.CONCEPT},
            EntityType.DOCUMENT: {EntityType.DOCUMENT, EntityType.CASE, EntityType.EVIDENCE},
        }

    async def disambiguate(
        self,
        mention: EntityMention,
        candidates: list[EntityCandidate],
        context: dict[str, Any] | None = None,
    ) -> list[EntityCandidate]:
        if mention.entity_type is None:
            # No type constraint, return all with slight penalty
            for candidate in candidates:
                candidate.context_features["type_match"] = "unknown"
            return candidates

        results = []
        compatible_types = self.type_compatibility.get(mention.entity_type, {mention.entity_type})

        for candidate in candidates:
            if candidate.entity_type in compatible_types:
                # Boost score for exact type match
                if candidate.entity_type == mention.entity_type:
                    candidate.score = min(1.0, candidate.score * 1.1)
                    candidate.context_features["type_match"] = "exact"
                else:
                    candidate.context_features["type_match"] = "compatible"
                candidate.method = DisambiguationMethod.TYPE_CONSTRAINT
                results.append(candidate)

        return results


class EmbeddingSimilarityStrategy(DisambiguationStrategy):
    """Disambiguation using embedding similarity."""

    def __init__(
        self,
        embedder: Callable[[list[str]], Coroutine[Any, Any, list[list[float]]]] | None = None,
        threshold: float = 0.7,
    ):
        self.embedder = embedder
        self.threshold = threshold

    async def disambiguate(
        self,
        mention: EntityMention,
        candidates: list[EntityCandidate],
        context: dict[str, Any] | None = None,
    ) -> list[EntityCandidate]:
        if not self.embedder or not candidates:
            return candidates

        # Get mention embedding (include context if available)
        mention_text = mention.text
        if mention.context:
            mention_text = f"{mention.context[:100]} {mention.text} {mention.context[-100:]}"

        try:
            mention_embeddings = await self.embedder([mention_text])
            mention_embedding = mention_embeddings[0]
        except Exception as e:
            logger.warning(f"Failed to generate mention embedding: {e}")
            return candidates

        results = []
        for candidate in candidates:
            # Use pre-computed entity embedding if available
            entity_embedding = candidate.context_features.get("embedding")

            if entity_embedding is None:
                # Generate embedding for candidate
                try:
                    candidate_embeddings = await self.embedder([candidate.entity_name])
                    entity_embedding = candidate_embeddings[0]
                except Exception:
                    continue

            # Calculate cosine similarity
            similarity = self._cosine_similarity(mention_embedding, entity_embedding)

            if similarity >= self.threshold:
                candidate.score = max(candidate.score, similarity)
                candidate.method = DisambiguationMethod.EMBEDDING_SIMILARITY
                candidate.context_features["embedding_similarity"] = similarity
                results.append(candidate)

        return sorted(results, key=lambda x: x.score, reverse=True)

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class ContextAnalysisStrategy(DisambiguationStrategy):
    """Analyze surrounding context for disambiguation."""

    # Context keywords for EB-1A specific entities
    EB1A_CONTEXT_PATTERNS = {
        EntityType.CRITERION: [
            r"criterion\s+(\d+|[ivx]+)",
            r"(?:awards?|prizes?|recognition)",
            r"(?:membership|association|society)",
            r"(?:published\s+material|media\s+coverage)",
            r"(?:judging|reviewer|evaluator)",
            r"(?:original\s+contribution|significant\s+impact)",
            r"(?:scholarly\s+articles?|publications?)",
            r"(?:exhibition|gallery|display)",
            r"(?:leading\s+role|critical\s+role)",
            r"(?:high\s+salary|remuneration)",
            r"(?:commercial\s+success)",
        ],
        EntityType.CASE: [
            r"matter\s+of\s+",
            r"aao\s+[a-z]{3}\d+",
            r"\bv\.\s+",
            r"(?:petition|case|application)",
            r"(?:approved|denied|rfe)",
        ],
        EntityType.REGULATION: [
            r"8\s*c\.?f\.?r\.?",
            r"(?:ina|immigration\s+and\s+nationality\s+act)",
            r"8\s*u\.?s\.?c\.?",
            r"(?:regulation|statute|provision)",
        ],
        EntityType.EVIDENCE: [
            r"(?:exhibit|evidence|document)",
            r"(?:letter|certificate|report)",
            r"(?:supporting|demonstrates|shows)",
        ],
    }

    async def disambiguate(
        self,
        mention: EntityMention,
        candidates: list[EntityCandidate],
        context: dict[str, Any] | None = None,
    ) -> list[EntityCandidate]:
        if not mention.context:
            return candidates

        context_lower = mention.context.lower()
        results = []

        for candidate in candidates:
            context_score = 0.0
            matching_patterns = []

            # Check for type-specific context patterns
            patterns = self.EB1A_CONTEXT_PATTERNS.get(candidate.entity_type, [])
            for pattern in patterns:
                if re.search(pattern, context_lower, re.IGNORECASE):
                    context_score += 0.1
                    matching_patterns.append(pattern)

            # Check if candidate name appears in context
            if candidate.entity_name.lower() in context_lower:
                context_score += 0.2

            # Check for alias mentions in context
            for alias in candidate.aliases:
                if alias.lower() in context_lower:
                    context_score += 0.1
                    break

            if context_score > 0:
                candidate.score = min(1.0, candidate.score + context_score)
                candidate.method = DisambiguationMethod.CONTEXT_ANALYSIS
                candidate.context_features["matching_patterns"] = matching_patterns[:5]
                candidate.context_features["context_boost"] = context_score
                results.append(candidate)
            else:
                results.append(candidate)

        return sorted(results, key=lambda x: x.score, reverse=True)


class LLMDisambiguationStrategy(DisambiguationStrategy):
    """Use LLM for complex disambiguation cases."""

    def __init__(
        self,
        llm_caller: Callable[[str, str], Coroutine[Any, Any, str]] | None = None,
        threshold: float = 0.6,
    ):
        self.llm_caller = llm_caller
        self.threshold = threshold

    async def disambiguate(
        self,
        mention: EntityMention,
        candidates: list[EntityCandidate],
        context: dict[str, Any] | None = None,
    ) -> list[EntityCandidate]:
        if not self.llm_caller or not candidates:
            return candidates

        # Only use LLM for ambiguous cases
        if len(candidates) <= 1 or (candidates and candidates[0].score > 0.9):
            return candidates

        # Prepare prompt
        candidate_descriptions = "\n".join(
            f"{i+1}. {c.entity_name} (Type: {c.entity_type.value}, "
            f"Current Score: {c.score:.2f})"
            for i, c in enumerate(candidates[:5])
        )

        prompt = f"""Given the following entity mention and candidate matches, determine the best match.

Mention: "{mention.text}"
Context: "{mention.context[:500] if mention.context else 'No context available'}"
Mention Type: {mention.entity_type.value if mention.entity_type else 'Unknown'}

Candidates:
{candidate_descriptions}

Instructions:
1. Consider the context and entity type
2. Return the number (1-{min(5, len(candidates))}) of the best matching candidate
3. If none match well, return 0
4. Also provide a confidence score (0-1)

Response format: MATCH:<number>,CONFIDENCE:<score>
Example: MATCH:2,CONFIDENCE:0.85"""

        try:
            response = await self.llm_caller("You are an entity disambiguation expert.", prompt)

            # Parse response
            match_num = 0
            confidence = 0.5

            match_pattern = re.search(r"MATCH:\s*(\d+)", response)
            conf_pattern = re.search(r"CONFIDENCE:\s*([0-9.]+)", response)

            if match_pattern:
                match_num = int(match_pattern.group(1))
            if conf_pattern:
                confidence = float(conf_pattern.group(1))

            # Update candidate scores based on LLM response
            if 1 <= match_num <= len(candidates):
                selected_idx = match_num - 1
                for i, candidate in enumerate(candidates):
                    if i == selected_idx:
                        candidate.score = max(candidate.score, confidence)
                        candidate.method = DisambiguationMethod.LLM_DISAMBIGUATION
                        candidate.context_features["llm_selected"] = True
                        candidate.context_features["llm_confidence"] = confidence
                    else:
                        candidate.score *= 0.8  # Reduce score for non-selected

        except Exception as e:
            logger.warning(f"LLM disambiguation failed: {e}")

        return sorted(candidates, key=lambda x: x.score, reverse=True)


class CorefResolver:
    """Coreference resolution for entity mentions."""

    # Pronoun patterns
    PRONOUNS = {
        "personal": {"he", "she", "it", "they", "him", "her", "them"},
        "possessive": {"his", "her", "its", "their", "hers", "theirs"},
        "demonstrative": {"this", "that", "these", "those"},
        "relative": {"who", "whom", "which", "that", "whose"},
    }

    # EB-1A specific referring expressions
    EB1A_REFERENCES = {
        EntityType.PERSON: [
            r"the\s+(?:beneficiary|petitioner|applicant|alien)",
            r"(?:dr\.|mr\.|ms\.|mrs\.)\s+\w+",
            r"the\s+(?:researcher|scientist|professor|expert)",
        ],
        EntityType.CRITERION: [
            r"this\s+criterion",
            r"the\s+(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+criterion",
            r"criterion\s+\(?[ivx]+\)?",
        ],
        EntityType.CASE: [
            r"this\s+(?:case|petition|matter)",
            r"the\s+(?:instant|present|current)\s+(?:case|petition)",
        ],
        EntityType.EVIDENCE: [
            r"this\s+(?:evidence|document|exhibit)",
            r"the\s+(?:above|foregoing|attached)\s+(?:evidence|document)",
        ],
    }

    def __init__(self, window_size: int = 5):
        """
        Initialize coreference resolver.

        Args:
            window_size: Number of sentences to consider for coreference
        """
        self.window_size = window_size
        self._clusters: dict[str, CorefCluster] = {}

    def resolve(
        self,
        mentions: list[EntityMention],
        context: str = "",
    ) -> list[CorefCluster]:
        """
        Resolve coreferences among mentions.

        Args:
            mentions: List of entity mentions to cluster
            context: Full document context

        Returns:
            List of coreference clusters
        """
        self._clusters = {}
        sentences = self._split_sentences(context) if context else []

        # Sort mentions by position
        sorted_mentions = sorted(mentions, key=lambda m: (m.sentence_id, m.start_pos))

        for mention in sorted_mentions:
            # Check if this is a pronoun or referring expression
            if self._is_anaphoric(mention):
                # Find antecedent
                antecedent = self._find_antecedent(mention, sorted_mentions, sentences)
                if antecedent:
                    self._merge_mentions(mention, antecedent)
                else:
                    self._create_cluster(mention)
            else:
                # Check if this mention should merge with existing cluster
                merged = False
                for cluster in self._clusters.values():
                    if self._should_merge(mention, cluster):
                        cluster.add_mention(mention)
                        merged = True
                        break

                if not merged:
                    self._create_cluster(mention)

        return list(self._clusters.values())

    def _is_anaphoric(self, mention: EntityMention) -> bool:
        """Check if mention is an anaphoric reference."""
        text_lower = mention.text.lower().strip()

        # Check pronouns
        for pronoun_set in self.PRONOUNS.values():
            if text_lower in pronoun_set:
                return True

        # Check referring expressions
        for patterns in self.EB1A_REFERENCES.values():
            for pattern in patterns:
                if re.match(pattern, text_lower, re.IGNORECASE):
                    return True

        return False

    def _find_antecedent(
        self,
        mention: EntityMention,
        all_mentions: list[EntityMention],
        sentences: list[str],
    ) -> EntityMention | None:
        """Find the antecedent for an anaphoric mention."""
        mention_idx = all_mentions.index(mention)

        # Look backwards for potential antecedents
        for i in range(mention_idx - 1, -1, -1):
            candidate = all_mentions[i]

            # Skip if too far away
            if mention.sentence_id - candidate.sentence_id > self.window_size:
                break

            # Skip other anaphoric mentions
            if self._is_anaphoric(candidate):
                continue

            # Check type compatibility
            if mention.entity_type and candidate.entity_type:
                if mention.entity_type != candidate.entity_type:
                    continue

            # Check gender/number agreement for pronouns
            if self._agrees_with(mention, candidate):
                return candidate

        return None

    def _agrees_with(self, anaphor: EntityMention, antecedent: EntityMention) -> bool:
        """Check if anaphor agrees with antecedent."""
        anaphor_lower = anaphor.text.lower()

        # Simple agreement check based on entity type
        if antecedent.entity_type == EntityType.PERSON:
            return anaphor_lower in {
                "he",
                "she",
                "him",
                "her",
                "his",
                "hers",
                "they",
                "them",
                "their",
            }
        if antecedent.entity_type in {EntityType.ORGANIZATION, EntityType.CASE}:
            return anaphor_lower in {"it", "its", "they", "them", "their", "this", "that"}
        if antecedent.entity_type == EntityType.CRITERION:
            return anaphor_lower in {"it", "this", "that"} or "criterion" in anaphor_lower

        return True  # Default to agreeing

    def _should_merge(self, mention: EntityMention, cluster: CorefCluster) -> bool:
        """Check if mention should merge with cluster."""
        if not cluster.representative:
            return False

        rep = cluster.representative

        # Same text (case-insensitive)
        if mention.text.lower() == rep.text.lower():
            return True

        # Same entity type and similar text
        if mention.entity_type == rep.entity_type:
            similarity = SequenceMatcher(None, mention.text.lower(), rep.text.lower()).ratio()
            if similarity > 0.8:
                return True

        # Check if one is abbreviation of other
        return bool(
            self._is_abbreviation(mention.text, rep.text)
            or self._is_abbreviation(rep.text, mention.text)
        )

    def _is_abbreviation(self, short: str, long: str) -> bool:
        """Check if short is an abbreviation of long."""
        if len(short) >= len(long):
            return False

        # Simple initials check
        words = long.split()
        if len(words) > 1:
            initials = "".join(w[0].upper() for w in words if w)
            if short.upper() == initials:
                return True

        return False

    def _create_cluster(self, mention: EntityMention) -> CorefCluster:
        """Create a new coreference cluster."""
        cluster_id = hashlib.md5(
            f"{mention.text}:{mention.start_pos}".encode(), usedforsecurity=False
        ).hexdigest()[:12]
        cluster = CorefCluster(cluster_id=cluster_id)
        cluster.add_mention(mention)
        self._clusters[cluster_id] = cluster
        return cluster

    def _merge_mentions(self, anaphor: EntityMention, antecedent: EntityMention) -> None:
        """Merge anaphor into antecedent's cluster."""
        # Find antecedent's cluster
        for cluster in self._clusters.values():
            if antecedent in cluster.mentions:
                cluster.add_mention(anaphor)
                return

        # If antecedent has no cluster, create one
        cluster = self._create_cluster(antecedent)
        cluster.add_mention(anaphor)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]


class EntityNormalizer:
    """Normalize entity names and surface forms."""

    # EB-1A specific normalization rules
    EB1A_NORMALIZATIONS = {
        # Criterion names
        r"criterion\s*(?:1|i|one)": "Criterion I (Awards)",
        r"criterion\s*(?:2|ii|two)": "Criterion II (Membership)",
        r"criterion\s*(?:3|iii|three)": "Criterion III (Published Material)",
        r"criterion\s*(?:4|iv|four)": "Criterion IV (Judging)",
        r"criterion\s*(?:5|v|five)": "Criterion V (Original Contribution)",
        r"criterion\s*(?:6|vi|six)": "Criterion VI (Scholarly Articles)",
        r"criterion\s*(?:7|vii|seven)": "Criterion VII (Exhibitions)",
        r"criterion\s*(?:8|viii|eight)": "Criterion VIII (Leading Role)",
        r"criterion\s*(?:9|ix|nine)": "Criterion IX (High Salary)",
        r"criterion\s*(?:10|x|ten)": "Criterion X (Commercial Success)",
        # Regulation references
        r"8\s*cfr\s*204\.5\s*\(h\)": "8 CFR 204.5(h)",
        r"8\s*c\.?f\.?r\.?\s*§?\s*204\.5": "8 CFR 204.5",
        r"ina\s*§?\s*203\s*\(b\)\s*\(1\)\s*\(a\)": "INA 203(b)(1)(A)",
        # Common case names
        r"matter\s+of\s+dhanasar": "Matter of Dhanasar",
        r"matter\s+of\s+kazarian": "Matter of Kazarian",
        # Organization abbreviations
        r"\buscis\b": "USCIS",
        r"\baao\b": "AAO",
        r"\bdhs\b": "DHS",
    }

    # Title normalization
    TITLE_PREFIXES = {
        "dr": "Dr.",
        "dr.": "Dr.",
        "mr": "Mr.",
        "mr.": "Mr.",
        "ms": "Ms.",
        "ms.": "Ms.",
        "mrs": "Mrs.",
        "mrs.": "Mrs.",
        "prof": "Prof.",
        "prof.": "Prof.",
    }

    def __init__(self, custom_rules: dict[str, str] | None = None):
        """
        Initialize entity normalizer.

        Args:
            custom_rules: Additional normalization rules (pattern -> normalized form)
        """
        self.custom_rules = custom_rules or {}

    def normalize(self, text: str, entity_type: EntityType | None = None) -> str:
        """
        Normalize entity text.

        Args:
            text: Entity text to normalize
            entity_type: Optional entity type for type-specific normalization

        Returns:
            Normalized entity text
        """
        normalized = text.strip()

        # Apply EB-1A specific normalizations
        for pattern, replacement in self.EB1A_NORMALIZATIONS.items():
            if re.search(pattern, normalized, re.IGNORECASE):
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # Apply custom rules
        for pattern, replacement in self.custom_rules.items():
            if re.search(pattern, normalized, re.IGNORECASE):
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # Type-specific normalization
        if entity_type == EntityType.PERSON:
            normalized = self._normalize_person_name(normalized)
        elif entity_type == EntityType.ORGANIZATION:
            normalized = self._normalize_organization(normalized)
        elif entity_type == EntityType.REGULATION:
            normalized = self._normalize_regulation(normalized)

        return normalized

    def _normalize_person_name(self, name: str) -> str:
        """Normalize person name."""
        parts = name.split()
        normalized_parts = []

        for i, part in enumerate(parts):
            part_lower = part.lower().rstrip(".,")
            if i == 0 and part_lower in self.TITLE_PREFIXES:
                normalized_parts.append(self.TITLE_PREFIXES[part_lower])
            else:
                # Title case for name parts
                normalized_parts.append(part.capitalize())

        return " ".join(normalized_parts)

    def _normalize_organization(self, name: str) -> str:
        """Normalize organization name."""
        # Remove common suffixes for matching
        suffixes = [", Inc.", ", LLC", ", Ltd.", " Inc.", " LLC", " Ltd."]
        normalized = name
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]

        return normalized.strip()

    def _normalize_regulation(self, ref: str) -> str:
        """Normalize regulation reference."""
        # Standardize CFR format
        ref = re.sub(r"(\d+)\s*c\.?f\.?r\.?\s*", r"\1 CFR ", ref, flags=re.IGNORECASE)

        # Standardize section symbol
        ref = re.sub(r"§\s*", "Section ", ref)

        return ref.strip()

    def generate_aliases(self, text: str, entity_type: EntityType | None = None) -> set[str]:
        """
        Generate common aliases for an entity.

        Args:
            text: Entity text
            entity_type: Optional entity type

        Returns:
            Set of aliases
        """
        aliases = set()
        normalized = self.normalize(text, entity_type)

        if normalized != text:
            aliases.add(normalized)

        # Generate additional aliases based on type
        if entity_type == EntityType.PERSON:
            aliases.update(self._generate_person_aliases(text))
        elif entity_type == EntityType.ORGANIZATION:
            aliases.update(self._generate_organization_aliases(text))
        elif entity_type == EntityType.CRITERION:
            aliases.update(self._generate_criterion_aliases(text))

        return aliases

    def _generate_person_aliases(self, name: str) -> set[str]:
        """Generate aliases for person name."""
        aliases = set()
        parts = name.split()

        if len(parts) >= 2:
            # Last name only
            aliases.add(parts[-1])

            # First initial + last name
            aliases.add(f"{parts[0][0]}. {parts[-1]}")

            # First name + last initial
            if len(parts[-1]) > 0:
                aliases.add(f"{parts[0]} {parts[-1][0]}.")

        return aliases

    def _generate_organization_aliases(self, name: str) -> set[str]:
        """Generate aliases for organization."""
        aliases = set()
        words = name.split()

        if len(words) > 1:
            # Acronym
            acronym = "".join(w[0].upper() for w in words if w and w[0].isupper())
            if len(acronym) >= 2:
                aliases.add(acronym)

        return aliases

    def _generate_criterion_aliases(self, name: str) -> set[str]:
        """Generate aliases for EB-1A criterion."""
        aliases = set()

        # Map between different criterion number formats
        roman_to_arabic = {
            "i": "1",
            "ii": "2",
            "iii": "3",
            "iv": "4",
            "v": "5",
            "vi": "6",
            "vii": "7",
            "viii": "8",
            "ix": "9",
            "x": "10",
        }
        arabic_to_roman = {v: k for k, v in roman_to_arabic.items()}

        match = re.search(r"criterion\s+([ivx]+|\d+)", name, re.IGNORECASE)
        if match:
            num = match.group(1).lower()
            if num in roman_to_arabic:
                aliases.add(f"Criterion {roman_to_arabic[num]}")
            elif num in arabic_to_roman:
                aliases.add(f"Criterion {arabic_to_roman[num].upper()}")

        return aliases


class EntityLinker:
    """
    Main entity linking class that coordinates disambiguation strategies.

    Links extracted entity mentions to nodes in the knowledge graph using
    multiple disambiguation strategies including exact matching, fuzzy matching,
    type constraints, embedding similarity, context analysis, and LLM-based
    disambiguation.
    """

    def __init__(
        self,
        knowledge_graph: KnowledgeGraph,
        embedder: Callable[[list[str]], Coroutine[Any, Any, list[list[float]]]] | None = None,
        llm_caller: Callable[[str, str], Coroutine[Any, Any, str]] | None = None,
        normalizer: EntityNormalizer | None = None,
        coref_resolver: CorefResolver | None = None,
        min_confidence: float = 0.5,
        max_candidates: int = 10,
    ):
        """
        Initialize Entity Linker.

        Args:
            knowledge_graph: Knowledge graph to link entities to
            embedder: Optional async function for generating embeddings
            llm_caller: Optional async LLM function for disambiguation
            normalizer: Entity normalizer instance
            coref_resolver: Coreference resolver instance
            min_confidence: Minimum confidence threshold for links
            max_candidates: Maximum candidates to consider per mention
        """
        self.graph = knowledge_graph
        self.embedder = embedder
        self.llm_caller = llm_caller
        self.normalizer = normalizer or EntityNormalizer()
        self.coref_resolver = coref_resolver or CorefResolver()
        self.min_confidence = min_confidence
        self.max_candidates = max_candidates

        # Initialize disambiguation strategies
        self._strategies: list[DisambiguationStrategy] = [
            ExactMatchStrategy(),
            FuzzyMatchStrategy(threshold=0.7),
            TypeConstraintStrategy(),
            ContextAnalysisStrategy(),
        ]

        if embedder:
            self._strategies.append(EmbeddingSimilarityStrategy(embedder=embedder))

        if llm_caller:
            self._strategies.append(LLMDisambiguationStrategy(llm_caller=llm_caller))

        # Statistics
        self._stats = {
            "mentions_processed": 0,
            "mentions_linked": 0,
            "mentions_unlinked": 0,
            "avg_confidence": 0.0,
            "disambiguation_methods": {},
        }

    async def link(
        self,
        mention: EntityMention,
        context: dict[str, Any] | None = None,
    ) -> EntityLink:
        """
        Link a single entity mention to the knowledge graph.

        Args:
            mention: Entity mention to link
            context: Additional context for disambiguation

        Returns:
            EntityLink with the best matching entity or None if no match
        """
        # Normalize mention text
        normalized_text = self.normalizer.normalize(mention.text, mention.entity_type)
        mention_with_norm = EntityMention(
            text=normalized_text,
            start_pos=mention.start_pos,
            end_pos=mention.end_pos,
            entity_type=mention.entity_type,
            context=mention.context,
            doc_id=mention.doc_id,
            sentence_id=mention.sentence_id,
        )

        # Get initial candidates from knowledge graph
        candidates = self._get_candidates(mention_with_norm)

        if not candidates:
            self._update_stats(linked=False)
            return EntityLink(
                mention=mention,
                candidate=None,
                linked=False,
                confidence=0.0,
                disambiguation_details={"reason": "no_candidates"},
            )

        # Apply disambiguation strategies sequentially
        for strategy in self._strategies:
            candidates = await strategy.disambiguate(mention_with_norm, candidates, context)

            # Early exit if we have a high-confidence match
            if candidates and candidates[0].score >= 0.95:
                break

        # Filter by minimum confidence
        candidates = [c for c in candidates if c.score >= self.min_confidence]

        if not candidates:
            self._update_stats(linked=False)
            return EntityLink(
                mention=mention,
                candidate=None,
                linked=False,
                confidence=0.0,
                disambiguation_details={"reason": "below_threshold"},
            )

        # Select best candidate
        best_candidate = candidates[0]

        self._update_stats(
            linked=True, confidence=best_candidate.score, method=best_candidate.method
        )

        return EntityLink(
            mention=mention,
            candidate=best_candidate,
            linked=True,
            confidence=best_candidate.score,
            disambiguation_details={
                "method": best_candidate.method.value,
                "candidates_considered": len(candidates),
                "context_features": best_candidate.context_features,
            },
        )

    async def link_batch(
        self,
        mentions: list[EntityMention],
        context: str = "",
        resolve_coreference: bool = True,
        concurrency: int = 10,
    ) -> list[EntityLink]:
        """
        Link multiple entity mentions with optional coreference resolution.

        Args:
            mentions: List of entity mentions to link
            context: Document context for coreference resolution
            resolve_coreference: Whether to resolve coreferences
            concurrency: Maximum concurrent link operations

        Returns:
            List of EntityLinks
        """
        if not mentions:
            return []

        # Resolve coreferences if enabled
        coref_clusters: list[CorefCluster] = []
        if resolve_coreference and context:
            coref_clusters = self.coref_resolver.resolve(mentions, context)

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)

        async def link_with_semaphore(mention: EntityMention) -> EntityLink:
            async with semaphore:
                return await self.link(mention)

        # Link representative mentions from each cluster
        cluster_links: dict[str, EntityLink] = {}
        non_clustered_mentions: list[EntityMention] = list(mentions)

        for cluster in coref_clusters:
            if cluster.representative:
                # Link the representative mention
                link = await self.link(cluster.representative)
                cluster_links[cluster.cluster_id] = link
                cluster.linked_entity_id = link.entity_id
                cluster.confidence = link.confidence

                # Remove clustered mentions from non-clustered list
                for m in cluster.mentions:
                    if m in non_clustered_mentions:
                        non_clustered_mentions.remove(m)

        # Link remaining non-clustered mentions concurrently
        remaining_links = await asyncio.gather(
            *[link_with_semaphore(m) for m in non_clustered_mentions]
        )

        # Combine results
        results: list[EntityLink] = []
        mention_to_cluster: dict[int, str] = {}

        for cluster in coref_clusters:
            for m in cluster.mentions:
                mention_to_cluster[id(m)] = cluster.cluster_id

        for mention in mentions:
            cluster_id = mention_to_cluster.get(id(mention))
            if cluster_id and cluster_id in cluster_links:
                # Use cluster's linked entity
                cluster_link = cluster_links[cluster_id]
                results.append(
                    EntityLink(
                        mention=mention,
                        candidate=cluster_link.candidate,
                        linked=cluster_link.linked,
                        confidence=cluster_link.confidence,
                        disambiguation_details={
                            **cluster_link.disambiguation_details,
                            "via_coreference": True,
                            "cluster_id": cluster_id,
                        },
                    )
                )
            else:
                # Find in remaining links
                for link in remaining_links:
                    if (
                        link.mention.start_pos == mention.start_pos
                        and link.mention.doc_id == mention.doc_id
                    ):
                        results.append(link)
                        break
                else:
                    # Mention not found, link it now
                    link = await self.link(mention)
                    results.append(link)

        return results

    def _get_candidates(self, mention: EntityMention) -> list[EntityCandidate]:
        """Get candidate entities from knowledge graph."""
        candidates = []

        # Search by name
        entity = self.graph.get_entity_by_name(mention.text)
        if entity:
            candidates.append(self._entity_to_candidate(entity, 0.8))

        # Search by type if specified
        if mention.entity_type:
            type_entities = self.graph.get_entities_by_type(mention.entity_type)
            for entity in type_entities[: self.max_candidates * 2]:
                if entity.id not in {c.entity_id for c in candidates}:
                    candidates.append(self._entity_to_candidate(entity, 0.3))

        # Search in aliases
        for entity_id, entity in self.graph._entities.items():
            if entity_id in {c.entity_id for c in candidates}:
                continue

            mention_lower = mention.text.lower()
            if mention_lower in {a.lower() for a in entity.aliases}:
                candidates.append(self._entity_to_candidate(entity, 0.7))

            if len(candidates) >= self.max_candidates * 2:
                break

        # Limit candidates
        return candidates[: self.max_candidates]

    def _entity_to_candidate(self, entity: Entity, initial_score: float) -> EntityCandidate:
        """Convert knowledge graph entity to candidate."""
        return EntityCandidate(
            entity_id=entity.id,
            entity_name=entity.name,
            entity_type=entity.entity_type,
            score=initial_score,
            method=DisambiguationMethod.EXACT_MATCH,
            aliases=entity.aliases.copy(),
            source_docs=entity.source_docs.copy(),
            context_features={"embedding": entity.embedding} if entity.embedding else {},
        )

    def _update_stats(
        self,
        linked: bool,
        confidence: float = 0.0,
        method: DisambiguationMethod | None = None,
    ) -> None:
        """Update linking statistics."""
        self._stats["mentions_processed"] += 1

        if linked:
            self._stats["mentions_linked"] += 1

            # Update average confidence
            n = self._stats["mentions_linked"]
            old_avg = self._stats["avg_confidence"]
            self._stats["avg_confidence"] = old_avg + (confidence - old_avg) / n

            # Track disambiguation methods
            if method:
                method_key = method.value
                self._stats["disambiguation_methods"][method_key] = (
                    self._stats["disambiguation_methods"].get(method_key, 0) + 1
                )
        else:
            self._stats["mentions_unlinked"] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get linking statistics."""
        total = self._stats["mentions_processed"]
        return {
            **self._stats,
            "link_rate": self._stats["mentions_linked"] / total if total > 0 else 0.0,
        }

    def reset_stats(self) -> None:
        """Reset linking statistics."""
        self._stats = {
            "mentions_processed": 0,
            "mentions_linked": 0,
            "mentions_unlinked": 0,
            "avg_confidence": 0.0,
            "disambiguation_methods": {},
        }


# Factory functions
def create_entity_linker(
    knowledge_graph: KnowledgeGraph,
    embedder: Callable[[list[str]], Coroutine[Any, Any, list[list[float]]]] | None = None,
    llm_caller: Callable[[str, str], Coroutine[Any, Any, str]] | None = None,
    min_confidence: float = 0.5,
) -> EntityLinker:
    """
    Create an EntityLinker with default configuration.

    Args:
        knowledge_graph: Knowledge graph to link entities to
        embedder: Optional embedding function
        llm_caller: Optional LLM function for disambiguation
        min_confidence: Minimum confidence threshold

    Returns:
        Configured EntityLinker instance
    """
    return EntityLinker(
        knowledge_graph=knowledge_graph,
        embedder=embedder,
        llm_caller=llm_caller,
        min_confidence=min_confidence,
    )


def create_normalizer(custom_rules: dict[str, str] | None = None) -> EntityNormalizer:
    """Create an EntityNormalizer with optional custom rules."""
    return EntityNormalizer(custom_rules=custom_rules)


def create_coref_resolver(window_size: int = 5) -> CorefResolver:
    """Create a CorefResolver with specified window size."""
    return CorefResolver(window_size=window_size)


__all__ = [
    "ContextAnalysisStrategy",
    # Coreference
    "CorefCluster",
    "CorefResolver",
    "DisambiguationMethod",
    # Disambiguation
    "DisambiguationStrategy",
    "EmbeddingSimilarityStrategy",
    # Core classes
    "EntityCandidate",
    "EntityLink",
    "EntityLinker",
    "EntityMention",
    # Normalization
    "EntityNormalizer",
    "ExactMatchStrategy",
    "FuzzyMatchStrategy",
    "LLMDisambiguationStrategy",
    # Enums
    "LinkConfidence",
    "TypeConstraintStrategy",
    "create_coref_resolver",
    # Factory functions
    "create_entity_linker",
    "create_normalizer",
]
