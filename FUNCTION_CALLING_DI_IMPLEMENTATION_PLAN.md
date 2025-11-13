# GPT-5 Function Calling & DI Container - Implementation Plan

**Дата**: 2025-11-12
**Задачи**: Sprint 1, Task #2 (Function Calling) + Task #1 (DI Унификация)
**Статус**: 🔧 **В РАЗРАБОТКЕ**

---

## 📋 Executive Summary

Комплексный план интеграции современного function calling (GPT-5 March 2025 updates) и унификации Dependency Injection для API/Telegram bot.

---

## 🔍 Текущее состояние (Audit Results)

### ✅ Railway Deployment Status
- **Platform**: Railway.app
- **Mode**: Webhook (через FastAPI)
- **Entry Point**: `api/main.py` (NOT main_production.py!)
- **Endpoint**: `POST /telegram/webhook`
- **Start Script**: `start_api.sh` → запускает `api.main:app`
- **Telegram Integration**: ✅ РАБОТАЕТ через `app.state.telegram_application`
- **Webhook URL**: `{RAILWAY_PUBLIC_DOMAIN}/telegram/webhook`

### ❌ Проблемы

1. **Function Calling**: Отсутствует
   - OpenAI client не поддерживает `tools` parameter
   - Нет Responses API support (March 2025)
   - Нет CFG (Context-Free Grammar) support
   - Документация упоминает custom tools (строка 35), но нет реализации

2. **DI Container**: Не унифицирован
   - `telegram_interface/middlewares/di_injection.py` - scaffold (4 строки)
   - MegaAgent создается дважды:
     - В `api/main.py`: `build_application(settings=settings)` → создает свой MegaAgent
     - В `telegram_interface/bot.py`: `mega_agent or MegaAgent(memory_manager=memory_manager)`
   - Нет shared state между API и Telegram handlers

---

## 🌟 GPT-5 Function Calling Updates (March 2025)

### **March 2025: Responses API Release**

#### 1. **Items** - Unified I/O Structure
```python
# Items represent inputs and outputs:
- Messages (user/assistant)
- Reasoning tokens (chain-of-thought)
- Function calls
- File search results
- Web search results
```

#### 2. **Built-in Tools** (No custom implementation needed!)
```python
Available built-in tools:
✅ file_search - Search through uploaded files
✅ web_search - Search the web
✅ code_interpreter - Execute Python code
✅ gpt-image-1 - Generate images
```

#### 3. **Enhanced Function Calling**
```python
# Old (DEPRECATED):
{
    "functions": [...],        # ❌ Deprecated
    "function_call": "auto"    # ❌ Deprecated
}

# New (2025):
{
    "tools": [                 # ✅ NEW
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                    },
                    "required": ["location"]
                }
            }
        }
    ],
    "tool_choice": "auto"      # ✅ or "required" or {"type": "function", "function": {"name": "get_weather"}}
}
```

#### 4. **Freeform Function Calling** (GPT-5 Only)
```python
{
    "type": "custom",          # ✅ NEW in GPT-5
    "name": "execute_sql",
    "payload_type": "text"     # Send raw SQL without JSON wrapping
}
```

#### 5. **Context-Free Grammar (CFG)** Support
```python
{
    "response_format": {
        "type": "cfg",
        "grammar": "digit = '0'-'9'; number = digit+;"
    }
}
```

#### 6. **Stateful Conversations**
```python
# Responses API automatically stores history
{
    "previous_response_id": "resp_abc123"  # Continue from previous
}
```

---

## 🏗️ Architecture Design

### **Phase 1: Core Infrastructure** (6 hours)

#### 1.1 Tool Registry System
Create centralized registry for all available tools:

