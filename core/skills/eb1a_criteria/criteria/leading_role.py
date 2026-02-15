"""
Leading Role Criterion - 8 CFR 204.5(h)(3)(viii)

Evidence of the beneficiary's performance of a leading or critical role
for organizations or establishments that have a distinguished reputation.
"""

from __future__ import annotations

from typing import Any

from ..base import (
    CriterionBase,
    CriterionType,
    EvaluationResult,
    Evidence,
    EvidenceStrength,
    PetitionSection,
    ValidationResult,
)


class LeadingRoleCriterion(CriterionBase):
    """
    Criterion 8: Leading or Critical Role in Distinguished Organizations.

    8 CFR 204.5(h)(3)(viii): Evidence of the beneficiary's performance of a leading
    or critical role for organizations or establishments that have a distinguished
    reputation.
    """

    CRITERION_TYPE = CriterionType.LEADING_ROLE
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(viii)"
    TITLE_EN = "Leading or Critical Role in Distinguished Organizations"
    TITLE_RU = "Ведущая или критическая роль в организациях с выдающейся репутацией"

    PROMPT = """
# CRITERION 8: LEADING OR CRITICAL ROLE IN DISTINGUISHED ORGANIZATIONS
## Regulatory Reference: 8 CFR 204.5(h)(3)(viii)

Evidence of the beneficiary's performance of a leading or critical role for
organizations or establishments that have a distinguished reputation.

---

## PART 1: PROVE THE ROLE WAS LEADING OR CRITICAL (Раздел 1)

В первом разделе доказываем, занимало ли лицо руководящую или лидирующую должность
в организации, учреждении, подразделении или отделе организации или учреждения.

Поручались ли клиенту задания, которые мог выполнить только он.

### Who Qualifies:

- Топ менеджеры
- Руководители топовых местных организаций
- Руководители международных организаций
- Лица, благодаря которым были достигнуты высокие результаты

Чаще всего этот критерий доказывается **рекомендательным письмом от работодателя**,
в котором описываются достижения работника как экстраординарной личности.

---

## PART 2: PROVE THE ORGANIZATION HAS DISTINGUISHED REPUTATION (Раздел 2)

Во втором разделе доказываем, имеет ли организация или учреждение, либо департамент
или подразделение, в котором лицо занимает или занимало руководящую или решающую
должность, выдающуюся репутацию.

---

## REQUIRED DOCUMENTATION FOR LEADING/CRITICAL ROLE:

Для определения того, что бенефициарий выполнял ведущую или критическую роль,
могут быть представлены следующие документы:

1. **Письма от нынешних или бывших сотрудников или тренеров**, которые лично знают
   о значимости ведущей или критической роли бенефициара

   Письма должны содержать подробную и доказательную информацию, в которой конкретно
   говорится о том, что роль бенефициара в организации или учреждении является или
   являлась ведущей или критической.

   Подробные сведения должны включать конкретные задачи или достижения бенефициара
   по сравнению с другими людьми, занятыми в аналогичной сфере деятельности.

2. **Документальные свидетельства**, подтверждающие, что роль получателя была/является
   ведущей или критически важной для организаций или учреждений

---

## LEADING ROLE VS CRITICAL ROLE:

### Leading Role (Ведущая роль):
- Доказательства должны подтверждать, что бенефициант является (или являлся) лидером
- Название должности с соответствующими обязанностями может помочь установить,
  является ли роль (или была ли она) на самом деле ведущей

### Critical Role (Критическая роль):
- Доказательства должны свидетельствовать о том, что бенефициар внес вклад,
  имеющий существенное значение для результатов деятельности организации или учреждения
- Вспомогательная роль может считаться "критической", если деятельность бенефициара
  в этой роли является (или была) важной
- **Не название роли бенефициара, а исполнение бенефициаром этой роли определяет,
  является ли эта роль (или была ли она) критической**

---

## REQUIRED DOCUMENTATION FOR DISTINGUISHED REPUTATION:

Чтобы помочь определить, что эти организации имеют выдающуюся репутацию:

- Независимые объективные доказательства, подтверждающие выдающуюся репутацию
  организаций или учреждений, либо подразделения или отдела
- Доказательства должны подтверждать **выдающиеся достижения, выдающиеся качества
  или превосходство** организации или учреждения
- Доказательства, подтверждающие выдающуюся репутацию организации или учреждения
  с учетом ее относительного размера и продолжительности существования

---

## QUALIFYING EXAMPLES (Примеры ведущих или критических ролей):

- Старший преподаватель или старшая исследовательская должность на выдающемся
  академическом факультете или программе
- Старшая исследовательская должность в выдающемся неакадемическом учреждении
  или компании
- Главный или назначенный исследователь департамента, учреждения или предприятия,
  получившего государственную награду за заслуги (например, SBIR)
- Член ключевого комитета известной организации
- Основатель или сооснователь стартапа, имеющего выдающуюся репутацию, или вкладчик
  интеллектуальной собственности в него
- Ведущая или решающая роль выдающейся организации или выдающегося подразделения
  учреждения или компании, подробно объясненная директором или главным исследователем

---

## USCIS GUIDANCE (Пояснения):

### On Evaluating Leading Role:
Офицеры смотрят на то, подтверждают ли доказательства, что данное лицо является
(или было) лидером внутри организации или учреждения, или ее подразделения или отдела.
Должность с соответствующими обязанностями может помочь установить, что роль
действительно является (или была) ведущей.

### On Evaluating Critical Role:
Офицеры проверяют, подтверждают ли доказательства, что данное лицо внесло существенный
вклад в результаты деятельности организации.

### On Letters:
Это один из критериев, когда письма от лиц, лично знающих о значении ведущей или
решающей роли человека, могут быть **особенно полезны** офицерам при принятии такого
решения, при условии, что письма содержат подробную и доказательную информацию.

Подтверждением опыта должны быть письма от работодателей.

### On Distinguished Reputation:
Относительный размер или долговечность организации или учреждения **сами по себе не
являются определяющим фактором**, но рассматриваются вместе с другой информацией
для определения наличия выдающейся репутации.

Другие важные факторы:
- Масштаб клиентской базы
- Соответствующее освещение в СМИ

**Definition**: Онлайн-словарь Мерриам-Вебстер определяет слово «выдающийся» как
«отмеченный выдающимся величием, отличием или превосходством» или «достойное
выдающегося человека».

### For Academic Institutions:
- Соответствующие и заслуживающие доверия национальные рейтинги
- Получение государственных исследовательских грантов

### For Startups:
Доказательства того, что бизнес получил значительное финансирование от государственных
органов, фондов венчурного капитала, инвесторов-ангелов или других подобных спонсоров,
соизмеримых с раундами финансирования, обычно проводимыми для стадии и отрасли
этого стартапа, как положительный фактор.

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Identify the organization and role held by beneficiary
2. Determine if role was leading or critical (or both)
3. Document specific duties and achievements
4. Compare performance to others in similar roles
5. Research organization's distinguished reputation
6. Gather employer recommendation letters
7. Include organization's awards, rankings, or recognition
8. Verify media coverage of organization
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For each role provide:
- Organization Name (Название организации)
- Position/Title (Должность)
- Period of Employment (Период работы)
- Part 1 Analysis: Leading/Critical Role Evidence (Анализ Раздела 1)
- Part 2 Analysis: Distinguished Reputation Evidence (Анализ Раздела 2)
- Role Type: Leading/Critical/Both (Тип роли)
- Specific Achievements (Конкретные достижения)
- Comparison to Peers (Сравнение с коллегами)
- Organization Rankings/Awards (Рейтинги/награды организации)
- Organization Media Coverage (Освещение организации в СМИ)
- Recommendation Letters Available (Рекомендательные письма)
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
        """Evaluate leading role evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for leading role criterion.",
                part2_analysis="Cannot assess organization reputation without evidence.",
                evidence_summary=[],
                missing_documents=[
                    "Employment verification",
                    "Recommendation letters from employers",
                    "Organization reputation documentation",
                    "Achievement documentation",
                ],
                recommendations=[
                    "Obtain detailed recommendation letters",
                    "Document specific achievements and contributions",
                    "Include organization awards and rankings",
                    "Add media coverage of organization",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.2, 0.8)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} role(s). Manual review needed.",
            part2_analysis="Organization reputation requires verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify recommendation letters are detailed",
                "Organization reputation documentation",
                "Achievement comparisons",
            ],
            recommendations=[
                "Ensure letters describe specific contributions",
                "Add organization rankings and awards",
                "Include media coverage of organization",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for leading role criterion."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No leading role evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner has performed leading and critical roles for organizations "
            "and establishments that have distinguished reputations:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Role {i}: {ev.title}**")
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
        """Validate petition text for leading role criterion."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "leading" not in petition_text.lower() and "critical" not in petition_text.lower():
            issues.append("Missing reference to leading or critical role")

        if "distinguished" not in petition_text.lower():
            issues.append("Missing reference to distinguished reputation")

        if (
            "achievement" not in petition_text.lower()
            and "contribution" not in petition_text.lower()
        ):
            suggestions.append("Consider adding specific achievements or contributions")

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
