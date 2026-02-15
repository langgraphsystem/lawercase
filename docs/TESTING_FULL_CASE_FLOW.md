# Тестирование полного цикла создания кейса: от ввода до PDF

## Обзор

Этот документ описывает **end-to-end тестирование** полного жизненного цикла кейса EB-1A:

```
Создание кейса → Анкетирование → Интерактивные обновления →
Анализ критериев → Загрузка документов → Генерация PDF →
Финализация пакета для USCIS
```

---

## 🎯 Тестируемый поток

### Полная последовательность действий:

```
1. CREATE CASE
   ├─ Минимальные данные (имя, поле)
   └─ Статус: "intake" (начальный)

2. INTAKE QUESTIONNAIRE (8 блоков)
   ├─ Блок 1: Основная информация
   ├─ Блок 2: Образование
   ├─ Блок 3: Карьера
   ├─ Блок 4: Достижения
   ├─ Блок 5: Членство
   ├─ Блок 6: Критическая роль
   ├─ Блок 7: Медиа
   └─ Блок 8: Коммерческий успех
   └─ Каждый ответ → обновление case в БД

3. CRITERIA ANALYSIS
   ├─ Анализ по 10 критериям EB-1A
   ├─ Обновление case.analysis_results
   └─ Статус: "analysis_complete"

4. DOCUMENT UPLOAD
   ├─ Загрузка supporting evidence
   ├─ Связывание с критериями
   └─ Статус: "documents_collected"

5. GENERATE PETITION
   ├─ Генерация narrative текста
   ├─ Формирование exhibit list
   ├─ Создание рекомендательных писем
   └─ Статус: "petition_draft"

6. REVIEW & EDIT
   ├─ Юрист редактирует через Web UI
   ├─ Клиент добавляет информацию через Telegram
   └─ Итеративные обновления

7. FINALIZE PDF PACKAGE
   ├─ Сборка master PDF
   ├─ OCR обработка (если нужно)
   ├─ Создание оглавления
   ├─ Генерация cover letter
   └─ Статус: "ready_for_filing"
```

---

## 🧪 Стратегия тестирования

### Уровни тестирования:

| Уровень | Что тестируем | Инструменты | Время |
|---------|---------------|-------------|-------|
| **Unit Tests** | Отдельные функции/компоненты | pytest | 5 мин |
| **Integration Tests** | Взаимодействие компонентов | pytest + Fakeredis | 10 мин |
| **API Tests** | REST endpoints E2E | pytest + httpx | 15 мин |
| **Workflow Tests** | LangGraph workflows | pytest + LangGraph checkpoint | 20 мин |
| **E2E Tests** | Полный цикл через UI/Telegram | Playwright / manual | 30 мин |
| **PDF Generation Tests** | Document assembly | pytest + PDF libraries | 10 мин |

---

## 1️⃣ Unit Tests - Отдельные компоненты

### 1.1 Тест создания кейса

**Файл:** `tests/unit/test_case_creation.py`

```python
import pytest
from datetime import datetime
from core.groupagents.mega_agent import MegaAgent, MegaAgentCommand, CommandType
from core.memory.memory_manager import MemoryManager


@pytest.mark.asyncio
async def test_create_case_minimal_data(mega_agent_fixture):
    """Test case creation with minimal required data."""

    cmd = MegaAgentCommand(
        user_id="test_user_001",
        command_type=CommandType.CASE,
        action="create",
        payload={
            "applicant_name": "John Doe",
            "field": "Machine Learning"
        }
    )

    response = await mega_agent_fixture.handle_command(cmd, user_role="lawyer")

    assert response.status == "success"
    assert "case_id" in response.metadata
    assert response.metadata["status"] == "intake"

    # Verify case stored in memory
    case_id = response.metadata["case_id"]
    memory_result = await mega_agent_fixture.memory_manager.episodic.retrieve(
        query=f"case {case_id}",
        top_k=1
    )
    assert len(memory_result) > 0


@pytest.mark.asyncio
async def test_case_initial_state():
    """Verify initial case state after creation."""

    from core.storage.case_store import get_case

    case = await get_case("test_case_001")

    assert case["status"] == "intake"
    assert case["criteria_met"] == {}
    assert case["documents"] == []
    assert case["analysis_results"] is None
    assert "created_at" in case
    assert "updated_at" in case
```

**Запуск:**
```bash
pytest tests/unit/test_case_creation.py -v
```

---

### 1.2 Тест интерактивного обновления кейса

**Файл:** `tests/unit/test_case_updates.py`