```python
# core/tools/tool_registry.py

from __future__ import annotations
from typing import Any, Callable, Protocol
from enum import Enum
from pydantic import BaseModel, Field


class ToolType(str, Enum):
    """Types of tools available in the system."""
    FUNCTION = "function"        # Standard function calling
    CUSTOM = "custom"            # GPT-5 freeform (raw text payload)
    BUILTIN_FILE_SEARCH = "file_search"
    BUILTIN_WEB_SEARCH = "web_search"
    BUILTIN_CODE_INTERPRETER = "code_interpreter"
    BUILTIN_IMAGE_GEN = "gpt-image-1"


class ToolParameter(BaseModel):
    """Tool parameter definition."""
    type: str
    description: str | None = None
    enum: list[str] | None = None
    required: bool = False


class FunctionTool(BaseModel):
    """Function tool definition."""
    type: ToolType = ToolType.FUNCTION
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    strict: bool = False  # Structured outputs mode


class ToolDefinition(BaseModel):
    """Unified tool definition."""
    id: str
    type: ToolType
    function: FunctionTool | None = None
    enabled: bool = True
    allowed_roles: list[str] = Field(default_factory=lambda: ["admin", "lawyer"])
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolExecutor(Protocol):
    """Protocol for tool execution."""
    async def __call__(self, **kwargs: Any) -> dict[str, Any]: ...


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._executors: dict[str, ToolExecutor] = {}
        self._load_builtin_tools()

    def _load_builtin_tools(self) -> None:
        """Register built-in GPT-5 tools."""
        # File search, web search, code interpreter, image gen
        # These don't need custom executors - handled by OpenAI
        pass

    def register_tool(
        self,
        tool: ToolDefinition,
        executor: ToolExecutor | None = None
    ) -> None:
        """Register a custom tool."""
        self._tools[tool.id] = tool
        if executor:
            self._executors[tool.id] = executor

    def get_tools_for_model(
        self,
        model: str,
        role: str | None = None
    ) -> list[dict[str, Any]]:
        """Get tools formatted for OpenAI API."""
        tools = []
        for tool in self._tools.values():
            if not tool.enabled:
                continue
            if role and role not in tool.allowed_roles:
                continue
            if tool.type == ToolType.FUNCTION and tool.function:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.function.name,
                        "description": tool.function.description,
                        "parameters": tool.function.parameters,
                        "strict": tool.function.strict
                    }
                })
            elif tool.type in {ToolType.BUILTIN_FILE_SEARCH, ToolType.BUILTIN_WEB_SEARCH}:
                tools.append({"type": tool.type.value})
        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a registered tool."""
        executor = self._executors.get(tool_name)
        if not executor:
            raise ValueError(f"No executor for tool: {tool_name}")
        return await executor(**arguments)


# Singleton instance
_registry: ToolRegistry | None = None

def get_tool_registry() -> ToolRegistry:
    """Get global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
```

#### 1.2 Update OpenAI Client

```python
# core/llm_interface/openai_client.py

# Add to __init__:
def __init__(
    self,
    ...
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] = "auto",
    **kwargs: Any,
) -> None:
    ...
    self.tools = tools
    self.tool_choice = tool_choice

# Add to acomplete:
async def acomplete(
    self,
    prompt: str,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    **params: Any
) -> dict[str, Any]:
    """Async completion with tools support."""
    tools = tools or self.tools
    tool_choice = tool_choice or self.tool_choice

    request_params = {
        "model": self.model,
        "messages": [{"role": "user", "content": prompt}],
        **self._get_model_params(),
        **params
    }

    # Add tools if provided
    if tools:
        request_params["tools"] = tools
        request_params["tool_choice"] = tool_choice

    # Circuit breaker protected call
    protected_call = self._circuit_breaker(self._acomplete_impl)
    return await protected_call(request_params)

async def _acomplete_impl(self, request_params: dict[str, Any]) -> dict[str, Any]:
    """Internal implementation with tool calls handling."""
    response = await self.client.chat.completions.create(**request_params)

    result = {
        "output": "",
        "provider": "openai",
        "model": response.model,
        "finish_reason": response.choices[0].finish_reason,
        "usage": response.usage.model_dump() if response.usage else {},
    }

    choice = response.choices[0]

    # Handle tool calls
    if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
        result["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in choice.message.tool_calls
        ]
        result["requires_tool_execution"] = True

    # Extract text response
    if choice.message.content:
        result["output"] = choice.message.content

    return result
```

