"""
Commercial Success Criterion - 8 CFR 204.5(h)(3)(x)

Evidence of commercial successes in the performing arts, as shown by
box office receipts or record, cassette, compact disk, or video sales.
"""

from __future__ import annotations

from typing import Any

from ..base import (
    CriterionBase,
    CriterionType,
    Evidence,
    EvaluationResult,
    EvidenceStrength,
    PetitionSection,
    ValidationResult,
)


class CommercialSuccessCriterion(CriterionBase):
    """
    Criterion 10: Commercial Successes in the Performing Arts.

    8 CFR 204.5(h)(3)(x): Evidence of commercial successes in the performing arts,
    as shown by box office receipts or record, cassette, compact disk, or video sales.
    """

    CRITERION_TYPE = CriterionType.COMMERCIAL_SUCCESS
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(x)"
    TITLE_EN = "Commercial Successes in the Performing Arts"
    TITLE_RU = "Коммерческий успех в исполнительском искусстве"

    PROMPT = """
# CRITERION 10: COMMERCIAL SUCCESSES IN THE PERFORMING ARTS
## Regulatory Reference: 8 CFR 204.5(h)(3)(x)

Evidence of commercial successes in the performing arts, as shown by box office
receipts or record, cassette, compact disk, or video sales.

---

## CRITERION FOCUS:

В данном критерии основное внимание уделяется **объему продаж и кассовым сборам**
как показателю коммерческого успеха бенефициара в исполнительском искусстве.

---

## WHAT IS NOT SUFFICIENT:

Одного факта записи и выпуска музыкальных сборников или участия в театральных,
кино- или телевизионных постановках **будет недостаточно**.

---

## REQUIRED DOCUMENTATION:

Чтобы помочь определить, что бенефициар добился коммерческого успеха в
исполнительском искусстве, заявитель может представить:

- **Кассовые чеки** (box office receipts)
- **Квитанции о продаже** аудио- или видеозаписей, подтверждающие успех
  в исполнительском искусстве

---

## KEY REQUIREMENT:

Доказательства должны свидетельствовать о том, что объем продаж и кассовые сборы
отражают **коммерческий успех бенефициара по сравнению с другими лицами**,
занимающимися аналогичной деятельностью в сфере исполнительского искусства.

---

## USCIS DETERMINATION:

USCIS определяет, добился ли человек коммерческого успеха в исполнительском искусстве.

Этот критерий ориентирован на **объем продаж и кассовые сборы** как меру
коммерческого успеха человека в исполнительском искусстве.

### What Is Insufficient:

Одного лишь факта, что человек записал и выпустил музыкальные сборники или принял
участие в театральных, кино- или телевизионных постановках, **само по себе недостаточно**
для соответствия этому критерию.

### What Is Required:

Доказательства должны показывать, что объем продаж и кассовые сборы отражают
коммерческий успех данного лица **по сравнению с другими лицами**, занимающимися
аналогичной деятельностью в сфере исполнительских искусств.

---

## TYPES OF EVIDENCE:

### Box Office Receipts (Кассовые сборы):
- Документация о кассовых сборах фильмов, спектаклей, концертов
- Сравнение с кассовыми сборами аналогичных произведений

### Record/Album Sales (Продажи альбомов):
- Сертификаты Gold, Platinum, Diamond за продажи
- Статистика продаж по данным рекорд-лейблов
- Данные о стриминговых прослушиваниях

### Video Sales (Продажи видео):
- Продажи DVD, Blu-ray
- Статистика просмотров на видеоплатформах

### Digital Sales (Цифровые продажи):
- Продажи на iTunes, Amazon Music, и др.
- Статистика стриминговых платформ (Spotify, Apple Music)

---

## COMPARISON REQUIREMENT:

Важно показать **сравнение** с другими исполнителями в этой области:

- Средние показатели продаж в индустрии
- Рейтинги и чарты (Billboard, national charts)
- Сертификации продаж (RIAA, IFPI)
- Награды за продажи

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Identify all commercial success evidence
2. Document sales figures with official sources
3. Verify box office receipts or sales certifications
4. Compare to industry averages and peers
5. Check for chart positions and certifications
6. Gather third-party verification of sales data
7. Document streaming statistics if applicable
8. Calculate percentage above industry average
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For each commercial success provide:
- Production/Work Name (Название работы/продукции)
- Type: Film/Music/Video/Other (Тип)
- Release Date (Дата выпуска)
- Beneficiary's Role (Роль бенефициара)
- Sales/Revenue Figures (Показатели продаж/выручки)
- Certifications (Gold/Platinum/etc.) (Сертификации)
- Chart Positions (Позиции в чартах)
- Comparison to Industry Average (Сравнение со средним по индустрии)
- Third-Party Verification Source (Источник верификации)
- Awards for Sales (Награды за продажи)
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
        """Evaluate commercial success evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for commercial success criterion.",
                part2_analysis="Cannot assess commercial success without sales/receipts data.",
                evidence_summary=[],
                missing_documents=[
                    "Box office receipts or sales figures",
                    "Sales certifications",
                    "Industry comparison statistics",
                    "Chart positions or rankings",
                ],
                recommendations=[
                    "Submit documented sales figures",
                    "Provide certifications (Gold, Platinum)",
                    "Include industry comparison data",
                    "Add chart positions if applicable",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.25, 0.8)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} commercial success item(s). Manual review needed.",
            part2_analysis="Sales comparison to peers requires verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify sales figures are documented",
                "Industry comparison data",
                "Third-party verification",
            ],
            recommendations=[
                "Add third-party sales verification",
                "Include industry average comparisons",
                "Document chart positions or certifications",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for commercial success criterion."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No commercial success evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner has achieved commercial success in the performing arts, "
            "as evidenced by the following sales and receipts documentation:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Commercial Success {i}: {ev.title}**")
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
        """Validate petition text for commercial success criterion."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "commercial" not in petition_text.lower():
            issues.append("Missing reference to commercial success")

        if "sales" not in petition_text.lower() and "receipts" not in petition_text.lower():
            issues.append("Missing reference to sales figures or receipts")

        if "comparison" not in petition_text.lower() and "average" not in petition_text.lower():
            suggestions.append("Consider adding comparison to industry peers")

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
