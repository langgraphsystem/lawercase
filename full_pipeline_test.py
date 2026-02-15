"""
FULL EB-1A PIPELINE TEST - От создания кейса до PDF
=====================================================

Этот скрипт позволяет протестировать весь pipeline:
1. Создание кейса
2. Интерактивный сбор данных (intake)
3. Анализ критериев EB-1A
4. Генерация petition letter
5. Создание финального PDF через LaTeX

Запуск: python full_pipeline_test.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
from typing import Any
import uuid


# Цвета для терминала
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")


def print_step(step_num: int, text: str):
    print(f"{Colors.CYAN}[ШАГ {step_num}]{Colors.ENDC} {Colors.BOLD}{text}{Colors.ENDC}")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")


def print_question(text: str):
    print(f"{Colors.YELLOW}? {text}{Colors.ENDC}")


class EB1APipelineTest:
    """Полный тест pipeline EB-1A петиции."""

    def __init__(self):
        self.case_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.user_data: dict[str, Any] = {}
        self.case_data: dict[str, Any] = {}
        self.criteria_evidence: dict[str, Any] = {}
        self.petition_sections: dict[str, str] = {}
        self.exhibits: list[dict[str, Any]] = []

        # Output directory
        self.output_dir = Path("output/test_cases") / self.case_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_input(self, prompt: str, default: str = "") -> str:
        """Получить ввод от пользователя."""
        if default:
            result = input(f"{prompt} [{default}]: ").strip()
            return result if result else default
        return input(f"{prompt}: ").strip()

    def get_multiline_input(self, prompt: str) -> str:
        """Получить многострочный ввод (заканчивается пустой строкой)."""
        print(f"{prompt}")
        print(f"{Colors.YELLOW}(Введите текст, пустая строка для завершения){Colors.ENDC}")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        return "\n".join(lines)

    def get_yes_no(self, prompt: str, default: bool = False) -> bool:
        """Да/Нет вопрос."""
        default_str = "да" if default else "нет"
        result = input(f"{prompt} (да/нет) [{default_str}]: ").strip().lower()
        if not result:
            return default
        return result in ("да", "yes", "y", "д", "1", "true")

    # ========== ШАГ 1: СБОР ПЕРСОНАЛЬНЫХ ДАННЫХ ==========
    def collect_personal_info(self) -> dict[str, Any]:
        """Сбор персональной информации."""
        print_step(1, "СБОР ПЕРСОНАЛЬНЫХ ДАННЫХ")
        print("-" * 60)

        personal = {
            "full_name": self.get_input("Полное имя (латиницей)", "Ivan Petrov"),
            "email": self.get_input("Email", "ivan@example.com"),
            "phone": self.get_input("Телефон", "+1-555-123-4567"),
            "current_country": self.get_input("Текущая страна проживания", "Russia"),
            "citizenship": self.get_input("Гражданство", "Russia"),
            "date_of_birth": self.get_input("Дата рождения (YYYY-MM-DD)", "1985-06-15"),
            "passport_number": self.get_input("Номер паспорта", "AB1234567"),
            "current_visa_status": self.get_input("Текущий визовый статус (если есть)", "None"),
        }

        print_success("Персональные данные собраны")
        return personal

    # ========== ШАГ 2: ПРОФЕССИОНАЛЬНАЯ ИНФОРМАЦИЯ ==========
    def collect_professional_info(self) -> dict[str, Any]:
        """Сбор профессиональной информации."""
        print_step(2, "ПРОФЕССИОНАЛЬНАЯ ИНФОРМАЦИЯ")
        print("-" * 60)

        professional = {
            "field": self.get_input(
                "Область экспертизы", "Computer Science / Artificial Intelligence"
            ),
            "specialization": self.get_input("Специализация", "Machine Learning and Deep Learning"),
            "years_of_experience": int(self.get_input("Лет опыта в области", "12")),
            "current_position": self.get_input("Текущая должность", "Senior AI Research Scientist"),
            "current_employer": self.get_input("Текущий работодатель", "Tech Company"),
            "education_level": self.get_input("Высшее образование", "PhD in Computer Science"),
            "university": self.get_input("Университет", "Moscow State University"),
            "graduation_year": self.get_input("Год окончания", "2015"),
        }

        print_success("Профессиональная информация собрана")
        return professional

    # ========== ШАГ 3: КРИТЕРИИ EB-1A ==========
    def collect_criteria_evidence(self) -> dict[str, Any]:
        """Сбор доказательств по 10 критериям EB-1A."""
        print_step(3, "ДОКАЗАТЕЛЬСТВА ПО 10 КРИТЕРИЯМ EB-1A")
        print("-" * 60)
        print_info("Для EB-1A необходимо соответствие минимум 3 из 10 критериев")
        print()

        criteria = {}

        # 1. AWARDS - Национальные/международные награды
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 1: НАГРАДЫ{Colors.ENDC}")
        print("Национальные или международные награды за выдающиеся достижения")
        if self.get_yes_no("Есть награды?"):
            criteria["awards"] = {
                "met": True,
                "evidence": self.get_multiline_input("Перечислите награды (по одной на строку):"),
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.8")),
            }
        else:
            criteria["awards"] = {"met": False}

        # 2. MEMBERSHIP - Членство в ассоциациях
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 2: ЧЛЕНСТВО В АССОЦИАЦИЯХ{Colors.ENDC}")
        print("Членство в ассоциациях, требующих выдающихся достижений")
        if self.get_yes_no("Есть членство в профессиональных ассоциациях?"):
            criteria["membership"] = {
                "met": True,
                "evidence": self.get_multiline_input(
                    "Перечислите ассоциации и требования к членству:"
                ),
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.7")),
            }
        else:
            criteria["membership"] = {"met": False}

        # 3. PUBLISHED MATERIAL - Публикации в СМИ
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 3: ПУБЛИКАЦИИ В СМИ{Colors.ENDC}")
        print("Публикации о вас в профессиональных или крупных СМИ")
        if self.get_yes_no("Есть публикации в СМИ о вашей работе?"):
            criteria["published_material"] = {
                "met": True,
                "evidence": self.get_multiline_input(
                    "Перечислите публикации (издание, дата, тема):"
                ),
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.6")),
            }
        else:
            criteria["published_material"] = {"met": False}

        # 4. JUDGING - Судейство
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 4: СУДЕЙСТВО{Colors.ENDC}")
        print("Участие в качестве судьи работ других в вашей области")
        if self.get_yes_no("Судили работы других (рецензирование, жюри)?"):
            criteria["judging"] = {
                "met": True,
                "evidence": self.get_multiline_input(
                    "Перечислите опыт судейства (конференции, журналы):"
                ),
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.8")),
            }
        else:
            criteria["judging"] = {"met": False}

        # 5. ORIGINAL CONTRIBUTIONS - Оригинальный вклад
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 5: ОРИГИНАЛЬНЫЙ ВКЛАД{Colors.ENDC}")
        print("Оригинальные научные, исследовательские или художественные вклады")
        if self.get_yes_no("Есть оригинальные вклады значительной важности?"):
            criteria["original_contributions"] = {
                "met": True,
                "evidence": self.get_multiline_input("Опишите ваши оригинальные вклады:"),
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.9")),
            }
        else:
            criteria["original_contributions"] = {"met": False}

        # 6. SCHOLARLY ARTICLES - Научные публикации
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 6: НАУЧНЫЕ ПУБЛИКАЦИИ{Colors.ENDC}")
        print("Авторство научных статей в профессиональных журналах")
        if self.get_yes_no("Есть научные публикации?"):
            num_publications = int(self.get_input("Количество публикаций", "25"))
            citations = int(self.get_input("Общее количество цитирований", "1500"))
            h_index = int(self.get_input("H-index", "18"))
            criteria["scholarly_articles"] = {
                "met": True,
                "evidence": f"Publications: {num_publications}, Citations: {citations}, H-index: {h_index}",
                "publications_count": num_publications,
                "citations_count": citations,
                "h_index": h_index,
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.85")),
            }
        else:
            criteria["scholarly_articles"] = {"met": False}

        # 7. EXHIBITIONS - Выставки
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 7: ВЫСТАВКИ{Colors.ENDC}")
        print("Демонстрация работ на художественных выставках или витринах")
        if self.get_yes_no("Есть выставки ваших работ?"):
            criteria["exhibitions"] = {
                "met": True,
                "evidence": self.get_multiline_input("Перечислите выставки:"),
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.7")),
            }
        else:
            criteria["exhibitions"] = {"met": False}

        # 8. LEADING ROLE - Лидирующая роль
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 8: ЛИДИРУЮЩАЯ/КРИТИЧЕСКАЯ РОЛЬ{Colors.ENDC}")
        print("Ведущая или критическая роль в организациях с выдающейся репутацией")
        if self.get_yes_no("Занимали лидирующие позиции?"):
            criteria["leading_role"] = {
                "met": True,
                "evidence": self.get_multiline_input("Опишите лидирующие роли:"),
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.8")),
            }
        else:
            criteria["leading_role"] = {"met": False}

        # 9. HIGH SALARY - Высокая зарплата
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 9: ВЫСОКАЯ ЗАРПЛАТА{Colors.ENDC}")
        print("Зарплата значительно выше среднего в вашей области")
        if self.get_yes_no("Зарплата значительно выше среднего?"):
            salary = int(self.get_input("Годовая зарплата (USD)", "250000"))
            criteria["high_salary"] = {
                "met": True,
                "evidence": f"Annual salary: ${salary:,} USD",
                "salary_amount": salary,
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.75")),
            }
        else:
            criteria["high_salary"] = {"met": False}

        # 10. COMMERCIAL SUCCESS - Коммерческий успех
        print(f"\n{Colors.BOLD}КРИТЕРИЙ 10: КОММЕРЧЕСКИЙ УСПЕХ{Colors.ENDC}")
        print("Коммерческий успех в области исполнительского искусства")
        if self.get_yes_no("Есть коммерческий успех (продажи, доход)?"):
            criteria["commercial_success"] = {
                "met": True,
                "evidence": self.get_multiline_input("Опишите коммерческий успех:"),
                "strength_score": float(self.get_input("Оценка силы (0.0-1.0)", "0.7")),
            }
        else:
            criteria["commercial_success"] = {"met": False}

        # Подсчет критериев
        met_count = sum(1 for c in criteria.values() if c.get("met", False))
        print()
        print("-" * 60)
        print_info(f"Критериев соответствует: {met_count}/10")

        if met_count >= 3:
            print_success("Минимум 3 критерия выполнен! Кандидат потенциально eligible для EB-1A")
        else:
            print_error(f"Недостаточно критериев ({met_count}/3). Нужно усилить доказательства")

        return criteria

    # ========== ШАГ 4: СБОР EXHIBITS ==========
    def collect_exhibits(self) -> list[dict[str, Any]]:
        """Сбор списка exhibits (доказательств)."""
        print_step(4, "СПИСОК EXHIBITS (ПРИЛОЖЕНИЙ)")
        print("-" * 60)
        print_info("Введите список документов-доказательств")
        print()

        exhibits = []
        exhibit_num = 1

        # Стандартные exhibits
        default_exhibits = [
            "Resume/CV",
            "Educational Credentials (Diploma, Transcripts)",
            "Employment Verification Letters",
            "Recommendation Letters",
            "Award Certificates",
            "Publication List with Citations",
            "Salary Documentation",
            "Passport Copy",
        ]

        print("Стандартные exhibits (нажмите Enter чтобы добавить, 's' чтобы пропустить):")
        for title in default_exhibits:
            response = input(f"  {exhibit_num}. {title} [Enter/s]: ").strip().lower()
            if response != "s":
                exhibits.append({"number": exhibit_num, "title": title, "page": ""})
                exhibit_num += 1

        print()
        print("Добавьте дополнительные exhibits (пустая строка для завершения):")
        while True:
            title = input(f"  {exhibit_num}. Название: ").strip()
            if not title:
                break
            exhibits.append({"number": exhibit_num, "title": title, "page": ""})
            exhibit_num += 1

        print_success(f"Добавлено {len(exhibits)} exhibits")
        return exhibits

    # ========== ШАГ 5: ГЕНЕРАЦИЯ КОНТЕНТА СЕКЦИЙ ==========
    def generate_petition_sections(self) -> dict[str, str]:
        """Генерация контента секций petition letter."""
        print_step(5, "ГЕНЕРАЦИЯ КОНТЕНТА PETITION LETTER")
        print("-" * 60)

        name = self.user_data.get("full_name", "Beneficiary")
        field = self.case_data.get("field", "Sciences")

        sections = {}

        # SUMMARY
        print_info("Генерация Summary секции...")
        summary_parts = [
            f"This petition is filed on behalf of {name}, an individual of extraordinary ability in the field of {field}.",
            "The beneficiary has demonstrated sustained national and international acclaim through the following achievements:",
        ]

        met_criteria = [k for k, v in self.criteria_evidence.items() if v.get("met", False)]
        for criterion in met_criteria:
            evidence = self.criteria_evidence[criterion].get("evidence", "")
            summary_parts.append(f"- {criterion.replace('_', ' ').title()}: {evidence[:200]}...")

        sections["summary"] = "\n\n".join(summary_parts)

        # Секции по критериям
        criterion_map = {
            "awards": "awards",
            "membership": "membership",
            "published_material": "press",
            "judging": "judging",
            "original_contributions": "contributions",
            "scholarly_articles": "scholarly",
            "exhibitions": "exhibitions",
            "leading_role": "leading_role",
            "high_salary": "salary",
            "commercial_success": "commercial",
        }

        for criterion, section_key in criterion_map.items():
            data = self.criteria_evidence.get(criterion, {})
            if data.get("met", False):
                evidence = data.get("evidence", "")
                sections[section_key] = f"""