#### 1.3 Tool Execution Loop

```python
# core/tools/executor.py

async def execute_tool_loop(
    client: OpenAIClient,
    initial_prompt: str,
    tools: list[dict[str, Any]],
    max_iterations: int = 5,
    registry: ToolRegistry | None = None
) -> dict[str, Any]:
    """Execute LLM with tool calling loop.

    Handles:
    1. Initial LLM call
    2. Tool execution
    3. Result feeding back to LLM
    4. Final answer extraction
    """
    registry = registry or get_tool_registry()
    messages = [{"role": "user", "content": initial_prompt}]

    for iteration in range(max_iterations):
        # Call LLM
        response = await client.acomplete(
            prompt=initial_prompt if iteration == 0 else "",
            messages=messages if iteration > 0 else None,
            tools=tools,
            tool_choice="auto"
        )

        # Check if tool calls required
        if not response.get("requires_tool_execution"):
            return response

        # Execute tool calls
        tool_calls = response.get("tool_calls", [])
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            # Execute tool
            tool_result = await registry.execute_tool(func_name, arguments)

            # Add to messages
            messages.append({
                "role": "assistant",
                "tool_calls": [tool_call]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(tool_result)
            })

    raise RuntimeError(f"Tool loop exceeded {max_iterations} iterations")
```

---

### **Phase 2: Useful Tools Implementation** (8 hours)

#### 2.1 Case Management Tools

```python
# tools/case_tools.py

from core.tools import ToolRegistry, ToolDefinition, FunctionTool, ToolType

async def get_case_info(case_id: str) -> dict[str, Any]:
    """Get case information."""
    # Implementation via CaseAgent
    pass

async def create_case(
    client_name: str,
    case_type: str,
    description: str
) -> dict[str, Any]:
    """Create new case."""
    pass

async def update_case_status(
    case_id: str,
    status: str
) -> dict[str, Any]:
    """Update case status."""
    pass

def register_case_tools(registry: ToolRegistry) -> None:
    """Register case management tools."""

    # Get case info
    registry.register_tool(
        ToolDefinition(
            id="get_case",
            type=ToolType.FUNCTION,
            function=FunctionTool(
                name="get_case",
                description="Retrieve information about a specific case",
                parameters={
                    "type": "object",
                    "properties": {
                        "case_id": {
                            "type": "string",
                            "description": "The unique identifier of the case"
                        }
                    },
                    "required": ["case_id"]
                }
            ),
            allowed_roles=["admin", "lawyer", "paralegal", "client"]
        ),
        executor=get_case_info
    )

    # Create case
    registry.register_tool(
        ToolDefinition(
            id="create_case",
            type=ToolType.FUNCTION,
            function=FunctionTool(
                name="create_case",
                description="Create a new case",
                parameters={
                    "type": "object",
                    "properties": {
                        "client_name": {"type": "string"},
                        "case_type": {
                            "type": "string",
                            "enum": ["eb1a", "eb2", "civil", "criminal"]
                        },
                        "description": {"type": "string"}
                    },
                    "required": ["client_name", "case_type"]
                }
            ),
            allowed_roles=["admin", "lawyer"]
        ),
        executor=create_case
    )
```

#### 2.2 Document Tools

