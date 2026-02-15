"""
FULL EB-1A PIPELINE TEST - АВТОМАТИЧЕСКИЙ РЕЖИМ
================================================

Автоматический тест с предзаполненными данными.
Не требует интерактивного ввода.

Запуск: python full_pipeline_test_auto.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
from typing import Any
import uuid

import structlog

logger = structlog.get_logger(__name__)


class EB1APipelineTestAuto:
    """Автоматический тест pipeline EB-1A с предзаполненными данными."""

    def __init__(self, case_id: str | None = None):
        self.case_id = (
            case_id or f"AUTO_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        )

        # Output directory
        self.output_dir = Path("output/test_cases") / self.case_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Предзаполненные данные
        self.user_data = self._get_sample_user_data()
        self.case_data = self._get_sample_case_data()
        self.criteria_evidence = self._get_sample_criteria()
        self.exhibits = self._get_sample_exhibits()
        self.petition_sections = {}

    def _get_sample_user_data(self) -> dict[str, Any]:
        """Примерные данные пользователя."""
        return {
            "full_name": "Ivan Petrov",
            "email": "ivan.petrov@example.com",
            "phone": "+1-555-123-4567",
            "current_country": "Russia",
            "citizenship": "Russia",
            "date_of_birth": "1985-06-15",
            "passport_number": "AB1234567",
            "current_visa_status": "None",
            "address": {
                "street": "123 Main Street",
                "city": "Moscow",
                "state": "",
                "zip": "123456",
                "country": "Russia",
            },
        }

    def _get_sample_case_data(self) -> dict[str, Any]:
        """Примерные данные кейса."""
        return {
            "field": "Artificial Intelligence and Machine Learning",
            "specialization": "Deep Learning, Natural Language Processing",
            "years_of_experience": 12,
            "current_position": "Senior AI Research Scientist",
            "current_employer": "Leading Tech Company",
            "education_level": "PhD in Computer Science",
            "university": "Moscow State University",
            "graduation_year": "2015",
            "proposed_employer": "Self-petition",
            "proposed_position": "Independent Researcher",
        }

    def _get_sample_criteria(self) -> dict[str, Any]:
        """Примерные доказательства по критериям."""
        return {
            "awards": {
                "met": True,
                "evidence": """
- Best Paper Award at NeurIPS 2022 for groundbreaking work on transformer architectures
- Google AI Research Award 2021 ($100,000 grant)
- ACM Distinguished Paper Award at SIGKDD 2020
- IEEE Outstanding Young Researcher Award 2019
                """.strip(),
                "strength_score": 0.85,
            },
            "membership": {
                "met": True,
                "evidence": """
- ACM Fellow (requires outstanding accomplishments in computing)
- IEEE Senior Member (requires significant contributions to the field)
- Association for Computational Linguistics (ACL) - requires peer review for membership
                """.strip(),
                "strength_score": 0.75,
            },
            "published_material": {
                "met": True,
                "evidence": """
- MIT Technology Review: "Top 35 Innovators Under 35" (2021)
- Wired Magazine: Feature article "The Future of AI" (2022)
- Forbes: "30 Under 30 in Technology" (2020)
- TechCrunch: Interview on AI breakthroughs (2023)
                """.strip(),
                "strength_score": 0.70,
            },
            "judging": {
                "met": True,
                "evidence": """
- Program Committee Member, NeurIPS (2020-2024)
- Area Chair, ICML (2021-2023)
- Reviewer for Nature Machine Intelligence
- Grant reviewer for NSF AI Research Initiative
- PhD thesis examiner at Stanford University and MIT
                """.strip(),
                "strength_score": 0.90,
            },
            "original_contributions": {
                "met": True,
                "evidence": """
- Invented novel "Efficient Transformer" architecture adopted by Google, Microsoft, and Meta
- Developed breakthrough algorithm for few-shot learning cited 5,000+ times
- Created open-source library used by 50,000+ developers worldwide
- Patent holder for 3 AI-related inventions (US Patents)
- Contributions directly influenced GPT-4 and other major LLM developments
                """.strip(),
                "strength_score": 0.95,
            },
            "scholarly_articles": {
                "met": True,
                "evidence": "Published 45 peer-reviewed papers",
                "publications_count": 45,
                "citations_count": 12500,
                "h_index": 28,
                "strength_score": 0.90,
            },
            "exhibitions": {
                "met": False,
                "evidence": "",
            },
            "leading_role": {
                "met": True,
                "evidence": """
