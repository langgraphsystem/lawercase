"""
High Salary Criterion - 8 CFR 204.5(h)(3)(ix)

Evidence that the beneficiary has commanded a high salary or other significantly
high remuneration for services, in relation to others in the field.
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


class HighSalaryCriterion(CriterionBase):
    """
    Criterion 9: High Salary or Other Significantly High Remuneration.

    8 CFR 204.5(h)(3)(ix): Evidence that the beneficiary has commanded a high salary
    or other significantly high remuneration for services, in relation to others
    in the field.
    """

    CRITERION_TYPE = CriterionType.HIGH_SALARY
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(ix)"
    TITLE_EN = "High Salary or Significantly High Remuneration"
    TITLE_RU = "Высокая заработная плата или высокое вознаграждение"

    PROMPT = """
# CRITERION 9: HIGH SALARY OR SIGNIFICANTLY HIGH REMUNERATION
## Regulatory Reference: 8 CFR 204.5(h)(3)(ix)

Evidence that the beneficiary has commanded a high salary or other significantly
high remuneration for services, in relation to others in the field.

---

## PART 1: PROVE THE SALARY/REMUNERATION (Раздел 1)

В первом разделе доказываем, была ли зарплата или вознаграждение высокой:
- Справка о зарплате
- Налоговые декларации
- Другие документы, подтверждающие доход

---

## PART 2: PROVE IT'S HIGH COMPARED TO OTHERS (Раздел 2)

Во втором разделе доказываем, является ли зарплата или вознаграждение человека
высокими по сравнению с компенсацией, выплачиваемой другим работающим в этой области.

**Конечно же все, что касается денег познается в сравнении, но в сравнении с местностью
где находится объект исследования.** Поэтому сравнивать зарплату необходимо с
официальной статистикой того региона, где живет наш претендент.

---

## REQUIRED DOCUMENTATION:

Чтобы помочь определить, что зарплата или вознаграждение бенефициара высоки по
сравнению с другими людьми, работающими в данной области, заявитель может представить:

1. **Копии форм W-2 или 1099** бенефициара за годы, в которые бенефициар получал
   высокую зарплату в данной сфере деятельности
   - В качестве альтернативы заявитель может предоставить аналогичные иностранные
     налоговые документы, подтверждающие годовую зарплату, полученную за пределами США

2. **Сообщения СМИ** о заметно высоких зарплатах, получаемых другими людьми в сфере
   деятельности бенефициара

3. **Составленный авторитетной профессиональной организацией список** самых
   высокооплачиваемых специалистов в данной области

4. **Географические или соответствующие должности исследования компенсаций**

5. **Обоснования организации** для выплаты зарплаты выше данных о компенсации

6. **Информация из Министерства труда США или аналогичных источников**, показывающая
   сравнение зарплат внутри штатов, между штатами и т.д.

---

## USCIS INTERPRETATION ON "COMMANDED":

USCIS не интерпретирует фразу «приказал» как означающую, что человек уже должен был
получить такую зарплату или вознаграждение, чтобы соответствовать критерию.

**Скорее, заслуживающий доверия контракт или предложение о работе**, показывающее
предполагаемую зарплату или вознаграждение, может доказать, что человек имел
возможность претендовать на такую компенсацию.

---

## EVIDENCE TYPES:

Доказательства, подтверждающие высокое вознаграждение, могут включать:

- Налоговые декларации, отчеты о заработной плате или другие доказательства
  прошлой зарплаты или вознаграждения за услуги
- Контракт, письмо с предложением о работе или другие доказательства
  предполагаемой зарплаты или вознаграждения за услуги
- Сравнительные данные о заработной плате или вознаграждении для сферы деятельности
  человека (географические исследования или исследования компенсаций)

---

## USCIS GUIDANCE ON COMPARISON (Пояснения):

### Useful Resources:
- Веб-страница Бюро статистики труда (BLS) с обзором данных BLS о заработной плате
  по регионам и профессиям
- Веб-сайт Career One Stop Министерства труда

### Important Considerations:

1. **Описание занятия**: Широкие описания, включающие несколько профессий или
   несколько отраслей, могут не обеспечить точного сравнения с другими в этой области

2. **Валидность опроса**: Некоторые веб-сайты предоставляют данные о заработной плате,
   сообщаемые пользователями, которые могут быть недопустимыми для сравнения

3. **Местоположение и валюта**: Офицеры оценивают людей, работающих за пределами США,
   на основе статистики заработной платы, относящихся к соответствующему месту работы,
   а не просто конвертируя зарплату в доллары США

4. **Размер заработной платы**: Офицеры учитывают, измеряют ли сравнительные данные
   почасовую ставку или годовую зарплату

---

## IMPORTANT NOTES (ВАЖНО):

