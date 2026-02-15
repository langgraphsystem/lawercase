"""Agent helper utilities (complexity analysis, planners, deep research, etc.)."""

from __future__ import annotations

from .complexity_analyzer import ComplexityAnalyzer, ComplexityResult, TaskTier
from .deep_research_agent import (
    DatabaseSearchTool,
    DeepResearchAgent,
    EvidenceSufficiency,
    EvidenceSufficiencyEvaluator,
    ReportSynthesizer,
    ResearchFinding,
    ResearchPhase,
    ResearchPlan,
    ResearchPlanner,
    ResearchQuestion,
    ResearchReport,
    ResearchTool,
    ScopeClarification,
    ScopeClarifier,
    SourceType,
    WebSearchTool,
    create_deep_research_agent,
)
from .report_synthesizer import (
    EnhancedReportSynthesizer,
    ReportFormat,
    ReportSection,
    SectionContent,
    StructuredReport,
    SynthesisConfig,
)
from .research_planner import (
    EnhancedResearchPlanner,
    PlanEvaluation,
    PlanningConfig,
    PlanningStrategy,
)
from .subagent_context_manager import (
    ExecutionStats,
    SubagentContextManager,
    SubagentResult,
    SubagentState,
    SubagentTask,
    create_subagent_manager,
)
from .subagent_spawner import (
    SpawnerStats,
    Subagent,
    SubagentConfig,
    SubagentSpawner,
    SubagentStatus,
    SubagentTask as SpawnerTask,
    SubagentType,
    create_subagent_spawner,
)

__all__ = [
    # Complexity Analysis
    "ComplexityAnalyzer",
    "ComplexityResult",
    "DatabaseSearchTool",
    # Deep Research Agent (v3.0)
    "DeepResearchAgent",
    # Enhanced Report Synthesizer
    "EnhancedReportSynthesizer",
    # Enhanced Research Planner
    "EnhancedResearchPlanner",
    # Evidence Sufficiency (v3.0)
    "EvidenceSufficiency",
    "EvidenceSufficiencyEvaluator",
    "ExecutionStats",
    "PlanEvaluation",
    "PlanningConfig",
    "PlanningStrategy",
    "ReportFormat",
    "ReportSection",
    "ReportSynthesizer",
    "ResearchFinding",
    "ResearchPhase",
    "ResearchPlan",
    # Planning & Synthesis
    "ResearchPlanner",
    "ResearchQuestion",
    "ResearchReport",
    # Research Tools
    "ResearchTool",
    # Scope Clarification (v3.0)
    "ScopeClarification",
    "ScopeClarifier",
    "SectionContent",
    "SourceType",
    "SpawnerStats",
    "SpawnerTask",
    "StructuredReport",
    "Subagent",
    "SubagentConfig",
    # Subagent Context Manager (v2.0)
    "SubagentContextManager",
    "SubagentResult",
    # Subagent Spawner
    "SubagentSpawner",
    "SubagentState",
    "SubagentStatus",
    "SubagentTask",
    "SubagentType",
    "SynthesisConfig",
    "TaskTier",
    "WebSearchTool",
    "create_deep_research_agent",
    "create_subagent_manager",
    "create_subagent_spawner",
]
