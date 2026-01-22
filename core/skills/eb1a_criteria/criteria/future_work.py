"""
Future Work Documentation - Area of Expertise

Documentation to establish that the beneficiary will continue to work
in their claimed area of expertise in the United States.
"""

from __future__ import annotations

from typing import Any

from ..base import (CriterionBase, CriterionType, EvaluationResult, Evidence,
                    EvidenceStrength, PetitionSection, ValidationResult)


class FutureWorkDocumentation(CriterionBase):
    """
    Documentation to Establish Future Work in Area of Expertise.

    This is a required supporting documentation section for EB-1A petitions,
    demonstrating that the beneficiary will continue to work in their
    claimed area of expertise upon entry to the United States.
    """

    CRITERION_TYPE = CriterionType.COMPARABLE_EVIDENCE  # Using as placeholder
    CFR_REFERENCE = "8 CFR 204.5(h)(5)"
    TITLE_EN = "Documentation of Future Work in Area of Expertise"
    TITLE_RU = "Документация о продолжении работы в области экспертизы"

    PROMPT = """
# DOCUMENTATION TO ESTABLISH THAT I WILL CONTINUE TO WORK IN THEIR CLAIMED AREA OF EXPERTISE

---

## PURPOSE:

Необходимо показать, как бенефициар будет продолжать работать в США в заявленной
области знаний.

В петиции не указано, что у бенефициара есть заранее оговоренные обязательства
по работе в данной области. Пожалуйста, предоставьте доказательства того, что
бенефициар приезжает в США для продолжения работы в данной области.

**Работа должна быть в области**, в которой бенефициар получил устойчивое
национальное или международное признание, и его достижения были признаны,
что указывает на то, что он является одним из того небольшого процента,
который поднялся на самый верх в этой области.

---

## REQUIRED DOCUMENTATION:

Доказательства, которые могут быть представлены для выполнения этого требования,
включают, но не ограничиваются:

### For Employment (Для работы по найму):
- **Job Offers** - если клиент планирует работать по найму
- **Трудовые договоры** - employment contracts

### For Entrepreneurs (Для предпринимателей):
- **Business Plan** - если клиент планирует открывать компанию
- Регистрационные документы компании
- Лицензии и разрешения

### Letters of Interest (Письма о заинтересованности):
- Письма от потенциальных работодателей
- Письма от партнеров
- Письма от клиентов

### Personal Statement (Заявление бенефициара):
- Заявление бенефициара с подробным описанием планов по продолжению работы в США

---

## IMPORTANT NOTES (ВАЖНО):

### Consistency with EB2 NIW:
Если у клиента есть кейс EB2 NIW, то часть Area of expertise в части Business Plan
или планов на будущее нужно перенести и сюда.

**То есть планы на будущее в двух кейсах должны быть идентичными в EB1 и в EB2 NIW.**

### RFE Prevention:
Поскольку практически во всех RFE офицеры запрашивают доказательства того, что клиент
продолжит свою деятельность на территории США, в этой части EB1 прикладываем:
- Job Offers, либо
- Business Plan

---

## TYPES OF EVIDENCE BY PROFESSION:

### For Employees:
- Offer letters from US employers
- Employment contracts
- Letters of intent from companies
- Professional correspondence showing job discussions

### For Entrepreneurs:
- Business registration documents (LLC, Corp)
- Business Plan with market analysis
- Lease agreements for business premises
- Partnership letters
- Letters of interest from potential clients/partners
- Franchise agreements (if applicable)

### For Freelancers/Consultants:
- Contracts with US clients
- Letters of intent from potential clients
- Portfolio of ongoing projects
- Platform profiles (if applicable)

### For Artists/Performers:
- Performance contracts
- Gallery representation agreements
- Commission agreements
- Tour schedules

### For Academics/Researchers:
- Research proposals
- Grant applications
- University appointment letters
- Collaboration agreements with US institutions

---

## BUSINESS PLAN REQUIREMENTS:

Если клиент представляет Business Plan, он должен включать:

1. **Executive Summary** - краткое описание бизнеса
2. **Company Description** - описание компании и её миссии
3. **Market Analysis** - анализ рынка и конкурентов
4. **Services/Products** - описание услуг или продуктов
5. **Marketing Strategy** - маркетинговая стратегия
6. **Operations Plan** - операционный план
7. **Financial Projections** - финансовые прогнозы
8. **Growth Strategy** - стратегия роста и расширения

---

## EXAMPLE ELEMENTS:

### Company Registration:
- Certificate of Authority
- Online Filing Receipt
- Employer Identification Number (EIN)
- State registration documents

### Lease Agreements:
- Commercial lease for business premises
- Equipment lease agreements

### Partnership Documentation:
- Letters of cooperation
- Partnership agreements
- Memorandums of Understanding (MOU)

### Client/Customer Evidence:
- Letters of recommendation from clients
- Testimonials
- Contracts for services

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Identify the beneficiary's claimed area of expertise
2. Review all future work documentation
3. Verify consistency with area of extraordinary ability
4. Check for Job Offers or Business Plan
5. Evaluate letters of interest and partnership documents
6. Assess credibility of business plans
7. Verify company registration if applicable
8. Check consistency with EB2 NIW case (if exists)
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For future work documentation provide:
- Area of Expertise (Область экспертизы)
- Employment Type: Employee/Entrepreneur/Freelancer (Тип занятости)
- Job Offer/Business Plan Status (Статус Job Offer/Business Plan)
- Company Name (if applicable) (Название компании)
- Company Registration Status (Статус регистрации)
- Business Plan Completeness (Полнота бизнес-плана)
- Letters of Interest Count (Количество писем о заинтересованности)
- Partnership Agreements (Партнерские соглашения)
- Consistency with Claimed Expertise (Соответствие заявленной экспертизе)
- Consistency with EB2 NIW (if applicable) (Соответствие с EB2 NIW)
- Documentation Status: Complete/Partial/Missing (Статус документации)
- Strengths and Weaknesses (Сильные и слабые стороны)
- Recommendations for Strengthening (Рекомендации по усилению)
- Draft Petition Language (Черновик текста петиции)
"""

    async def evaluate(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate future work documentation."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No future work documentation provided.",
                part2_analysis="Cannot assess future work plans without evidence.",
                evidence_summary=[],
                missing_documents=[
                    "Job Offer or Business Plan",
                    "Company registration (if entrepreneur)",
                    "Letters of interest",
                    "Personal statement of plans",
                ],
                recommendations=[
                    "Submit Job Offer from US employer OR detailed Business Plan",
                    "Include letters of interest from potential partners/clients",
                    "Provide company registration documents if applicable",
                    "Add personal statement describing future work plans",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.25, 0.85)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} future work document(s). Manual review needed.",
            part2_analysis="Consistency with area of expertise requires verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify Job Offer or Business Plan completeness",
                "Check consistency with claimed expertise",
                "Verify EB2 NIW consistency if applicable",
            ],
            recommendations=[
                "Ensure plans align with area of extraordinary ability",
                "Add more letters of interest if possible",
                "Include financial projections in Business Plan",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for future work documentation."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No future work documentation provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            "",
            "The Petitioner will continue to work in their claimed area of expertise "
            "upon entry to the United States, as evidenced by the following documentation:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Document {i}: {ev.title}**")
            content_parts.append(f"{ev.description}")
            content_parts.append("")
            if ev.file_path:
                attachment_ref = f"Attachment {i}: {ev.title}"
                attachments.append(attachment_ref)
                content_parts.append(f"(See {attachment_ref})")
                content_parts.append("")

        content = "\n".join(content_parts)

        return PetitionSection(
            criterion_type=self.CRITERION_TYPE,
            title=self.TITLE_EN,
            content=content,
            attachments=attachments,
            word_count=len(content.split()),
        )

    async def validate(
        self,
        petition_text: str,
        evidence: list[Evidence] | None = None,
    ) -> ValidationResult:
        """Validate petition text for future work documentation."""
        issues = []
        suggestions = []
        missing_elements = []

        if "continue" not in petition_text.lower() and "work" not in petition_text.lower():
            issues.append("Missing reference to continuation of work")

        if (
            "area of expertise" not in petition_text.lower()
            and "field" not in petition_text.lower()
        ):
            issues.append("Missing reference to area of expertise")

        if (
            "business plan" not in petition_text.lower()
            and "job offer" not in petition_text.lower()
        ):
            suggestions.append("Consider mentioning Job Offer or Business Plan")

        if "united states" not in petition_text.lower() and "u.s." not in petition_text.lower():
            suggestions.append("Consider explicitly mentioning United States")

        total_checks = 4
        passed_checks = total_checks - len(issues) - len(missing_elements)
        score = passed_checks / total_checks

        return ValidationResult(
            is_valid=len(issues) == 0 and len(missing_elements) == 0,
            issues=issues,
            suggestions=suggestions,
            missing_elements=missing_elements,
            score=score,
        )
