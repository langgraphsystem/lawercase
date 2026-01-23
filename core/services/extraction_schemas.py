"""
Extraction schemas for structured field extraction from documents.

Defines what fields to extract from each document type for EB-1A cases.
"""

from __future__ import annotations

# =============================================================================
# IDENTITY DOCUMENTS
# =============================================================================

PASSPORT_SCHEMA = {
    "full_name": "ФИО владельца паспорта",
    "full_name_en": "ФИО на английском (латиницей)",
    "date_of_birth": "Дата рождения в формате YYYY-MM-DD",
    "place_of_birth": "Место рождения",
    "passport_number": "Номер паспорта",
    "issue_date": "Дата выдачи в формате YYYY-MM-DD",
    "expiry_date": "Дата окончания срока действия в формате YYYY-MM-DD",
    "issuing_authority": "Кем выдан паспорт",
    "nationality": "Гражданство",
    "gender": "Пол (M или F)",
}

BIRTH_CERTIFICATE_SCHEMA = {
    "full_name": "ФИО ребёнка",
    "date_of_birth": "Дата рождения в формате YYYY-MM-DD",
    "place_of_birth": "Место рождения (город, страна)",
    "father_name": "ФИО отца",
    "mother_name": "ФИО матери",
    "certificate_number": "Номер свидетельства",
    "issue_date": "Дата выдачи в формате YYYY-MM-DD",
    "registry_office": "Название ЗАГСа или органа регистрации",
}

NATIONAL_ID_SCHEMA = {
    "full_name": "ФИО владельца",
    "id_number": "Номер удостоверения",
    "date_of_birth": "Дата рождения в формате YYYY-MM-DD",
    "issue_date": "Дата выдачи в формате YYYY-MM-DD",
    "expiry_date": "Дата окончания в формате YYYY-MM-DD",
}

# =============================================================================
# EDUCATION DOCUMENTS
# =============================================================================

SCHOOL_CERTIFICATE_SCHEMA = {
    "full_name": "ФИО выпускника",
    "school_name": "Название школы",
    "graduation_year": "Год окончания (число)",
    "certificate_number": "Номер аттестата",
    "gpa": "Средний балл",
}

DIPLOMA_SCHEMA = {
    "full_name": "ФИО выпускника",
    "institution_name": "Название учебного заведения",
    "institution_name_en": "Название учебного заведения на английском",
    "degree_type": "Тип степени (Бакалавр/Магистр/Кандидат наук/Доктор наук/PhD)",
    "field_of_study": "Специальность / направление подготовки",
    "graduation_date": "Дата выдачи диплома в формате YYYY-MM-DD",
    "diploma_number": "Номер диплома",
    "honors": "С отличием / Cum Laude / другие почести (если есть)",
    "thesis_title": "Тема диссертации (для PhD/кандидатов наук)",
}

TRANSCRIPT_SCHEMA = {
    "full_name": "ФИО студента",
    "institution_name": "Название учебного заведения",
    "total_credits": "Общее количество кредитов/часов (число)",
    "gpa": "Средний балл GPA (число с точкой)",
}

# =============================================================================
# EB-1A CRITERION 1: AWARDS
# =============================================================================

AWARD_SCHEMA = {
    "recipient_name": "ФИО получателя награды",
    "award_name": "Название награды/премии",
    "award_name_en": "Название награды на английском",
    "awarding_organization": "Организация, вручившая награду",
    "award_date": "Дата вручения в формате YYYY-MM-DD",
    "award_category": "Категория/номинация",
    "competition_name": "Название конкурса/соревнования (если применимо)",
    "place_rank": "Место (1-е место, 2-е место, лауреат и т.д.)",
    "num_participants": "Количество участников (число, если указано)",
    "geographic_scope": "Масштаб (Международный/Национальный/Региональный)",
}

# =============================================================================
# EB-1A CRITERION 2: MEMBERSHIP
# =============================================================================

MEMBERSHIP_SCHEMA = {
    "member_name": "ФИО члена организации",
    "organization_name": "Название организации",
    "organization_name_en": "Название организации на английском",
    "membership_type": "Тип членства (Fellow/Member/Associate)",
    "membership_number": "Номер членства/удостоверения",
    "start_date": "Дата начала членства в формате YYYY-MM-DD",
    "expiry_date": "Дата окончания членства в формате YYYY-MM-DD",
    "selection_criteria": "Критерии отбора для вступления",
}

# =============================================================================
# EB-1A CRITERION 3: PRESS
# =============================================================================