```python
# tools/document_tools.py

async def generate_letter(
    recipient: str,
    subject: str,
    content: str,
    tone: str = "professional"
) -> dict[str, Any]:
    """Generate legal letter."""
    # Via WriterAgent
    pass

async def generate_pdf(document_id: str) -> dict[str, Any]:
    """Generate PDF from document."""
    pass

def register_document_tools(registry: ToolRegistry) -> None:
    """Register document generation tools."""
    registry.register_tool(
        ToolDefinition(
            id="generate_letter",
            type=ToolType.FUNCTION,
            function=FunctionTool(
                name="generate_letter",
                description="Generate a professional legal letter",
                parameters={
                    "type": "object",
                    "properties": {
                        "recipient": {"type": "string"},
                        "subject": {"type": "string"},
                        "content": {"type": "string"},
                        "tone": {
                            "type": "string",
                            "enum": ["formal", "professional", "casual"]
                        }
                    },
                    "required": ["recipient", "subject", "content"]
                },
                strict=True  # Structured outputs
            ),
            allowed_roles=["admin", "lawyer", "paralegal"]
        ),
        executor=generate_letter
    )
```

#### 2.3 Memory/RAG Tools

```python
# tools/memory_tools.py

async def search_memory(
    query: str,
    topk: int = 5
) -> dict[str, Any]:
    """Search semantic memory."""
    pass

async def add_to_memory(
    text: str,
    tags: list[str] | None = None
) -> dict[str, Any]:
    """Add information to memory."""
    pass

def register_memory_tools(registry: ToolRegistry) -> None:
    """Register memory/RAG tools."""
    registry.register_tool(
        ToolDefinition(
            id="search_memory",
            type=ToolType.FUNCTION,
            function=FunctionTool(
                name="search_memory",
                description="Search through the system's memory for relevant information",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "topk": {"type": "integer", "default": 5}
                    },
                    "required": ["query"]
                }
            )
        ),
        executor=search_memory
    )
```

---

### **Phase 3: DI Container Unification** (12 hours)

#### 3.1 Create DI Container

```python
# core/di/container.py

from __future__ import annotations
from typing import Any, Callable, TypeVar
from collections.abc import Awaitable

T = TypeVar('T')


class Container:
    """Dependency Injection container."""

    def __init__(self):
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}
        self._async_factories: dict[str, Callable[[], Awaitable[Any]]] = {}

    def register_singleton(self, key: str, instance: Any) -> None:
        """Register singleton instance."""
        self._singletons[key] = instance

    def register_factory(
        self,
        key: str,
        factory: Callable[[], T],
        is_async: bool = False
    ) -> None:
        """Register factory function."""
        if is_async:
            self._async_factories[key] = factory  # type: ignore
        else:
            self._factories[key] = factory

    def get(self, key: str) -> Any:
        """Get dependency (sync)."""
        # Check singletons first
        if key in self._singletons:
            return self._singletons[key]

        # Check factories
        if key in self._factories:
            instance = self._factories[key]()
            return instance

        raise KeyError(f"Dependency not found: {key}")

    async def aget(self, key: str) -> Any:
        """Get dependency (async)."""
        # Check singletons
        if key in self._singletons:
            return self._singletons[key]

        # Check async factories
        if key in self._async_factories:
            instance = await self._async_factories[key]()
            return instance

        # Fallback to sync
        if key in self._factories:
            return self._factories[key]()

        raise KeyError(f"Dependency not found: {key}")

    def get_or_create_singleton(
        self,
        key: str,
        factory: Callable[[], T]
    ) -> T:
        """Get existing singleton or create new one."""
        if key not in self._singletons:
            self._singletons[key] = factory()
        return self._singletons[key]


# Global container
_container: Container | None = None


def get_container() -> Container:
    """Get global DI container."""
    global _container
    if _container is None:
        _container = Container()
        _initialize_container(_container)
    return _container


def _initialize_container(container: Container) -> None:
    """Initialize container with default dependencies."""
    from core.memory.memory_manager import MemoryManager
    from core.groupagents.mega_agent import MegaAgent
    from core.tools.tool_registry import get_tool_registry

    # Singletons
    container.register_singleton("memory_manager", MemoryManager())
    container.register_singleton("tool_registry", get_tool_registry())

    # Factories
    def create_mega_agent() -> MegaAgent:
        memory = container.get("memory_manager")
        return MegaAgent(memory_manager=memory)

    container.register_factory("mega_agent", create_mega_agent)
```

#### 3.2 Integrate in api/main.py

