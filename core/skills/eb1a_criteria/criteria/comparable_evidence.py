"""
Comparable Evidence Criterion - 8 CFR 204.5(h)(4)

If the above standards do not readily apply to the beneficiary's occupation,
the petitioner may submit comparable evidence to establish the beneficiary's
eligibility.
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


class ComparableEvidenceCriterion(CriterionBase):
    """
    Comparable Evidence - 8 CFR 204.5(h)(4).

    If the above standards do not readily apply to the beneficiary's occupation,
    the petitioner may submit comparable evidence to establish the beneficiary's
    eligibility.
    """

    CRITERION_TYPE = CriterionType.COMPARABLE_EVIDENCE
    CFR_REFERENCE = "8 CFR 204.5(h)(4)"
    TITLE_EN = "Comparable Evidence"
    TITLE_RU = "Сравнимые доказательства"

    PROMPT = """
# COMPARABLE EVIDENCE
## Regulatory Reference: 8 CFR 204.5(h)(4)

If the above standards do not readily apply to the beneficiary's occupation,
the petitioner may submit comparable evidence to establish the beneficiary's
eligibility.

---

## PURPOSE:

Здесь включаем доказательства и достижения клиента, которые **не вошли в 10 критериев**,
вплоть до назначения на должность. Все достижения расписываются в деталях.

---

## EXAMPLES OF COMPARABLE EVIDENCE:

- **Гранты** (например, грант «Болашак» и другие государственные гранты)
- **Патенты** (если не использованы в критерии оригинальных вкладов)
- **Стипендии** и другие академические награды
- **Государственные назначения** и должности
- **Лицензии** специального значения
- **Профессиональные сертификации** высокого уровня
- **Другие достижения**, демонстрирующие экстраординарные способности

---

## WHEN TO USE:

Comparable evidence используется когда:

1. Стандартные 10 критериев не применимы непосредственно к профессии бенефициара
2. У клиента есть значительные достижения, которые не укладываются точно
   ни в один из 10 критериев
3. Область деятельности имеет уникальные показатели успеха, не отраженные
   в стандартных критериях

---

## USCIS GUIDANCE:

### When Comparable Evidence Applies:

USCIS рассматривает comparable evidence когда заявитель демонстрирует, что
стандартные критерии **не применимы** или **не легко применимы** к профессии
бенефициара.

### Burden of Proof:

Заявитель должен:
1. Объяснить, почему стандартные критерии не применимы
2. Показать, как представленные доказательства **сопоставимы** по значимости
   со стандартными критериями
3. Доказать, что достижения демонстрируют экстраординарные способности

---

## DOCUMENTATION REQUIREMENTS:

Для каждого comparable evidence необходимо:

- **Описание достижения** - что именно было достигнуто
- **Объяснение значимости** - почему это важно в данной области
- **Сравнение со стандартными критериями** - как это соотносится с 10 критериями
- **Документальные доказательства** - сертификаты, письма, публикации

---

## SPECIFIC EXAMPLES:

### Government Grants (Государственные гранты):

**Грант «Болашак»** - это государственная международная стипендия Республики Казахстан.
Программа была создана в 1993 году по указу Президента Республики Казахстан для
подготовки высококвалифицированных кадров для приоритетных секторов экономики.

Получение такого гранта может свидетельствовать о признании экстраординарных
способностей на государственном уровне.

### Patents (Патенты):

Если патенты не были использованы в критерии оригинальных вкладов (Criterion 5),
они могут быть представлены как comparable evidence, особенно если:
- Патенты имеют коммерческое применение
- Патенты получили признание в отрасли
- Патенты были лицензированы другими

### Professional Certifications (Профессиональные сертификации):

Сертификации, которые:
- Требуют исключительной квалификации
- Имеют ограниченное число держателей
- Признаны на национальном или международном уровне

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Identify all evidence not fitting standard 10 criteria
2. Explain why standard criteria don't apply to this occupation
3. Draw comparisons to similar achievements under standard criteria
4. Document the significance of each achievement
5. Verify third-party recognition or validation
6. Assess national/international scope of achievement
7. Gather supporting documentation for each item
8. Determine comparability to standard criteria
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For each comparable evidence item provide:
- Achievement/Evidence Name (Название достижения)
- Type: Grant/Patent/Certification/Other (Тип)
- Date Achieved (Дата достижения)
- Why Standard Criteria Don't Apply (Почему стандартные критерии не применимы)
- Comparable Standard Criterion (Сопоставимый стандартный критерий)
- Significance to Field (Значимость для области)
- Recognition Level: Local/National/International (Уровень признания)
- Selection/Acceptance Rate (if applicable) (Уровень отбора/принятия)
- Third-Party Validation (Верификация третьими лицами)
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
        """Evaluate comparable evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No comparable evidence provided.",
                part2_analysis="Cannot assess comparability without evidence.",
                evidence_summary=[],
                missing_documents=[
                    "Documentation of achievements",
                    "Explanation of why standard criteria don't apply",
                    "Comparison to standard criteria",
                    "Third-party validation",
                ],
                recommendations=[
                    "Document each achievement in detail",
                    "Explain how it compares to standard criteria",
                    "Provide third-party recognition evidence",
                    "Include significance to the field",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.2, 0.7)  # Slightly lower max for comparable

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} comparable evidence item(s). Manual review needed.",
            part2_analysis="Comparability to standard criteria requires verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify explanation of why standard criteria don't apply",
                "Comparison documentation",
                "Third-party validation",
            ],
            recommendations=[
                "Strengthen explanation of why standard criteria don't apply",
                "Draw explicit parallels to standard criteria",
                "Add more third-party recognition evidence",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for comparable evidence."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No comparable evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner submits the following comparable evidence to establish "
            "eligibility, as the standard criteria do not readily apply to the "
            "beneficiary's occupation:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Evidence {i}: {ev.title}**")
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
        """Validate petition text for comparable evidence."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "comparable" not in petition_text.lower():
            issues.append("Missing reference to comparable evidence")

        if "standard" not in petition_text.lower() and "criteria" not in petition_text.lower():
            suggestions.append("Consider explaining why standard criteria don't apply")

        if "occupation" not in petition_text.lower() and "field" not in petition_text.lower():
            suggestions.append("Consider explaining the occupation/field context")

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
