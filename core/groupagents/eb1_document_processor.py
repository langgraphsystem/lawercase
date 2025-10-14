"""
EB-1A Document Processor

Обрабатывает:
1. Загруженные PDF/изображения (OCR, извлечение данных)
2. Генерацию документов на основе шаблонов и LLM
3. Автоматический маппинг на 10 критериев
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any
import uuid

from .eb1_documents import (
    COVER_LETTER_TEMPLATE,
    CRITERION_SECTION_TEMPLATES,
    RECOMMENDATION_LETTER_TEMPLATE,
    USCIS_KEYWORDS_BY_CRITERION,
    EB1DocumentType,
    GeneratedDocument,
    RecommendationLetterData,
    UploadedDocument,
)
from .eb1_models import EB1Criterion, EB1PetitionData


class EB1DocumentProcessor:
    """
    Процессор документов для EB-1A петиций.

    Функции:
    - Обработка загруженных PDF/изображений
    - OCR и извлечение текста
    - Классификация документов по типам
    - Генерация документов через LLM
    - Валидация на соответствие требованиям USCIS
    """

    def __init__(self, llm_client: Any | None = None):
        """
        Args:
            llm_client: LLM клиент для генерации (например, Anthropic Claude)
        """
        self.llm_client = llm_client

        # Хранилище загруженных и сгенерированных документов
        self._uploaded_docs: dict[str, UploadedDocument] = {}
        self._generated_docs: dict[str, GeneratedDocument] = {}

    # ========== ОБРАБОТКА ЗАГРУЖЕННЫХ ДОКУМЕНТОВ ==========

    async def process_uploaded_file(
        self, file_path: str, original_filename: str, petition_id: str
    ) -> UploadedDocument:
        """
        Обработка загруженного файла (PDF, изображение).

        Args:
            file_path: Путь к файлу
            original_filename: Оригинальное имя
            petition_id: ID петиции

        Returns:
            UploadedDocument с извлеченными данными
        """
        document_id = f"upload_{uuid.uuid4().hex[:12]}"

        # Определение типа файла
        file_type = self._detect_file_type(file_path)

        uploaded_doc = UploadedDocument(
            document_id=document_id,
            file_path=file_path,
            file_type=file_type,
            original_filename=original_filename,
        )

        # Извлечение текста
        if file_type == "pdf":
            extracted_text = await self._extract_text_from_pdf(file_path)
        elif file_type in ["png", "jpg", "jpeg"]:
            extracted_text = await self._extract_text_from_image(file_path)
        else:
            extracted_text = ""

        uploaded_doc.extracted_text = extracted_text

        # Классификация документа
        detected_type = await self._classify_document(extracted_text)
        uploaded_doc.detected_type = detected_type

        # Определение критериев, которые подтверждает документ
        detected_criteria = await self._detect_criteria_in_document(extracted_text)
        uploaded_doc.detected_criteria = detected_criteria

        # Извлечение структурированных данных
        extracted_data = await self._extract_structured_data(extracted_text, detected_type)
        uploaded_doc.extracted_data = extracted_data

        # Сохранение
        self._uploaded_docs[document_id] = uploaded_doc

        return uploaded_doc

    async def _extract_text_from_pdf(self, file_path: str) -> str:
        """Извлечение текста из PDF (с использованием PyPDF2 или pdfplumber)"""
        try:
            # Попытка импорта библиотеки
            try:
                import pdfplumber

                with pdfplumber.open(file_path) as pdf:
                    text_parts = []
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    return "\n\n".join(text_parts)
            except ImportError:
                # Fallback на PyPDF2
                try:
                    import PyPDF2

                    with open(file_path, "rb") as file:
                        reader = PyPDF2.PdfReader(file)
                        text_parts = []
                        for page in reader.pages:
                            text = page.extract_text()
                            if text:
                                text_parts.append(text)
                        return "\n\n".join(text_parts)
                except ImportError:
                    return "[PDF extraction libraries not available - install pdfplumber or PyPDF2]"
        except Exception as e:
            return f"[Error extracting PDF: {e}]"

    async def _extract_text_from_image(self, file_path: str) -> str:
        """Извлечение текста из изображения (OCR с использованием pytesseract)"""
        try:
            from PIL import Image
            import pytesseract

            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except ImportError:
            return "[OCR library not available - install pytesseract and Tesseract-OCR]"
        except Exception as e:
            return f"[Error extracting text from image: {e}]"

    def _detect_file_type(self, file_path: str) -> str:
        """Определение типа файла по расширению"""
        extension = Path(file_path).suffix.lower().lstrip(".")
        if extension in ["pdf"]:
            return "pdf"
        if extension in ["png", "jpg", "jpeg"]:
            return extension
        return "unknown"

    async def _classify_document(self, text: str) -> EB1DocumentType | None:
        """Классификация документа по содержимому"""
        text_lower = text.lower()

        # Простая эвристика (можно заменить на LLM)
        if "recommendation" in text_lower or "letter of support" in text_lower:
            return EB1DocumentType.RECOMMENDATION_LETTER

        if "award" in text_lower or "prize" in text_lower or "recipient" in text_lower:
            return EB1DocumentType.AWARDS_DOCUMENTATION

        if "member" in text_lower and "association" in text_lower:
            return EB1DocumentType.MEMBERSHIP_PROOF

        if "publication" in text_lower or "journal" in text_lower or "article" in text_lower:
            return EB1DocumentType.PUBLICATIONS_LIST

        if "salary" in text_lower or "compensation" in text_lower or "employment" in text_lower:
            return EB1DocumentType.SALARY_VERIFICATION

        return None

    async def _detect_criteria_in_document(self, text: str) -> list[EB1Criterion]:
        """Определение критериев, которые подтверждает документ"""
        detected_criteria = []
        text_lower = text.lower()

        # Проверка ключевых слов для каждого критерия
        for criterion, keywords in USCIS_KEYWORDS_BY_CRITERION.items():
            keyword_matches = sum(1 for kw in keywords if kw.lower() in text_lower)

            # Если найдено хотя бы 2 ключевых слова, считаем критерий подтвержденным
            if keyword_matches >= 2:
                detected_criteria.append(criterion)

        return detected_criteria

    async def _extract_structured_data(
        self, text: str, doc_type: EB1DocumentType | None
    ) -> dict[str, Any]:
        """Извлечение структурированных данных из текста"""

        data: dict[str, Any] = {}

        if doc_type == EB1DocumentType.AWARDS_DOCUMENTATION:
            # Попытка извлечь название награды, год, организацию
            data["award_name"] = self._extract_pattern(text, r"award:?\s*(.+)", default="")
            data["year"] = self._extract_pattern(text, r"(\d{4})", default="")
            data["organization"] = self._extract_pattern(text, r"by:?\s*(.+)", default="")

        elif doc_type == EB1DocumentType.PUBLICATIONS_LIST:
            # Извлечение количества публикаций и цитирований
            pub_count = self._extract_pattern(text, r"(\d+)\s*publications?", default="0")
            citation_count = self._extract_pattern(text, r"(\d+)\s*citations?", default="0")
            data["publication_count"] = int(pub_count) if pub_count.isdigit() else 0
            data["citation_count"] = int(citation_count) if citation_count.isdigit() else 0

        elif doc_type == EB1DocumentType.SALARY_VERIFICATION:
            # Извлечение зарплаты
            salary = self._extract_pattern(text, r"\$\s*([\d,]+)", default="0").replace(",", "")
            data["salary_amount"] = int(salary) if salary.isdigit() else 0

        return data

    def _extract_pattern(self, text: str, pattern: str, default: str = "") -> str:
        """Извлечение паттерна из текста"""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else default

    # ========== ГЕНЕРАЦИЯ ДОКУМЕНТОВ ==========

    async def generate_recommendation_letter(
        self, letter_data: RecommendationLetterData, petition: EB1PetitionData
    ) -> GeneratedDocument:
        """
        Генерация рекомендательного письма на основе данных.

        Args:
            letter_data: Данные для письма
            petition: Данные петиции

        Returns:
            GeneratedDocument с сгенерированным текстом
        """
        document_id = f"gen_rec_{uuid.uuid4().hex[:12]}"

        # Формирование промпта для LLM
        generation_prompt = self._build_recommendation_letter_prompt(letter_data, petition)

        # Генерация через LLM (если доступен) или использование шаблона
        if self.llm_client:
            content = await self._generate_with_llm(generation_prompt)
        else:
            content = self._generate_from_template(letter_data, petition)

        # Создание документа
        generated_doc = GeneratedDocument(
            document_id=document_id,
            petition_id=petition.petition_id,
            document_type=EB1DocumentType.RECOMMENDATION_LETTER,
            content=content,
            supporting_criteria=letter_data.supporting_criteria,
            template_used="recommendation_letter_v1",
            generation_prompt=generation_prompt,
        )

        self._generated_docs[document_id] = generated_doc

        return generated_doc

    def _build_recommendation_letter_prompt(
        self, letter_data: RecommendationLetterData, petition: EB1PetitionData
    ) -> str:
        """Построение промпта для LLM"""

        prompt = f"""
