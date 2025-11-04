# LangGraph Architecture Patterns для mega_agent_pro

## 🎯 Основные архитектурные паттерны

### 1. Supervisor Pattern
**Назначение**: Центральное управление и маршрутизация задач между агентами

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from typing import Literal

class SupervisorState(TypedDict):
    task: str
    selected_agents: List[str]
    agent_results: Dict[str, Any]
    final_result: Any
    routing_reasoning: str

def create_supervisor_workflow():
    """Создание supervisor workflow с динамической маршрутизацией"""

    workflow = StateGraph(SupervisorState)

    # Узел анализа задачи
    workflow.add_node("analyze_task", analyze_task_node)

    # Узел выбора агентов
    workflow.add_node("select_agents", select_agents_node)

    # Узлы специализированных агентов
    workflow.add_node("case_agent", case_agent_node)
    workflow.add_node("writer_agent", writer_agent_node)
    workflow.add_node("validator_agent", validator_agent_node)
    workflow.add_node("rag_agent", rag_agent_node)

    # Узел синтеза результатов
    workflow.add_node("synthesize_results", synthesize_results_node)

    # Маршрутизация
    workflow.add_edge(START, "analyze_task")
    workflow.add_edge("analyze_task", "select_agents")

    # Условная маршрутизация к агентам
    workflow.add_conditional_edges(
        "select_agents",
        route_to_agents,
        {
            "case_processing": "case_agent",
            "document_generation": "writer_agent",
            "validation": "validator_agent",
            "information_retrieval": "rag_agent",
            "parallel_processing": "parallel_execution"
        }
    )

    # Возврат к синтезу
    workflow.add_edge("case_agent", "synthesize_results")
    workflow.add_edge("writer_agent", "synthesize_results")
    workflow.add_edge("validator_agent", "synthesize_results")
    workflow.add_edge("rag_agent", "synthesize_results")

    workflow.add_edge("synthesize_results", END)

    return workflow.compile()

async def analyze_task_node(state: SupervisorState) -> SupervisorState:
    """Анализ задачи с помощью LLM"""

    analysis_prompt = f"""
    Проанализируй следующую задачу и определи её тип и сложность:

    Задача: {state['task']}

    Верни анализ в формате JSON:
    {{
        "task_type": "case_creation|document_generation|validation|research|complex",
        "complexity": "simple|medium|complex",
        "required_agents": ["agent1", "agent2"],
        "estimated_time": "время в минутах",
        "dependencies": ["зависимость1", "зависимость2"]
    }}
    """

    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    response = await llm.ainvoke([HumanMessage(content=analysis_prompt)])

    analysis = json.loads(response.content)
    state['task_analysis'] = analysis

    return state
```

### 2. Fan-out/Fan-in Pattern
**Назначение**: Параллельное выполнение задач с последующим объединением результатов

```python
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

class ParallelProcessingState(TypedDict):
    query: str
    parallel_tasks: List[str]
    agent_results: Dict[str, Any]
    merged_result: Any

def create_parallel_workflow():
    """Workflow для параллельной обработки"""

    workflow = StateGraph(ParallelProcessingState)

    # Узел разделения задач
    workflow.add_node("split_tasks", split_tasks_node)

    # Параллельные узлы
    workflow.add_node("rag_search", rag_search_node)
    workflow.add_node("legal_research", legal_research_node)
    workflow.add_node("case_analysis", case_analysis_node)

    # Узел объединения
    workflow.add_node("merge_results", merge_results_node)

    # Fan-out маршрутизация
    workflow.add_conditional_edges(
        "split_tasks",
        fan_out_routing,
        ["rag_search", "legal_research", "case_analysis"]
    )

    # Fan-in - все пути ведут к объединению
    workflow.add_edge("rag_search", "merge_results")
    workflow.add_edge("legal_research", "merge_results")
    workflow.add_edge("case_analysis", "merge_results")

    workflow.add_edge("merge_results", END)

    return workflow.compile()

async def fan_out_routing(state: ParallelProcessingState) -> List[Send]:
    """Динамическое создание параллельных задач"""

    sends = []
    for task in state['parallel_tasks']:
        if task == "rag_search":
            sends.append(Send("rag_search", {"query": state['query'], "task_type": "rag"}))
        elif task == "legal_research":
            sends.append(Send("legal_research", {"query": state['query'], "task_type": "legal"}))
        elif task == "case_analysis":
            sends.append(Send("case_analysis", {"query": state['query'], "task_type": "case"}))

    return sends