PRESS_ARTICLE_SCHEMA = {
    "article_title": "Заголовок статьи",
    "publication_name": "Название издания (газета, журнал, сайт)",
    "publication_date": "Дата публикации в формате YYYY-MM-DD",
    "author_name": "Автор статьи",
    "subject_name": "О ком статья (ФИО)",
    "article_url": "URL статьи (если есть)",
    "circulation": "Тираж/охват издания (число)",
}

# =============================================================================
# EB-1A CRITERION 4: JUDGING
# =============================================================================

JUDGING_SCHEMA = {
    "reviewer_name": "ФИО рецензента/эксперта",
    "organization_name": "Название организации (журнал, конференция, фонд)",
    "role": "Роль (Рецензент/Член жюри/Эксперт/Член редколлегии)",
    "review_period": "Период работы",
    "num_reviews": "Количество рецензий/оценок (число)",
    "subject_area": "Область экспертизы",
}

# =============================================================================
# EB-1A CRITERION 5: CONTRIBUTION (Patents)
# =============================================================================

PATENT_SCHEMA = {
    "inventor_name": "ФИО изобретателя",
    "patent_title": "Название изобретения",
    "patent_number": "Номер патента",
    "filing_date": "Дата подачи заявки в формате YYYY-MM-DD",
    "grant_date": "Дата выдачи патента в формате YYYY-MM-DD",
    "patent_office": "Патентное ведомство (USPTO/EPO/WIPO/Роспатент)",
    "classification": "Классификация патента (МПК)",
    "claims_count": "Количество пунктов формулы (число)",
    "citations_count": "Количество цитирований патента (число)",
}

# =============================================================================
# EB-1A CRITERION 6: SCHOLARLY ARTICLES
# =============================================================================

PUBLICATION_SCHEMA = {
    "title": "Название статьи",
    "authors": "Список авторов через запятую",
    "applicant_position": "Позиция заявителя в списке авторов (число: 1, 2, 3...)",
    "journal_name": "Название журнала/конференции",
    "journal_impact_factor": "Импакт-фактор журнала (число с точкой)",
    "publication_date": "Дата публикации в формате YYYY-MM-DD",
    "volume": "Том",
    "issue": "Выпуск/номер",
    "pages": "Страницы (например: 123-145)",
    "doi": "DOI статьи",
    "issn": "ISSN журнала",
}

CITATION_REPORT_SCHEMA = {
    "author_name": "ФИО автора",
    "source": "Источник данных (Google Scholar/Scopus/Web of Science)",
    "total_citations": "Общее количество цитирований (число)",
    "h_index": "Индекс Хирша h-index (число)",
    "i10_index": "Индекс i10 (число)",
    "report_date": "Дата отчёта в формате YYYY-MM-DD",
}

# =============================================================================
# EB-1A CRITERION 7: EXHIBITION
# =============================================================================

EXHIBITION_SCHEMA = {
    "artist_name": "ФИО художника/автора",
    "exhibition_name": "Название выставки",
    "venue": "Место проведения (галерея, музей)",
    "exhibition_dates": "Даты проведения",
    "curator": "Куратор выставки",
    "num_artworks": "Количество работ (число)",
}

# =============================================================================
# EB-1A CRITERION 8: LEADERSHIP
# =============================================================================

LEADERSHIP_SCHEMA = {
    "person_name": "ФИО руководителя",
    "organization_name": "Название организации",
    "position_title": "Должность",
    "start_date": "Дата начала работы в формате YYYY-MM-DD",
    "end_date": "Дата окончания работы в формате YYYY-MM-DD (или 'по настоящее время')",
    "num_subordinates": "Количество подчинённых (число)",
    "budget_managed": "Бюджет под управлением (сумма с валютой)",
    "key_achievements": "Ключевые достижения через точку с запятой",
}

# =============================================================================
# EB-1A CRITERION 9: HIGH SALARY
# =============================================================================

SALARY_SCHEMA = {
    "employee_name": "ФИО сотрудника",
    "employer_name": "Название работодателя",
    "position_title": "Должность",
    "salary_amount": "Сумма зарплаты (число)",
    "salary_currency": "Валюта (USD/EUR/RUB и т.д.)",
    "salary_period": "Период (Annual/Monthly/Yearly)",
    "start_date": "Дата начала работы в формате YYYY-MM-DD",
    "bonus": "Бонус (если указан)",
    "stock_options": "Опционы/акции (если указаны)",
    "location": "Место работы (город, страна)",
}

# =============================================================================
# EB-1A CRITERION 10: COMMERCIAL SUCCESS
# =============================================================================

