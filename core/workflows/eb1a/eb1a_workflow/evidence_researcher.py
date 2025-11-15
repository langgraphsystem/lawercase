"""Evidence Researcher for EB-1A petitions using RAG.

This module uses Retrieval-Augmented Generation to research and gather
additional evidence for EB-1A petitions, including:
- Legal precedents and case law
- Industry statistics and benchmarks
- Peer comparisons and rankings
- Citation analysis and impact metrics
- Organization background research
- Competition statistics and selection rates
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ....memory.memory_manager import MemoryManager
from ..eb1a_coordinator import (EB1ACriterion, EB1AEvidence,
                                EB1APetitionRequest, EvidenceType)

# === New Models for Research ===


class OrganizationProfile(BaseModel):
    """
    Профиль исследованной организации.

    Используется для демонстрации престижности наград,
    селективности членства, и т.д.
    """

    name: str = Field(..., description="Название организации")
    founded_year: int | None = Field(None, description="Год основания")
    location: str | None = Field(None, description="Местоположение (страна/город)")
    member_count: int | None = Field(None, description="Количество членов")
    total_applications: int | None = Field(None, description="Общее число заявок (если применимо)")
    acceptance_rate: float | None = Field(
        None, ge=0.0, le=1.0, description="Процент принятия (0.0-1.0)"
    )
    mission_statement: str | None = Field(None, description="Миссия организации")
    notable_members: list[str] = Field(default_factory=list, description="Известные члены")
    media_mentions: int | None = Field(None, description="Количество упоминаний в медиа")
    website: str | None = Field(None, description="Официальный сайт")
    selectivity_indicators: list[str] = Field(
        default_factory=list, description="Индикаторы селективности (требования, процесс отбора)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Дополнительные данные")

    def get_prestige_score(self) -> float:
        """
        Рассчитать оценку престижности (0.0-1.0).

        Основывается на:
        - Acceptance rate (ниже = лучше)
        - Member count (больше может быть лучше для крупных org)
        - Notable members
        - Media mentions
        """
        score = 0.5  # Base

        # Acceptance rate bonus (lower is better)
        if self.acceptance_rate is not None:
            if self.acceptance_rate < 0.05:  # < 5%
                score += 0.25
            elif self.acceptance_rate < 0.10:  # < 10%
                score += 0.15
            elif self.acceptance_rate < 0.20:  # < 20%
                score += 0.10

        # Notable members bonus
        if len(self.notable_members) >= 5:
            score += 0.10
        elif len(self.notable_members) >= 2:
            score += 0.05

        # Media mentions bonus
        if self.media_mentions and self.media_mentions > 1000:
            score += 0.10
        elif self.media_mentions and self.media_mentions > 100:
            score += 0.05

        # Selectivity indicators bonus
        if len(self.selectivity_indicators) >= 3:
            score += 0.05

        return min(1.0, score)


class CompetitionStats(BaseModel):
    """
    Статистика конкурса/награды.

    Используется для демонстрации конкурентности и престижности наград.
    """

    competition_name: str = Field(..., description="Название конкурса/награды")
    year: int = Field(..., description="Год проведения")
    total_entries: int | None = Field(None, description="Общее число заявок/участников")
    total_winners: int | None = Field(None, description="Общее число победителей")
    acceptance_rate: float | None = Field(None, ge=0.0, le=1.0, description="Процент победителей")
    geographic_scope: str | None = Field(
        None, description="Географический охват (local/national/international)"
    )
    jury_composition: list[str] = Field(
        default_factory=list, description="Состав жюри (эксперты, организации)"
    )
    selection_criteria: list[str] = Field(default_factory=list, description="Критерии отбора")
    prize_value: str | None = Field(None, description="Денежная стоимость или описание приза")
    previous_winners: list[str] = Field(
        default_factory=list, description="Известные предыдущие победители"
    )
    media_coverage: int | None = Field(None, description="Количество статей/упоминаний в медиа")
    organizing_body: str | None = Field(None, description="Организующий орган")
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_competitiveness_score(self) -> float:
        """
        Рассчитать оценку конкурентности (0.0-1.0).

        Основывается на:
        - Acceptance rate (ниже = лучше)
        - Total entries (больше = лучше)
        - Geographic scope
        - Jury quality
        """
        score = 0.5  # Base

        # Acceptance rate bonus (lower is better)
        if self.acceptance_rate is not None:
            if self.acceptance_rate < 0.01:  # < 1%
                score += 0.25
            elif self.acceptance_rate < 0.05:  # < 5%
                score += 0.20
            elif self.acceptance_rate < 0.10:  # < 10%
                score += 0.15
            elif self.acceptance_rate < 0.20:  # < 20%
                score += 0.10

        # Total entries bonus
        if self.total_entries:
            if self.total_entries > 1000:
                score += 0.15
            elif self.total_entries > 500:
                score += 0.10
            elif self.total_entries > 100:
                score += 0.05

        # Geographic scope bonus
        if self.geographic_scope:
            if "international" in self.geographic_scope.lower():
                score += 0.10
            elif "national" in self.geographic_scope.lower():
                score += 0.05

        return min(1.0, score)


class PublicationProfile(BaseModel):
    """
    Профиль публикации/журнала/конференции.

    Для исследования престижности outlet'ов.
    """

    name: str = Field(..., description="Название публикации/конференции")
    publication_type: str = Field(..., description="Тип (journal/conference/magazine/newspaper)")
    impact_factor: float | None = Field(None, description="Impact Factor (для журналов)")
    h5_index: int | None = Field(None, description="h5-index (для конференций)")
    circulation: int | None = Field(None, description="Тираж/читательская аудитория")
    acceptance_rate: float | None = Field(None, ge=0.0, le=1.0)
    geographic_reach: str | None = Field(None, description="Geographic reach")
    ranking: str | None = Field(None, description="Рейтинг (Q1/Q2/A*/tier-1, etc.)")
    publisher: str | None = Field(None, description="Издатель")
    editorial_board: list[str] = Field(
        default_factory=list, description="Редакторы/известные члены"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceResearcher:
    """
    RAG-powered evidence researcher for EB-1A petitions.

    Uses semantic search and retrieval to find:
    - Relevant legal precedents (Kazarian, Visinscaia, etc.)
    - Industry-specific benchmarks and statistics
    - Comparable cases and success patterns
    - Citation metrics and impact data

    Example:
        >>> researcher = EvidenceResearcher(memory_manager)
        >>> request = EB1APetitionRequest(...)
        >>> additional_evidence = await researcher.research(request)
        >>> print(f"Found {len(additional_evidence)} additional evidence items")
    """

    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize Evidence Researcher.

        Args:
            memory_manager: Memory manager for RAG queries
        """
        self.memory = memory_manager

        # Legal precedents database (in real implementation, would be in vector DB)
        self.legal_precedents = self._initialize_precedents()

    def _initialize_precedents(self) -> dict[str, dict[str, Any]]:
        """Initialize legal precedents database."""
        return {
            "kazarian": {
                "case": "Kazarian v. USCIS, 596 F.3d 1115 (9th Cir. 2010)",
                "summary": "Two-step analysis: (1) evidence meets regulatory criteria, (2) final merits determination",
                "relevance": "Establishes framework for evaluating EB-1A evidence",
                "key_points": [
                    "Must first determine if evidence meets plain language of criteria",
                    "Then conduct final merits determination of extraordinary ability",
                    "USCIS cannot impose requirements not found in regulations",
                ],
            },
            "visinscaia": {
                "case": "Visinscaia v. Beers, 4 F. Supp. 3d 126 (D.D.C. 2013)",
                "summary": "Clarifies that extraordinary ability requires sustained acclaim and recognition",
                "relevance": "Defines standards for demonstrating extraordinary ability",
                "key_points": [
                    "Must show sustained national or international acclaim",
                    "Recognition must be by peers and experts in field",
                    "Evidence must be compelling and conclusive",
                ],
            },
            "buletini": {
                "case": "Buletini v. INS, 860 F. Supp. 1222 (E.D. Mich. 1994)",
                "summary": "Awards must be nationally or internationally recognized",
                "relevance": "Clarifies award criterion requirements",
                "key_points": [
                    "Awards must have significant recognition beyond local level",
                    "Selection process must be competitive",
                    "Must demonstrate excellence, not just participation",
                ],
            },
        }

    async def research(self, request: EB1APetitionRequest) -> list[EB1AEvidence]:
        """
        Research and gather additional evidence for petition.

        Args:
            request: EB-1A petition request

        Returns:
            List of additional evidence items found through research
        """
        additional_evidence: list[EB1AEvidence] = []

        # Research for each primary criterion
        for criterion in request.primary_criteria:
            criterion_evidence = await self._research_criterion(criterion, request)
            additional_evidence.extend(criterion_evidence)

        # Research legal precedents
        legal_evidence = await self._research_legal_precedents(request)
        additional_evidence.extend(legal_evidence)

        # Research industry benchmarks
        benchmark_evidence = await self._research_benchmarks(request)
        additional_evidence.extend(benchmark_evidence)

        return additional_evidence

    async def _research_criterion(
        self, criterion: EB1ACriterion, request: EB1APetitionRequest
    ) -> list[EB1AEvidence]:
        """
        Research evidence specific to a criterion.

        Args:
            criterion: EB-1A criterion to research
            request: Full petition request

        Returns:
            Evidence items found for this criterion
        """
        evidence_items: list[EB1AEvidence] = []

        # Construct search query based on criterion
        query = self._build_criterion_query(criterion, request)

        # Use RAG to find relevant information
        try:
            # Search semantic memory for relevant context
            context_records = await self.memory.aretrieve(
                query=query,
                user_id=request.beneficiary_name,  # Use beneficiary as namespace
                topk=5,
                filters={"type": "legal_research"},
            )

            # Convert retrieved records to evidence items
            for record in context_records:
                evidence = self._record_to_evidence(record, criterion)
                if evidence:
                    evidence_items.append(evidence)

        except Exception as e:
            # Log error but continue (don't fail entire research)
            print(f"Error researching {criterion.value}: {e}")

        return evidence_items

    async def _research_legal_precedents(self, request: EB1APetitionRequest) -> list[EB1AEvidence]:
        """
        Research relevant legal precedents.

        Args:
            request: Petition request

        Returns:
            Legal precedent evidence items
        """
        evidence_items: list[EB1AEvidence] = []

        # Find most relevant precedents for petition's criteria
        for criterion in request.primary_criteria:
            precedent_key = self._get_relevant_precedent(criterion)
            if precedent_key and precedent_key in self.legal_precedents:
                precedent = self.legal_precedents[precedent_key]

                # Create evidence item from precedent
                evidence = EB1AEvidence(
                    criterion=criterion,
                    evidence_type=EvidenceType.RECOMMENDATION_LETTER,  # Closest type
                    title=f"Legal Precedent: {precedent['case']}",
                    description=precedent["summary"],
                    source="Legal Database",
                    metadata={
                        "case_citation": precedent["case"],
                        "key_points": precedent["key_points"],
                        "relevance": precedent["relevance"],
                    },
                )
                evidence_items.append(evidence)

        return evidence_items

    async def _research_benchmarks(self, request: EB1APetitionRequest) -> list[EB1AEvidence]:
        """
        Research industry benchmarks and statistics.

        Args:
            request: Petition request

        Returns:
            Benchmark evidence items
        """
        evidence_items: list[EB1AEvidence] = []

        # For high salary criterion, find salary benchmarks
        if EB1ACriterion.HIGH_SALARY in request.primary_criteria:
            salary_benchmark = await self._get_salary_benchmark(request.field_of_expertise)
            if salary_benchmark:
                evidence_items.append(salary_benchmark)

        # For scholarly articles, find citation benchmarks
        if (
            EB1ACriterion.SCHOLARLY_ARTICLES in request.primary_criteria
            and request.citations_count is not None
        ):
            citation_benchmark = self._get_citation_benchmark(
                request.field_of_expertise, request.citations_count, request.h_index
            )
            if citation_benchmark:
                evidence_items.append(citation_benchmark)

        return evidence_items

    def _build_criterion_query(self, criterion: EB1ACriterion, request: EB1APetitionRequest) -> str:
        """Build search query for criterion research."""
        criterion_name = criterion.value.split("_", 1)[1].replace("_", " ")
        return (
            f"EB-1A petition {criterion_name} criterion in {request.field_of_expertise} "
            f"evidence requirements examples"
        )

    def _record_to_evidence(self, record: Any, criterion: EB1ACriterion) -> EB1AEvidence | None:
        """Convert memory record to evidence item."""
        try:
            # Extract relevant fields from memory record
            text = getattr(record, "text", "") if hasattr(record, "text") else str(record)
            metadata = getattr(record, "metadata", {}) if hasattr(record, "metadata") else {}

            return EB1AEvidence(
                criterion=criterion,
                evidence_type=EvidenceType.RECOMMENDATION_LETTER,
                title=f"Research Finding: {criterion.value}",
                description=text[:500],  # Truncate to 500 chars
                source="RAG Research",
                metadata=metadata,
            )
        except Exception:
            return None

    def _get_relevant_precedent(self, criterion: EB1ACriterion) -> str | None:
        """Get most relevant legal precedent for criterion."""
        precedent_map = {
            EB1ACriterion.AWARDS: "buletini",
            EB1ACriterion.MEMBERSHIP: "kazarian",
            EB1ACriterion.PRESS: "visinscaia",
            EB1ACriterion.JUDGING: "kazarian",
            EB1ACriterion.ORIGINAL_CONTRIBUTION: "visinscaia",
            EB1ACriterion.SCHOLARLY_ARTICLES: "kazarian",
        }
        return precedent_map.get(criterion)

    async def _get_salary_benchmark(self, field: str) -> EB1AEvidence | None:
        """Get salary benchmark data for field."""
        # In real implementation, would query salary databases
        # For now, return placeholder benchmark

        # Common tech field benchmarks (example data)
        field_benchmarks = {
            "artificial intelligence": {"median": 150000, "top_10_percent": 250000},
            "machine learning": {"median": 145000, "top_10_percent": 240000},
            "software engineering": {"median": 130000, "top_10_percent": 200000},
        }

        field_lower = field.lower()
        benchmark = field_benchmarks.get(field_lower)

        if benchmark:
            return EB1AEvidence(
                criterion=EB1ACriterion.HIGH_SALARY,
                evidence_type=EvidenceType.SALARY_EVIDENCE,
                title=f"Salary Benchmark: {field}",
                description=(
                    f"Industry salary data for {field}:\n"
                    f"- Median salary: ${benchmark['median']:,}\n"
                    f"- Top 10% threshold: ${benchmark['top_10_percent']:,}"
                ),
                source="Bureau of Labor Statistics / Industry Surveys",
                date=datetime.utcnow(),
                metadata={
                    "field": field,
                    "median_salary": benchmark["median"],
                    "top_10_percent": benchmark["top_10_percent"],
                    "source": "BLS/Glassdoor/Levels.fyi",
                },
            )

        return None

    def _get_citation_benchmark(
        self, field: str, citations: int, h_index: int | None
    ) -> EB1AEvidence | None:
        """Get citation benchmark data for field."""
        # Calculate percentile (simplified)
        percentile = self._calculate_citation_percentile(citations, h_index)

        if percentile >= 75:  # Top quartile
            return EB1AEvidence(
                criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
                evidence_type=EvidenceType.CITATION_REPORT,
                title=f"Citation Metrics Analysis: {field}",
                description=(
                    f"Citation metrics demonstrate high impact in {field}:\n"
                    f"- Total citations: {citations:,}\n"
                    f"- H-index: {h_index}\n"
                    f"- Estimated percentile: {percentile}th (top quartile)"
                ),
                source="Google Scholar / Web of Science",
                date=datetime.utcnow(),
                metadata={
                    "field": field,
                    "total_citations": citations,
                    "h_index": h_index,
                    "percentile": percentile,
                },
            )

        return None

    def _calculate_citation_percentile(self, citations: int, h_index: int | None) -> int:
        """Calculate approximate citation percentile."""
        # Simplified calculation - in reality would use field-specific data
        if citations > 1000:
            return 95
        if citations > 500:
            return 90
        if citations > 250:
            return 85
        if citations > 100:
            return 80
        if citations > 50:
            return 75
        return 50

    # === New Web Research Methods ===

    async def research_organization(
        self, org_name: str, context: str | None = None
    ) -> OrganizationProfile:
        """
        Исследование организации через web search и извлечение данных.

        Собирает:
        - Год основания, местоположение
        - Количество членов
        - Миссию и значимость
        - Известных членов
        - Упоминания в медиа

        Args:
            org_name: Название организации
            context: Дополнительный контекст (тип org, область деятельности)

        Returns:
            OrganizationProfile: Профиль организации с собранными данными

        Example:
            >>> researcher = EvidenceResearcher(memory)
            >>> profile = await researcher.research_organization(
            ...     "IEEE Computer Society",
            ...     context="professional organization computer science"
            ... )
            >>> print(f"Founded: {profile.founded_year}")
            >>> print(f"Prestige Score: {profile.get_prestige_score():.2f}")
        """
        # Build search query
        search_query = f"{org_name} organization"
        if context:
            search_query += f" {context}"
        search_query += " founded members mission"

        # ПРИМЕЧАНИЕ: В реальной реализации здесь был бы вызов web search API
        # Для демонстрации используем симуляцию
        search_results = await self._simulate_web_search(search_query)

        # Extract structured data from search results
        profile = await self._extract_org_profile(org_name, search_results)

        return profile

    async def research_competition_stats(
        self, competition_name: str, year: int, context: str | None = None
    ) -> CompetitionStats:
        """
        Исследование статистики конкурса/награды.

        Собирает:
        - Количество заявок/участников
        - Количество победителей
        - Acceptance rate
        - Состав жюри
        - Критерии отбора

        Args:
            competition_name: Название конкурса/награды
            year: Год проведения
            context: Дополнительный контекст (область, тип конкурса)

        Returns:
            CompetitionStats: Статистика конкурса

        Example:
            >>> stats = await researcher.research_competition_stats(
            ...     "Best Paper Award",
            ...     year=2023,
            ...     context="IEEE International Conference on Computer Vision"
            ... )
            >>> print(f"Acceptance Rate: {stats.acceptance_rate:.1%}")
            >>> print(f"Competitiveness: {stats.get_competitiveness_score():.2f}")
        """
        # Build search query
        search_query = f"{competition_name} {year}"
        if context:
            search_query += f" {context}"
        search_query += " statistics entries winners acceptance rate"

        # Simulate web search
        search_results = await self._simulate_web_search(search_query)

        # Extract competition statistics
        stats = await self._extract_competition_stats(
            competition_name, year, search_results, context
        )

        return stats

    async def research_publication(
        self, publication_name: str, publication_type: str = "journal"
    ) -> PublicationProfile:
        """
        Исследование публикации/журнала/конференции.

        Собирает:
        - Impact factor / h-index
        - Acceptance rate
        - Тираж/аудитория
        - Рейтинг
        - Издатель

        Args:
            publication_name: Название публикации
            publication_type: Тип (journal/conference/magazine/newspaper)

        Returns:
            PublicationProfile: Профиль публикации

        Example:
            >>> profile = await researcher.research_publication(
            ...     "Nature",
            ...     publication_type="journal"
            ... )
            >>> print(f"Impact Factor: {profile.impact_factor}")
        """
        search_query = (
            f"{publication_name} {publication_type} impact factor acceptance rate circulation"
        )

        search_results = await self._simulate_web_search(search_query)

        profile = await self._extract_publication_profile(
            publication_name, publication_type, search_results
        )

        return profile

    async def enrich_evidence_with_research(
        self, evidence_item: EB1AEvidence, research_type: str = "auto"
    ) -> EB1AEvidence:
        """
        Обогащение существующего evidence item дополнительными исследованиями.

        Args:
            evidence_item: Существующий evidence item
            research_type: Тип исследования (auto/organization/competition/publication)

        Returns:
            EB1AEvidence: Обогащённый evidence item с дополнительными данными

        Example:
            >>> evidence = EB1AEvidence(
            ...     criterion=EB1ACriterion.AWARDS,
            ...     title="Best Paper Award",
            ...     description="Received at IEEE Conference"
            ... )
            >>> enriched = await researcher.enrich_evidence_with_research(evidence)
            >>> print(enriched.metadata.get("competition_stats"))
        """
        enriched_metadata = evidence_item.metadata.copy()

        # Determine what to research based on evidence type
        if research_type == "auto":
            research_type = self._determine_research_type(evidence_item)

        try:
            if research_type == "organization":
                # Extract organization name from evidence
                org_name = self._extract_organization_name(evidence_item)
                if org_name:
                    org_profile = await self.research_organization(org_name)
                    enriched_metadata["organization_profile"] = org_profile.model_dump()
                    enriched_metadata["prestige_score"] = org_profile.get_prestige_score()

            elif research_type == "competition":
                # Extract competition info
                comp_name = evidence_item.title
                year = evidence_item.date.year if evidence_item.date else datetime.utcnow().year
                stats = await self.research_competition_stats(comp_name, year)
                enriched_metadata["competition_stats"] = stats.model_dump()
                enriched_metadata["competitiveness_score"] = stats.get_competitiveness_score()

            elif research_type == "publication":
                # Extract publication info
                pub_name = self._extract_publication_name(evidence_item)
                if pub_name:
                    profile = await self.research_publication(pub_name)
                    enriched_metadata["publication_profile"] = profile.model_dump()

        except Exception as e:
            # Log error but don't fail
            enriched_metadata["research_error"] = str(e)

        # Create new evidence item with enriched metadata
        enriched_evidence = EB1AEvidence(
            criterion=evidence_item.criterion,
            evidence_type=evidence_item.evidence_type,
            title=evidence_item.title,
            description=evidence_item.description,
            source=evidence_item.source,
            date=evidence_item.date,
            exhibit_number=evidence_item.exhibit_number,
            file_path=evidence_item.file_path,
            metadata=enriched_metadata,
        )

        return enriched_evidence

    # === Helper Methods for Web Research ===

    async def _simulate_web_search(self, query: str) -> dict[str, Any]:
        """
        Симуляция web search (заглушка).

        В реальной реализации здесь был бы вызов:
        - Google Custom Search API
        - Bing Search API
        - DuckDuckGo API
        - Или scraping через Beautiful Soup

        Args:
            query: Поисковый запрос

        Returns:
            dict: Симулированные результаты поиска
        """
        # В продакшене заменить на реальный API:
        # response = await search_api.search(query)
        # return response

        # Для демонстрации возвращаем структурированные данные
        simulated_results = {
            "query": query,
            "results": [
                {
                    "title": f"About {query}",
                    "snippet": f"Information about {query}...",
                    "url": f"https://example.com/{query.replace(' ', '-')}",
                }
            ],
            "metadata": {"total_results": 100, "search_time": 0.5},
        }

        return simulated_results

    async def _extract_org_profile(
        self, org_name: str, search_results: dict[str, Any]
    ) -> OrganizationProfile:
        """
        Извлечение данных организации из результатов поиска.

        В реальной реализации использовал бы:
        - LLM для extraction (GPT-5, Claude)
        - Named Entity Recognition
        - Structured data extraction

        Args:
            org_name: Название организации
            search_results: Результаты web search

        Returns:
            OrganizationProfile: Извлечённый профиль
        """
        # В продакшене использовать LLM для extraction:
        # profile_data = await llm.extract_structured_data(
        #     text=search_results,
        #     schema=OrganizationProfile
        # )

        # Для демонстрации используем heuristics и примерные данные
        profile = OrganizationProfile(
            name=org_name,
            founded_year=self._extract_year(search_results),
            location=self._extract_location(search_results),
            member_count=self._extract_number(search_results, pattern=r"(\d+[,\d]*)\s*members?"),
            mission_statement=f"Professional organization dedicated to advancing {org_name}",
            website=f"https://{org_name.lower().replace(' ', '')}.org",
            selectivity_indicators=[
                "Peer nomination required",
                "Demonstrated excellence in field",
                "Rigorous review process",
            ],
            metadata={
                "research_date": datetime.utcnow().isoformat(),
                "search_query": search_results.get("query"),
            },
        )

        # Calculate acceptance rate if member count available
        if profile.member_count:
            # Heuristic: assume 10x applications for selective orgs
            profile.total_applications = profile.member_count * 10
            profile.acceptance_rate = 0.1  # 10%

        return profile

    async def _extract_competition_stats(
        self, competition_name: str, year: int, search_results: dict[str, Any], context: str | None
    ) -> CompetitionStats:
        """
        Извлечение статистики конкурса из результатов поиска.

        Args:
            competition_name: Название конкурса
            year: Год
            search_results: Результаты поиска
            context: Контекст

        Returns:
            CompetitionStats: Статистика конкурса
        """
        # Extract numbers from search results
        total_entries = self._extract_number(
            search_results, pattern=r"(\d+[,\d]*)\s*(?:submissions?|entries|participants?)"
        )

        total_winners = self._extract_number(
            search_results, pattern=r"(\d+[,\d]*)\s*(?:winners?|awards?|selected)"
        )

        # Calculate acceptance rate
        acceptance_rate = None
        if total_entries and total_winners:
            acceptance_rate = total_winners / total_entries

        stats = CompetitionStats(
            competition_name=competition_name,
            year=year,
            total_entries=total_entries,
            total_winners=total_winners,
            acceptance_rate=acceptance_rate,
            geographic_scope=self._determine_scope(competition_name, context),
            selection_criteria=["Peer review", "Technical merit", "Innovation and impact"],
            organizing_body=context if context else "Professional Organization",
            metadata={
                "research_date": datetime.utcnow().isoformat(),
                "search_query": search_results.get("query"),
            },
        )

        return stats

    async def _extract_publication_profile(
        self, publication_name: str, publication_type: str, search_results: dict[str, Any]
    ) -> PublicationProfile:
        """
        Извлечение профиля публикации из результатов поиска.

        Args:
            publication_name: Название публикации
            publication_type: Тип публикации
            search_results: Результаты поиска

        Returns:
            PublicationProfile: Профиль публикации
        """
        # Extract impact metrics
        impact_factor = self._extract_float(
            search_results, pattern=r"impact\s*factor[:\s]+(\d+\.?\d*)"
        )

        h5_index = self._extract_number(search_results, pattern=r"h5[-\s]index[:\s]+(\d+)")

        circulation = self._extract_number(search_results, pattern=r"circulation[:\s]+(\d+[,\d]*)")

        profile = PublicationProfile(
            name=publication_name,
            publication_type=publication_type,
            impact_factor=impact_factor,
            h5_index=h5_index,
            circulation=circulation,
            geographic_reach="International",
            metadata={
                "research_date": datetime.utcnow().isoformat(),
                "search_query": search_results.get("query"),
            },
        )

        return profile

    def _determine_research_type(self, evidence_item: EB1AEvidence) -> str:
        """Определить тип исследования для evidence item."""
        criterion = evidence_item.criterion

        if criterion in [EB1ACriterion.AWARDS]:
            return "competition"
        if criterion in [EB1ACriterion.MEMBERSHIP]:
            return "organization"
        if criterion in [EB1ACriterion.PRESS, EB1ACriterion.SCHOLARLY_ARTICLES]:
            return "publication"
        return "organization"

    def _extract_organization_name(self, evidence_item: EB1AEvidence) -> str | None:
        """Извлечь название организации из evidence."""
        # Simple heuristic: look in metadata or description
        if "organization" in evidence_item.metadata:
            return evidence_item.metadata["organization"]

        # Try to extract from description
        desc = evidence_item.description.lower()
        if "member of" in desc:
            # Extract text after "member of"
            match = re.search(r"member of\s+([A-Z][A-Za-z\s&]+)", evidence_item.description)
            if match:
                return match.group(1).strip()

        return None

    def _extract_publication_name(self, evidence_item: EB1AEvidence) -> str | None:
        """Извлечь название публикации из evidence."""
        if "publication" in evidence_item.metadata:
            return evidence_item.metadata["publication"]

        # Try to extract from title or description
        # Look for patterns like "in X" or "published in X"
        match = re.search(r"(?:in|published in)\s+([A-Z][A-Za-z\s&]+)", evidence_item.description)
        if match:
            return match.group(1).strip()

        return None

    def _extract_year(self, search_results: dict[str, Any]) -> int | None:
        """Извлечь год из результатов поиска."""
        # Look for 4-digit years
        results_text = str(search_results)
        match = re.search(r"(19\d{2}|20\d{2})", results_text)
        if match:
            return int(match.group(1))
        return None

    def _extract_location(self, search_results: dict[str, Any]) -> str | None:
        """Извлечь местоположение из результатов поиска."""
        # Simple heuristic
        results_text = str(search_results)
        countries = ["USA", "United States", "UK", "United Kingdom", "Canada", "Germany", "France"]
        for country in countries:
            if country in results_text:
                return country
        return None

    def _extract_number(self, search_results: dict[str, Any], pattern: str) -> int | None:
        """Извлечь число по регулярному выражению."""
        results_text = str(search_results)
        match = re.search(pattern, results_text, re.IGNORECASE)
        if match:
            number_str = match.group(1).replace(",", "")
            try:
                return int(number_str)
            except ValueError:
                return None
        return None

    def _extract_float(self, search_results: dict[str, Any], pattern: str) -> float | None:
        """Извлечь дробное число по регулярному выражению."""
        results_text = str(search_results)
        match = re.search(pattern, results_text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _determine_scope(self, name: str, context: str | None) -> str:
        """Определить географический охват."""
        text = f"{name} {context or ''}".lower()

        if any(word in text for word in ["international", "world", "global", "ieee", "acm"]):
            return "international"
        if any(word in text for word in ["national", "american", "european"]):
            return "national"
        return "regional"
