"""
Published Material Criterion - 8 CFR 204.5(h)(3)(iii)

Evidence of published material about the beneficiary in professional or
major trade publications or other major media.
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


class PublishedMaterialCriterion(CriterionBase):
    """
    Criterion 3: Published Material About the Beneficiary.

    8 CFR 204.5(h)(3)(iii): Evidence of published material about the beneficiary
    in professional or major trade publications or other major media, relating
    to the beneficiary's work in the field for which classification is sought.
    """

    CRITERION_TYPE = CriterionType.PUBLISHED_MATERIAL
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(iii)"
    TITLE_EN = "Published Material About the Beneficiary"
    TITLE_RU = "Публикации о бенефициаре в профессиональных или крупных СМИ"

    PROMPT = """
# CRITERION 3: PUBLISHED MATERIAL ABOUT THE BENEFICIARY
## Regulatory Reference: 8 CFR 204.5(h)(3)(iii)

Evidence of published material about the beneficiary in professional or major trade
publications or other major media, relating to the beneficiary's work in the field
for which classification is sought.

---

## PART 1: PROVE THE MATERIAL IS ABOUT THE PETITIONER (Раздел 1)

В первом разделе доказываем, связан ли опубликованный материал с человеком и его
конкретной работой в области, для которой запрашивается классификация.

Для того чтобы опубликованный материал соответствовал этому критерию, он должен быть
в первую очередь посвящен клиенту и связан с его работой в данной области и, как
указано в правилах, быть напечатан "в профессиональных или крупных торговых изданиях
или других крупных средствах массовой информации" и "должен содержать название, дату
и автора материала, а также любой необходимый перевод".

### Required Documentation for Part 1:

Чтобы помочь определить, что опубликованный материал относится к бенефициару и его
работе в данной области, заявитель может представить:

- Дополнительные опубликованные материалы, относящиеся к бенефициару и его работе
- Документальное подтверждение того, что представленный опубликованный материал
  касается бенефициара и его работы в данной области
- Название, дата и автор опубликованного материала
- Перевод материала (если оригинал на иностранном языке)

### Key Points for Part 1:

- Опубликованные материалы должны быть датированы до даты подачи формы I-140
- Материалы должны быть посвящены работе бенефициара в данной области, а не только
  работодателю или другим организациям, с которыми бенефициар связан
- Маркетинговые материалы, созданные с целью продажи продукции бенефициара или
  продвижения его услуг, обычно не считаются опубликованными материалами о бенефициаре
- Неоцененные списки в предметном указателе или сносках недостаточны

---

## PART 2: PROVE THE PUBLICATION IS A MAJOR PUBLICATION (Раздел 2)

Во втором разделе доказываем, относится ли издание к категории профессионального
издания, крупного отраслевого издания или крупного медийного издания.

Включаем: историю издания, рейтинг, посещаемость (по количеству посетителей,
градация посетителей по страновой принадлежности) и другие показатели.

### Required Documentation for Part 2:

Чтобы помочь определить, что публикации соответствуют критериям профессиональных
или крупных торговых изданий или других крупных СМИ, необходимо представить:

- Независимые объективные данные о тираже (онлайн и/или в печатном виде)
- Целевая аудитория издания
- Рейтинг издания в своей отрасли
- Географический охват читателей
- Статистика посещаемости сайта (если онлайн-публикация)

**Примечание**: Представленные доказательства должны соответствовать формату СМИ.
Если материал был опубликован в Интернете, доказательства должны относиться к веб-сайту.
Если материал был опубликован в печати, доказательства должны относиться к печатному изданию.

---

## QUALIFYING TYPES OF MEDIA (Типы подходящих СМИ):

Примеры подходящих средств массовой информации могут включать, помимо прочего:

- Профессиональные или крупные печатные публикации (газетные статьи, статьи в
  популярных и академических журналах, книги, учебники или аналогичные публикации)
- Профессиональные или крупные онлайн-публикации, посвященные человеку и его работе
- Стенограммы профессиональных или крупных аудио- или видеорепортажей

---

## USCIS GUIDANCE (Пояснения):

### On Subject of Publication:

Публикуемый материал должен быть посвящен человеку и иметь отношение к его работе
в данной сфере, а не только о работодателе человека и работе работодателя или другой
организации и работе этой организации.

Любые материалы, подаваемые заявителем, должны демонстрировать ценность работы и
вклада человека и не должны быть сосредоточены исключительно на работодателе или
организации, с которой связано это лицо.

**ВАЖНО**: Маркетинговые материалы, созданные с целью продажи продуктов человека или
продвижения услуг человека, обычно не считаются опубликованными материалами о человеке
(это включает казалось бы объективный контент о бенефициаре в крупных печатных изданиях,
за который заплатил бенефициар или работодатель бенефициара).

### On Broader Topics:

Человек и его творчество не обязательно должны быть единственным предметом материала.
Опубликованный материал, который охватывает более широкую тему, но включает существенное
обсуждение работы человека в этой области и упоминает это лицо в связи с работой,
может считаться материалом о человеке, относящимся к его работе.

### On Group Work:

Офицеры могут рассматривать материалы, которые сосредоточены исключительно или в первую
очередь на работе или исследовании, проводимых группой, членом которой является это лицо,
при условии, что в материалах упоминается это лицо в связи с работой или другие
доказательства в учетных документах значимы для роли этого человека в работе или исследовании.

### On Major Media Assessment:

При оценке того, является ли представленная публикация профессиональной публикацией,
крупным отраслевым изданием или крупным средством массовой информации, соответствующие
факторы включают:
- Целевую аудиторию (для профессиональных и крупных отраслевых изданий)
- Относительный тираж, читательскую аудиторию или зрительскую аудиторию

Чтобы считаться крупным СМИ, публикация должна иметь значительное национальное или
международное распространение. Местное издание не заслужит признания на национальном уровне.

Некоторые газеты, например The New York Times, номинально обслуживают конкретный
населенный пункт, но, в отличие от местных газет, могут считаться крупными СМИ,
поскольку имеют значительное национальное распространение.

---

## IMPORTANT NOTE (ВАЖНО):

Газеты, журналы, интернет-порталы, ТВ в сфере деятельности Клиента и говорящие о
Клиенте, берущие интервью у Клиента, приглашающие Клиента как эксперта в сфере его
деятельности. Обратите внимание, чтобы это не был ярко выраженный маркетинговый материал.
В идеале использовать отраслевые СМИ.

**Редакторы не пишут и не корректируют для клиента статьи перед размещением их в СМИ.**
Клиент самостоятельно предоставляет ссылки на ранее опубликованные статьи, а в случае
решения об опубликовании новых самостоятельно ищет людей, кто этим занимается.

В данном критерии необходимо сначала указать заголовок статьи и уже потом описывается
сама статья. Информацию (статистику) об источнике публикации (журнал, газета либо
веб-сайт) можно найти в разделе для рекламодателей или в МедиаКите.

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Verify each publication is primarily about the beneficiary and their work
2. Confirm title, date, and author are documented for each publication
3. Research circulation/traffic statistics for each publication
4. Determine if publications are professional, major trade, or major media
5. Exclude marketing materials and paid placements
6. Verify geographic reach (national/international distribution)
7. Check industry ranking and reputation of publications
8. Identify any gaps in documentation
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For each publication provide:
- Article Title and Date (Заголовок статьи и дата)
- Publication Name (Название издания)
- Author (Автор)
- Part 1 Analysis: About Beneficiary and Work (Анализ Раздела 1)
- Part 2 Analysis: Major Publication Evidence (Анализ Раздела 2)
- Circulation/Traffic Statistics (Тираж/статистика посещаемости)
- Industry Ranking (Рейтинг в отрасли)
- Geographic Reach (Географический охват)
- Target Audience (Целевая аудитория)
- Documentation Status: Complete/Partial/Missing (Статус документации)
- Marketing Content Check: Yes/No (Проверка на маркетинговый контент)
- Strengths and Weaknesses (Сильные и слабые стороны)
- Recommendations for Strengthening (Рекомендации по усилению)
- Draft Petition Language (Черновик текста петиции)
"""

    async def evaluate(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate published material evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for published material criterion.",
                part2_analysis="Cannot assess publication quality without evidence.",
                evidence_summary=[],
                missing_documents=[
                    "Published articles about beneficiary",
                    "Circulation/traffic statistics",
                    "Publication industry rankings",
                    "Target audience documentation",
                ],
                recommendations=[
                    "Submit copies of published articles",
                    "Provide circulation data for each publication",
                    "Include publication's industry ranking",
                    "Document geographic reach of publications",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.2, 0.8)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} publication(s). Manual review needed.",
            part2_analysis="Publication quality and reach require verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify circulation statistics are included",
                "Publication ranking documentation",
                "Geographic reach evidence",
            ],
            recommendations=[
                "Verify each publication is about beneficiary, not employer",
                "Exclude any marketing or paid content",
                "Add traffic/circulation statistics",
                "Include industry ranking for each publication",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for published material criterion."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No published material evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner has been featured in the following professional and "
            "major media publications, which relate to the Petitioner's work in the field:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Publication {i}: {ev.title}**")
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
        """Validate petition text for published material criterion."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "circulation" not in petition_text.lower() and "traffic" not in petition_text.lower():
            suggestions.append("Consider adding circulation/traffic statistics")

        if "major" not in petition_text.lower():
            issues.append("Missing reference to 'major' publication status")

        if "marketing" in petition_text.lower() or "advertisement" in petition_text.lower():
            issues.append("Publication may be marketing material - verify it is editorial content")

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