```python
import pytest
from core.intake.synthesis import synthesize_intake_fact
from core.storage.case_store import update_case, get_case


@pytest.mark.asyncio
async def test_intake_answer_updates_case():
    """Test that each intake answer updates the case."""

    case_id = "test_case_002"

    # Simulate answering Block 1, Question 1
    fact = synthesize_intake_fact(
        block_id="basic_info",
        question="full_name",
        answer="Ivan Petrov",
        case_id=case_id
    )

    # Update case with new fact
    await update_case(case_id, {
        "facts": [fact],
        "intake_progress": {
            "current_block": "basic_info",
            "completed_blocks": [],
            "total_facts": 1
        }
    })

    # Verify case updated
    case = await get_case(case_id)
    assert case["intake_progress"]["total_facts"] == 1
    assert len(case["facts"]) == 1
    assert case["facts"][0]["content"] == "Applicant's full name is Ivan Petrov"


@pytest.mark.asyncio
async def test_progressive_case_enrichment():
    """Test case gets progressively richer with each answer."""

    case_id = "test_case_003"

    # Simulate multiple answers
    answers = [
        ("basic_info", "full_name", "Jane Smith"),
        ("basic_info", "date_of_birth", "1990-05-20"),
        ("basic_info", "citizenship", "Russia"),
        ("education", "degree", "PhD in Computer Science"),
        ("career", "current_position", "Senior ML Engineer at Google"),
    ]

    for block_id, question, answer in answers:
        fact = synthesize_intake_fact(block_id, question, answer, case_id)
        await update_case(case_id, {
            "$push": {"facts": fact},
            "$inc": {"intake_progress.total_facts": 1}
        })

    # Verify progressive enrichment
    case = await get_case(case_id)
    assert case["intake_progress"]["total_facts"] == 5
    assert len(case["facts"]) == 5

    # Verify facts are searchable in semantic memory
    from core.memory.stores.supabase_semantic_store import SupabaseSemanticStore
    store = SupabaseSemanticStore()
    results = await store.search(f"case {case_id}", top_k=10)
    assert len(results) >= 5
```

**Запуск:**
```bash
pytest tests/unit/test_case_updates.py -v
```

---

## 2️⃣ Integration Tests - Компонентное взаимодействие

### 2.1 Тест полного анкетирования

**Файл:** `tests/integration/test_intake_flow.py`

```python
import pytest
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes
from telegram_interface.handlers.intake_handlers import (
    start_intake,
    handle_intake_answer,
    complete_intake
)


@pytest.mark.asyncio
async def test_full_intake_questionnaire_flow():
    """Test complete intake flow through all 8 blocks."""

    user_id = 12345
    case_id = "test_case_intake_001"

    # Mock Telegram update
    update = create_mock_update(user_id, "/intake_start")
    context = create_mock_context()

    # 1. Start intake
    await start_intake(update, context)

    progress = await get_progress(user_id)
    assert progress["current_block"] == "basic_info"
    assert progress["current_step"] == 0

    # 2. Simulate answering all questions in Block 1
    block1_answers = [
        "Ivan Petrov",           # full_name
        "1985-06-15",            # date_of_birth
        "Russia",                # citizenship
        "Москва",                # birth_place
    ]

    for answer_text in block1_answers:
        update = create_mock_update(user_id, answer_text)
        await handle_intake_answer(update, context)

    progress = await get_progress(user_id)
    assert "basic_info" in progress["completed_blocks"]
    assert progress["current_block"] == "education"

    # 3. Continue through all 8 blocks...
    # (Abbreviated for brevity - full test would complete all blocks)

    # 4. Verify case updated after each answer
    from core.storage.case_store import get_case
    case = await get_case(case_id)

    assert case["intake_progress"]["total_facts"] >= 4
    assert case["status"] == "intake" or case["status"] == "intake_complete"


@pytest.mark.asyncio
async def test_intake_with_pause_and_resume():
    """Test pausing intake and resuming later."""

    user_id = 12346
    case_id = "test_case_pause_001"

    # Start intake
    update = create_mock_update(user_id, "/intake_start")
    context = create_mock_context()
    await start_intake(update, context)

    # Answer 2 questions
    await handle_intake_answer(
        create_mock_update(user_id, "John Doe"),
        context
    )
    await handle_intake_answer(
        create_mock_update(user_id, "1990-01-01"),
        context
    )

    # Pause (simulate clicking pause button)
    progress_before = await get_progress(user_id)
    assert progress_before["current_step"] == 2

    # Resume later
    update = create_mock_update(user_id, "/intake_resume")
    await resume_intake(update, context)

    progress_after = await get_progress(user_id)
    assert progress_after["current_step"] == 2  # Same position
    assert progress_after["current_block"] == progress_before["current_block"]

    # Continue answering
    await handle_intake_answer(
        create_mock_update(user_id, "USA"),
        context
    )

    progress_final = await get_progress(user_id)
    assert progress_final["current_step"] == 3


def create_mock_update(user_id: int, text: str):
    """Helper to create mock Telegram update."""
    user = User(id=user_id, first_name="Test", is_bot=False)
    chat = Chat(id=user_id, type="private")
    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text=text
    )
    return Update(update_id=1, message=message)


def create_mock_context():
    """Helper to create mock context."""
    # Implementation depends on your test setup
    pass
```

**Запуск:**
```bash
pytest tests/integration/test_intake_flow.py -v
```

---

## 3️⃣ API Tests - REST Endpoints E2E

### 3.1 Тест полного API цикла

**Файл:** `tests/e2e/test_api_full_cycle.py`