```python
# api/main.py

from core.di import get_container

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan with DI container."""

    # Initialize DI container
    container = get_container()
    app.state.di_container = container

    # Get shared MegaAgent from container
    mega_agent = container.get("mega_agent")

    # Build Telegram app with shared MegaAgent
    telegram_app = build_application(
        settings=settings,
        mega_agent=mega_agent  # Use shared instance!
    )
    ...
```

#### 3.3 Telegram Middleware for DI

```python
# telegram_interface/middlewares/di_injection.py

from telegram import Update
from telegram.ext import Application, ContextTypes
from core.di import get_container


class DIMiddleware:
    """Middleware to inject dependencies into Telegram handlers."""

    def __init__(self, application: Application):
        self.application = application
        self.container = get_container()

    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Inject dependencies into context."""
        context.bot_data["di_container"] = self.container
        context.bot_data["mega_agent"] = self.container.get("mega_agent")
        context.bot_data["memory_manager"] = self.container.get("memory_manager")
        context.bot_data["tool_registry"] = self.container.get("tool_registry")


def setup_di_middleware(application: Application) -> None:
    """Setup DI middleware for Telegram bot."""
    middleware = DIMiddleware(application)
    application.add_handler(middleware, group=-1)  # Run before other handlers
```

---

## 📊 Implementation Roadmap

### **Sprint 1: Core Infrastructure** (6h)
- [ ] Create `core/tools/tool_registry.py` (2h)
- [ ] Update `core/llm_interface/openai_client.py` with tools support (2h)
- [ ] Create `core/tools/executor.py` for tool loop (1h)
- [ ] Add tests for tool registry (1h)

### **Sprint 2: Tools Implementation** (8h)
- [ ] Implement case management tools (2h)
- [ ] Implement document generation tools (2h)
- [ ] Implement memory/RAG tools (2h)
- [ ] Register all tools in registry (1h)
- [ ] Add tests for tools (1h)

### **Sprint 3: DI Container** (12h)
- [ ] Create `core/di/container.py` (3h)
- [ ] Update `api/main.py` to use DI (2h)
- [ ] Update `telegram_interface/bot.py` to use DI (2h)
- [ ] Implement DI middleware for Telegram (2h)
- [ ] Refactor handlers to use injected dependencies (2h)
- [ ] Add tests for DI container (1h)

### **Sprint 4: Integration & Testing** (6h)
- [ ] Integrate function calling in MegaAgent (2h)
- [ ] End-to-end testing with real tools (2h)
- [ ] Railway deployment testing (1h)
- [ ] Documentation (1h)

**Total**: ~32 hours

---

## ✅ Acceptance Criteria

### Function Calling
- [ ] OpenAI client supports `tools` parameter
- [ ] Tool registry with 10+ useful tools
- [ ] Tool execution loop handles multi-turn conversations
- [ ] MegaAgent can invoke tools automatically
- [ ] Telegram bot can use tools via commands

### DI Container
- [ ] Single global container
- [ ] Shared MegaAgent instance between API and Telegram
- [ ] Telegram middleware injects dependencies
- [ ] No duplicate service creation
- [ ] Easy to test with mock dependencies

---

## 🚀 Quick Start (After Implementation)

```python
# API endpoint
from fastapi import Depends
from core.di import get_container

@app.post("/ask")
async def ask(
    query: str,
    container = Depends(get_container)
):
    mega_agent = container.get("mega_agent")
    tools = container.get("tool_registry").get_tools_for_model("gpt-5")

    result = await mega_agent.handle_command_with_tools(
        query=query,
        tools=tools
    )
    return result

# Telegram handler
async def telegram_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mega_agent = context.bot_data["mega_agent"]
    tools = context.bot_data["tool_registry"].get_tools_for_model("gpt-5")

    result = await mega_agent.handle_command_with_tools(
        query=update.message.text,
        tools=tools
    )
    await update.message.reply_text(result["output"])
```

---

**Next Step**: Begin Sprint 1 implementation! 🚀
