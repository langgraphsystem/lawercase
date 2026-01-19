"""
Membership Criterion - 8 CFR 204.5(h)(3)(ii)

Evidence of membership in associations in the field which demand
outstanding achievements of their members, as judged by recognized
national or international experts.
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


class MembershipCriterion(CriterionBase):
    """
    Criterion 2: Membership in Associations.

    8 CFR 204.5(h)(3)(ii): Evidence of membership in associations in the field
    which demand outstanding achievements of their members, as judged by
    recognized national or international experts.
    """

    CRITERION_TYPE = CriterionType.MEMBERSHIP
    CFR_REFERENCE = "8 CFR 204.5(h)(3)(ii)"
    TITLE_EN = "Membership in Associations Requiring Outstanding Achievements"
    TITLE_RU = "Членство в ассоциациях, требующих выдающихся достижений"

    PROMPT = """
# CRITERION 2: MEMBERSHIP IN ASSOCIATIONS REQUIRING OUTSTANDING ACHIEVEMENTS
## Regulatory Reference: 8 CFR 204.5(h)(3)(ii)

Evidence of membership in associations in the field which demand outstanding achievements
of their members, as judged by recognized national or international experts.

---

## PART 1: PROVE THE PETITIONER IS A MEMBER (Раздел 1)

Для определения того, что членство бенефициара соответствует этому критерию,
необходимо представить следующие документы:

- Доказательства, описывающие цели, миссию или целевое членство ассоциации
- Доказательства, подтверждающие уровень известности ассоциации в данной области
- Доказательства конкретного типа членства иностранца в ассоциациях в той области,
  для которой запрашивается классификация

### Required Documentation for Part 1:

- Membership certificate or card (Сертификат или карточка члена)
- Official letter confirming membership status (Официальное письмо о статусе членства)
- Membership ID and validity dates (Членский номер и сроки действия)

---

## PART 2: PROVE THE ASSOCIATION DEMANDS OUTSTANDING ACHIEVEMENTS (Раздел 2)

Membership requires that members have outstanding achievements in the field as judged
by recognized experts in that field.

### Required Documentation for Part 2:

- Подтверждение того, что лица, рассматривающие заявления потенциальных членов,
  признаны национальными или международными экспертами в своих дисциплинах или областях
- Раздел устава или подзаконных актов ассоциации, в котором говорится о квалификации,
  предъявляемой к экспертам, входящим в состав комиссии ассоциации по рассмотрению заявлений
- Раздел устава или подзаконных актов ассоциации, в котором обсуждаются критерии членства
- Требования принятия в ассоциацию, устав организации или документация о том, что есть
  комиссия, состоящая из профессоров/экспертов, которые отбирают претендентов
- CV или LinkedIn профили экспертов, которые отбирали заявителя в ассоциацию

---

## USCIS GUIDANCE (Пояснения):

Заявитель должен продемонстрировать, что членство в ассоциации требует выдающихся
достижений в области, для которой он претендует на классификацию, по мнению признанных
национальных или международных экспертов.

Ассоциации могут иметь несколько уровней членства. Уровень членства, предоставляемый
лицу, должен показывать, что для получения этого уровня членства признанные национальные
или международные эксперты сочли это лицо достигшим выдающихся достижений в области,
для которой требуется классификация.

### Qualifying Example (Пример соответствующего членства):

В качестве возможного примера, общее членство в международной организации специалистов
в области инженерии и технологий может НЕ соответствовать требованиям критерия. Однако,
если та же самая организация на уровне стипендиатов (Fellows) частично требует, чтобы
кандидат имел достижения, которые, например, внесли важный вклад в развитие или
применение техники, науки и технологий, и чтобы совет экспертов и комитет нынешних
стипендиатов судил о номинациях на стипендии, тот более высокий уровень стипендиата
может быть квалификационным.

Другой возможный квалификационный пример может включать членство в качестве стипендиата
(Fellow) в научном обществе, занимающемся искусственным интеллектом, если членство
основано на признании значительного и устойчивого вклада кандидата в область ИИ,
а группа нынешних стипендиатов осуществляет отбор новых членов.

### Non-Qualifying Factors (Факторы, НЕ соответствующие критерию):

Соответствующие факторы, которые могут привести к выводу о том, что членство лица в
ассоциации НЕ было основано на выдающихся достижениях в этой области, включают случаи,
когда членство лица основывалось исключительно на следующих факторах (отдельно или
в совокупности):

- Уровень образования или многолетний опыт работы в определенной области
- Оплата взноса или подписка на публикации ассоциации
- Требование, обязательное или иное, для трудоустройства по определенным профессиям,
  которое обычно наблюдается при членстве в профсоюзе или членстве в гильдии для актеров