```python
import pytest
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_full_api_cycle_from_login_to_pdf():
    """Test complete cycle via API: login → create case → intake → analyze → PDF."""

    async with httpx.AsyncClient(base_url=BASE_URL) as client:

        # Step 1: Login
        login_response = await client.post("/auth/login", json={
            "email": "lawyer@eb1a.com",
            "password": "demo1234"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create case
        case_response = await client.post(
            "/api/v1/cases",
            headers=headers,
            json={
                "applicant_name": "API Test User",
                "field": "Artificial Intelligence",
                "status": "intake"
            }
        )
        assert case_response.status_code == 201
        case_id = case_response.json()["case_id"]

        # Step 3: Submit intake data via multiple /v1/ask calls
        intake_data = {
            "full_name": "API Test User",
            "date_of_birth": "1988-03-10",
            "citizenship": "India",
            "education": ["PhD Computer Science, MIT 2015"],
            "awards": ["Best Paper Award ICML 2020", "ACM Fellow 2022"],
            "publications": ["50+ papers in top-tier conferences"],
            "current_position": "Principal Scientist, OpenAI"
        }

        for key, value in intake_data.items():
            ask_response = await client.post(
                "/v1/ask",
                headers=headers,
                json={
                    "query": f"Update case {case_id}: {key} is {value}",
                    "case_id": case_id
                }
            )
            assert ask_response.status_code == 200

        # Step 4: Request criteria analysis
        analyze_response = await client.post(
            "/v1/ask",
            headers=headers,
            json={
                "query": f"Analyze EB-1A criteria for case {case_id}",
                "case_id": case_id
            }
        )
        assert analyze_response.status_code == 200
        analysis = analyze_response.json()
        assert "criteria" in analysis["llm_response"].lower()

        # Step 5: Verify case updated with analysis
        case_get_response = await client.get(
            f"/api/v1/cases/{case_id}",
            headers=headers
        )
        assert case_get_response.status_code == 200
        case_data = case_get_response.json()
        assert case_data["status"] in ["intake_complete", "analysis_complete"]

        # Step 6: Generate petition draft
        generate_response = await client.post(
            "/v1/ask",
            headers=headers,
            json={
                "query": f"Generate petition letter for case {case_id}",
                "case_id": case_id
            }
        )
        assert generate_response.status_code == 200

        # Step 7: Trigger PDF generation (via document monitor API)
        pdf_response = await client.post(
            f"/api/document-monitor/generate/{case_id}",
            headers=headers,
            json={
                "include_exhibits": True,
                "ocr_provider": "none"  # Skip OCR in tests
            }
        )
        assert pdf_response.status_code == 200
        thread_id = pdf_response.json()["thread_id"]

        # Step 8: Poll for PDF completion
        import asyncio
        max_attempts = 30
        for attempt in range(max_attempts):
            status_response = await client.get(
                f"/api/document-monitor/status/{thread_id}",
                headers=headers
            )
            status_data = status_response.json()

            if status_data["status"] == "completed":
                assert "pdf_url" in status_data
                print(f"PDF generated: {status_data['pdf_url']}")
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"PDF generation failed: {status_data.get('error')}")

            await asyncio.sleep(2)
        else:
            pytest.fail("PDF generation timed out")

        # Step 9: Download and verify PDF
        pdf_url = status_data["pdf_url"]
        pdf_download = await client.get(pdf_url)
        assert pdf_download.status_code == 200
        assert pdf_download.headers["content-type"] == "application/pdf"
        assert len(pdf_download.content) > 10000  # PDF should be substantial

        # Step 10: Verify case finalized
        final_case_response = await client.get(
            f"/api/v1/cases/{case_id}",
            headers=headers
        )
        final_case = final_case_response.json()
        assert final_case["status"] in ["petition_draft", "ready_for_filing"]
        assert final_case["pdf_url"] == pdf_url


@pytest.mark.asyncio
async def test_streaming_agui_protocol():
    """Test AG-UI SSE streaming for real-time updates."""

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:

        # Login
        login_response = await client.post("/auth/login", json={
            "email": "lawyer@eb1a.com",
            "password": "demo1234"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Stream analysis via AG-UI
        events_received = []

        async with client.stream(
            "POST",
            "/agui/run",
            headers=headers,
            json={
                "prompt": "Analyze EB-1A criteria for a candidate with 50 publications",
                "stream": True
            }
        ) as response:
            assert response.status_code == 200

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json
                    event_data = json.loads(line[6:])
                    events_received.append(event_data)

                    if event_data.get("type") == "RUN_COMPLETE":
                        break

        # Verify event sequence
        event_types = [e.get("type") for e in events_received]
        assert "RUN_START" in event_types
        assert "TEXT_CHUNK" in event_types or "TEXT_DELTA" in event_types
        assert "RUN_COMPLETE" in event_types
```

**Запуск:**
```bash
# Start server first
uvicorn api.main:app --reload &

# Run tests
pytest tests/e2e/test_api_full_cycle.py -v -s

# Stop server
kill %1
```

---

## 4️⃣ Workflow Tests - LangGraph Pipelines

