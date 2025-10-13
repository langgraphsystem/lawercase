"""
EB1Agent - Интерактивный агент для EB-1A петиций

Обеспечивает:
- Conversational интерфейс для сбора данных
- Оценку соответствия 10 критериям USCIS
- Генерацию документов (I-140, Cover Letter, Evidence Lists)
- Интеграцию с MemoryManager
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent, MemoryRecord
from .eb1_models import (
    EB1_QUESTIONNAIRE_TEMPLATES,
    EB1Answer,
    EB1ConversationState,
    EB1Criterion,
    EB1CriterionEvidence,
    EB1FieldOfExpertise,
    EB1PersonalInfo,
    EB1PetitionData,
    EB1PetitionStatus,
    EB1Question,
    EB1QuestionnaireStep,
)


class EB1Agent:
    """
    Агент для управления EB-1A петициями с conversational интерфейсом.

    Основной workflow:
    1. Пользователь: "Хочу создать EB-1A петицию"
    2. Агент создает petition и начинает интерактивный опрос
    3. Собирает данные по 10 критериям USCIS
    4. Анализирует соответствие (нужно минимум 3 из 10)
    5. Генерирует документы если критерии выполнены
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        """
        Инициализация EB1Agent.

        Args:
            memory_manager: Менеджер памяти
        """
        self.memory = memory_manager or MemoryManager()

        # Хранилище петиций
        self._petitions: dict[str, EB1PetitionData] = {}

        # Хранилище состояний диалогов
        self._conversations: dict[str, EB1ConversationState] = {}

        # Вопросники по этапам
        self._questionnaires = EB1_QUESTIONNAIRE_TEMPLATES

    # ========== ОСНОВНЫЕ ОПЕРАЦИИ ==========

    async def create_petition(self, user_id: str) -> tuple[EB1PetitionData, str]:
        """
        Создание новой EB-1A петиции и начало интерактивного процесса.

        Args:
            user_id: ID пользователя

        Returns:
            tuple: (EB1PetitionData, welcome_message)
        """
        petition_id = f"eb1_{uuid.uuid4().hex[:12]}"

        # Создание петиции
        petition = EB1PetitionData(
            petition_id=petition_id,
            user_id=user_id,
            status=EB1PetitionStatus.DATA_COLLECTION,
            current_step=EB1QuestionnaireStep.PERSONAL_INFO,
        )

        self._petitions[petition_id] = petition

        # Создание состояния диалога
        conversation = EB1ConversationState(
            petition_id=petition_id,
            current_step=EB1QuestionnaireStep.PERSONAL_INFO,
            awaiting_input=True,
        )

        self._conversations[petition_id] = conversation

        # Audit log
        await self._log_audit(
            user_id=user_id,
            action="create_eb1_petition",
            payload={"petition_id": petition_id},
        )

        # Сохранение в память
        await self._store_petition_memory(petition, user_id, "created")

        # Генерация приветственного сообщения
        welcome_message = self._generate_welcome_message(petition_id)

        # Первый вопрос
        first_question = await self.get_next_question(petition_id)
        conversation.last_bot_message = welcome_message + "\n\n" + first_question

        return petition, conversation.last_bot_message

    async def process_user_message(self, petition_id: str, user_message: str, user_id: str) -> str:
        """
        Обработка сообщения пользователя в контексте петиции.

        Args:
            petition_id: ID петиции
            user_message: Сообщение пользователя
            user_id: ID пользователя

        Returns:
            str: Ответ бота
        """
        petition = self._petitions.get(petition_id)
        conversation = self._conversations.get(petition_id)

        if not petition or not conversation:
            return f"❌ Петиция {petition_id} не найдена. Создайте новую петицию командой '/create_eb1'"

        # Сохранение ответа
        response = await self._process_answer(petition, conversation, user_message, user_id)

        # Обновление памяти
        await self._store_interaction_memory(petition_id, user_message, response, user_id)

        return response

    async def get_next_question(self, petition_id: str) -> str:
        """
        Получение следующего вопроса для пользователя.

        Args:
            petition_id: ID петиции

        Returns:
            str: Текст следующего вопроса
        """
        conversation = self._conversations.get(petition_id)
        if not conversation:
            return "❌ Диалог не найден"

        petition = self._petitions[petition_id]
        current_step = conversation.current_step

        # Проверка завершения опросника
        if current_step == EB1QuestionnaireStep.COMPLETED:
            return await self._generate_completion_message(petition)

        # Получение вопросов для текущего этапа
        questions = self._questionnaires.get(current_step, [])

        # Поиск следующего невыполненного вопроса
        for question in questions:
            if question.question_id not in conversation.answers:
                conversation.current_question_id = question.question_id
                return self._format_question(question)

        # Все вопросы этапа завершены - переход к следующему этапу
        return await self._advance_to_next_step(petition, conversation)

    # ========== ОБРАБОТКА ОТВЕТОВ ==========

    async def _process_answer(
        self,
        petition: EB1PetitionData,
        conversation: EB1ConversationState,
        user_message: str,
        user_id: str,
    ) -> str:
        """Обработка ответа пользователя"""

        current_question_id = conversation.current_question_id
        if not current_question_id:
            return "❌ Не найден текущий вопрос. Попробуйте /status"

        # Получение вопроса
        question = self._get_question_by_id(current_question_id)
        if not question:
            return "❌ Вопрос не найден"

        # Валидация ответа
        validation_result = self._validate_answer(question, user_message)
        if not validation_result["valid"]:
            return f"❌ {validation_result['error']}\n\n{self._format_question(question)}"

        # Сохранение ответа
        answer = EB1Answer(
            question_id=current_question_id,
            answer=validation_result["parsed_value"],
            answered_at=datetime.utcnow(),
        )

        conversation.answers[current_question_id] = answer

        # Обновление данных петиции
        await self._update_petition_from_answer(petition, question, answer)

        # Обновление evidence если это вопрос о критерии
        if question.criterion:
            await self._update_criterion_evidence(petition, question, answer)

        # Подтверждение и следующий вопрос
        confirmation = f"✅ Записано: {self._format_answer_confirmation(question, answer)}"

        next_question = await self.get_next_question(petition.petition_id)

        return f"{confirmation}\n\n{next_question}"

    def _validate_answer(self, question: EB1Question, user_message: str) -> dict[str, Any]:
        """Валидация ответа пользователя"""

        user_message = user_message.strip()

        if question.question_type == "yes_no":
            lower = user_message.lower()
            if lower in ["да", "yes", "y", "д", "+", "1", "true"]:
                return {"valid": True, "parsed_value": True}
            if lower in ["нет", "no", "n", "н", "-", "0", "false"]:
                return {"valid": True, "parsed_value": False}
            return {
                "valid": False,
                "error": "Пожалуйста, ответьте 'да' или 'нет'",
            }

        if question.question_type == "number":
            try:
                value = float(user_message.replace(",", "").replace(" ", ""))
                rules = question.validation_rules
                if "min" in rules and value < rules["min"]:
                    return {
                        "valid": False,
                        "error": f"Значение должно быть больше {rules['min']}",
                    }
                if "max" in rules and value > rules["max"]:
                    return {
                        "valid": False,
                        "error": f"Значение должно быть меньше {rules['max']}",
                    }
                return {"valid": True, "parsed_value": value}
            except ValueError:
                return {"valid": False, "error": "Пожалуйста, введите число"}

        if question.question_type == "text":
            if question.required and not user_message:
                return {"valid": False, "error": "Это обязательное поле"}

            rules = question.validation_rules
            if "format" in rules and rules["format"] == "email":
                if "@" not in user_message or "." not in user_message.split("@")[1]:
                    return {"valid": False, "error": "Введите корректный email адрес"}

            return {"valid": True, "parsed_value": user_message}

        if question.question_type == "list":
            # Разделение по новым строкам или запятым
            items = [
                item.strip() for item in user_message.replace("\n", ",").split(",") if item.strip()
            ]
            return {"valid": True, "parsed_value": items}

        return {"valid": True, "parsed_value": user_message}

    async def _update_petition_from_answer(
        self, petition: EB1PetitionData, question: EB1Question, answer: EB1Answer
    ) -> None:
        """Обновление данных петиции на основе ответа"""

        qid = question.question_id
        value = answer.answer

        # Personal Info
        if qid == "personal_full_name":
            if not petition.personal_info:
                petition.personal_info = EB1PersonalInfo(
                    full_name=value, email="", current_country=""
                )
            else:
                petition.personal_info.full_name = value

        elif qid == "personal_email":
            if petition.personal_info:
                petition.personal_info.email = value

        elif qid == "personal_country":
            if petition.personal_info:
                petition.personal_info.current_country = value

        elif qid == "personal_visa_status":
            if petition.personal_info:
                petition.personal_info.current_visa_status = value

        # Field of Expertise
        elif qid == "field_main":
            if not petition.field_of_expertise:
                petition.field_of_expertise = EB1FieldOfExpertise(
                    field=value,
                    years_of_experience=0,
                    current_position="",
                    education_level="",
                )
            else:
                petition.field_of_expertise.field = value

        elif qid == "field_years":
            if petition.field_of_expertise:
                petition.field_of_expertise.years_of_experience = int(value)

        elif qid == "field_position":
            if petition.field_of_expertise:
                petition.field_of_expertise.current_position = value

        elif qid == "field_education":
            if petition.field_of_expertise:
                petition.field_of_expertise.education_level = value

        petition.updated_at = datetime.utcnow()

    async def _update_criterion_evidence(
        self, petition: EB1PetitionData, question: EB1Question, answer: EB1Answer
    ) -> None:
        """Обновление доказательств по критерию"""

        if not question.criterion:
            return

        criterion_key = question.criterion.value

        # Инициализация evidence если нет
        if criterion_key not in petition.criteria_evidence:
            petition.criteria_evidence[criterion_key] = EB1CriterionEvidence(
                criterion=question.criterion
            )

        evidence = petition.criteria_evidence[criterion_key]

        # Обработка вопроса "has" (есть ли доказательства)
        if question.question_id.endswith("_has"):
            evidence.met = bool(answer.answer)

        # Обработка вопроса "list" (список доказательств)
        elif question.question_id.endswith("_list"):
            if isinstance(answer.answer, list):
                for item in answer.answer:
                    evidence.evidence_items.append({"description": item, "type": "text"})
                evidence.evidence_count = len(evidence.evidence_items)
                evidence.description = "\n".join(answer.answer)

        # Обработка специфичных вопросов
        elif question.question_id == "scholarly_count":
            evidence.evidence_count = int(answer.answer)
            evidence.evidence_items.append(
                {"type": "publications_count", "count": int(answer.answer)}
            )

        elif question.question_id == "scholarly_citations":
            evidence.evidence_items.append({"type": "citations_count", "count": int(answer.answer)})

        elif question.question_id == "salary_amount":
            evidence.evidence_items.append({"type": "salary", "amount_usd": float(answer.answer)})

        # Обновление силы доказательств
        evidence.strength_score = self._calculate_evidence_strength(evidence)

    def _calculate_evidence_strength(self, evidence: EB1CriterionEvidence) -> float:
        """Расчет силы доказательств для критерия"""

        if not evidence.met:
            return 0.0

        score = 0.5  # Базовый балл за наличие доказательств

        # Бонусы за количество
        if evidence.evidence_count > 0:
            score += min(0.3, evidence.evidence_count * 0.05)

        # Специфичные бонусы
        for item in evidence.evidence_items:
            if item.get("type") == "citations_count" and item.get("count", 0) > 100:
                score += 0.1
            if item.get("type") == "salary" and item.get("amount_usd", 0) > 150000:
                score += 0.1

        return min(1.0, score)

    # ========== НАВИГАЦИЯ ПО ЭТАПАМ ==========

    async def _advance_to_next_step(
        self, petition: EB1PetitionData, conversation: EB1ConversationState
    ) -> str:
        """Переход к следующему этапу опросника"""

        current_step = conversation.current_step
        conversation.completed_steps.append(current_step)

        # Определение следующего этапа
        all_steps = list(EB1QuestionnaireStep)
        current_index = all_steps.index(current_step)

        if current_index + 1 < len(all_steps):
            next_step = all_steps[current_index + 1]
            conversation.current_step = next_step
            petition.current_step = next_step

            # Специальная логика для пропуска критериев
            if next_step == EB1QuestionnaireStep.REVIEW_SUMMARY:
                return await self._generate_criteria_summary(petition, conversation)

            return (
                f"✅ Раздел '{self._get_step_name(current_step)}' завершен!\n\n"
                + await self.get_next_question(petition.petition_id)
            )

        # Завершение опросника
        conversation.current_step = EB1QuestionnaireStep.COMPLETED
        return await self._finalize_petition(petition, conversation)

    async def _generate_criteria_summary(
        self, petition: EB1PetitionData, conversation: EB1ConversationState
    ) -> str:
        """Генерация итоговой сводки по критериям"""

        # Подсчет критериев
        met_criteria = []
        not_met_criteria = []

        for criterion in EB1Criterion:
            evidence = petition.criteria_evidence.get(criterion.value)
            if evidence and evidence.met:
                met_criteria.append(criterion)
            else:
                not_met_criteria.append(criterion)

        petition.criteria_met_count = len(met_criteria)

        # Оценка eligibility (нужно минимум 3 критерия)
        if len(met_criteria) >= 3:
            petition.eligibility_score = min(1.0, len(met_criteria) / 10.0 + 0.3)
            petition.recommendation = "✅ РЕКОМЕНДУЕТСЯ подавать петицию EB-1A"
            petition.status = EB1PetitionStatus.READY_FOR_FILING
        else:
            petition.eligibility_score = len(met_criteria) / 10.0
            petition.recommendation = (
                "⚠️ Недостаточно критериев. Рекомендуется собрать больше доказательств."
            )
            petition.status = EB1PetitionStatus.CRITERIA_REVIEW

        # Формирование сообщения
        summary = "📊 ИТОГОВАЯ ОЦЕНКА СООТВЕТСТВИЯ EB-1A\n"
        summary += "=" * 50 + "\n\n"

        summary += f"✅ Соответствует критериям: {len(met_criteria)}/10\n"
        summary += f"📈 Оценка: {petition.eligibility_score:.0%}\n"
        summary += f"💡 {petition.recommendation}\n\n"

        summary += "✅ Выполненные критерии:\n"
        for i, criterion in enumerate(met_criteria, 1):
            evidence = petition.criteria_evidence[criterion.value]
            summary += f"  {i}. {self._get_criterion_name(criterion)} "
            summary += f"(сила: {evidence.strength_score:.0%})\n"

        if not_met_criteria:
            summary += "\n❌ Не выполненные критерии:\n"
            for criterion in not_met_criteria:
                summary += f"  - {self._get_criterion_name(criterion)}\n"

        summary += "\n" + ("=" * 50) + "\n"

        if len(met_criteria) >= 3:
            summary += "\n🎉 Отлично! Вы соответствуете минимальным требованиям для EB-1A.\n"
            summary += "Хотите, чтобы я подготовил документы для подачи? (да/нет)"
            conversation.current_step = EB1QuestionnaireStep.DOCUMENT_GENERATION
        else:
            summary += "\n⚠️ Для EB-1A нужно минимум 3 критерия из 10.\n"
            summary += "Рекомендации:\n"
            summary += "1. Соберите больше доказательств по невыполненным критериям\n"
            summary += "2. Рассмотрите альтернативные визовые категории (EB-2 NIW, O-1)\n"
            summary += "3. Обратитесь к иммиграционному адвокату для детального разбора\n\n"
            summary += "Сохранить текущий прогресс? (да/нет)"
            conversation.current_step = EB1QuestionnaireStep.COMPLETED

        conversation.last_bot_message = summary
        return summary

    async def _finalize_petition(
        self, petition: EB1PetitionData, conversation: EB1ConversationState
    ) -> str:
        """Завершение и сохранение петиции"""

        petition.completed_at = datetime.utcnow()
        petition.updated_at = datetime.utcnow()

        # Сохранение в память
        await self._store_petition_memory(petition, petition.user_id, "completed")

        return (
            "✅ Петиция сохранена!\n\n"
            f"📋 ID петиции: {petition.petition_id}\n"
            f"📊 Критериев выполнено: {petition.criteria_met_count}/10\n"
            f"📈 Оценка: {petition.eligibility_score:.0%}\n\n"
            "Вы можете:\n"
            "- /status <petition_id> - Посмотреть статус\n"
            "- /generate_docs <petition_id> - Сгенерировать документы\n"
            "- /create_eb1 - Создать новую петицию"
        )

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    def _get_question_by_id(self, question_id: str) -> EB1Question | None:
        """Поиск вопроса по ID"""
        for questions in self._questionnaires.values():
            for question in questions:
                if question.question_id == question_id:
                    return question
        return None

    def _format_question(self, question: EB1Question) -> str:
        """Форматирование вопроса для пользователя"""
        text = f"❓ {question.question_text}"
        if question.help_text:
            text += f"\n💡 {question.help_text}"
        if not question.required:
            text += "\n(Опционально - можете пропустить командой /skip)"
        return text

    def _format_answer_confirmation(self, question: EB1Question, answer: EB1Answer) -> str:
        """Форматирование подтверждения ответа"""
        value = answer.answer
        if isinstance(value, bool):
            return "Да" if value else "Нет"
        if isinstance(value, list):
            return f"{len(value)} пунктов"
        return str(value)[:100]

    def _generate_welcome_message(self, petition_id: str) -> str:
        """Генерация приветственного сообщения"""
        return (
            "🇺🇸 СОЗДАНИЕ ПЕТИЦИИ EB-1A\n"
            "=" * 50 + "\n\n"
            "Добро пожаловать в процесс подготовки петиции EB-1A!\n\n"
            "EB-1A - это виза для людей с экстраординарными способностями\n"
            "в науке, искусстве, образовании, бизнесе или спорте.\n\n"
            "📋 Я задам вам вопросы по 10 критериям USCIS.\n"
            "✅ Для подачи нужно соответствовать минимум 3 из 10 критериев.\n"
            "⏱️ Процесс займет 15-30 минут.\n\n"
            f"🆔 ID вашей петиции: {petition_id}\n\n"
            "Начнем с персональной информации:"
        )

    async def _generate_completion_message(self, petition: EB1PetitionData) -> str:
        """Сообщение о завершении"""
        return (
            "🎉 Поздравляю! Опросник завершен.\n\n"
            f"Критериев выполнено: {petition.criteria_met_count}/10\n"
            f"Оценка: {petition.eligibility_score:.0%}\n\n"
            f"{petition.recommendation}"
        )

    def _get_step_name(self, step: EB1QuestionnaireStep) -> str:
        """Получение названия этапа"""
        names = {
            EB1QuestionnaireStep.PERSONAL_INFO: "Персональная информация",
            EB1QuestionnaireStep.FIELD_OF_EXPERTISE: "Область экспертизы",
            EB1QuestionnaireStep.CRITERION_AWARDS: "Критерий 1: Награды",
            EB1QuestionnaireStep.CRITERION_MEMBERSHIP: "Критерий 2: Членство",
            EB1QuestionnaireStep.CRITERION_PRESS: "Критерий 3: Публикации в СМИ",
            EB1QuestionnaireStep.CRITERION_JUDGING: "Критерий 4: Судейство",
            EB1QuestionnaireStep.CRITERION_CONTRIBUTION: "Критерий 5: Оригинальный вклад",
            EB1QuestionnaireStep.CRITERION_SCHOLARLY: "Критерий 6: Научные публикации",
            EB1QuestionnaireStep.CRITERION_EXHIBITION: "Критерий 7: Выставки",
            EB1QuestionnaireStep.CRITERION_LEADERSHIP: "Критерий 8: Лидерство",
            EB1QuestionnaireStep.CRITERION_SALARY: "Критерий 9: Высокая зарплата",
            EB1QuestionnaireStep.CRITERION_COMMERCIAL: "Критерий 10: Коммерческий успех",
        }
        return names.get(step, step.value)

    def _get_criterion_name(self, criterion: EB1Criterion) -> str:
        """Получение названия критерия"""
        names = {
            EB1Criterion.AWARDS: "Национальные/международные премии",
            EB1Criterion.MEMBERSHIP: "Членство в ассоциациях",
            EB1Criterion.PRESS: "Публикации в СМИ о вас",
            EB1Criterion.JUDGING: "Судейство работ других",
            EB1Criterion.CONTRIBUTION: "Оригинальный вклад в область",
            EB1Criterion.SCHOLARLY: "Научные публикации",
            EB1Criterion.EXHIBITION: "Выставки работ",
            EB1Criterion.LEADERSHIP: "Лидерские роли",
            EB1Criterion.SALARY: "Высокая зарплата",
            EB1Criterion.COMMERCIAL: "Коммерческий успех",
        }
        return names.get(criterion, criterion.value)

    # ========== ПУБЛИЧНЫЕ МЕТОДЫ ДЛЯ УПРАВЛЕНИЯ ==========

    async def get_petition_status(self, petition_id: str) -> dict[str, Any]:
        """Получение статуса петиции"""
        petition = self._petitions.get(petition_id)
        if not petition:
            return {"error": "Petition not found"}

        conversation = self._conversations.get(petition_id)

        return {
            "petition_id": petition.petition_id,
            "status": petition.status.value,
            "current_step": petition.current_step.value,
            "criteria_met": petition.criteria_met_count,
            "eligibility_score": petition.eligibility_score,
            "recommendation": petition.recommendation,
            "completed_steps": len(conversation.completed_steps) if conversation else 0,
            "total_questions_answered": len(conversation.answers) if conversation else 0,
        }

    async def get_petition(self, petition_id: str) -> EB1PetitionData | None:
        """Получение полных данных петиции"""
        return self._petitions.get(petition_id)

    # ========== ПАМЯТЬ И АУДИТ ==========

    async def _log_audit(self, user_id: str, action: str, payload: dict[str, Any]) -> None:
        """Логирование audit события"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"eb1_agent_{user_id}",
            source="eb1_agent",
            action=action,
            payload=payload,
            tags=["eb1", "immigration"],
        )
        await self.memory.alog_audit(event)

    async def _store_petition_memory(
        self, petition: EB1PetitionData, user_id: str, action: str
    ) -> None:
        """Сохранение петиции в семантическую память"""
        memory_text = (
            f"EB-1A Petition {action}: {petition.petition_id}, "
            f"status={petition.status.value}, criteria_met={petition.criteria_met_count}"
        )

        record = MemoryRecord(
            text=memory_text,
            user_id=user_id,
            type="semantic",
            metadata={
                "petition_id": petition.petition_id,
                "action": action,
                "criteria_met": petition.criteria_met_count,
                "eligibility_score": petition.eligibility_score,
            },
            tags=["eb1", "petition"],
        )

        await self.memory.awrite([record])

    async def _store_interaction_memory(
        self, petition_id: str, user_message: str, bot_response: str, user_id: str
    ) -> None:
        """Сохранение взаимодействия в память"""
        memory_text = f"EB1 Q&A - User: {user_message[:100]}... Bot: {bot_response[:100]}..."

        record = MemoryRecord(
            text=memory_text,
            user_id=user_id,
            type="episodic",
            metadata={"petition_id": petition_id},
            tags=["eb1", "conversation"],
        )

        await self.memory.awrite([record])
