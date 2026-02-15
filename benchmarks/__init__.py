"""Performance benchmarking suite for MegaAgent Pro.

Provides quality metrics and evaluation:
- DeepResearchBench: End-to-end research quality evaluation
- QualityEvaluator: Multi-dimensional quality scoring
- FactChecker: Fact verification pipeline
- CitationValidator: Citation accuracy validation
- BaselineComparator: Comparison with baselines
"""

from __future__ import annotations

from .baseline_comparison import (
    BaselineModel,
    ComparisonMetric,
    ComparisonResult,
    EnhancedBaselineComparator,
    LeaderboardEntry,
    SignificanceLevel,
    StatisticalComparison,
)
from .citation_validator import (
    CitationAnalysis,
    CitationFormat,
    CitationMetadata,
    EnhancedCitationValidation,
    EnhancedCitationValidator,
    SourceAuthority,
    ValidationStatus,
)
from .deep_research_bench import (
    BaselineComparator as SimpleBaselineComparator,
    BenchmarkResult,
    CitationValidation,
    CitationValidator as BaseCitationValidator,
    DeepResearchBench,
    FactChecker as BaseFactChecker,
    FactVerificationResult,
    QualityDimension,
    QualityEvaluator as BaseQualityEvaluator,
    QualityScore,
    VerificationStatus,
    create_deep_research_bench,
)
from .fact_checker import (
    Claim,
    ClaimExtractor,
    ClaimType,
    FactChecker,
    FactCheckReport,
    VerificationResult,
    VerificationStatus as EnhancedVerificationStatus,
)

# Enhanced components
from .quality_evaluator import (
    DimensionScore,
    EvaluationConfig,
    QualityEvaluator,
    QualityGrade,
    QualityReport,
)

# Backwards compatibility
CitationValidator = EnhancedCitationValidator
BaselineComparator = EnhancedBaselineComparator

__all__ = [
    "BaseCitationValidator",
    "BaseFactChecker",
    "BaseQualityEvaluator",
    # Baseline Comparison (enhanced)
    "BaselineComparator",
    "BaselineModel",
    # Benchmark
    "BenchmarkResult",
    "CitationAnalysis",
    "CitationFormat",
    "CitationMetadata",
    # Citation Validation (enhanced)
    "CitationValidation",
    "CitationValidator",
    "Claim",
    "ClaimExtractor",
    "ClaimType",
    "ComparisonMetric",
    "ComparisonResult",
    "DeepResearchBench",
    "DimensionScore",
    "EnhancedBaselineComparator",
    "EnhancedCitationValidation",
    "EnhancedCitationValidator",
    "EnhancedVerificationStatus",
    "EvaluationConfig",
    "FactCheckReport",
    "FactChecker",
    # Fact Verification (enhanced)
    "FactVerificationResult",
    "LeaderboardEntry",
    # Quality Dimensions
    "QualityDimension",
    "QualityEvaluator",
    "QualityGrade",
    "QualityReport",
    # Quality Scoring (enhanced)
    "QualityScore",
    "SignificanceLevel",
    "SimpleBaselineComparator",
    "SourceAuthority",
    "StatisticalComparison",
    "ValidationStatus",
    "VerificationResult",
    "VerificationStatus",
    "create_deep_research_bench",
]

__version__ = "2.0.0"