You are an expert immigration attorney writing a recommendation letter for an EB-1A petition.

TASK: Generate a professional, persuasive recommendation letter that will help the beneficiary
obtain EB-1A visa approval.

BENEFICIARY INFORMATION:
- Name: {letter_data.candidate_name}
- Field: {letter_data.candidate_field}

RECOMMENDER INFORMATION:
- Name: {letter_data.recommender_name}
- Title: {letter_data.recommender_title}
- Organization: {letter_data.recommender_organization}
- Credentials: {letter_data.recommender_credentials}
- Relationship: {letter_data.recommender_relationship}
- Years Known: {letter_data.years_known}

CRITERIA TO SUPPORT:
{self._format_criteria_for_prompt(letter_data.supporting_criteria)}

SPECIFIC ACHIEVEMENTS TO MENTION:
{self._format_list(letter_data.specific_achievements)}

COLLABORATION EXAMPLES:
{self._format_list(letter_data.collaboration_examples)}

IMPACT STATEMENTS:
{self._format_list(letter_data.impact_statements)}

CRITICAL REQUIREMENTS:
1. Use USCIS-specific terminology for each criterion (provided below)
2. Provide concrete examples and quantifiable achievements
3. Demonstrate "sustained national/international acclaim"
4. Show "extraordinary ability" clearly
5. Be professional but persuasive
6. Length: 2-3 pages

