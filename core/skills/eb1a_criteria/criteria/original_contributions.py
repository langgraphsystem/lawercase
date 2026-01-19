"""
Original Contributions Criterion - 8 CFR 204.5(h)(3)(v)

Evidence of the beneficiary's original scientific, scholarly, artistic,
athletic, or business-related contributions of major significance to the field.
"""

from __future__ import annotations

from typing import Any

from ..base import (CriterionBase, CriterionType, EvaluationResult, Evidence,
                    EvidenceStrength, PetitionSection, ValidationResult)


class OriginalContributionsCriterion(CriterionBase):
    """
    Criterion 5: Original Contributions of Major Significance.

    8 CFR 204.5(h)(3)(v): Evidence of the beneficiary's original scientific,
    scholarly, artistic, athletic, or business-related contributions of major
    significance to the field.
    """

    CRITERION_TYPE = CriterionType.ORIGINAL_CONTRIBUTIONS
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(v)"
    TITLE_EN = "Original Contributions of Major Significance"
    TITLE_RU = "Оригинальный вклад большого значения в данную область"

    PROMPT = """
# CRITERION 5: ORIGINAL CONTRIBUTIONS OF MAJOR SIGNIFICANCE
## Regulatory Reference: 8 CFR 204.5(h)(3)(v)

Evidence of the beneficiary's original scientific, scholarly, artistic,
athletic, or business-related contributions of major significance to the field.

---

## PART 1: PROVE THE CONTRIBUTION IS ORIGINAL (Раздел 1)

В первом разделе доказываем, внес ли человек оригинальный вклад в данную область.

### What Qualifies as Original Contribution:

- Вклад в развитие спорта, нации, экономики, предприятия
- Подтверждение патентами, разработками, мнением других экспертов
- Научные труды о чем-то новом, что дает развитие в определенной сфере
- **Идеальный вариант**: когда научный труд используется на практике и дает результаты

### Example:
Хореограф по чукотским танцам. Хореограф занимался с детьми, участвовал в различных
конкурсах и привозил в страну грамоты и призы. Такой хореограф получил грамоту от
правительства (от областного комитета) за вклад в культуру области.

---

## PART 2: PROVE THE CONTRIBUTION HAS MAJOR SIGNIFICANCE (Раздел 2)

Во втором разделе доказываем, имеет ли оригинальный вклад большое значение для данной области.

---

## REQUIRED DOCUMENTATION:

Чтобы помочь определить, является ли вклад бенефициара оригинальным и значимым,
заявитель может представить:

- Объективные документальные доказательства значимости вклада бенефициара в данную область
- Документальное подтверждение того, что люди в данной области в настоящее время считают
  работу бенефициара важной
- Свидетельства и/или письма поддержки от экспертов, в которых обсуждается значительный
  вклад бенефициара
- Доказательства того, что значительный вклад вызвал широкие общественные комментарии
  в данной области или был широко процитирован
- Доказательства того, что работа бенефициара была реализована другими:
  - Контракты с компаниями, использующими продукцию бенефициара
  - Лицензионные технологии, используемые другими
  - О патентах, используемых в настоящее время и доказавших свою значимость для данной области

---

## QUALIFYING EXAMPLES (Примеры соответствующих доказательств):

- Публикуемые материалы о значении оригинального творчества человека
- Отзывы, письма и письменные показания об оригинальной работе человека
- Документация о том, что оригинальная работа человека цитировалась на уровне,
  указывающем на большую значимость в данной области
- Патенты или лицензии, полученные на основе работы человека, или свидетельства
  коммерческого использования работы человека

---

## USCIS GUIDANCE (Пояснения):

### Focus of Analysis:
Анализ по этому критерию фокусируется на том, представляет ли оригинальная работа
человека **значительный** и **значительный вклад** в эту область.

### On Funding, Patents, Publications:
Доказательства того, что работа человека была профинансирована, запатентована или
опубликована, хотя и потенциально демонстрируют оригинальность работы, **сами по себе
не обязательно доказывают**, что работа имеет важное значение для данной области.

### On Citations and Recognition:
Опубликованное исследование, вызвавшее широкое обсуждение его важности со стороны
других специалистов в этой области, а также документация, которая получила высокую
оценку по сравнению с работами других специалистов в этой области, могут служить
доказательством значимости вклада человека в эту область.

### On Patents:
Доказательства того, что лицо разработало запатентованную технологию, которая
привлекла значительное внимание или коммерциализацию, могут установить значимость
первоначального вклада человека в эту область.

**Если патент остается на рассмотрении**, USCIS обычно требует дополнительных
подтверждающих доказательств, подтверждающих оригинальность вклада человека,
таких как подробные рекомендательные письма.

### On Expert Letters:
Подробные письма экспертов в этой области, объясняющие характер и значимость вклада
человека, также могут обеспечить ценный контекст для оценки заявленного первоначального
вклада, имеющего большое значение, особенно когда запись включает документацию,
подтверждающую заявленную значимость.

Представленные письма должны:
- Конкретно описывать вклад человека и его значение в данной области
- Излагать основу знаний и опыта автора

---

## IMPORTANT NOTE ON LETTERS (ВАЖНО о письмах):

Письма и свидетельства, если они подаются, должны содержать как можно больше подробностей
о вкладе бенефициара и подробно объяснять:
- Каким образом вклад был "оригинальным" (не просто повторение работы других)
- Какое значение он имел

**Общие заявления о важности начинаний, не подкрепленные документальными доказательствами,
недостаточны.**

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Identify each claimed original contribution
2. Verify originality (not repeating others' work)
3. Assess significance to the field
4. Document citations, usage, or implementation by others
5. Review expert letters for specificity and credibility
6. Check for patents and their commercial use
7. Evaluate recognition from professional community
8. Identify gaps in documentation
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For each original contribution provide:
- Contribution Description (Описание вклада)
- Field/Industry Impact Area (Область влияния)
- Part 1 Analysis: Originality Evidence (Анализ Раздела 1: Оригинальность)
- Part 2 Analysis: Major Significance Evidence (Анализ Раздела 2: Значимость)
- Citations/References by Others (Цитирования другими)
- Implementation/Usage by Others (Использование другими)
- Patents/Licenses (Патенты/Лицензии)
- Expert Letters Supporting (Письма экспертов в поддержку)
- Media Coverage/Publications (Освещение в СМИ/Публикации)
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
        """Evaluate original contributions evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for original contributions criterion.",
                part2_analysis="Cannot assess significance without contribution evidence.",
                evidence_summary=[],
                missing_documents=[
                    "Documentation of original contributions",
                    "Expert letters describing significance",
                    "Evidence of citations or implementation",
                    "Patents or licenses if applicable",
                ],
                recommendations=[
                    "Document each original contribution in detail",
                    "Obtain expert letters explaining significance",
                    "Gather citation or usage evidence",
                    "Include any patents or commercial use proof",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.2, 0.8)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} potential contribution(s). Manual review needed.",
            part2_analysis="Significance and originality require expert verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify expert letters are specific about contributions",
                "Citation evidence",
                "Implementation documentation",
            ],
            recommendations=[
                "Ensure expert letters describe HOW contribution is original",
                "Add evidence of citations or usage by others",
                "Include proof of impact on the field",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for original contributions criterion."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No original contributions evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner has made the following original contributions of major "
            "significance to the field:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Contribution {i}: {ev.title}**")
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
        """Validate petition text for original contributions criterion."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "original" not in petition_text.lower():
            issues.append("Missing reference to 'original' nature of contribution")

        if (
            "significance" not in petition_text.lower()
            and "significant" not in petition_text.lower()
        ):
            issues.append("Missing reference to 'significance' to the field")

        if "implemented" not in petition_text.lower() and "cited" not in petition_text.lower():
            suggestions.append("Consider adding evidence of implementation or citation by others")

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
