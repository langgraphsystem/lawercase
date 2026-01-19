"""
National Benefit Documentation

Documentation to establish that the beneficiary's entry will substantially
benefit prospectively the United States.
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


class NationalBenefitDocumentation(CriterionBase):
    """
    Documentation to Establish National Benefit.

    This is a required supporting documentation section for EB-1A petitions,
    demonstrating that the beneficiary's entry will substantially benefit
    prospectively the United States.
    """

    CRITERION_TYPE = CriterionType.COMPARABLE_EVIDENCE  # Using as placeholder
    CFR_REFERENCE = "8 CFR 204.5(h)(5)"
    TITLE_EN = "Documentation of Substantial Benefit to the United States"
    TITLE_RU = "Документация о существенной пользе для Соединенных Штатов"

    PROMPT = """
# DOCUMENTATION TO ESTABLISH THAT THE BENEFICIARY'S ENTRY WILL SUBSTANTIALLY BENEFIT PROSPECTIVELY THE UNITED STATES

---

## PURPOSE:

Необходимо показать, каким образом въезд бенефициара принесет существенную пользу
Соединенным Штатам в перспективе.

В петиции не указано, что въезд бенефициара принесет существенную пользу Соединенным
Штатам в перспективе. Пожалуйста, представьте доказательства того, что въезд бенефициара
принесет существенную пользу Соединенным Штатам в перспективе.

---

## REQUIRED DOCUMENTATION:

Доказательства, которые могут быть представлены для удовлетворения этого требования,
включают, но не ограничиваются ими:

### Letters from Employers/Professionals:
- Письма от нынешних или потенциальных работодателей
- Письма от лиц, работающих в сфере деятельности бенефициара

### Evidence of National Interest:
- Другие доказательства, объясняющие, как работа бенефициара будет выгодна и полезна
  для интересов Соединенных Штатов **на национальном уровне**

### Personal Statement:
- Заявление от бенефициара с подробным описанием планов о том, как его работа
  в перспективе принесет существенную пользу Соединенным Штатам

---

## OVERLAP WITH FUTURE WORK SECTION:

В данному критерию можно повторить:

- **Job Offers** - если клиент планирует работать по найму
- **Трудовые договоры**
- **Business Plan** - если клиент планирует открывать компанию
- **Письма о заинтересованности**
- **Заявление бенефициара** с подробным описанием планов по продолжению работы в США

---

## IMPORTANT NOTES (ВАЖНО):

### Consistency with EB2 NIW:
Если у клиента есть кейс EB2 NIW, то часть Area of expertise в части Business Plan
или планов на будущее нужно перенести и сюда.

**То есть планы на будущее в двух кейсах должны быть идентичными в EB1 и в EB2 NIW.**

### RFE Prevention:
Поскольку практически во всех RFE офицеры запрашивают доказательства того, что клиент
продолжит свою деятельность на территории США, в этой части EB1 прикладываем
Job Offers либо Business Plan.

---

## TYPES OF NATIONAL BENEFIT:

### Economic Benefits (Экономические выгоды):
- **Job Creation** - создание рабочих мест для граждан США
- **Tax Contributions** - уплата налогов в бюджет США
- **Business Revenue** - генерация дохода и рост экономики
- **Investment** - привлечение инвестиций
- **Export Growth** - рост экспорта

### Industry/Field Benefits (Отраслевые выгоды):
- **Innovation** - внедрение инноваций в отрасль
- **Knowledge Transfer** - передача знаний и опыта
- **Industry Development** - развитие отрасли
- **Competition Enhancement** - усиление конкуренции

### Social Benefits (Социальные выгоды):
- **Community Service** - служение обществу
- **Education** - образовательный вклад
- **Healthcare** - вклад в здравоохранение
- **Environmental Protection** - защита окружающей среды
- **Cultural Enrichment** - культурное обогащение

### Research/Academic Benefits (Научные выгоды):
- **Research Advancement** - развитие научных исследований
- **Publications** - публикации в научных журналах
- **Patents** - получение патентов
- **Technology Development** - разработка технологий

---

## EVIDENCE EXAMPLES:

### For Entrepreneurs:
- Tax returns showing tax payments
- Payroll records showing job creation
- Business growth metrics
- Letters from employees
- Economic impact studies
- Partnership with US companies

### For Employees:
- Letters from employers about value
- Letters from colleagues about contributions
- Project outcomes and impact
- Industry recognition
- Company growth attributable to beneficiary

