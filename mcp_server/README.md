# MegaAgent MCP Server

MCP (Model Context Protocol) сервер для интеграции LangGraph workflows с Claude Code.

## Установка в Claude Code

Сервер уже добавлен в `.mcp.json`. Чтобы активировать, перезапустите Claude Code в директории проекта.

Или добавьте вручную:

```bash
claude mcp add megaagent -- python -m mcp_server.server
```

## Доступные инструменты

### run_workflow
Запуск LangGraph workflow для обработки EB-1A кейса.

```
Workflows:
- intake_questionnaire - Анкетирование клиента
- document_analysis - Анализ документов
- criteria_evaluation - Оценка критериев EB-1A
- letter_generation - Генерация писем
- full_pipeline - Полный процесс
```

### invoke_agent
Прямой вызов специализированного агента.

```
Agents:
- intake - Агент анкетирования
- researcher - Исследователь доказательств
- writer - Писатель петиций
- reviewer - Рецензент
- rag_pipeline - RAG поиск
- validator - Валидатор
- supervisor - Супервизор
```

### query_case
Запрос информации о кейсе из базы данных.

### search_knowledge_base
Семантический поиск в базе знаний EB-1A (политики USCIS, case law, RFE ответы).

### analyze_criteria
Анализ соответствия 10 критериям EB-1A для кейса.

### generate_document
Генерация документов:
- petition_letter
- exhibit_list
- recommendation_letter
- cover_letter
- rfe_response

### list_cases
Список кейсов с фильтрацией по статусу.

### memory_search
Поиск в памяти агентов (эпизодическая, семантическая, процедурная).

## Примеры использования в Claude Code

```
# Запустить анкетирование для кейса
> Use megaagent run_workflow with workflow="intake_questionnaire" and case_id="case-123"

# Поиск в базе знаний
> Use megaagent search_knowledge_base with query="extraordinary ability criteria awards"

# Анализ критериев
> Use megaagent analyze_criteria with case_id="case-123"

# Генерация письма
> Use megaagent generate_document with case_id="case-123" and document_type="petition_letter"
```

## Архитектура

```
Claude Code
    │
    ├── MCP Protocol (stdio)
    │       │
    │       ▼
    │   MegaAgent MCP Server
    │       │
    │       ├── run_workflow ──► LangGraph StateGraph
    │       │                        │
    │       │                        ├── IntakeNode
    │       │                        ├── ResearchNode
    │       │                        ├── WriterNode
    │       │                        └── ReviewNode
    │       │
    │       ├── invoke_agent ──► MegaAgent / Specialized Agents
    │       │
    │       ├── search_knowledge_base ──► RAG Pipeline
    │       │                                  │
    │       │                                  └── Supabase Vector Store
    │       │
    │       └── query_case ──► Case Repository
    │                              │
    │                              └── PostgreSQL
    │
    └── Response to Claude Code
```

## Запуск вручную

```bash
cd mega_agent_pro_codex_handoff
python -m mcp_server.server
```

## Конфигурация

Переменные окружения (из `.env`):

| Variable | Description |
|----------|-------------|
| OPENAI_API_KEY | OpenAI API ключ |
| ANTHROPIC_API_KEY | Anthropic API ключ |
| SUPABASE_URL | URL Supabase проекта |
| SUPABASE_SERVICE_ROLE_KEY | Service role ключ Supabase |

## Файлы

```
mcp_server/
├── __init__.py      # Экспорты модуля
├── __main__.py      # Entry point для python -m
├── server.py        # MCP сервер и инструменты
└── README.md        # Документация
```