The beneficiary satisfies this criterion through the following evidence:

{evidence}

This evidence demonstrates that {name} has achieved recognition at the national and international level in the field of {field}.
"""
            else:
                sections[section_key] = "[Not applicable - criterion not claimed]"

        # FINAL MERITS
        sections["final_merits"] = f"""
Based on the totality of the evidence presented, {name} has demonstrated extraordinary ability in {field}.

The beneficiary meets {len(met_criteria)} of the 10 regulatory criteria, well exceeding the minimum requirement of 3 criteria.

The evidence shows a level of expertise indicating that {name} is one of the small percentage who have risen to the very top of the field.
"""

        # NATIONAL IMPORTANCE
        sections["national_importance"] = f"""
{name}'s continued work in the United States will substantially benefit prospectively the United States.

The beneficiary's expertise in {field} addresses critical needs in the U.S. economy and scientific advancement.
"""

        print_success("Секции petition letter сгенерированы")
        return sections

    # ========== ШАГ 6: ГЕНЕРАЦИЯ PDF ==========
    async def generate_pdf_package(self) -> str:
        """Генерация финального PDF пакета."""
        print_step(6, "ГЕНЕРАЦИЯ PDF ПАКЕТА")
        print("-" * 60)

        try:
            from core.services.pdf_package_generator import PDFPackageGenerator

            generator = PDFPackageGenerator(output_dir=str(self.output_dir))

            print_info("Генерация PDF компонентов...")
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

            print_success(f"PDF пакет создан: {result}")
            return result

        except ImportError as e:
            print_error(f"Не удалось импортировать PDFPackageGenerator: {e}")
            return await self.generate_pdf_fallback()
        except Exception as e:
            print_error(f"Ошибка генерации PDF: {e}")
            return await self.generate_pdf_fallback()

    async def generate_pdf_fallback(self) -> str:
        """Fallback генерация отдельных PDF через LaTeX."""
        print_info("Использую fallback генерацию через LaTeX...")

        try:
            from core.services.latex_generator import LaTeXGenerator

            latex = LaTeXGenerator()
            name = self.user_data.get("full_name", "Beneficiary")
            field = self.case_data.get("field", "Sciences")

            results = []

            # Cover page
            try:
                cover = latex.generate_cover_page(
                    output_path=self.output_dir / "cover_page.pdf",
                    name=name,
                    include_premium=True,
                )
                results.append(f"Cover: {cover}")
                print_success(f"  Cover page: {cover}")
            except Exception as e:
                print_error(f"  Cover page failed: {e}")

            # Petition letter
            try:
                petition = latex.generate_petition_letter(
                    output_path=self.output_dir / "petition_letter.pdf",
                    name=name,
                    field=field,
                    sections=self.petition_sections,
                )
                results.append(f"Petition: {petition}")
                print_success(f"  Petition letter: {petition}")
            except Exception as e:
                print_error(f"  Petition letter failed: {e}")

            # Statement of intent
            try:
                statement = latex.generate_statement_of_intent(
                    output_path=self.output_dir / "statement.pdf",
                    name=name,
                    field=field,
                )
                results.append(f"Statement: {statement}")
                print_success(f"  Statement: {statement}")
            except Exception as e:
                print_error(f"  Statement failed: {e}")

            # Exhibits list
            try:
                exhibits = latex.generate_exhibits_list(
                    output_path=self.output_dir / "exhibits_list.pdf",
                    name=name,
                    exhibits=self.exhibits,
                )
                results.append(f"Exhibits: {exhibits}")
                print_success(f"  Exhibits list: {exhibits}")
            except Exception as e:
                print_error(f"  Exhibits list failed: {e}")

            return str(self.output_dir)

        except Exception as e:
            print_error(f"LaTeX fallback failed: {e}")
            return ""

    # ========== ШАГ 7: СОХРАНЕНИЕ ДАННЫХ ==========
    def save_case_data(self):
        """Сохранение данных кейса в JSON."""
        print_step(7, "СОХРАНЕНИЕ ДАННЫХ КЕЙСА")
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

        print_success(f"Данные сохранены: {case_file}")
        return case_file

    # ========== MAIN RUN ==========
    async def run(self):
        """Запуск полного pipeline."""
        print_header("EB-1A FULL PIPELINE TEST")
        print_info(f"Case ID: {self.case_id}")
        print_info(f"Output directory: {self.output_dir}")
        print()

        # Шаг 1: Персональные данные
        self.user_data = self.collect_personal_info()
        print()

        # Шаг 2: Профессиональная информация
        self.case_data = self.collect_professional_info()
        print()

        # Шаг 3: Критерии EB-1A
        self.criteria_evidence = self.collect_criteria_evidence()
        print()

        # Шаг 4: Exhibits
        self.exhibits = self.collect_exhibits()
        print()

        # Шаг 5: Генерация секций
        self.petition_sections = self.generate_petition_sections()
        print()

        # Шаг 6: Генерация PDF
        pdf_result = await self.generate_pdf_package()
        print()

        # Шаг 7: Сохранение данных
        json_file = self.save_case_data()
        print()

        # Итоговая сводка
        print_header("ИТОГОВАЯ СВОДКА")

        met_criteria = [k for k, v in self.criteria_evidence.items() if v.get("met", False)]

        print(f"Case ID:           {self.case_id}")
        print(f"Beneficiary:       {self.user_data.get('full_name')}")
        print(f"Field:             {self.case_data.get('field')}")
        print(f"Criteria Met:      {len(met_criteria)}/10")
        print(f"Met Criteria:      {', '.join(met_criteria)}")
        print(f"Exhibits:          {len(self.exhibits)}")
        print(f"Output Directory:  {self.output_dir}")
        print(f"JSON Data:         {json_file}")
        print(f"PDF Package:       {pdf_result}")
        print()

        if len(met_criteria) >= 3:
            print_success("Кандидат потенциально ELIGIBLE для EB-1A!")
        else:
            print_error(f"Недостаточно критериев ({len(met_criteria)}/3)")

        print()
        print_header("ТЕСТ ЗАВЕРШЕН")

        return {
            "case_id": self.case_id,
            "output_dir": str(self.output_dir),
            "json_file": str(json_file),
            "pdf_result": pdf_result,
            "criteria_met": len(met_criteria),
        }


async def main():
    """Main entry point."""
    pipeline = EB1APipelineTest()
    result = await pipeline.run()
    return result


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("EB-1A FULL PIPELINE TEST".center(80))
    print("От создания кейса до генерации PDF".center(80))
    print("=" * 80 + "\n")

    try:
        result = asyncio.run(main())
        print(f"\nРезультат: {json.dumps(result, indent=2)}")
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback

        traceback.print_exc()