- Director of AI Research at Tech Company (100+ person team)
- Founding member of OpenAI research team (2016-2018)
- Technical Lead for Google Brain's NLP division (2018-2020)
- Advisory Board Member for AI safety organizations
                """.strip(),
                "strength_score": 0.85,
            },
            "high_salary": {
                "met": True,
                "evidence": "Annual salary: $450,000 USD (top 1% in the field)",
                "salary_amount": 450000,
                "strength_score": 0.80,
            },
            "commercial_success": {
                "met": False,
                "evidence": "",
            },
        }

    def _get_sample_exhibits(self) -> list[dict[str, Any]]:
        """Примерный список exhibits."""
        return [
            {"number": 1, "title": "Resume/Curriculum Vitae", "page": ""},
            {"number": 2, "title": "PhD Diploma from Moscow State University", "page": ""},
            {"number": 3, "title": "Employment Verification Letter - Current Employer", "page": ""},
            {"number": 4, "title": "Employment Verification Letter - Google", "page": ""},
            {"number": 5, "title": "Employment Verification Letter - OpenAI", "page": ""},
            {"number": 6, "title": "NeurIPS 2022 Best Paper Award Certificate", "page": ""},
            {"number": 7, "title": "Google AI Research Award Letter", "page": ""},
            {"number": 8, "title": "ACM Distinguished Paper Award Certificate", "page": ""},
            {"number": 9, "title": "IEEE Outstanding Young Researcher Award", "page": ""},
            {"number": 10, "title": "ACM Fellow Certificate", "page": ""},
            {"number": 11, "title": "IEEE Senior Member Certificate", "page": ""},
            {"number": 12, "title": "MIT Technology Review Article", "page": ""},
            {"number": 13, "title": "Wired Magazine Feature Article", "page": ""},
            {"number": 14, "title": "Forbes 30 Under 30 Recognition", "page": ""},
            {"number": 15, "title": "NeurIPS Program Committee Appointment Letters", "page": ""},
            {"number": 16, "title": "ICML Area Chair Confirmation", "page": ""},
            {
                "number": 17,
                "title": "Nature Machine Intelligence Reviewer Confirmation",
                "page": "",
            },
            {"number": 18, "title": "List of Publications with Citation Counts", "page": ""},
            {"number": 19, "title": "Google Scholar Profile Screenshot", "page": ""},
            {"number": 20, "title": "Patent Certificates (3 US Patents)", "page": ""},
            {
                "number": 21,
                "title": "Recommendation Letter - Prof. John Smith (Stanford)",
                "page": "",
            },
            {"number": 22, "title": "Recommendation Letter - Prof. Jane Doe (MIT)", "page": ""},
            {
                "number": 23,
                "title": "Recommendation Letter - Dr. Bob Wilson (Google AI)",
                "page": "",
            },
            {"number": 24, "title": "Salary Documentation and Tax Returns", "page": ""},
            {
                "number": 25,
                "title": "Bureau of Labor Statistics Data on Salary Percentiles",
                "page": "",
            },
            {"number": 26, "title": "Passport Copy", "page": ""},
        ]

    def generate_petition_sections(self) -> dict[str, str]:
        """Генерация секций petition letter."""
        name = self.user_data.get("full_name", "Beneficiary")
        field = self.case_data.get("field", "Sciences")

        sections = {}

        # SUMMARY
        met_criteria = [k for k, v in self.criteria_evidence.items() if v.get("met", False)]

        sections["summary"] = f"""
This petition is filed on behalf of {name}, an individual of extraordinary ability in the field of {field}.

The beneficiary has achieved sustained national and international acclaim and is among the small percentage who have risen to the very top of the field. {name} satisfies {len(met_criteria)} of the 10 regulatory criteria for extraordinary ability, significantly exceeding the minimum requirement of 3 criteria.