### 4.1 Тест EB-1A workflow

**Файл:** `tests/workflows/test_eb1a_workflow.py`

```python
import pytest
from core.orchestration.pipeline_manager import build_eb1a_pipeline
from core.memory.memory_manager import MemoryManager
from core.llm.intelligent_router import IntelligentRouter


@pytest.mark.asyncio
async def test_eb1a_workflow_full_pipeline():
    """Test complete EB-1A LangGraph workflow."""

    memory_manager = MemoryManager()  # Use test fixtures
    llm_router = IntelligentRouter()

    pipeline = build_eb1a_pipeline(memory_manager, llm_router)

    # Initial state
    initial_state = {
        "case_id": "workflow_test_001",
        "applicant_name": "Workflow Test User",
        "field": "Quantum Computing",
        "intake_data": {
            "education": ["PhD Physics, Caltech"],
            "awards": ["Nobel Prize nominee", "ACM Fellow"],
            "publications": ["100+ papers in Nature, Science"],
            "current_role": "Chief Scientist at IBM Quantum"
        },
        "criteria_results": {},
        "gaps": [],
        "documents": []
    }

    # Execute workflow
    result = await pipeline.ainvoke(initial_state)

    # Verify workflow completion
    assert result["status"] == "completed"
    assert "criteria_results" in result
    assert len(result["criteria_results"]) == 10  # All 10 EB-1A criteria

    # Verify at least 3 criteria met (EB-1A requirement)
    met_criteria = [k for k, v in result["criteria_results"].items() if v["met"]]
    assert len(met_criteria) >= 3

    # Verify documents generated
    assert "petition_letter" in result["documents"]
    assert "exhibit_list" in result["documents"]

    # Verify gaps identified
    assert isinstance(result["gaps"], list)

    # Verify audit trail
    audit_events = await memory_manager.episodic.retrieve(
        query=f"workflow {result['case_id']}",
        top_k=20
    )
    assert len(audit_events) > 0


@pytest.mark.asyncio
async def test_workflow_node_transitions():
    """Test individual workflow node transitions."""

    from core.orchestration.workflow_graph import (
        eligibility_check_node,
        criteria_assessment_node,
        strength_analysis_node,
        gap_analysis_node,
        document_generation_node
    )

    state = {
        "case_id": "node_test_001",
        "applicant_name": "Node Test",
        "field": "AI",
        "intake_data": {"awards": ["Best Paper"]},
        "criteria_results": {},
        "gaps": []
    }

    # Test eligibility check
    state = await eligibility_check_node(state)
    assert "eligibility_passed" in state

    # Test criteria assessment
    state = await criteria_assessment_node(state)
    assert "criteria_results" in state
    assert len(state["criteria_results"]) > 0

    # Test strength analysis
    state = await strength_analysis_node(state)
    assert "strength_score" in state
    assert 0 <= state["strength_score"] <= 100

    # Test gap analysis
    state = await gap_analysis_node(state)
    assert "gaps" in state

    # Test document generation
    state = await document_generation_node(state)
    assert "documents" in state
```

**Запуск:**
```bash
pytest tests/workflows/test_eb1a_workflow.py -v
```

---

## 5️⃣ E2E Tests - UI/Telegram полный цикл

### 5.1 Playwright test для Web UI

**Файл:** `tests/e2e/test_web_ui_full_cycle.py`

```python
import pytest
from playwright.async_api import async_playwright, expect


@pytest.mark.asyncio
async def test_web_ui_complete_cycle():
    """Test complete cycle via Web UI using Playwright."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set True for CI
        context = await browser.new_context()
        page = await context.new_page()

        # Step 1: Navigate and login
        await page.goto("https://eb1a-frontend.vercel.app/")
        await page.fill('input[type="email"]', "lawyer@eb1a.com")
        await page.fill('input[type="password"]', "demo1234")
        await page.click('button[type="submit"]')

        # Wait for redirect to chat page
        await page.wait_for_url("**/chat")

        # Step 2: Create new case
        await page.click('text="+ Новый кейс"')
        await page.fill('input[name="applicant_name"]', "E2E Test User")
        await page.fill('input[name="field"]', "Biotechnology")
        await page.click('button:has-text("Создать")')

        # Wait for case creation
        await page.wait_for_selector('text="E2E Test User"')

        # Step 3: Select the case
        await page.click('text="E2E Test User"')

        # Step 4: Submit intake via chat
        chat_input = page.locator('textarea[placeholder*="вопрос"]')

        await chat_input.fill("Меня зовут E2E Test User, я родился 1985-03-15")
        await page.click('button:has-text("Отправить")')
        await page.wait_for_selector('text="Сохранил"')

        await chat_input.fill("У меня PhD in Biotechnology from Stanford")
        await page.click('button:has-text("Отправить")')
        await page.wait_for_selector('text="Сохранил"')

        # Step 5: Request analysis
        await chat_input.fill("Проанализируй мои шансы на EB-1A")
        await page.click('button:has-text("Отправить")')

        # Wait for streaming response to complete
        await page.wait_for_selector('text="Критерий"', timeout=60000)

        # Verify analysis appears
        await expect(page.locator('text="критерий"')).to_be_visible()

        # Step 6: Request document generation
        await chat_input.fill("Сгенерируй черновик петиции")
        await page.click('button:has-text("Отправить")')

        # Wait for generation to complete
        await page.wait_for_selector('text="петиция"', timeout=120000)

        # Step 7: Verify PDF link appears
        pdf_link = page.locator('a[href*=".pdf"]')
        await expect(pdf_link).to_be_visible(timeout=60000)

        # Take screenshot for verification
        await page.screenshot(path="test_results/e2e_web_ui_complete.png")

        await browser.close()
```