### For Artists/Performers:
- Letters from venues/galleries
- Ticket sales and attendance records
- Media coverage of cultural impact
- Awards and recognition
- Educational programs

### For Academics/Researchers:
- Research impact statements
- Citation metrics
- Grant funding brought to US institutions
- Student mentorship records
- Collaboration with US researchers

---

## KEY PHRASES FOR PETITION:

При написании этого раздела используйте следующие ключевые фразы:

- "will substantially benefit the United States"
- "in the national interest"
- "economic contribution"
- "job creation"
- "tax contributions"
- "industry advancement"
- "knowledge transfer"
- "cultural enrichment"
- "prospectively benefit"

---

## GOVERNMENT SUPPORT:

Цитаты от государственных лиц могут усилить аргументацию. Например:

Vice President Harris stated regarding small businesses:
> "Our small businesses in the United States actually employ almost half of the workforce
> that is not in public work in the government. So, we're talking about a gigantic, huge
> workforce that is contributing to the economy, paying taxes, and doing the work that
> is about strengthening our economy and, by extension, our country."

---

## QUANTIFIABLE METRICS:

При возможности приведите количественные показатели:

- **Revenue/Sales**: $XXX,XXX в год
- **Jobs Created**: X рабочих мест
- **Tax Payments**: $XX,XXX в налогах
- **Growth Rate**: X% рост за период
- **Clients Served**: X клиентов
- **Projects Completed**: X проектов

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Identify all evidence of national benefit
2. Categorize benefits: economic, social, industry, research
3. Document quantifiable metrics where available
4. Review letters from employers/professionals
5. Assess job creation evidence
6. Review tax payment documentation
7. Evaluate industry impact evidence
8. Check consistency with EB2 NIW case (if exists)
9. Rate overall strength of evidence

## RESPONSE FORMAT:

For national benefit documentation provide:
- Primary Benefit Type: Economic/Social/Industry/Research (Тип основной пользы)
- Jobs Created/Planned (Созданные/планируемые рабочие места)
- Tax Contributions (documented) (Налоговые взносы)
- Revenue/Business Growth (Доход/рост бизнеса)
- Industry Impact Description (Влияние на отрасль)
- Letters of Support Count (Количество писем поддержки)
- Quantifiable Metrics (Количественные показатели)
- Social/Community Impact (Социальное воздействие)
- Environmental Considerations (Экологические соображения)
- Consistency with EB2 NIW (if applicable) (Соответствие с EB2 NIW)
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
        """Evaluate national benefit documentation."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No national benefit documentation provided.",
                part2_analysis="Cannot assess national benefit without evidence.",
                evidence_summary=[],
                missing_documents=[
                    "Letters from employers or professionals",
                    "Evidence of economic contribution",
                    "Tax payment documentation",
                    "Job creation evidence",
                    "Personal statement of national benefit",
                ],
                recommendations=[
                    "Submit letters explaining benefit to US",
                    "Provide tax returns showing contributions",
                    "Document job creation if applicable",
                    "Include personal statement of planned benefits",
                    "Add quantifiable metrics where possible",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.2, 0.85)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} national benefit document(s). Manual review needed.",
            part2_analysis="National benefit claims require verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify quantifiable benefit metrics",
                "Check for tax documentation",
                "Verify job creation claims",
            ],
            recommendations=[
                "Add more specific benefit metrics",
                "Include tax returns if available",
                "Document job creation with payroll records",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for national benefit documentation."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No national benefit documentation provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            "",
            "The Petitioner's entry will substantially benefit prospectively the United States, "
            "as demonstrated by the following evidence:",
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

        content_parts.append("")
        content_parts.append(
            "Thus, the evidence demonstrates that the Petitioner's entry would have "
            "substantial benefits for the United States."
        )

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
        """Validate petition text for national benefit documentation."""
        issues = []
        suggestions = []
        missing_elements = []

        if "benefit" not in petition_text.lower():
            issues.append("Missing reference to benefit")

        if "united states" not in petition_text.lower() and "u.s." not in petition_text.lower():
            issues.append("Missing reference to United States")

        if "substantial" not in petition_text.lower() and "prospective" not in petition_text.lower():
            suggestions.append("Consider using 'substantially benefit prospectively' language")

        if "economic" not in petition_text.lower() and "job" not in petition_text.lower():
            suggestions.append("Consider mentioning economic benefits or job creation")

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