The evidence demonstrates extraordinary ability through:
- Major nationally and internationally recognized awards in the field
- Membership in associations requiring outstanding achievements
- Published material about the beneficiary's work in major media
- Participation as a judge of the work of others
- Original contributions of major significance to the field
- Authorship of scholarly articles in professional journals
- Performance in leading or critical roles for distinguished organizations
- Command of a high salary relative to others in the field

Based on the totality of the evidence, USCIS should find that {name} has extraordinary ability in {field} and qualifies for classification under INA section 203(b)(1)(A).
        """.strip()

        # AWARDS
        awards_data = self.criteria_evidence.get("awards", {})
        sections["awards"] = (
            f"""
The beneficiary has received nationally and internationally recognized awards for excellence in the field of {field}.

{awards_data.get('evidence', 'N/A')}

These awards represent recognition at the highest levels of the field and demonstrate that {name} has achieved sustained national and international acclaim.
        """.strip()
            if awards_data.get("met")
            else "[Not applicable]"
        )

        # MEMBERSHIP
        membership_data = self.criteria_evidence.get("membership", {})
        sections["membership"] = (
            f"""
The beneficiary holds membership in associations that require outstanding achievements of their members, as judged by recognized national or international experts.

{membership_data.get('evidence', 'N/A')}

These memberships demonstrate peer recognition of the beneficiary's extraordinary contributions to the field.
        """.strip()
            if membership_data.get("met")
            else "[Not applicable]"
        )

        # PUBLISHED MATERIAL (PRESS)
        press_data = self.criteria_evidence.get("published_material", {})
        sections["press"] = (
            f"""
Published material in professional or major trade publications or major media about the beneficiary and the beneficiary's work in the field.

{press_data.get('evidence', 'N/A')}

This media coverage demonstrates that {name}'s work has garnered significant attention and recognition beyond the academic community.
        """.strip()
            if press_data.get("met")
            else "[Not applicable]"
        )

        # JUDGING
        judging_data = self.criteria_evidence.get("judging", {})
        sections["judging"] = (
            f"""
The beneficiary has participated as a judge of the work of others in the field, either individually or on a panel.

{judging_data.get('evidence', 'N/A')}

This extensive judging experience demonstrates that {name} is recognized as an authority whose expertise is sought to evaluate the work of others in {field}.
        """.strip()
            if judging_data.get("met")
            else "[Not applicable]"
        )

        # ORIGINAL CONTRIBUTIONS
        contributions_data = self.criteria_evidence.get("original_contributions", {})
        sections["contributions"] = (
            f"""
The beneficiary has made original scientific, scholarly, or artistic contributions of major significance in the field.

{contributions_data.get('evidence', 'N/A')}

These contributions have had a demonstrable impact on the field and have been widely adopted and recognized by the scientific community.
        """.strip()
            if contributions_data.get("met")
            else "[Not applicable]"
        )

        # SCHOLARLY ARTICLES
        scholarly_data = self.criteria_evidence.get("scholarly_articles", {})
        if scholarly_data.get("met"):
            pubs = scholarly_data.get("publications_count", 0)
            cites = scholarly_data.get("citations_count", 0)
            h_idx = scholarly_data.get("h_index", 0)
            sections["scholarly"] = f"""
The beneficiary is the author of scholarly articles in professional journals or other major media in the field.

Publication metrics:
- Total peer-reviewed publications: {pubs}
- Total citations: {cites:,}
- H-index: {h_idx}

These metrics place {name} in the top tier of researchers in {field}, demonstrating significant scholarly impact and influence.
            """.strip()
        else:
            sections["scholarly"] = "[Not applicable]"

        # EXHIBITIONS
        sections["exhibitions"] = "[Not applicable - criterion not claimed]"

        # LEADING ROLE
        leading_data = self.criteria_evidence.get("leading_role", {})
        sections["leading_role"] = (
            f"""
The beneficiary has performed in a leading or critical role for organizations or establishments that have a distinguished reputation.

{leading_data.get('evidence', 'N/A')}