**Запуск:**
```bash
# Install Playwright browsers first
playwright install

# Run test
pytest tests/e2e/test_web_ui_full_cycle.py -v -s
```

---

### 5.2 Manual Telegram test script

**Файл:** `tests/manual/telegram_full_cycle.md`

```markdown
# Manual Test: Telegram Full Cycle

## Prerequisites
- Telegram app installed
- Bot deployed and accessible
- Your Telegram user_id added to TELEGRAM_ALLOWED_USERS

## Test Steps

### 1. Initial Contact
- [ ] Open Telegram
- [ ] Find bot: @your_eb1a_bot
- [ ] Send: `/start`
- [ ] Verify: Welcome message received

### 2. Start Intake
- [ ] Send: `/intake_start`
- [ ] Verify: First question appears with navigation buttons

### 3. Complete Block 1 (Basic Info)
- [ ] Answer: Full name (e.g., "Manual Test User")
- [ ] Verify: "Сохранил" confirmation
- [ ] Answer: Date of birth (e.g., "1990-01-01")
- [ ] Verify: Confirmation
- [ ] Answer: Citizenship (e.g., "USA")
- [ ] Verify: Block 1 completion message

### 4. Test Navigation
- [ ] Click "🔙 Назад" button
- [ ] Verify: Returns to previous question
- [ ] Re-answer the question
- [ ] Click "⏸ Пауза" button
- [ ] Verify: Progress saved message

### 5. Resume Intake
- [ ] Send: `/intake_status`
- [ ] Verify: Shows current progress (Block 1 partially complete)
- [ ] Send: `/intake_resume`
- [ ] Verify: Resumes at exact same question

### 6. Complete Remaining Blocks (or skip)
- [ ] Click "⏭ Пропустить" for questions without answers
- [ ] Complete at least 3-4 questions per block
- [ ] Verify: Progress messages after each block

### 7. Analyze Criteria
- [ ] Send: `/eb1_analyze`
- [ ] Verify: Analysis message starts (may take 30-60 seconds)
- [ ] Verify: 10 criteria listed with status
- [ ] Verify: Overall score provided
- [ ] Verify: Recommendations listed

### 8. Generate Letter
- [ ] Send: `/generate_letter Recommendation`
- [ ] Verify: Letter template generated
- [ ] Verify: Contains applicant name and achievements

### 9. Upload Document
- [ ] Send a PDF file to bot
- [ ] Verify: File uploaded confirmation
- [ ] Verify: File linked to case

### 10. Create Formal Case
- [ ] Send: `/case_create`
- [ ] Follow prompts to finalize case
- [ ] Verify: Case ID returned
- [ ] Send: `/case_get <case_id>`
- [ ] Verify: Full case data displayed

### 11. Trigger PDF Generation
- [ ] Send: `/generate_petition <case_id>`
- [ ] Verify: "Generating..." message
- [ ] Wait 2-5 minutes
- [ ] Verify: PDF link received
- [ ] Click link and verify PDF downloads

## Expected Results

✅ All steps complete without errors
✅ Case data persists between sessions
✅ PDF generated successfully
✅ PDF contains:
   - Cover letter
   - Petition narrative
   - Exhibit list
   - Supporting documents

## Time Required
- Full manual test: ~30-45 minutes
- Quick smoke test (steps 1-7): ~15 minutes
```

---

## 6️⃣ PDF Generation Tests

### 6.1 Тест сборки PDF пакета

**Файл:** `tests/pdf/test_pdf_generation.py`

