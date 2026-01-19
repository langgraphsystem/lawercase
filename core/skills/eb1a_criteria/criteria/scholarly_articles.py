"""
Scholarly Articles Criterion - 8 CFR 204.5(h)(3)(vi)

Evidence of the beneficiary's authorship of scholarly articles in the field,
in professional or major trade publications or other major media.
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


class ScholarlyArticlesCriterion(CriterionBase):
    """
    Criterion 6: Authorship of Scholarly Articles.

    8 CFR 204.5(h)(3)(vi): Evidence of the beneficiary's authorship of scholarly
    articles in the field, in professional or major trade publications or other
    major media.
    """

    CRITERION_TYPE = CriterionType.SCHOLARLY_ARTICLES
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(vi)"
    TITLE_EN = "Authorship of Scholarly Articles"
    TITLE_RU = "Авторство научных статей в профессиональных изданиях"

    PROMPT = """
# CRITERION 6: AUTHORSHIP OF SCHOLARLY ARTICLES
## Regulatory Reference: 8 CFR 204.5(h)(3)(vi)

Evidence of the beneficiary's authorship of scholarly articles in the field,
in professional or major trade publications or other major media.

---

## PART 1: PROVE THE PETITIONER IS THE AUTHOR (Раздел 1)

В первом разделе доказываем, действительно ли является петиционер автором указанных
научных статей в данной области. Имеются ли цитирования статьи, рецензии и скачивания.

### What Qualifies as Scholarly Article:

Научная статья:
- Сообщает об оригинальных исследованиях и экспериментах
- Или состоит из философских рассуждений
- Как правило, имеет сноски, концевые сноски или библиографию
- Может включать графики, диаграммы или рисунки в качестве иллюстрации концепции
- **Написана для сведущих людей в данной области**

В академической сфере научная статья:
- Сообщает об оригинальных исследованиях, экспериментах или философских рассуждениях
- Написана исследователем или экспертом в этой области, который часто связан с
  колледжем, университетом или исследовательским институтом
- Обычно рецензируется другими экспертами в области специализации

---

## PART 2: PROVE THE PUBLICATION IS PROFESSIONAL/MAJOR (Раздел 2)

Во втором разделе доказываем, относится ли издание к категории профессионального издания,
крупного отраслевого издания или крупного медийного издания.

---

## WHO COUNTS AS "LEARNED":

"Обученный" определяется как "обладающий глубокими знаниями, полученными в результате
обучения". К образованным лицам относятся все лица, обладающие глубокими знаниями
в определенной области.

---

## REQUIRED DOCUMENTATION:

Чтобы соответствовать этому критерию, представьте полный список научных статей,
автором которых является бенефициар. Доказательства этого могут включать:

1. **Результаты поиска научной литературы** на сайтах (например, SciFinder или Google Scholar),
   где указан автор, название статьи и журнал публикации

2. **Бумажные копии статей** бенефициара. Не обязательно представлять полные тексты статей.
   Для каждой статьи необходимо предоставить только страницы, показывающие:
   - О бенефициаре как авторе
   - Название статьи
   - Журнал, в котором она была опубликована

3. **Документальное подтверждение** того, что издания, в которых опубликованы статьи,
   являются профессиональными изданиями, торговыми изданиями или другими крупными СМИ.
   - Такие доказательства могут включать информацию о тираже
   - Если статья была опубликована в Интернете, доказательства должны относиться к веб-сайту
   - Если статья была опубликована в печати, доказательства должны относиться к печатному изданию

---

## QUALIFYING EXAMPLES (Примеры подходящих публикаций):

- Публикации в профессиональных рецензируемых журналах
- Публикация презентаций на конференциях, признанных на национальном или международном уровне
- Колонка эксперта в отраслевом СМИ

**Примечание**: Данный критерий чаще всего подтверждается научными статьями либо колонкой
эксперта в отраслевом СМИ. Данный пункт покрывается у всех кандидатов наук, поскольку
все они пишут статьи в профессиональные журналы.

---

## USCIS GUIDANCE (Пояснения):

### First Determination:
USCIS определяет, писал ли человек научные статьи в этой области.

### Second Determination:
USCIS определяет, квалифицируется ли публикация как профессиональная публикация,
крупное отраслевое издание или крупное издание в средствах массовой информации.

### Factors for Assessment:
При оценке того, является ли представленная публикация профессиональным изданием
или крупным СМИ, соответствующие факторы включают:
- Целевую аудиторию (для профессиональных журналов)
- Тираж или читательскую аудиторию по сравнению с другими СМИ в данной области
  (для крупных СМИ)

---

## VAK PUBLICATIONS (ВАК):

Журналы, входящие в перечень Высшей аттестационной комиссии (ВАК), являются
профессиональными рецензируемыми изданиями.

**О ВАК**:
- Высшая аттестационная комиссия (ВАК) – это основной орган государственного значения
- Отвечает за присуждение ученых степеней (кандидатов и докторов наук) и званий
  (доцент и профессор) в России
- Проводит государственную аттестацию научных работников
- Анализирует научные работы
- Имеет собственный утвержденный список рецензируемых журналов, рекомендуемых для публикаций

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. List all scholarly articles authored by the beneficiary
2. Verify authorship for each article
3. Determine scholarly nature (original research, peer-reviewed)
4. Research publication quality and reach
5. Document citations count (Google Scholar, etc.)
6. Verify publication is professional or major trade
7. Include circulation/readership statistics
8. Identify any gaps in documentation
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For each scholarly article provide:
- Article Title (Название статьи)
- Publication/Journal Name (Название издания/журнала)
- Publication Date (Дата публикации)
- Co-Authors (if any) (Соавторы)
- Part 1 Analysis: Authorship Verification (Анализ Раздела 1)
- Part 2 Analysis: Publication Quality (Анализ Раздела 2)
- Peer-Reviewed: Yes/No (Рецензирование: Да/Нет)
- VAK Listed: Yes/No (Входит в перечень ВАК: Да/Нет)
- Citation Count (Количество цитирований)
- Google Scholar/Database Listing (Индексация в базах данных)
- Circulation/Impact Factor (Тираж/Импакт-фактор)
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
        """Evaluate scholarly articles evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for scholarly articles criterion.",
                part2_analysis="Cannot assess publication quality without articles.",
                evidence_summary=[],
                missing_documents=[
                    "Scholarly articles authored by beneficiary",
                    "Publication information",
                    "Citation counts",
                    "Journal impact factors/rankings",
                ],
                recommendations=[
                    "Submit copies of scholarly articles",
                    "Provide Google Scholar citations",
                    "Include journal impact factor data",
                    "Document peer review process",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.2, 0.8)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} scholarly article(s). Manual review needed.",
            part2_analysis="Publication quality and citation impact require verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify citation counts are included",
                "Journal ranking documentation",
                "Peer review evidence",
            ],
            recommendations=[
                "Add Google Scholar citation data",
                "Include journal impact factors",
                "Document peer review status",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for scholarly articles criterion."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No scholarly articles evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner has authored the following scholarly articles in professional "
            "and major trade publications:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Article {i}: {ev.title}**")
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
        """Validate petition text for scholarly articles criterion."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "scholarly" not in petition_text.lower() and "peer-reviewed" not in petition_text.lower():
            issues.append("Missing reference to scholarly or peer-reviewed nature")

        if "professional" not in petition_text.lower() and "major" not in petition_text.lower():
            suggestions.append("Consider adding reference to professional/major publication status")

        if "citation" not in petition_text.lower():
            suggestions.append("Consider adding citation information")

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