COMMERCIAL_SUCCESS_SCHEMA = {
    "product_name": "Название продукта/проекта",
    "creator_name": "ФИО создателя",
    "revenue": "Выручка/доход (число)",
    "revenue_currency": "Валюта",
    "sales_units": "Количество продаж (число)",
    "time_period": "Период (например: 2020-2023)",
    "market": "Рынок (страна/регион)",
}

# =============================================================================
# CAREER / EMPLOYMENT
# =============================================================================

EMPLOYMENT_CONTRACT_SCHEMA = {
    "employee_name": "ФИО сотрудника",
    "employer_name": "Название работодателя",
    "position_title": "Должность",
    "start_date": "Дата начала работы в формате YYYY-MM-DD",
    "end_date": "Дата окончания работы в формате YYYY-MM-DD",
    "salary": "Зарплата (сумма с валютой)",
    "responsibilities": "Обязанности через точку с запятой",
}

RECOMMENDATION_LETTER_SCHEMA = {
    "recommender_name": "ФИО рекомендателя",
    "recommender_title": "Должность рекомендателя",
    "recommender_organization": "Организация рекомендателя",
    "applicant_name": "ФИО рекомендуемого (заявителя)",
    "relationship": "Как рекомендатель знает заявителя",
    "years_known": "Сколько лет знакомы (число)",
    "letter_date": "Дата письма в формате YYYY-MM-DD",
    "key_qualities": "Ключевые качества через точку с запятой",
    "specific_achievements": "Конкретные достижения через точку с запятой",
}

WORK_REFERENCE_SCHEMA = {
    "employee_name": "ФИО сотрудника",
    "employer_name": "Название работодателя",
    "position_title": "Должность",
    "employment_period": "Период работы",
    "reference_author": "Автор рекомендации",
    "reference_author_title": "Должность автора рекомендации",
}

# =============================================================================
# SCHEMA MAPPING BY DOCUMENT TYPE ID
# =============================================================================

EXTRACTION_SCHEMAS: dict[str, dict[str, str]] = {
    # Identity
    "passport": PASSPORT_SCHEMA,
    "birth_certificate": BIRTH_CERTIFICATE_SCHEMA,
    "national_id": NATIONAL_ID_SCHEMA,
    # Education
    "school_certificate": SCHOOL_CERTIFICATE_SCHEMA,
    "bachelor_diploma": DIPLOMA_SCHEMA,
    "master_diploma": DIPLOMA_SCHEMA,
    "phd_diploma": DIPLOMA_SCHEMA,
    "transcript": TRANSCRIPT_SCHEMA,
    # EB-1A Criterion 1: Awards
    "award_certificate": AWARD_SCHEMA,
    "competition_winner": AWARD_SCHEMA,
    # EB-1A Criterion 2: Membership
    "membership_certificate": MEMBERSHIP_SCHEMA,
    # EB-1A Criterion 3: Press
    "press_article": PRESS_ARTICLE_SCHEMA,
    # EB-1A Criterion 4: Judging
    "judging_evidence": JUDGING_SCHEMA,
    # EB-1A Criterion 5: Contribution
    "patent": PATENT_SCHEMA,
    "invention_certificate": PATENT_SCHEMA,
    # EB-1A Criterion 6: Scholarly Articles
    "publication": PUBLICATION_SCHEMA,
    "citation_report": CITATION_REPORT_SCHEMA,
    # EB-1A Criterion 7: Exhibition
    "exhibition_catalog": EXHIBITION_SCHEMA,
    # EB-1A Criterion 8: Leadership
    "leadership_evidence": LEADERSHIP_SCHEMA,
    # EB-1A Criterion 9: High Salary
    "salary_document": SALARY_SCHEMA,
    "offer_letter": SALARY_SCHEMA,
    # EB-1A Criterion 10: Commercial Success
    "commercial_success": COMMERCIAL_SUCCESS_SCHEMA,
    # Career
    "employment_contract": EMPLOYMENT_CONTRACT_SCHEMA,
    "recommendation_letter": RECOMMENDATION_LETTER_SCHEMA,
    "work_reference": WORK_REFERENCE_SCHEMA,
}


def get_schema_for_document_type(doc_type_id: str) -> dict[str, str] | None:
    """Get extraction schema for a document type."""
    return EXTRACTION_SCHEMAS.get(doc_type_id)


def get_all_document_types_with_schemas() -> list[str]:
    """Get list of all document types that have extraction schemas."""
    return list(EXTRACTION_SCHEMAS.keys())