```python
import pytest
from pathlib import Path
import PyPDF2


@pytest.mark.asyncio
async def test_pdf_assembly_from_case():
    """Test PDF assembly from case data."""

    from core.services.pdf_package_generator import PDFPackageGenerator
    from core.storage.case_store import get_case

    case_id = "pdf_test_001"
    case = await get_case(case_id)

    generator = PDFPackageGenerator()
    pdf_path = await generator.generate_package(
        case=case,
        include_cover_letter=True,
        include_exhibit_list=True,
        include_exhibits=True
    )

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 50000  # At least 50KB

    # Verify PDF structure
    with open(pdf_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)

        # Check page count
        assert len(pdf_reader.pages) >= 10  # Cover + petition + exhibits

        # Check first page (cover letter)
        first_page_text = pdf_reader.pages[0].extract_text()
        assert "USCIS" in first_page_text
        assert case["applicant_name"] in first_page_text

        # Check TOC/exhibit list
        toc_found = False
        for page in pdf_reader.pages[:5]:
            text = page.extract_text()
            if "Table of Contents" in text or "Exhibit List" in text:
                toc_found = True
                break
        assert toc_found


@pytest.mark.asyncio
async def test_pdf_metadata():
    """Test PDF metadata is correct."""

    from core.services.pdf_package_generator import PDFPackageGenerator

    case_id = "pdf_meta_test_001"
    generator = PDFPackageGenerator()
    pdf_path = await generator.generate_package(case_id)

    with open(pdf_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        metadata = pdf_reader.metadata

        assert metadata.get("/Title") is not None
        assert "EB-1A" in metadata.get("/Title", "")
        assert metadata.get("/Author") is not None
        assert metadata.get("/CreationDate") is not None


@pytest.mark.asyncio
async def test_pdf_bookmarks():
    """Test PDF has proper bookmarks/navigation."""

    from core.services.pdf_package_generator import PDFPackageGenerator

    case_id = "pdf_bookmark_test_001"
    generator = PDFPackageGenerator()
    pdf_path = await generator.generate_package(case_id)

    with open(pdf_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)

        # Check for outline/bookmarks
        if pdf_reader.outline:
            bookmark_titles = [item.title for item in pdf_reader.outline if hasattr(item, 'title')]
            assert "Cover Letter" in bookmark_titles or "Petition" in bookmark_titles
            assert "Exhibits" in bookmark_titles or len(bookmark_titles) >= 3
```

**Запуск:**
```bash
pytest tests/pdf/test_pdf_generation.py -v
```

---

## 7️⃣ Automated Test Suite

### Создание полного test suite

**Файл:** `tests/full_cycle_suite.py`

```python
"""
Full Cycle Test Suite - Orchestrates all tests in sequence.

This suite runs a complete end-to-end test simulating a real user journey.
"""

import pytest
import asyncio
from datetime import datetime


class TestFullCycleIntegration:
    """Integration test class for full case lifecycle."""

    @pytest.fixture(autouse=True)
    async def setup_test_case(self):
        """Setup unique test case for this test run."""
        self.test_id = f"full_cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.case_id = None
        yield
        # Cleanup after tests
        if self.case_id:
            await self._cleanup_test_case(self.case_id)

    @pytest.mark.asyncio
    async def test_01_create_case(self, authenticated_client):
        """Step 1: Create case via API."""
        response = await authenticated_client.post("/api/v1/cases", json={
            "applicant_name": f"Test User {self.test_id}",
            "field": "Machine Learning"
        })
        assert response.status_code == 201
        self.case_id = response.json()["case_id"]
        print(f"✓ Created case: {self.case_id}")

    @pytest.mark.asyncio
    async def test_02_intake_block1(self, authenticated_client):
        """Step 2: Complete intake block 1."""
        assert self.case_id is not None

        answers = [
            ("full_name", "Integration Test User"),
            ("date_of_birth", "1985-01-01"),
            ("citizenship", "Canada")
        ]

        for field, value in answers:
            response = await authenticated_client.post("/v1/ask", json={
                "query": f"Update case {self.case_id}: {field} = {value}",
                "case_id": self.case_id
            })
            assert response.status_code == 200

        print(f"✓ Completed intake block 1")

    @pytest.mark.asyncio
    async def test_03_intake_block2(self, authenticated_client):
        """Step 3: Complete intake block 2 (education)."""
        # Similar to test_02 for education block
        pass

    # ... (continue for all blocks)

    @pytest.mark.asyncio
    async def test_08_analyze_criteria(self, authenticated_client):
        """Step 8: Analyze EB-1A criteria."""
        response = await authenticated_client.post("/v1/ask", json={
            "query": f"Analyze EB-1A criteria for case {self.case_id}",
            "case_id": self.case_id
        })
        assert response.status_code == 200
        assert "criteria" in response.json()["llm_response"].lower()
        print(f"✓ Criteria analyzed")

    @pytest.mark.asyncio
    async def test_09_generate_documents(self, authenticated_client):
        """Step 9: Generate petition documents."""
        response = await authenticated_client.post("/v1/ask", json={
            "query": f"Generate petition for case {self.case_id}",
            "case_id": self.case_id
        })
        assert response.status_code == 200
        print(f"✓ Documents generated")

    @pytest.mark.asyncio
    async def test_10_assemble_pdf(self, authenticated_client):
        """Step 10: Assemble final PDF package."""
        response = await authenticated_client.post(
            f"/api/document-monitor/generate/{self.case_id}",
            json={"include_exhibits": True}
        )
        assert response.status_code == 200
        thread_id = response.json()["thread_id"]

        # Poll for completion
        for _ in range(30):
            status_response = await authenticated_client.get(
                f"/api/document-monitor/status/{thread_id}"
            )
            status = status_response.json()["status"]
            if status == "completed":
                pdf_url = status_response.json()["pdf_url"]
                print(f"✓ PDF generated: {pdf_url}")
                break
            await asyncio.sleep(2)
        else:
            pytest.fail("PDF generation timed out")

    async def _cleanup_test_case(self, case_id):
        """Cleanup test case from database."""
        from core.storage.case_store import delete_case
        await delete_case(case_id)
```