async def merge_results_node(state: ParallelProcessingState) -> ParallelProcessingState:
    """Интеллектуальное объединение результатов"""

    # Сбор всех результатов
    all_results = state['agent_results']

    # LLM-based синтез
    synthesis_prompt = f"""
    Объедини следующие результаты от разных агентов в единый ответ:

    RAG результат: {all_results.get('rag_search', '')}
    Юридическое исследование: {all_results.get('legal_research', '')}
    Анализ дела: {all_results.get('case_analysis', '')}

    Создай связный и полный ответ, учитывая все найденную информацию.
    """

    llm = ChatOpenAI(model="gpt-5-mini")
    response = await llm.ainvoke([HumanMessage(content=synthesis_prompt)])

    state['merged_result'] = response.content
    return state
```

### 3. Self-Correction Pattern
**Назначение**: Автоматическая коррекция и улучшение результатов агентов

```python
class SelfCorrectionState(TypedDict):
    task: str
    initial_result: Any
    corrections: List[Dict]
    final_result: Any
    confidence_score: float
    correction_count: int

def create_self_correction_workflow():
    """Workflow для самокоррекции агентов"""

    workflow = StateGraph(SelfCorrectionState)

    workflow.add_node("initial_execution", initial_execution_node)
    workflow.add_node("confidence_assessment", confidence_assessment_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("correction", correction_node)
    workflow.add_node("finalize", finalize_node)

    workflow.add_edge(START, "initial_execution")
    workflow.add_edge("initial_execution", "confidence_assessment")

    # Условная логика коррекции
    workflow.add_conditional_edges(
        "confidence_assessment",
        should_correct,
        {
            "correct": "reflection",
            "finalize": "finalize"
        }
    )

    workflow.add_edge("reflection", "correction")
    workflow.add_edge("correction", "confidence_assessment")  # Цикл коррекции
    workflow.add_edge("finalize", END)

    return workflow.compile()

async def confidence_assessment_node(state: SelfCorrectionState) -> SelfCorrectionState:
    """Оценка уверенности в результате"""

    assessment_prompt = f"""
    Оцени уверенность в следующем результате по шкале от 0 до 1:

    Задача: {state['task']}
    Результат: {state['initial_result']}

    Критерии оценки:
    - Полнота (все аспекты задачи покрыты)
    - Точность (информация корректна)
    - Релевантность (ответ соответствует вопросу)
    - Ясность (результат понятен)

    Верни только число от 0 до 1:
    """

    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    response = await llm.ainvoke([HumanMessage(content=assessment_prompt)])

    try:
        confidence = float(response.content.strip())
        state['confidence_score'] = confidence
    except (ValueError, AttributeError):
        state['confidence_score'] = 0.5

    return state

def should_correct(state: SelfCorrectionState) -> Literal["correct", "finalize"]:
    """Решение о необходимости коррекции"""

    if (state['confidence_score'] < 0.8 and
        state.get('correction_count', 0) < 3):
        return "correct"
    else:
        return "finalize"

async def reflection_node(state: SelfCorrectionState) -> SelfCorrectionState:
    """Рефлексия над результатом для выявления проблем"""

    reflection_prompt = f"""
    Проанализируй результат и найди конкретные проблемы для улучшения:

    Задача: {state['task']}
    Текущий результат: {state['initial_result']}
    Оценка уверенности: {state['confidence_score']}

    Определи:
    1. Что именно нужно улучшить?
    2. Какая информация отсутствует?
    3. Какие есть неточности?
    4. Как можно сделать ответ более полным?

    Верни конкретные рекомендации для улучшения.
    """

    llm = ChatOpenAI(model="gpt-5-mini")
    response = await llm.ainvoke([HumanMessage(content=reflection_prompt)])

    if 'corrections' not in state:
        state['corrections'] = []

    state['corrections'].append({
        "iteration": len(state['corrections']) + 1,
        "reflection": response.content,
        "timestamp": datetime.utcnow().isoformat()
    })

    return state
```

### 4. Human-in-the-Loop Pattern
**Назначение**: Интеграция человеческого контроля в критических точках workflow

```python
class HITLState(TypedDict):
    task: str
    ai_recommendation: str
    human_decision: Optional[str]
    final_action: str
    requires_approval: bool

def create_hitl_workflow():
    """Workflow с human-in-the-loop checkpoints"""

    workflow = StateGraph(HITLState)

    workflow.add_node("ai_analysis", ai_analysis_node)
    workflow.add_node("risk_assessment", risk_assessment_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("execute_action", execute_action_node)

    workflow.add_edge(START, "ai_analysis")
    workflow.add_edge("ai_analysis", "risk_assessment")

    # Условная остановка для человеческого решения
    workflow.add_conditional_edges(
        "risk_assessment",
        requires_human_approval,
        {
            "human_needed": "human_review",
            "auto_proceed": "execute_action"
        }
    )

    workflow.add_edge("human_review", "execute_action")
    workflow.add_edge("execute_action", END)

    # Компиляция с interrupt points
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"]
    )

async def risk_assessment_node(state: HITLState) -> HITLState:
    """Оценка рисков для определения необходимости человеческого вмешательства"""

    risk_prompt = f"""
    Оцени риски следующего действия:

    Задача: {state['task']}
    Рекомендация ИИ: {state['ai_recommendation']}

    Критерии высокого риска:
    - Финансовые последствия > $10,000
    - Юридические риски
    - Безвозвратные действия
    - Влияние на клиентские отношения

    Верни JSON:
    {{
        "risk_level": "low|medium|high",
        "risk_factors": ["фактор1", "фактор2"],
        "requires_approval": true/false,
        "reasoning": "объяснение"
    }}
    """

    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    response = await llm.ainvoke([HumanMessage(content=risk_prompt)])

    risk_assessment = json.loads(response.content)
    state['requires_approval'] = risk_assessment['requires_approval']
    state['risk_assessment'] = risk_assessment

    return state

def requires_human_approval(state: HITLState) -> Literal["human_needed", "auto_proceed"]:
    """Маршрутизация на основе оценки рисков"""
    return "human_needed" if state['requires_approval'] else "auto_proceed"

# Использование с паузой для человеческого решения
async def run_with_human_approval(workflow, initial_state, thread_id):
    """Выполнение workflow с возможностью человеческого вмешательства"""

    config = {"configurable": {"thread_id": thread_id}}

    # Запуск до точки остановки
    result = await workflow.ainvoke(initial_state, config=config)

    # Проверка на необходимость человеческого решения
    if workflow.get_state(config).next == ("human_review",):
        print("Требуется человеческое решение. Workflow приостановлен.")
        return "awaiting_human_input"

    return result

async def resume_with_human_decision(workflow, human_decision, thread_id):
    """Возобновление workflow после человеческого решения"""

    config = {"configurable": {"thread_id": thread_id}}

    # Обновление состояния с человеческим решением
    await workflow.aupdate_state(
        config,
        {"human_decision": human_decision}
    )

    # Продолжение выполнения
    final_result = await workflow.ainvoke(None, config=config)
    return final_result
```

### 5. Error Recovery Pattern
**Назначение**: Robust обработка ошибок с автоматическим восстановлением

```python
class ErrorRecoveryState(TypedDict):
    task: str
    attempts: int
    last_error: Optional[str]
    fallback_strategies: List[str]
    result: Optional[Any]

def create_error_recovery_workflow():
    """Workflow с comprehensive error handling"""

    workflow = StateGraph(ErrorRecoveryState)

    workflow.add_node("primary_execution", primary_execution_node)
    workflow.add_node("error_analysis", error_analysis_node)
    workflow.add_node("fallback_strategy", fallback_strategy_node)
    workflow.add_node("final_fallback", final_fallback_node)

    workflow.add_edge(START, "primary_execution")

    # Условная обработка ошибок
    workflow.add_conditional_edges(
        "primary_execution",
        check_execution_success,
        {
            "success": END,
            "error": "error_analysis"
        }
    )

    workflow.add_edge("error_analysis", "fallback_strategy")

    workflow.add_conditional_edges(
        "fallback_strategy",
        check_fallback_success,
        {
            "success": END,
            "retry": "primary_execution",
            "final_fallback": "final_fallback"
        }
    )

    workflow.add_edge("final_fallback", END)

    return workflow.compile()

async def primary_execution_node(state: ErrorRecoveryState) -> ErrorRecoveryState:
    """Основное выполнение с обработкой ошибок"""

    try:
        # Основная логика выполнения
        result = await execute_main_task(state['task'])
        state['result'] = result
        state['execution_status'] = 'success'

    except Exception as e:
        state['last_error'] = str(e)
        state['execution_status'] = 'error'
        state['attempts'] = state.get('attempts', 0) + 1

        # Логирование ошибки
        logger.error(f"Primary execution failed: {e}", extra={
            "task": state['task'],
            "attempt": state['attempts']
        })

    return state

async def error_analysis_node(state: ErrorRecoveryState) -> ErrorRecoveryState:
    """Анализ ошибки для выбора стратегии восстановления"""

    error_analysis_prompt = f"""
    Проанализируй ошибку и предложи стратегию восстановления:

    Задача: {state['task']}
    Ошибка: {state['last_error']}
    Попытка номер: {state['attempts']}

    Возможные стратегии:
    1. retry_with_backoff - повторить с задержкой
    2. alternative_approach - использовать альтернативный метод
    3. simplified_task - упростить задачу
    4. manual_intervention - требуется ручное вмешательство

    Верни JSON:
    {{
        "recommended_strategy": "strategy_name",
        "reasoning": "объяснение",
        "retry_delay": "секунды для retry",
        "max_retries": "максимум попыток"
    }}
    """

    llm = ChatOpenAI(model="gpt-5-mini")
    response = await llm.ainvoke([HumanMessage(content=error_analysis_prompt)])

    analysis = json.loads(response.content)
    state['recovery_strategy'] = analysis

    return state

def check_execution_success(state: ErrorRecoveryState) -> Literal["success", "error"]:
    """Проверка успешности выполнения"""
    return state.get('execution_status', 'error')

def check_fallback_success(state: ErrorRecoveryState) -> Literal["success", "retry", "final_fallback"]:
    """Определение следующего шага после fallback"""

    if state.get('execution_status') == 'success':
        return "success"
    elif state.get('attempts', 0) < 3:
        return "retry"
    else:
        return "final_fallback"
```

### 6. Context Enrichment Pattern
**Назначение**: Динамическое обогащение контекста на основе хода выполнения

```python
class ContextEnrichmentState(TypedDict):
    base_context: str
    enriched_context: str
    context_sources: List[str]
    relevance_scores: Dict[str, float]

def create_context_enrichment_workflow():
    """Workflow для динамического обогащения контекста"""

    workflow = StateGraph(ContextEnrichmentState)

    workflow.add_node("analyze_context_needs", analyze_context_needs_node)
    workflow.add_node("gather_related_info", gather_related_info_node)
    workflow.add_node("score_relevance", score_relevance_node)
    workflow.add_node("merge_context", merge_context_node)

    workflow.add_edge(START, "analyze_context_needs")
    workflow.add_edge("analyze_context_needs", "gather_related_info")
    workflow.add_edge("gather_related_info", "score_relevance")
    workflow.add_edge("score_relevance", "merge_context")
    workflow.add_edge("merge_context", END)

    return workflow.compile()

async def analyze_context_needs_node(state: ContextEnrichmentState) -> ContextEnrichmentState:
    """Анализ потребностей в дополнительном контексте"""

    analysis_prompt = f"""
    Проанализируй базовый контекст и определи, какая дополнительная информация нужна:

    Базовый контекст: {state['base_context']}

    Определи:
    1. Какие ключевые понятия требуют разъяснения?
    2. Какая историческая информация может быть релевантна?
    3. Какие связанные дела или прецеденты стоит найти?
    4. Какие дополнительные источники нужно проверить?

    Верни список конкретных информационных потребностей.
    """

    llm = ChatOpenAI(model="gpt-5-mini")
    response = await llm.ainvoke([HumanMessage(content=analysis_prompt)])

    state['context_needs'] = response.content
    return state
```

## 🔧 Интеграция паттернов

### Композитный Workflow
```python
def create_mega_agent_workflow():
    """Главный workflow, объединяющий все паттерны"""

    workflow = StateGraph(MegaAgentState)

    # Supervisor как точка входа
    workflow.add_node("supervisor", supervisor_node)

    # Подключение специализированных workflow
    workflow.add_node("self_correction_flow", self_correction_workflow)
    workflow.add_node("parallel_processing_flow", parallel_workflow)
    workflow.add_node("hitl_flow", hitl_workflow)
    workflow.add_node("error_recovery_flow", error_recovery_workflow)

    # Маршрутизация к соответствующему workflow
    workflow.add_conditional_edges(
        "supervisor",
        route_to_specialized_workflow,
        {
            "simple_task": "direct_execution",
            "complex_task": "parallel_processing_flow",
            "risky_task": "hitl_flow",
            "error_prone_task": "error_recovery_flow",
            "quality_critical": "self_correction_flow"
        }
    )

    return workflow.compile(
        checkpointer=PostgresSaver.from_conn_string(postgres_url),
        interrupt_before=["human_review", "critical_decision"]
    )
```

Эти паттерны обеспечивают надежную, масштабируемую и maintainable архитектуру для complex multi-agent системы mega_agent_pro.