In these leadership positions, {name} has directed strategic initiatives, managed large research teams, and made decisions that significantly impacted these organizations' direction in {field}.
        """.strip()
            if leading_data.get("met")
            else "[Not applicable]"
        )

        # HIGH SALARY
        salary_data = self.criteria_evidence.get("high_salary", {})
        if salary_data.get("met"):
            salary = salary_data.get("salary_amount", 0)
            sections["salary"] = f"""
The beneficiary commands a high salary or other significantly high remuneration for services, in relation to others in the field.

Current compensation: ${salary:,} USD annually

According to Bureau of Labor Statistics data, this salary places {name} in the top 1% of earners in {field}. The median salary for similar positions is approximately $150,000, meaning the beneficiary earns approximately 3x the median.

This exceptional compensation reflects the high value that employers place on {name}'s extraordinary expertise and contributions.
            """.strip()
        else:
            sections["salary"] = "[Not applicable]"

        # COMMERCIAL SUCCESS
        sections["commercial"] = "[Not applicable - criterion not claimed]"

        # FINAL MERITS
        sections["final_merits"] = f"""
Based on the totality of the evidence presented, {name} has demonstrated extraordinary ability in {field}.

The beneficiary satisfies {len(met_criteria)} of the 10 regulatory criteria:
{chr(10).join(f'- {c.replace("_", " ").title()}' for c in met_criteria)}

This significantly exceeds the minimum requirement of meeting 3 criteria.

The evidence shows that {name} has:
1. Received sustained national and international acclaim
2. Achieved recognition that demonstrates extraordinary ability
3. Risen to the very top of the field of {field}

The beneficiary's achievements include major awards, elite memberships, extensive media coverage, significant judging responsibilities, groundbreaking original contributions, highly-cited scholarly publications, leadership of distinguished organizations, and exceptional compensation.

USCIS should find that {name} meets the requirements for extraordinary ability classification under INA section 203(b)(1)(A).
        """.strip()

        # NATIONAL IMPORTANCE
        sections["national_importance"] = f"""
{name}'s continued work in the United States will substantially benefit prospectively the United States.

The beneficiary's expertise in {field} addresses critical needs:

1. NATIONAL SECURITY: AI and machine learning are essential to U.S. national security and competitiveness.

2. ECONOMIC BENEFIT: The beneficiary's innovations have generated significant economic value through commercialization and efficiency improvements.

3. SCIENTIFIC ADVANCEMENT: {name}'s research pushes the boundaries of {field}, maintaining American leadership in this critical technology area.

4. WORKFORCE DEVELOPMENT: Through mentorship and collaboration, the beneficiary helps train the next generation of American AI researchers.

5. GLOBAL COMPETITIVENESS: Retaining top talent like {name} is essential as other nations invest heavily in AI research.

