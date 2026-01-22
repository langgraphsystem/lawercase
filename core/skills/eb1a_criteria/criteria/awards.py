"""
Awards Criterion - 8 CFR 204.5(h)(3)(i)

Evidence of receipt of lesser nationally or internationally recognized
prizes or awards for excellence in the field of endeavor.
"""

from __future__ import annotations

from typing import Any

from ..base import (CriterionBase, CriterionType, EvaluationResult, Evidence,
                    EvidenceStrength, PetitionSection, ValidationResult)


class AwardsCriterion(CriterionBase):
    """
    Criterion 1: Awards for Excellence.

    8 CFR 204.5(h)(3)(i): Evidence of receipt of lesser nationally or
    internationally recognized prizes or awards for excellence in the
    field of endeavor.
    """

    CRITERION_TYPE = CriterionType.AWARDS
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(i)"
    TITLE_EN = "Prizes or Awards for Excellence"
    TITLE_RU = "Призы или награды за выдающиеся достижения"

    PROMPT = """
# CRITERION 1: PRIZES OR AWARDS FOR EXCELLENCE
## Regulatory Reference: 8 CFR 204.5(h)(3)(i)

Evidence of receipt of lesser nationally or internationally recognized prizes or awards
for excellence in the field of endeavor.

---

## PART 1: PROVE THE PETITIONER RECEIVED THE AWARD (Раздел 1)

В первом разделе доказываем: был ли человек получателем призов или наград.

Ничто не мешает человеку рассчитывать на командную награду, при условии, что он является
одним из получателей награды. Описание этого типа доказательств в аффидевите указывает
на то, что основное внимание следует уделять получению наград или призов лицом, а не
получению наград или призов работодателем.

Награда может быть известна на международном или национальном уровне, может быть известна
только в профессиональных кругах. Главное доказать, что за награду был конкурс, были
претенденты и Клиент стал победителем.

### Required Documentation for Part 1:

Чтобы подтвердить получение награды Petitioner, для любого представленного приза или
награды необходимо указать:

- Копию сертификата на каждый приз или награду
- Четкую фотографию каждого приза или награды
- Публичное объявление о присуждении призов или наград, выпущенное организацией,
  предоставляющей грант

Чтобы показать, что призы или награды находятся в сфере деятельности получателя,
пожалуйста, необходимо представить:

- Документальное подтверждение наличия национальных или международных премий или наград,
  полученных за выдающиеся достижения в области деятельности бенефициара
- Документальное подтверждение того, по каким критериям были присуждены премии или награды
- Документальное подтверждение, описывающее, как эти призы или награды связаны с областью
  деятельности бенефициара
- Документальное подтверждение следующего:
  - Значение призов или наград
  - Кто рассматривается на соискание премий или наград
  - Сколько призов или наград вручается ежегодно
  - Предыдущие лауреаты, связанные с областью деятельности получателя

---

## PART 2: PROVE THE AWARD IS NATIONALLY OR INTERNATIONALLY RECOGNIZED (Раздел 2)

Во втором разделе доказываем: является ли награда менее значимым национальным или
международным призом или наградой, которую человек получил за выдающиеся достижения
в области деятельности.

Как указано в простом тексте постановления, этот критерий не требует, чтобы награда
или приз имели тот же уровень признания и престижа, что и Нобелевская премия или
другая награда, которая могла бы считаться одноразовым достижением.

### Required Documentation for Part 2:

Чтобы показать, что они являются национально или международно признанными призами
или наградами, необходимо представить объективные документальные свидетельства:

- Критерии, используемые для присуждения премий или наград
- Значимость премий или наград, включая национальное или международное признание,
  которое разделяют премии или награды
- Репутация организации или комиссии, присуждающей премии или награды
- Кто рассматривается на соискание премий или наград, включая географический охват,
  в котором могут быть представлены кандидаты
- Сколько премий или наград присуждается ежегодно
- Предыдущие лауреаты премий или наград

Чтобы продемонстрировать выдающиеся достижения в области, послужившие основанием
для присуждения премии или награды, заявитель может представить:

- Объективные документальные свидетельства, описывающие, как призы или награды
  связаны с достижениями в сфере деятельности бенефициара
- Объективные документальные доказательства критериев, использованных для
  присуждения премий или наград, включая доказательства того, что критерием
  для получения премий или наград было превосходство в данной области

---

## QUALIFYING EXAMPLES (Примеры наград, отвечающих требованиям):

Примерами наград, отвечающих требованиям, могут быть, в частности, следующие:

- Определенные награды известных национальных институтов или известных
  профессиональных ассоциаций
- Определенные награды за докторские диссертации
- Определенные награды за презентации на национально или международно
  признанных конференциях

---

## USCIS GUIDANCE (Пояснения):

Соответствующие соображения относительно того, было ли основанием для присуждения
премий или наград достижение выдающихся результатов в данной области, включают,
но не ограничиваются следующим:

- Критерии, используемые для присуждения наград или премий
- Национальное или международное значение премий или наград в данной области
- Количество лауреатов или получателей премии
- Ограничения для конкурентов

Хотя многие академические награды не имеют требуемого уровня признания, могут
существовать такие, которые признаны на национальном или международном уровне
как награды за выдающиеся достижения, и они могут удовлетворять требованиям
этого критерия.

Например, награда, доступная только лицам, проживающим в одном населенном пункте,
работодателю или учебному заведению, может иметь незначительное национальное или
международное признание, в то время как награда, открытая для членов известного
национального учреждения (включая докторантуру в университете R1 или R2) или
профессиональной организации, может быть признана на национальном уровне.

Аналогичным образом, национальное или международное признание чаще всего
ассоциируется с наградами, присуждаемыми лицам самого высокого уровня в данной
области. Однако нет конкретного требования, чтобы награда была открыта для всех
членов области, включая самых опытных, чтобы соответствовать требованиям этого
критерия.

Хотя ограничения на участников могут быть важным фактором, в некоторых случаях
доказательства могут установить, что награда или приз признаются на национальном
или международном уровне, несмотря на то, что они ограничены молодежью, любителями
или начинающими профессионалами.

Например, награды, присуждаемые новым игрокам или «новобранцам» в основных
спортивных лигах, могут получить национальное или даже международное освещение
в СМИ.

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Для каждой награды проверьте, указан ли петиционер как получатель
2. Задокументируйте название награды, дату получения и организацию-учредителя
3. Оцените географический охват: Местный/Региональный/Национальный/Международный
4. Проанализируйте критерии отбора и конкурсный процесс
5. Задокументируйте количество номинантов vs. победителей
6. Изучите предыдущих лауреатов и их положение в области
7. Соберите освещение награды в СМИ
8. Определите недостающую документацию и рекомендуйте, как её получить
9. Подготовьте тезисы для рекомендательных писем
10. Оцените общую силу: Exceptional/Strong/Moderate/Weak/Insufficient

## RESPONSE FORMAT:

For each award provide:
- Award Name and Year (Название и год награды)
- Awarding Organization (Организация-учредитель)
- Recognition Level: Local/Regional/National/International (Уровень признания)
- Part 1 Analysis: Receipt Documentation Status (Анализ Раздела 1)
- Part 2 Analysis: Recognition Level Evidence (Анализ Раздела 2)
- Selection Process Description (Описание процесса отбора)
- Competition Statistics: nominees vs. winners (Статистика конкурса)
- Geographic Scope of Candidates (Географический охват кандидатов)
- Previous Laureates Analysis (Анализ предыдущих лауреатов)
- Media Coverage Found (Найденное освещение в СМИ)
- Documentation Status: Complete/Partial/Missing (Статус документации)
- Strengths and Weaknesses (Сильные и слабые стороны)
- Missing Documents Needed (Недостающие документы)
- Recommendations for Strengthening (Рекомендации по усилению)
- Draft Petition Language (Черновик текста петиции)
"""

    async def evaluate(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """
        Evaluate awards evidence.

        Args:
            evidence: List of evidence items
            case_context: Additional case context

        Returns:
            EvaluationResult with detailed analysis
        """
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for awards criterion.",
                part2_analysis="Cannot assess recognition level without evidence.",
                evidence_summary=[],
                missing_documents=[
                    "Award certificates",
                    "Photos of awards",
                    "Selection criteria documentation",
                    "Competition statistics",
                ],
                recommendations=[
                    "Submit copies of all award certificates",
                    "Provide documentation of selection process",
                    "Include information about other nominees/winners",
                ],
            )

        # Build prompt and call LLM if available
        prompt = self.get_prompt(evidence, case_context)

        if self.llm_router:
            # Call LLM for analysis
            response = await self.llm_router.route_request(
                prompt=prompt,
                task_type="analysis",
            )
            # Parse response and create EvaluationResult
            # For now, return a structured result

        # Default evaluation logic without LLM
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]

        # Calculate preliminary score based on evidence count and types
        score = min(len(evidence) * 0.2, 0.8)  # Max 0.8 without LLM analysis

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} potential award(s). Manual review needed.",
            part2_analysis="Recognition level requires manual assessment of each award.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify all certificates are included",
                "Selection criteria documentation",
                "Competition statistics",
            ],
            recommendations=[
                "Verify each award has complete documentation",
                "Add selection criteria for each award",
                "Include media coverage if available",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """
        Generate petition section for awards criterion.

        Args:
            evidence: List of evidence items
            case_context: Additional case context

        Returns:
            PetitionSection with generated text
        """
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No awards evidence provided]",
                attachments=[],
                word_count=0,
            )

        # Build petition section
        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner has received the following nationally and internationally "
            "recognized prizes and awards for excellence in the field:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Award {i}: {ev.title}**")
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
        """
        Validate petition text for awards criterion.

        Args:
            petition_text: Text to validate
            evidence: Optional evidence for cross-reference

        Returns:
            ValidationResult with issues and suggestions
        """
        issues = []
        suggestions = []
        missing_elements = []

        # Check for required elements
        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if (
            "nationally" not in petition_text.lower()
            and "internationally" not in petition_text.lower()
        ):
            issues.append("Missing reference to national/international recognition level")

        if "selection" not in petition_text.lower() and "criteria" not in petition_text.lower():
            suggestions.append("Consider adding selection criteria description")

        if "attachment" not in petition_text.lower():
            missing_elements.append("Attachment references")

        # Calculate validation score
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
