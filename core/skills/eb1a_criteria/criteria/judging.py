"""
Judging Criterion - 8 CFR 204.5(h)(3)(iv)

Evidence of the beneficiary's participation as a judge of the work of
others in the same or an allied field of specialization.
"""

from __future__ import annotations

from typing import Any

from ..base import (CriterionBase, CriterionType, EvaluationResult, Evidence,
                    EvidenceStrength, PetitionSection, ValidationResult)


class JudgingCriterion(CriterionBase):
    """
    Criterion 4: Judging the Work of Others.

    8 CFR 204.5(h)(3)(iv): Evidence of the beneficiary's participation, either
    individually or on a panel, as a judge of the work of others in the same
    or an allied field of specialization for which classification is sought.
    """

    CRITERION_TYPE = CriterionType.JUDGING
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(iv)"
    TITLE_EN = "Judging the Work of Others"
    TITLE_RU = "Участие в качестве судьи работы других лиц"

    PROMPT = """
# CRITERION 4: JUDGING THE WORK OF OTHERS
## Regulatory Reference: 8 CFR 204.5(h)(3)(iv)

Evidence of the beneficiary's participation, either individually or on a panel,
as a judge of the work of others in the same or an allied field of specialization
for which classification is sought.

---

## REQUIRED DOCUMENTATION:

Для доказательства этого критерия прилагаем следующие документы:

- Письмо или скриншот электронной переписки о приглашении на судейство
- Бланки проведенной экспертизы или протоколы с результатами
- Программа конкурса, соревнований или другого мероприятия, где в судейской
  коллегии указан наш клиент, бейджи с указанием его статуса как судьи
- Фотографии, где петиционер запечатлен в процессе судейства, а также на фоне
  баннеров с наименованием мероприятия
- Рекомендательное или благодарственное письмо об участии петиционера в судействе

---

## TYPES OF JUDGING ACTIVITIES:

### General Categories:
- **Судья** - официальное назначение судьей конкурса или соревнований
- **Жюри** - участие в составе жюри или экспертной комиссии
- **Член экспертной комиссии** - оценка работ других специалистов

### Specific Examples:
- Тренеры довольно часто имеют судейскую книгу
- Экспертов приглашают по договорам для оценки работы других специалистов

---

## USCIS INTERPRETATION:

Фраза "судья" подразумевает официальное назначение на должность судьи, либо в составе
коллегии, либо индивидуально, как указано в положении 8 C.F.R. § 204.5(h)(3)(iv).

Независимо от широких словарных определений слов "судья" и "работа", окончательное
решение о том, соответствует ли доказательство простым требованиям нормативного акта,
остается за USCIS. См. Matter of Caron International, 19 I&N Dec. 791, 795 (Comm'r 1988).

**ВАЖНО**: Первоначальные доказательства должны продемонстрировать, что бенефициар
"признан в области экспертизы", поэтому положение не может быть истолковано как
включающее каждый неформальный случай оценки подчиненных сотрудников или продукции.

---

## QUALIFYING EXAMPLES (Примеры подходящего судейства):

Примеры оценки работы других могут включать, помимо прочего:

1. **Рецензирование научного журнала** - о чем свидетельствует просьба журнала провести
   рецензию, сопровождаемая доказательством того, что рецензия действительно была завершена

2. **Рецензирование тезисов или статей** для презентации на научных конференциях
   в соответствующей области

3. **Работа в докторском диссертационном комитете** (Ph.D. dissertation committee),
   который выносит окончательное решение о том, соответствует ли работа кандидата
   требованиям для получения докторской степени (подтверждается ведомственными записями)

4. **Рецензент государственных программ финансирования исследований**

---

## DOCUMENTATION REQUIREMENTS:

Документы, которые помогут определить, работал ли бенефициар в качестве судьи:

- Независимые и объективные документы о событии или случае, когда он выступал в качестве судьи
- О работе, которая оценивалась
- Об уровне участников
- О том, как он был выбран в качестве официального судьи
- Свидетельства о том, когда происходило судейство

---

## USCIS GUIDANCE (Пояснения):

Заявитель должен доказать, что это лицо не только было приглашено для оценки работы
других лиц, но также и то, что **оно действительно участвовало** в оценке работы
других лиц в той же или смежной области специализации.

Например, заявитель может документировать работу по рецензированию, предоставив:
- Копию запроса из журнала на проведение рецензии
- Доказательства, подтверждающие, что человек действительно завершил рецензию

**ВАЖНО**: Оценка работы других людей или рецензирование должно быть на
**БЕЗВОЗМЕЗДНОЙ** основе.

---

## IF CLIENT HAS NO JUDGING EXPERIENCE:

Если у Клиента нет судейства, то он может сделать его:
- Клиент может обратиться в свой Университет и взять дипломные работы либо диссертации
  для рецензии

### For Beauty Industry:
- Конкурс мастеров типа BEAUTY BATTLE на лучшую стрижку/окрашивание/маникюр
- Участники: мастера и клиенты в команде
- Условия могут быть: выложить фотографию выполненной услуги и запустить голосование
  в соцсетях
- Ассоциации проводят конференции, организаторами могут быть продавцы расходных
  материалов, в рамках рекламы

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Verify official invitation or appointment as judge
2. Confirm actual participation (not just invitation)
3. Document the nature of work being judged
4. Identify level and prestige of the event/competition
5. Verify the judging is in same or allied field
6. Check if judging was compensated (should be uncompensated for scholarly review)
7. Gather supporting documentation (photos, certificates, protocols)
8. Obtain testimonial letters from organizers
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For each judging activity provide:
- Event/Activity Name and Date (Название мероприятия и дата)
- Type of Judging: Panel/Individual/Peer Review (Тип судейства)
- Field Alignment: Same/Allied (Соответствие области)
- Official Appointment Documentation (Документация о назначении)
- Proof of Actual Participation (Доказательство фактического участия)
- Level of Competition/Event (Уровень мероприятия)
- Number of Participants Judged (Количество оцененных участников)
- Selection Criteria Used (Использованные критерии отбора)
- Documentation Status: Complete/Partial/Missing (Статус документации)
- Compensated: Yes/No (Оплачиваемое: Да/Нет)
- Strengths and Weaknesses (Сильные и слабые стороны)
- Recommendations for Strengthening (Рекомендации по усилению)
- Draft Petition Language (Черновик текста петиции)
"""

    async def evaluate(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate judging evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for judging criterion.",
                part2_analysis="Cannot assess judging activities without evidence.",
                evidence_summary=[],
                missing_documents=[
                    "Invitation to judge",
                    "Proof of actual participation",
                    "Event/competition documentation",
                    "Judging protocols or results",
                ],
                recommendations=[
                    "Submit invitation letters to judge",
                    "Provide proof of completed judging",
                    "Include event program showing judge status",
                    "Add photos or certificates from judging",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.25, 0.8)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} judging activity(ies). Manual review needed.",
            part2_analysis="Verify actual participation and field alignment.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify proof of actual judging (not just invitation)",
                "Event documentation",
                "Judging protocols",
            ],
            recommendations=[
                "Confirm each judging activity includes proof of participation",
                "Verify judging is in same or allied field",
                "Add testimonial letters from organizers",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for judging criterion."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No judging evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner has participated as a judge of the work of others in the field, "
            "demonstrating recognition of expertise by peers and professional organizations:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Judging Activity {i}: {ev.title}**")
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
        """Validate petition text for judging criterion."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "judge" not in petition_text.lower() and "panel" not in petition_text.lower():
            issues.append("Missing reference to judging or panel participation")

        if "invited" in petition_text.lower() and "participated" not in petition_text.lower():
            suggestions.append("Ensure proof of actual participation, not just invitation")

        if "field" not in petition_text.lower():
            suggestions.append("Consider explicitly stating the field alignment")

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