**Запуск полного suite:**
```bash
pytest tests/full_cycle_suite.py -v -s --tb=short
```

---

## 8️⃣ CI/CD Integration

### GitHub Actions workflow для full cycle tests

**Файл:** `.github/workflows/e2e-tests.yml`

```yaml
name: E2E Full Cycle Tests

on:
  push:
    branches: [ main, hardening/roadmap-v1 ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_eb1a
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-asyncio httpx playwright
          playwright install chromium

      - name: Set up test environment
        env:
          DATABASE_URL: postgresql://postgres:test_password@localhost/test_eb1a
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET_KEY: test_secret_key_for_ci
        run: |
          # Run migrations
          python -m alembic upgrade head

          # Seed test data
          python tests/fixtures/seed_test_data.py

      - name: Run unit tests
        run: pytest tests/unit/ -v

      - name: Run integration tests
        run: pytest tests/integration/ -v

      - name: Start API server in background
        run: |
          uvicorn api.main:app --host 0.0.0.0 --port 8000 &
          sleep 10
        env:
          DATABASE_URL: postgresql://postgres:test_password@localhost/test_eb1a
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET_KEY: test_secret_key_for_ci

      - name: Run E2E API tests
        run: pytest tests/e2e/test_api_full_cycle.py -v -s

      - name: Run workflow tests
        run: pytest tests/workflows/ -v

      - name: Run PDF generation tests
        run: pytest tests/pdf/ -v

      - name: Run full cycle integration suite
        run: pytest tests/full_cycle_suite.py -v -s

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: |
            test_results/
            htmlcov/

      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'E2E Tests Failed',
              body: `E2E test suite failed. Check [workflow run](${context.payload.repository.html_url}/actions/runs/${context.runId})`
            })
```

---

## 9️⃣ Manual Testing Checklist

### Печатная чек-лист для QA

**Файл:** `tests/manual/TESTING_CHECKLIST.md`

```markdown
# 📋 Full Cycle Testing Checklist

Test Date: ________________
Tester: ___________________
Environment: □ Dev  □ Staging  □ Production

## Phase 1: Case Creation
- [ ] 1.1 Login successful (Web/Telegram/API)
- [ ] 1.2 Create case with minimal data
- [ ] 1.3 Case ID generated
- [ ] 1.4 Case appears in list
- [ ] 1.5 Initial status = "intake"

## Phase 2: Intake Questionnaire
- [ ] 2.1 Start intake (/intake_start or UI)
- [ ] 2.2 Block 1: Basic Info (4 questions)
- [ ] 2.3 Block 2: Education (3+ questions)
- [ ] 2.4 Block 3: Career (3+ questions)
- [ ] 2.5 Block 4: Achievements (awards/pubs/patents)
- [ ] 2.6 Block 5: Membership
- [ ] 2.7 Block 6: Critical Role
- [ ] 2.8 Block 7: Media
- [ ] 2.9 Block 8: Commercial Success
- [ ] 2.10 Each answer saved to case
- [ ] 2.11 Progress indicator updates
- [ ] 2.12 Pause/Resume works correctly
- [ ] 2.13 Back button works

## Phase 3: Real-Time Updates
- [ ] 3.1 View case in API - facts present
- [ ] 3.2 View case in Web UI - data synchronized
- [ ] 3.3 Semantic memory contains facts
- [ ] 3.4 intake_progress.total_facts correct
- [ ] 3.5 Can search for case facts

## Phase 4: Criteria Analysis
- [ ] 4.1 Trigger analysis (/eb1_analyze or chat)
- [ ] 4.2 Analysis completes within 60s
- [ ] 4.3 All 10 criteria evaluated
- [ ] 4.4 Percentage score calculated
- [ ] 4.5 Recommendations provided
- [ ] 4.6 Case status updated
- [ ] 4.7 Analysis saved to case.analysis_results

## Phase 5: Document Upload
- [ ] 5.1 Upload PDF via Telegram
- [ ] 5.2 Upload PDF via Web UI
- [ ] 5.3 File stored correctly
- [ ] 5.4 File linked to case
- [ ] 5.5 File metadata captured
- [ ] 5.6 Can retrieve uploaded file

## Phase 6: Document Generation
- [ ] 6.1 Request letter generation
- [ ] 6.2 Petition narrative generated
- [ ] 6.3 Exhibit list created
- [ ] 6.4 Recommendation letters templated
- [ ] 6.5 Documents contain case data
- [ ] 6.6 Documents are editable
- [ ] 6.7 Save edited versions

## Phase 7: PDF Assembly
- [ ] 7.1 Trigger PDF generation
- [ ] 7.2 Progress updates received
- [ ] 7.3 PDF generation completes
- [ ] 7.4 PDF file size > 100KB
- [ ] 7.5 PDF contains cover letter
- [ ] 7.6 PDF contains petition
- [ ] 7.7 PDF contains exhibit list
- [ ] 7.8 PDF contains all exhibits
- [ ] 7.9 PDF has bookmarks/TOC
- [ ] 7.10 PDF metadata correct

## Phase 8: Review & Edit
- [ ] 8.1 Open PDF in viewer
- [ ] 8.2 All pages render correctly
- [ ] 8.3 No missing images/data
- [ ] 8.4 Request edits via chat
- [ ] 8.5 Re-generate with edits
- [ ] 8.6 Verify changes applied

## Phase 9: Finalization
- [ ] 9.1 Case status = "ready_for_filing"
- [ ] 9.2 Final PDF downloadable
- [ ] 9.3 PDF URL persists
- [ ] 9.4 Can share PDF link
- [ ] 9.5 Archive case (optional)

## Performance Checks
- [ ] Intake answer response < 2s
- [ ] Analysis completion < 60s
- [ ] PDF generation < 5 minutes
- [ ] Chat responses stream in real-time
- [ ] No timeouts or errors

## Data Integrity
- [ ] All answers persisted
- [ ] No data loss on pause/resume
- [ ] Semantic search returns correct facts
- [ ] Case history complete
- [ ] Audit trail present

## Error Handling
- [ ] Invalid input rejected gracefully
- [ ] Network errors handled
- [ ] Timeout recovery works
- [ ] Error messages helpful
- [ ] Can retry after failure

## Notes:
________________________________________________
________________________________________________
________________________________________________

## Overall Result:
□ PASS - Ready for production
□ CONDITIONAL PASS - Minor issues (list below)
□ FAIL - Critical issues (list below)

Issues Found:
________________________________________________
________________________________________________
________________________________________________
```

