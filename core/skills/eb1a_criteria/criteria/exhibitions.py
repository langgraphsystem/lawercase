"""
Exhibitions Criterion - 8 CFR 204.5(h)(3)(vii)

Evidence of the display of the beneficiary's work in the field at artistic
exhibitions or showcases.
"""

from __future__ import annotations

from typing import Any

from ..base import (CriterionBase, CriterionType, EvaluationResult, Evidence,
                    EvidenceStrength, PetitionSection, ValidationResult)


class ExhibitionsCriterion(CriterionBase):
    """
    Criterion 7: Display of Work at Artistic Exhibitions or Showcases.

    8 CFR 204.5(h)(3)(vii): Evidence of the display of the beneficiary's work
    in the field at artistic exhibitions or showcases.
    """

    CRITERION_TYPE = CriterionType.EXHIBITIONS
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(vii)"
    TITLE_EN = "Display of Work at Artistic Exhibitions or Showcases"
    TITLE_RU = "Демонстрация работ на художественных выставках или витринах"

    PROMPT = """
# CRITERION 7: DISPLAY OF WORK AT ARTISTIC EXHIBITIONS OR SHOWCASES
## Regulatory Reference: 8 CFR 204.5(h)(3)(vii)

Evidence of the display of the beneficiary's work in the field at artistic
exhibitions or showcases.

---

## PART 1: PROVE THE WORK IS THE BENEFICIARY'S (Раздел 1)

В первом разделе доказываем, является ли представленная работа результатом труда
данного лица.

### Required Documentation for Part 1:

Чтобы помочь определить, что выставленная работа была создана бенефициаром,
заявитель может представить:

- Доказательства того, что произведение в первую очередь было создано бенефициаром
- Материалы, созданные с целью рекламы художественных произведений бенефициара
- Отчеты о продажах, в которых бенефициар указан как автор проданных произведений

---

## PART 2: PROVE THE VENUE WAS AN EXHIBITION OR SHOWCASE (Раздел 2)

Во втором разделе доказываем, были ли места (виртуальные или иные), где демонстрировалась
работа человека, художественными выставками или витринами.

**Definition**: Онлайн-словарь Merriam-Webster определяет «выставку» как публичный показ
(произведений искусства, промышленных объектов или спортивных навыков).

### Required Documentation for Part 2:

Чтобы помочь определить, что места, где демонстрировались работы бенефициара, являются
художественными выставками или витринами, заявитель может представить:

- Доказательства того, что места (виртуальные или иные), где демонстрировались работы
  бенефициара, являлись художественными выставками или витринами
- Материалы, созданные для продвижения и рекламы художественных выставок или витрин

---

## SCOPE OF CRITERION:

Данный критерий чаще всего используется в искусстве, но бывают и бизнес-выставки,
которые можно показать.

### Can Include:

В данный критерий также можно включать доказательства, если клиент принимал участие
на **научно-технических выставках** и представлял собственные разработки:
- Инновационные проекты
- Стартапы
- Баннеры и флаеры своей компании

### Documentation Requirements:

Прикладываются:
- Фотографии
- Документальные доказательства
- Описание самого мероприятия

---

## TYPES OF QUALIFYING EXHIBITIONS:

### Art Exhibitions:
- Художественные галереи
- Музейные выставки
- Международные арт-биеннале

### Professional Exhibitions:
- Профессиональные образовательные выставки (например, ICEF event)
- Научно-технические выставки
- Отраслевые ярмарки

### Special Category - Dog Shows (Выставки собак):

**Монопородные выставки** - когда участвуют только представители одной породы.
Обычно такие выставки организовывают клубы, которые занимаются разведением конкретной породы.

Типы выставок собак:
- **Чемпион Национального Клуба Породы** - самая престижная и главная выставка,
  проводимая ежегодно. Лучший кобель и Лучшая сука становятся Чемпионами Клуба
- **Победитель Клуба** - выставки, где назначают Победителей Национального Клуба
- **Кандидат в Чемпионы Клуба** - выставки, позволяющие получить титул Кандидата
  в Чемпионы Национального Клуба Породы

**Интернациональные выставки собак всех пород (CAC - FCI)** проводятся в соответствии
с требованиями FCI и Положением РКФ о выставках ранга CACIB, САС.

К участию в Интернациональных выставках ранга CAC допускаются только породы собак,
признанные FCI.

---

## EXAMPLE - EDUCATIONAL EXHIBITIONS:

Работая в English School of Canada, я приезжала в Москву на профессиональную
образовательную выставку ICEF event - это ведущие в мире сетевые конференции B2B
для международных специалистов в области образования, стремящихся расширить свою сеть.

EduCanada - это ежегодная крупная учебная ярмарка, официальное образовательное
мероприятие, организованное правительством Канады. На ярмарке можно напрямую общаться
с представителями учебных заведений и получить ответы на вопросы по поводу обучения.

Imagine Education au/in Canada - это не только выставка образовательных учреждений,
но и бренд, созданный в результате совместных усилий Министерства иностранных дел,
торговли и развития Канады (DFATD) и Совета министров образования по продвижению
непревзойденно высокой ценности канадского образовательного опыта.

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Verify the work displayed was created by the beneficiary
2. Confirm the venue qualifies as an artistic exhibition or showcase
3. Document the prestige and reach of the exhibition
4. Collect promotional materials from the exhibition
5. Gather photos showing the beneficiary's work on display
6. Verify the exhibition relates to the beneficiary's field
7. Document sales or recognition received at exhibitions
8. Identify any gaps in documentation
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For each exhibition/showcase provide:
- Exhibition/Showcase Name (Название выставки/витрины)
- Location and Date (Место и дата)
- Work Displayed (Выставленная работа)
- Part 1 Analysis: Work Attribution (Анализ Раздела 1)
- Part 2 Analysis: Venue Qualification (Анализ Раздела 2)
- Exhibition Prestige/Reach (Престиж/охват выставки)
- Number of Participants/Exhibitors (Количество участников/экспонентов)
- Promotional Materials Available (Рекламные материалы)
- Photos/Visual Documentation (Фотодокументация)
- Awards/Recognition at Exhibition (Награды/признание на выставке)
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
        """Evaluate exhibitions evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for exhibitions criterion.",
                part2_analysis="Cannot assess exhibition venues without evidence.",
                evidence_summary=[],
                missing_documents=[
                    "Exhibition participation documentation",
                    "Photos of displayed work",
                    "Exhibition promotional materials",
                    "Proof of work attribution",
                ],
                recommendations=[
                    "Submit photos showing work on display",
                    "Provide exhibition program/catalog",
                    "Include promotional materials",
                    "Document venue's artistic status",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.25, 0.8)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} exhibition(s). Manual review needed.",
            part2_analysis="Venue qualifications require verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify work attribution documents",
                "Exhibition promotional materials",
                "Venue qualification evidence",
            ],
            recommendations=[
                "Add photos of work on display",
                "Include exhibition catalogs or programs",
                "Document venue prestige and reach",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for exhibitions criterion."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No exhibitions evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner's work has been displayed at the following artistic "
            "exhibitions and showcases:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Exhibition {i}: {ev.title}**")
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
        """Validate petition text for exhibitions criterion."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "exhibition" not in petition_text.lower() and "showcase" not in petition_text.lower():
            issues.append("Missing reference to exhibition or showcase")

        if "display" not in petition_text.lower():
            suggestions.append("Consider adding reference to work being displayed")

        if "attachment" not in petition_text.lower():
            suggestions.append("Consider referencing photo/visual attachments")

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