### On DOL Data:
Информация Министерства труда США о преобладающих ставках заработной платы сама по себе,
как правило, **не позволяет установить**, является ли зарплата или иное вознаграждение
"значительно" выше, чем у других сотрудников в данной области.

Если информация о преобладающей ставке заработной платы Министерства труда США
представлена, она **должна сопровождаться другими подтверждающими доказательствами**.

### On W-2/1099 Forms:
Касательно форм W-2 или 1099, как указано в Руководстве USCIS **не получится**
предоставить доказательства поскольку зарплата по ним маленькая. Для сравнения лучше
брать заработную плату в своей сфере до заезда в США.

### On Salary Certificate Position:
Информация о зарплате, которая дается в виде справки – должность клиента должна
указываться как в области его Area of expertise, поскольку Officer USCIS может не принять.

**Пример проблемы**: Клиентка работала в казахстанской компании на позиции Fuel Engineer
(в Справке о заработной плате указано Fuel Engineer), Area of expertise клиентки в I-140
Petroleum engineer, статистика о средней зарплате по стране для сравнения бралась по
Petroleum Engineer. В RFE Officer указал, что это две разные позиции и НЕ принял доказательства.

**Решение**: В BLS либо DOL найти функциональные обязанности и сопоставить их через
сравнение, либо получить письмо от кадровиков, в котором указывается сфера экспертности.

### On Periods:
Периоды, указываемые в справке о заработной плате: 1 месяц, 3 месяца, 6 месяцев либо год.
Если в справке указывается заработная плата за последние три года, то мы не можем брать
информацию по заработной плате меньше, чем за год.

Периоды должны быть идентичными (например, справка или декларация за 2022 год →
для сравнения используем статданные за 2022 год).

### Currency Conversion:
**Конвертация валют обязательна.**

### For Freelancers:
По фрилансерам не будет справки о заработной плате, у них услуги оказываются по контрактам.
Клиент может получить письмо от компании, в котором будет указан контракт на определенную
сумму с указанием периода выполнения работы.

---

## For Entrepreneurs:
При сравнении доходов компании клиента с доходами других компаний можно использовать
анализ финансовых показателей компаний, аналогичных по основной деятельности и региону.

В отношении предпринимателей или основателей стартапов офицеры рассматривают доказательства
того, что бизнес получил значительное финансирование от государственных органов, фондов
венчурного капитала, инвесторов-ангелов при оценке достоверности представленных контрактов.

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Document salary/remuneration with official records
2. Identify appropriate comparison statistics
3. Match job position with correct occupational category
4. Convert currency if salary is from outside US
5. Ensure comparison periods align
6. Calculate multiple (e.g., 1.3x, 2x higher than average)
7. Address any job title mismatches
8. Include regional and industry context
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For salary/remuneration evidence provide:
- Position/Title (Должность)
- Employer/Company (Работодатель/Компания)
- Salary Period (Период заработной платы)
- Documented Salary Amount (Задокументированная сумма)
- Currency and Conversion (Валюта и конвертация)
- Part 1 Analysis: Salary Documentation (Анализ Раздела 1)
- Part 2 Analysis: Comparison Evidence (Анализ Раздела 2)
- Comparison Source (Источник сравнения)
- Average/Median in Field (Средняя/Медианная по отрасли)
- Multiple Above Average (Во сколько раз выше среднего)
- Geographic Region of Comparison (Регион сравнения)
- Job Title Alignment Check (Проверка соответствия должности)
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
        """Evaluate high salary evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for high salary criterion.",
                part2_analysis="Cannot assess salary comparison without documentation.",
                evidence_summary=[],
                missing_documents=[
                    "Salary documentation (W-2, tax returns, certificates)",
                    "Industry salary comparison statistics",
                    "Regional wage data",
                    "Currency conversion if applicable",
                ],
                recommendations=[
                    "Submit salary certificates or tax documents",
                    "Provide BLS or DOL comparison statistics",
                    "Include currency conversion if non-US salary",
                    "Match job title with occupational category",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.25, 0.8)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} salary document(s). Manual review needed.",
            part2_analysis="Salary comparison requires verification against statistics.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify comparison statistics are included",
                "Job title alignment documentation",
                "Currency conversion if needed",
            ],
            recommendations=[
                "Ensure job title matches occupational category",
                "Include regional/industry comparison data",
                "Add currency conversion calculation",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for high salary criterion."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No high salary evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner has commanded a high salary in relation to others in the field, "
            "as evidenced by the following documentation:",
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
        """Validate petition text for high salary criterion."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "high" not in petition_text.lower() or "salary" not in petition_text.lower():
            issues.append("Missing reference to high salary")

        if "comparison" not in petition_text.lower() and "average" not in petition_text.lower():
            issues.append("Missing comparison to others in the field")

        if "statistic" not in petition_text.lower() and "bls" not in petition_text.lower():
            suggestions.append("Consider citing specific statistical sources")

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