---

## 🎯 Запуск всех тестов

### Простая команда для запуска всего

**Файл:** `scripts/run_all_tests.sh`

```bash
#!/bin/bash

echo "🧪 Starting Full Cycle Test Suite"
echo "=================================="

# Set test environment
export TESTING=true
export DATABASE_URL="postgresql://test_user:test_pass@localhost/test_eb1a"
export REDIS_URL="redis://localhost:6379/1"

# Start services if needed
echo "📦 Starting test services..."
docker-compose -f docker-compose.test.yml up -d postgres redis

# Wait for services
echo "⏳ Waiting for services..."
sleep 5

# Run migrations
echo "🔄 Running migrations..."
python -m alembic upgrade head

# Run unit tests
echo "1️⃣  Running unit tests..."
pytest tests/unit/ -v --tb=short

# Run integration tests
echo "2️⃣  Running integration tests..."
pytest tests/integration/ -v --tb=short

# Start API server in background
echo "🚀 Starting API server..."
uvicorn api.main:app --port 8000 &
API_PID=$!
sleep 10

# Run E2E tests
echo "3️⃣  Running E2E API tests..."
pytest tests/e2e/test_api_full_cycle.py -v -s

# Run workflow tests
echo "4️⃣  Running workflow tests..."
pytest tests/workflows/ -v

# Run PDF tests
echo "5️⃣  Running PDF generation tests..."
pytest tests/pdf/ -v

# Run full cycle suite
echo "6️⃣  Running full cycle integration suite..."
pytest tests/full_cycle_suite.py -v -s

# Cleanup
echo "🧹 Cleaning up..."
kill $API_PID
docker-compose -f docker-compose.test.yml down

echo "✅ All tests completed!"
```

**Запуск:**
```bash
chmod +x scripts/run_all_tests.sh
./scripts/run_all_tests.sh
```

---

## 📊 Мониторинг и отчёты

### pytest HTML reports

```bash
# Install pytest-html
pip install pytest-html

# Run with HTML report
pytest tests/ -v --html=test_results/report.html --self-contained-html

# Open report
open test_results/report.html  # macOS
xdg-open test_results/report.html  # Linux
start test_results/report.html  # Windows
```

### Coverage reports

```bash
# Install coverage
pip install pytest-cov

# Run with coverage
pytest tests/ --cov=core --cov=api --cov-report=html --cov-report=term

# View coverage
open htmlcov/index.html
```

---

## 📝 Резюме

### Полный цикл тестирования включает:

1. **Unit Tests** (5 мин) - Отдельные функции
2. **Integration Tests** (10 мин) - Взаимодействие компонентов
3. **API Tests** (15 мин) - REST endpoints E2E
4. **Workflow Tests** (20 мин) - LangGraph pipelines
5. **E2E UI Tests** (30 мин) - Playwright/manual
6. **PDF Tests** (10 мин) - Document generation

**Общее время автоматизированных тестов:** ~60 минут
**Общее время с ручным тестированием:** ~90 минут

### Критерии успеха:

✅ Все unit/integration тесты проходят
✅ API tests создают case и получают анализ
✅ Workflow tests генерируют критерии
✅ PDF генерируется и содержит все секции
✅ Нет data loss при pause/resume
✅ Real-time updates работают

---

**Следующие шаги:** Смотрите файлы в `tests/` для реализации этих тестов!