---

## IMPORTANT NOTE (ВАЖНО):

Если в Уставах или регламентирующих документах НЕ прописаны условия вступления в
Ассоциацию, ОБЯЗАТЕЛЬНО добавляем следующие абзацы:

### Template for Selection Process Description:

"The candidate selection process for [Association Name] includes several stages to ensure
the highest standards of quality and professionalism. Candidates are required to submit
a comprehensive application detailing their qualifications, achievements, and contributions
to the industry. This application is then reviewed by a selection committee comprised
of experienced professionals and industry experts.

Candidates for membership in [Association Name] are expected to demonstrate exceptional
talents, skills, and achievements in [Client's Area of Expertise], with an emphasis on
contributions to [Client's Field]. They must possess a deep understanding of complex
systems and have a track record of innovative contributions to the industry."

---

## Evidence to Evaluate:
{evidence_list}

## Case Context:
{case_context}

---

## INSTRUCTIONS FOR ANALYSIS:

1. Verify current membership status with documentation
2. Obtain and analyze association bylaws/charter
3. Identify membership requirements and levels
4. Document who evaluates membership applications
5. Research qualifications of reviewers/judges
6. Calculate acceptance rate if available
7. List other distinguished members
8. Determine if membership is achievement-based vs. fee-based
9. Rate overall strength

## RESPONSE FORMAT:

For each membership provide:
- Organization Name and Field (Название организации и область)
- Membership Category/Level (Категория/уровень членства)
- Part 1 Analysis: Membership Documentation Status (Анализ Раздела 1)
- Part 2 Analysis: Outstanding Achievement Requirement Evidence (Анализ Раздела 2)
- Admission Requirements Description (Описание требований к приему)
- Selection Committee Composition (Состав отборочной комиссии)
- Reviewer/Judge Qualifications (Квалификация проверяющих)
- Acceptance Rate Statistics (Статистика приема)
- Other Distinguished Members (Другие выдающиеся члены)
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
        """Evaluate membership evidence."""
        if not evidence:
            return EvaluationResult(
                criterion_type=self.CRITERION_TYPE,
                strength=EvidenceStrength.INSUFFICIENT,
                score=0.0,
                part1_analysis="No evidence provided for membership criterion.",
                part2_analysis="Cannot assess if association requires outstanding achievements.",
                evidence_summary=[],
                missing_documents=[
                    "Membership certificate",
                    "Association bylaws",
                    "Selection criteria documentation",
                    "Committee member qualifications",
                ],
                recommendations=[
                    "Submit membership certificate",
                    "Provide association bylaws showing membership requirements",
                    "Include CVs of selection committee members",
                ],
            )

        prompt = self.get_prompt(evidence, case_context)
        evidence_summary = [f"{ev.title}: {ev.description}" for ev in evidence]
        score = min(len(evidence) * 0.25, 0.8)

        return EvaluationResult(
            criterion_type=self.CRITERION_TYPE,
            strength=self._calculate_strength(score),
            score=score,
            part1_analysis=f"Found {len(evidence)} membership(s). Manual review needed.",
            part2_analysis="Outstanding achievement requirements need verification.",
            evidence_summary=evidence_summary,
            missing_documents=[
                "Verify association bylaws are included",
                "Selection committee documentation",
            ],
            recommendations=[
                "Verify each membership is achievement-based",
                "Add selection committee credentials",
                "Include acceptance rate statistics",
            ],
        )

    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """Generate petition section for membership criterion."""
        if not evidence:
            return PetitionSection(
                criterion_type=self.CRITERION_TYPE,
                title=self.TITLE_EN,
                content="[No membership evidence provided]",
                attachments=[],
                word_count=0,
            )

        content_parts = [
            f"## {self.TITLE_EN}",
            f"### Regulatory Reference: {self.CFR_REFERENCE}",
            "",
            "The Petitioner is a member of the following associations which demand "
            "outstanding achievements of their members, as judged by recognized "
            "national or international experts:",
            "",
        ]

        attachments = []
        for i, ev in enumerate(evidence, 1):
            content_parts.append(f"**Membership {i}: {ev.title}**")
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
        """Validate petition text for membership criterion."""
        issues = []
        suggestions = []
        missing_elements = []

        if self.CFR_REFERENCE not in petition_text:
            missing_elements.append("CFR reference citation")

        if "outstanding" not in petition_text.lower():
            issues.append("Missing reference to 'outstanding achievements' requirement")

        if "expert" not in petition_text.lower():
            suggestions.append("Consider adding reference to expert judges/reviewers")

        if "bylaws" not in petition_text.lower() and "charter" not in petition_text.lower():
            suggestions.append("Consider referencing association bylaws or charter")

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