USCIS KEYWORDS TO INCLUDE:
{self._format_uscis_keywords(letter_data.supporting_criteria, letter_data.keywords_for_criteria)}

FORMAT:
- Professional letterhead format
- Formal business letter structure
- Clear sections for each criterion
- Strong opening and closing

Generate the complete recommendation letter now:
"""
        return prompt

    def _generate_from_template(
        self, letter_data: RecommendationLetterData, petition: EB1PetitionData
    ) -> str:
        """Генерация из шаблона (без LLM)"""

        # Формирование секций для каждого критерия
        criterion_sections = []
        for _i, criterion in enumerate(letter_data.supporting_criteria, 1):
            template = CRITERION_SECTION_TEMPLATES.get(criterion, "")
            if template:
                section = template.format(
                    criterion_name=criterion.value.upper(),
                    candidate_name=letter_data.candidate_name,
                    field=letter_data.candidate_field,
                    specific_awards=(
                        ", ".join(letter_data.specific_achievements[:2])
                        if letter_data.specific_achievements
                        else "[specific awards here]"
                    ),
                    memberships=(
                        ", ".join(letter_data.specific_achievements[:2])
                        if letter_data.specific_achievements
                        else "[memberships here]"
                    ),
                    press_examples=(
                        ", ".join(letter_data.specific_achievements[:2])
                        if letter_data.specific_achievements
                        else "[press examples here]"
                    ),
                    judging_examples=(
                        "; ".join(letter_data.specific_achievements[:2])
                        if letter_data.specific_achievements
                        else "[judging examples here]"
                    ),
                    contribution_details=(
                        ". ".join(letter_data.specific_achievements[:2])
                        if letter_data.specific_achievements
                        else "[contribution details here]"
                    ),
                    publication_count=(
                        petition.criteria_evidence.get("scholarly", {}).get(
                            "evidence_count", "numerous"
                        )
                    ),
                    citation_count="[citation count]",
                    key_publications=(
                        "; ".join(letter_data.specific_achievements[:2])
                        if letter_data.specific_achievements
                        else "[key publications here]"
                    ),
                    leadership_roles=(
                        "; ".join(letter_data.specific_achievements[:2])
                        if letter_data.specific_achievements
                        else "[leadership roles here]"
                    ),
                    achievements=(
                        "; ".join(letter_data.specific_achievements[:2])
                        if letter_data.specific_achievements
                        else "[achievements here]"
                    ),
                    salary_amount="[salary amount]",
                )
                criterion_sections.append(section)

        # Формирование impact statements
        impact_text = "\n".join(
            f"• {statement}"
            for statement in (letter_data.impact_statements or ["[Impact statement here]"])
        )

        # Заполнение основного шаблона
        content = RECOMMENDATION_LETTER_TEMPLATE.format(
            date=datetime.now().strftime("%B %d, %Y"),
            uscis_office_address="[USCIS Office Address]",
            candidate_name=letter_data.candidate_name,
            field_of_expertise=letter_data.candidate_field,
            recommender_name=letter_data.recommender_name,
            recommender_title=letter_data.recommender_title,
            recommender_organization=letter_data.recommender_organization,
            recommender_credentials=letter_data.recommender_credentials,
            years_known=letter_data.years_known,
            relationship=letter_data.recommender_relationship,
            criterion_section_1=criterion_sections[0] if len(criterion_sections) > 0 else "",
            criterion_section_2=criterion_sections[1] if len(criterion_sections) > 1 else "",
            criterion_section_3=criterion_sections[2] if len(criterion_sections) > 2 else "",
            impact_statements=impact_text,
            recommender_contact="[Contact Information]",
        )

        return content

    async def generate_cover_letter(self, petition: EB1PetitionData) -> GeneratedDocument:
        """Генерация сопроводительного письма для I-140"""

        document_id = f"gen_cover_{uuid.uuid4().hex[:12]}"

        # Формирование списка критериев
        met_criteria = [
            criterion for criterion, evidence in petition.criteria_evidence.items() if evidence.met
        ]

        criteria_list_text = "\n".join(
            f"✓ {self._get_criterion_full_name(EB1Criterion(criterion))}"
            for criterion in met_criteria
        )

        # Формирование списка exhibits (документов)
        exhibit_list_text = self._generate_exhibit_list(petition)

        # Заполнение шаблона
        content = COVER_LETTER_TEMPLATE.format(
            date=datetime.now().strftime("%B %d, %Y"),
            uscis_service_center="[USCIS Service Center Address]",
            petitioner_name=(
                petition.personal_info.full_name if petition.personal_info else "[Petitioner]"
            ),
            candidate_name=(
                petition.personal_info.full_name if petition.personal_info else "[Candidate]"
            ),
            field_of_expertise=(
                petition.field_of_expertise.field if petition.field_of_expertise else "[Field]"
            ),
            years_of_experience=(
                petition.field_of_expertise.years_of_experience
                if petition.field_of_expertise
                else "[X]"
            ),
            criteria_list=criteria_list_text,
            exhibit_list=exhibit_list_text,
            petitioner_signature="[Signature]",
            petitioner_title="Self-Petition" if petition.personal_info else "[Title]",
        )

        generated_doc = GeneratedDocument(
            document_id=document_id,
            petition_id=petition.petition_id,
            document_type=EB1DocumentType.COVER_LETTER,
            content=content,
            supporting_criteria=[EB1Criterion(c) for c in met_criteria],
            template_used="cover_letter_v1",
        )

        self._generated_docs[document_id] = generated_doc

        return generated_doc

    async def _generate_with_llm(self, prompt: str) -> str:
        """Генерация через LLM (Claude/GPT/Gemini).

        Использует переданный llm_client для генерации документа.
        Поддерживает:
        - Anthropic Claude (claude-sonnet-4-5-20250929, claude-opus-4-1-20250805)
        - OpenAI GPT (gpt-4.1, gpt-4.1-mini, o3-mini)
        - Google Gemini (gemini-2.5-pro, gemini-2.5-flash)

        Args:
            prompt: Промпт для генерации

        Returns:
            Сгенерированный текст документа
        """
        if not self.llm_client:
            return "[LLM client not configured - using template fallback]"

        try:
            # Вызов единого интерфейса acomplete у всех клиентов
            result = await self.llm_client.acomplete(
                prompt=prompt,
                temperature=0.3,  # Низкая температура для более точных и предсказуемых документов
                max_tokens=8192,  # Длинные документы (письма 2-3 страницы)
            )

            # Извлечение сгенерированного текста
            if "error" in result:
                error_msg = result.get("error", "Unknown error")
                return f"[LLM generation error: {error_msg}]"

            output = result.get("output", "")
            if not output:
                return "[LLM returned empty response - using template fallback]"

            return output

        except Exception as e:
            # Если произошла ошибка, возвращаем информативное сообщение
            return f"[LLM generation failed: {e!s}]"

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    def _format_criteria_for_prompt(self, criteria: list[EB1Criterion]) -> str:
        """Форматирование критериев для промпта"""
        return "\n".join(
            f"- {criterion.value.upper()}: {self._get_criterion_full_name(criterion)}"
            for criterion in criteria
        )

    def _format_list(self, items: list[str]) -> str:
        """Форматирование списка"""
        if not items:
            return "[None provided]"
        return "\n".join(f"- {item}" for item in items)

    def _format_uscis_keywords(
        self, criteria: list[EB1Criterion], custom_keywords: dict[str, list[str]]
    ) -> str:
        """Форматирование USCIS ключевых слов"""
        result = []
        for criterion in criteria:
            keywords = custom_keywords.get(criterion.value) or USCIS_KEYWORDS_BY_CRITERION.get(
                criterion, []
            )
            result.append(f"{criterion.value.upper()}: {', '.join(keywords)}")
        return "\n".join(result)

    def _get_criterion_full_name(self, criterion: EB1Criterion) -> str:
        """Полное название критерия"""
        names = {
            EB1Criterion.AWARDS: "Receipt of nationally or internationally recognized prizes or awards",
            EB1Criterion.MEMBERSHIP: "Membership in associations requiring outstanding achievements",
            EB1Criterion.PRESS: "Published material in professional or major trade publications about the beneficiary",
            EB1Criterion.JUDGING: "Participation as a judge of the work of others",
            EB1Criterion.CONTRIBUTION: "Original scientific, scholarly, or business-related contributions of major significance",
            EB1Criterion.SCHOLARLY: "Authorship of scholarly articles in professional journals",
            EB1Criterion.EXHIBITION: "Display of work at artistic exhibitions or showcases",
            EB1Criterion.LEADERSHIP: "Leading or critical role in distinguished organizations",
            EB1Criterion.SALARY: "High salary or remuneration compared to others in the field",
            EB1Criterion.COMMERCIAL: "Commercial success in the performing arts",
        }
        return names.get(criterion, criterion.value)

    def _generate_exhibit_list(self, petition: EB1PetitionData) -> str:
        """Генерация списка exhibits"""
        exhibits = [
            "Exhibit A: Form I-140 with filing fee",
            "Exhibit B: Beneficiary's Passport and I-94",
            "Exhibit C: Curriculum Vitae",
        ]

        exhibit_counter = ord("D")

        for criterion_key, evidence in petition.criteria_evidence.items():
            if evidence.met:
                criterion = EB1Criterion(criterion_key)
                exhibits.append(
                    f"Exhibit {chr(exhibit_counter)}: Evidence for {self._get_criterion_full_name(criterion)}"
                )
                exhibit_counter += 1

        exhibits.append(f"Exhibit {chr(exhibit_counter)}: Letters of Recommendation")

        return "\n".join(exhibits)

    # ========== ПУБЛИЧНЫЕ МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ ДОКУМЕНТОВ ==========

    def get_uploaded_document(self, document_id: str) -> UploadedDocument | None:
        """Получение загруженного документа"""
        return self._uploaded_docs.get(document_id)

    def get_generated_document(self, document_id: str) -> GeneratedDocument | None:
        """Получение сгенерированного документа"""
        return self._generated_docs.get(document_id)

    def get_all_documents_for_petition(
        self, petition_id: str
    ) -> dict[str, list[GeneratedDocument | UploadedDocument]]:
        """Получение всех документов для петиции"""
        generated = [doc for doc in self._generated_docs.values() if doc.petition_id == petition_id]

        return {
            "generated": generated,
            "uploaded": list(self._uploaded_docs.values()),  # Можно добавить фильтр по petition_id
        }