The United States has a strong national interest in having {name} continue this important work within its borders.
        """.strip()

        return sections

    async def generate_pdf_package(self) -> str:
        """Генерация PDF пакета."""
        print("\n[STEP 6] GENERATING PDF PACKAGE")
        print("-" * 60)

        try:
            from core.services.pdf_package_generator import PDFPackageGenerator

            generator = PDFPackageGenerator(output_dir=str(self.output_dir))

            print("Generating PDF components:")
            print("  - Cover page (LaTeX)")
            print("  - Form G-1145")
            print("  - Form I-140")
            print("  - Form I-907 (Premium Processing)")
            print("  - Passport placeholder")
            print("  - Petition Letter (LaTeX)")
            print("  - Statement of Intent (LaTeX)")
            print("  - Exhibits List (LaTeX)")

            result = await generator.generate_package(
                case_id=self.case_id,
                case_data=self.case_data,
                user_data=self.user_data,
                petition_sections=self.petition_sections,
                exhibits=self.exhibits,
                include_premium=True,
                include_attorney=False,
            )

            print(f"\n✓ PDF package created: {result}")
            return result

        except ImportError as e:
            print(f"✗ Could not import PDFPackageGenerator: {e}")
            return await self.generate_pdf_fallback()
        except Exception as e:
            print(f"✗ Error generating PDF: {e}")
            import traceback

            traceback.print_exc()
            return await self.generate_pdf_fallback()

    def generate_case_site(self) -> str:
        """Генерация интерактивного сайта для кейса."""
        print("\n[STEP 6a] GENERATING CASE WEBSITE")
        print("-" * 60)

        try:
            from core.services.case_site_generator import CaseSiteGenerator

            generator = CaseSiteGenerator()

            # Подготовка exhibits для сайта (по табам)
            exhibits_by_tab = {
                "A": [],  # Identity
                "B": [],  # Awards
                "C": [],  # Membership
                "D": [],  # Press
                "E": [],  # Judging
                "F": [],  # Contributions
                "G": [],  # Articles
                "H": [],  # Leading Role
                "I": [],  # Salary
                "J": [],  # Other
            }

            # Распределяем exhibits по табам
            for exhibit in self.exhibits:
                title = exhibit.get("title", "").lower()
                if (
                    "passport" in title
                    or "resume" in title
                    or "cv" in title
                    or "credential" in title
                ):
                    exhibits_by_tab["A"].append(exhibit)
                elif "award" in title:
                    exhibits_by_tab["B"].append(exhibit)
                elif "member" in title or "fellow" in title:
                    exhibits_by_tab["C"].append(exhibit)
                elif "press" in title or "review" in title or "forbes" in title or "wired" in title:
                    exhibits_by_tab["D"].append(exhibit)
                elif "committee" in title or "reviewer" in title:
                    exhibits_by_tab["E"].append(exhibit)
                elif "patent" in title:
                    exhibits_by_tab["F"].append(exhibit)
                elif "publication" in title or "scholar" in title or "article" in title:
                    exhibits_by_tab["G"].append(exhibit)
                elif "recommendation" in title or "letter" in title:
                    exhibits_by_tab["H"].append(exhibit)
                elif "salary" in title or "labor" in title:
                    exhibits_by_tab["I"].append(exhibit)
                else:
                    exhibits_by_tab["J"].append(exhibit)

            site_path = generator.generate_site(
                case_id=self.case_id,
                case_data=self.case_data,
                user_data=self.user_data,
                petition_sections=self.petition_sections,
                exhibits=exhibits_by_tab,
            )

            print(f"  ✓ Site generated: {site_path}")
            print("  Pages created:")
            print("    - index.html (Dashboard)")
            print("    - forms/index.html (USCIS Forms)")
            print("    - petition/index.html (Petition Letter)")
            print("    - exhibits/index.html (Evidence Tabs)")

            # Создаём локальную ссылку
            local_url = f"file:///{Path(site_path).absolute().as_posix()}/index.html"
            print(f"\n  🌐 Open in browser: {local_url}")

            return site_path

        except Exception as e:
            print(f"  ✗ Site generation failed: {e}")
            import traceback

            traceback.print_exc()
            return ""

    async def generate_pdf_fallback(self) -> str:
        """Fallback: генерация через LaTeX напрямую."""
        print("\nUsing fallback LaTeX generation...")

        try:
            from core.services.latex_generator import LaTeXGenerator

            latex = LaTeXGenerator()
            name = self.user_data.get("full_name", "Beneficiary")
            field = self.case_data.get("field", "Sciences")

            # Cover page
            try:
                cover = latex.generate_cover_page(
                    output_path=self.output_dir / "cover_page.pdf",
                    name=name,
                    include_premium=True,
                )
                print(f"  ✓ Cover page: {cover}")
            except Exception as e:
                print(f"  ✗ Cover page failed: {e}")

            # Petition letter
            try:
                petition = latex.generate_petition_letter(
                    output_path=self.output_dir / "petition_letter.pdf",
                    name=name,
                    field=field,
                    sections=self.petition_sections,
                )
                print(f"  ✓ Petition letter: {petition}")
            except Exception as e:
                print(f"  ✗ Petition letter failed: {e}")

            # Statement of intent
            try:
                statement = latex.generate_statement_of_intent(
                    output_path=self.output_dir / "statement.pdf",
                    name=name,
                    field=field,
                )
                print(f"  ✓ Statement: {statement}")
            except Exception as e:
                print(f"  ✗ Statement failed: {e}")

            # Exhibits list
            try:
                exhibits = latex.generate_exhibits_list(
                    output_path=self.output_dir / "exhibits_list.pdf",
                    name=name,
                    exhibits=self.exhibits,
                )
                print(f"  ✓ Exhibits list: {exhibits}")
            except Exception as e:
                print(f"  ✗ Exhibits list failed: {e}")

            return str(self.output_dir)

        except Exception as e:
            print(f"LaTeX fallback failed: {e}")
            return ""

    def save_case_data(self) -> Path:
        """Сохранение данных в JSON."""
        print("\n[STEP 7] SAVING CASE DATA")
        print("-" * 60)

        case_file = self.output_dir / f"{self.case_id}_data.json"

        full_data = {
            "case_id": self.case_id,
            "created_at": datetime.now().isoformat(),
            "user_data": self.user_data,
            "case_data": self.case_data,
            "criteria_evidence": self.criteria_evidence,
            "exhibits": self.exhibits,
            "petition_sections": self.petition_sections,
        }

        with open(case_file, "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Case data saved: {case_file}")
        return case_file

    async def run(self) -> dict[str, Any]:
        """Запуск полного pipeline."""
        print("=" * 80)
        print("EB-1A FULL PIPELINE TEST - AUTOMATIC MODE".center(80))
        print("=" * 80)
        print()
        print(f"Case ID: {self.case_id}")
        print(f"Output:  {self.output_dir}")
        print()

        # Step 1-4: Данные уже предзаполнены
        print("[STEP 1-4] USING PRE-FILLED DATA")
        print("-" * 60)
        print(f"  Beneficiary: {self.user_data.get('full_name')}")
        print(f"  Field: {self.case_data.get('field')}")

        met_criteria = [k for k, v in self.criteria_evidence.items() if v.get("met", False)]
        print(f"  Criteria met: {len(met_criteria)}/10")
        print(f"  Met: {', '.join(met_criteria)}")
        print(f"  Exhibits: {len(self.exhibits)}")

        # Step 5: Генерация секций
        print("\n[STEP 5] GENERATING PETITION SECTIONS")
        print("-" * 60)
        self.petition_sections = self.generate_petition_sections()
        print(f"  Generated {len(self.petition_sections)} sections")
        for key in self.petition_sections:
            length = len(self.petition_sections[key])
            print(f"    - {key}: {length} chars")

        # Step 6: PDF генерация
        pdf_result = await self.generate_pdf_package()

        # Step 6a: Генерация сайта
        site_path = self.generate_case_site()

        # Step 7: Сохранение
        json_file = self.save_case_data()

        # Итог
        print("\n" + "=" * 80)
        print("SUMMARY".center(80))
        print("=" * 80)
        print()
        print(f"Case ID:          {self.case_id}")
        print(f"Beneficiary:      {self.user_data.get('full_name')}")
        print(f"Field:            {self.case_data.get('field')}")
        print(f"Criteria Met:     {len(met_criteria)}/10")
        print(f"Exhibits:         {len(self.exhibits)}")
        print(f"Output Directory: {self.output_dir}")
        print(f"JSON Data:        {json_file}")
        print(f"PDF Package:      {pdf_result}")
        print(f"Case Website:     {site_path}")
        print()

        if len(met_criteria) >= 3:
            print("✓ CANDIDATE IS POTENTIALLY ELIGIBLE FOR EB-1A!")
        else:
            print(f"✗ Insufficient criteria ({len(met_criteria)}/3)")

        # Показываем URL для открытия в браузере
        if site_path:
            site_url = f"file:///{Path(site_path).absolute().as_posix()}/index.html"
            print("\n🌐 Open site in browser:")
            print(f"   {site_url}")

        print("\n" + "=" * 80)
        print("TEST COMPLETED".center(80))
        print("=" * 80)

        return {
            "case_id": self.case_id,
            "output_dir": str(self.output_dir),
            "json_file": str(json_file),
            "pdf_result": pdf_result,
            "site_path": site_path,
            "criteria_met": len(met_criteria),
        }


async def main():
    """Main entry point."""
    pipeline = EB1APipelineTestAuto()
    result = await pipeline.run()
    return result


if __name__ == "__main__":
    print()
    try:
        result = asyncio.run(main())
        print(f"\nResult: {json.dumps(result, indent=2)}")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
