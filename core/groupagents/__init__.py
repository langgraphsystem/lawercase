"""
Core Group Agents для mega_agent_pro multi-agent system.

Этот модуль содержит специализированные агенты для различных аспектов
юридической системы:

- MegaAgent: Центральный оркестратор
- SupervisorAgent: Динамическая маршрутизация задач
- CaseAgent: Управление делами и случаями
- WriterAgent: Генерация документов и писем
- ValidatorAgent: Валидация с самокоррекцией
- RAGPipelineAgent: Гибридный поиск и RAG
- LegalResearchAgent: Юридические исследования
"""

from __future__ import annotations

__version__ = "2.0.0"
__author__ = "mega_agent_pro team"

# Export main agents when implemented
__all__ = [
    "CaseAgent",
    "WriterAgent",
    # "MegaAgent",
    # "SupervisorAgent",
    # "ValidatorAgent",
    # "RAGPipelineAgent",
    # "LegalResearchAgent",
]

# Import implemented agents
try:
    from .case_agent import CaseAgent
except ImportError:
    pass  # Agent not yet implemented
try:
    from .writer_agent import WriterAgent
except ImportError:
    pass  # Agent not yet implemented

