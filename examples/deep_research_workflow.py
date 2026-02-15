"""Deep Research Workflow Examples.

This module demonstrates the complete Deep Research Agent workflow including:
- Research planning with strategy selection
- Subagent spawning for parallel research
- Fact checking and verification
- Quality evaluation and benchmarking
- Report synthesis with multiple formats
"""

from __future__ import annotations

import asyncio

from benchmarks.baseline_comparison import (
    EnhancedBaselineComparator,
)
from benchmarks.citation_validator import (
    EnhancedCitationValidator,
)
from benchmarks.fact_checker import (
    FactChecker,
)

# Benchmarking components
from benchmarks.quality_evaluator import (
    EvaluationConfig,
    QualityEvaluator,
)

# Core Deep Research components
from core.agents.deep_research_agent import (
    ResearchFinding,
    SourceType,
)
from core.agents.report_synthesizer import (
    EnhancedReportSynthesizer,
    ReportFormat,
    ReportSection,
    SynthesisConfig,
)

# Enhanced components
from core.agents.research_planner import (
    EnhancedResearchPlanner,
    PlanningStrategy,
)
from core.agents.subagent_spawner import (
    SubagentSpawner,
    SubagentTask,
    SubagentType,
)

# Metrics
from utils.metrics.self_correction_analytics import (
    CorrectionTrigger,
    CorrectionType,
    SelfCorrectionAnalytics,
)


# Mock LLM caller for examples
async def mock_llm_caller(prompt: str) -> str:
    """Mock LLM caller for demonstration."""
    await asyncio.sleep(0.1)  # Simulate API call

    if "sub-questions" in prompt.lower():
        return """1. What is the history of quantum computing?
2. What are the key principles and algorithms?
3. What are current applications and limitations?
4. What future developments are expected?"""

    if "score" in prompt.lower():
        return "8"

    if "extract" in prompt.lower() and "fact" in prompt.lower():
        return """- Quantum computers use qubits instead of classical bits
- Qubits can exist in superposition states
- Google achieved quantum supremacy in 2019"""

    if "verify" in prompt.lower():
        return "verified"

    if "summarize" in prompt.lower() or "key findings" in prompt.lower():
        return """Key findings:
1. Quantum computing represents a paradigm shift in computation
2. Current systems face significant decoherence challenges
3. Near-term applications focus on optimization and simulation"""

    return f"Response to: {prompt[:50]}..."


# Example 1: Basic Research Planning
async def example_research_planning():
    """Demonstrate research planning with different strategies."""
    print("\n=== Example 1: Research Planning ===\n")

    planner = EnhancedResearchPlanner(llm_caller=mock_llm_caller)

    # Create plans with different strategies
    strategies = [
        PlanningStrategy.BREADTH_FIRST,
        PlanningStrategy.DEPTH_FIRST,
        PlanningStrategy.BALANCED,
    ]

    question = "What is quantum computing and what are its applications?"

    for strategy in strategies:
        print(f"Planning with {strategy.value} strategy...")
        plan = await planner.create_strategic_plan(
            question=question,
            context="User wants comprehensive overview",
            strategy=strategy,
        )

        print(f"   Strategy: {plan.strategy}")
        print(f"   Sub-questions: {len(plan.sub_questions)}")
        print(f"   Priority score: {plan.priority_score:.2f}\n")

    # Evaluate and optimize a plan
    print("Evaluating and optimizing plan...")
    plan = await planner.create_strategic_plan(question)
    evaluation = await planner.evaluate_plan(plan)

    print(f"   Quality score: {evaluation.quality_score:.2f}")
    print(f"   Coverage: {evaluation.coverage_score:.2f}")
    print(f"   Feasibility: {evaluation.feasibility_score:.2f}")

    if evaluation.improvement_suggestions:
        print(f"   Suggestions: {evaluation.improvement_suggestions[0]}\n")


# Example 2: Subagent Spawning
async def example_subagent_spawning():
    """Demonstrate parallel subagent execution."""
    print("\n=== Example 2: Subagent Spawning ===\n")

    spawner = SubagentSpawner(
        max_concurrent=3,
        default_timeout=30.0,
    )

    # Define research tasks
    queries = [
        "quantum computing basics",
        "quantum algorithms overview",
        "quantum hardware developments",
        "quantum error correction",
    ]

    tasks = [
        SubagentTask(
            task_id=f"task_{i}",
            subagent_id="",
            query=query,
            context={"depth": "standard"},
        )
        for i, query in enumerate(queries)
    ]

    # Mock executor
    async def research_executor(query: str, context: dict) -> dict:
        await asyncio.sleep(0.2)  # Simulate research
        return {
            "query": query,
            "findings": [f"Finding about {query}"],
            "sources": ["https://example.com/source"],
        }

    print(f"Spawning {len(tasks)} subagents for parallel research...")
    results = await spawner.spawn_and_execute(
        tasks=tasks,
        executor=research_executor,
        subagent_type=SubagentType.WEB_SEARCHER,
    )

    print("\nResults:")
    for task in results:
        status = task.status.value
        print(f"   Task {task.task_id}: {status}")

    stats = spawner.get_stats()
    print("\nStatistics:")
    print(f"   Total spawned: {stats['total_spawned']}")
    print(f"   Completed: {stats['completed_tasks']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")
    print(f"   Avg task time: {stats['avg_task_time']:.2f}s\n")


# Example 3: Fact Checking
async def example_fact_checking():
    """Demonstrate fact extraction and verification."""
    print("\n=== Example 3: Fact Checking ===\n")

    fact_checker = FactChecker(llm_caller=mock_llm_caller)

    text = """
    Quantum computing uses qubits that can exist in superposition states.
    Google claimed quantum supremacy in 2019 with their Sycamore processor.
    Current quantum computers have error rates around 0.1% to 1%.
    IBM has deployed over 20 quantum systems accessible via cloud.
    """

    print("Checking facts in research output...")
    report = await fact_checker.check(text)

    print("\nFact Check Report:")
    print(f"   Total claims: {report.total_claims}")
    print(f"   Verified: {report.verified_count}")
    print(f"   Unverified: {report.unverified_count}")
    print(f"   Contradicted: {report.contradicted_count}")
    print(f"   Overall credibility: {report.credibility_score:.2f}")

    if report.summary:
        print(f"   Summary: {report.summary[:100]}...\n")


# Example 4: Quality Evaluation
async def example_quality_evaluation():
    """Demonstrate multi-dimensional quality evaluation."""
    print("\n=== Example 4: Quality Evaluation ===\n")

    evaluator = QualityEvaluator(
        llm_caller=mock_llm_caller,
        config=EvaluationConfig(
            include_relevance=True,
            include_accuracy=True,
            include_completeness=True,
            min_score_threshold=0.6,
        ),
    )

    query = "Explain quantum entanglement"
    answer = """
    Quantum entanglement is a phenomenon where two or more quantum particles
    become correlated in such a way that the quantum state of each particle
    cannot be described independently. When particles are entangled, measuring
    one particle instantly affects the other, regardless of distance.

    This was famously called "spooky action at a distance" by Einstein.
    Entanglement is fundamental to quantum computing and quantum cryptography.
    """

    print("Evaluating research output quality...")
    report = await evaluator.evaluate(
        query=query,
        answer=answer,
        sources=["https://arxiv.org/quantum"],
        context={"expected_depth": "detailed"},
    )

    print("\nQuality Report:")
    print(f"   Overall score: {report.overall_score:.2f}")
    print(f"   Grade: {report.grade.value}")
    print(f"   Passed: {report.passed}")

    print("\n   Dimension scores:")
    for score in report.dimension_scores:
        print(f"      {score.dimension.value}: {score.score:.2f}")

    if report.recommendations:
        print("\n   Recommendations:")
        for rec in report.recommendations[:3]:
            print(f"      - {rec}\n")


# Example 5: Citation Validation
async def example_citation_validation():
    """Demonstrate citation validation."""
    print("\n=== Example 5: Citation Validation ===\n")

    validator = EnhancedCitationValidator(llm_caller=mock_llm_caller)

    citations = [
        "https://arxiv.org/abs/2301.12345",
        "https://nature.com/articles/quantum-computing",
        "https://example-blog.com/my-thoughts",
        "10.1038/nature12345",
        "invalid-citation",
    ]

    context = "Research on quantum computing applications"

    print("Validating citations...")
    results, analysis = await validator.validate_batch(
        citations=citations,
        context=context,
    )

    print("\nValidation Results:")
    for result in results:
        status = result.status.value
        authority = result.authority.value
        print(f"   {result.citation[:40]}...")
        print(f"      Status: {status}, Authority: {authority}, Score: {result.overall_score:.2f}")

    print("\nAnalysis:")
    print(f"   Total: {analysis.total_citations}")
    print(f"   Valid: {analysis.valid_count}")
    print(f"   Invalid: {analysis.invalid_count}")
    print(f"   Domain diversity: {analysis.domain_diversity:.2f}")

    if analysis.issues:
        print(f"   Issues: {', '.join(analysis.issues)}\n")


# Example 6: Report Synthesis
async def example_report_synthesis():
    """Demonstrate report synthesis with multiple formats."""
    print("\n=== Example 6: Report Synthesis ===\n")

    synthesizer = EnhancedReportSynthesizer(
        llm_caller=mock_llm_caller,
        config=SynthesisConfig(
            format=ReportFormat.MARKDOWN,
            include_sections=[
                ReportSection.EXECUTIVE_SUMMARY,
                ReportSection.KEY_FINDINGS,
                ReportSection.SOURCES,
                ReportSection.RECOMMENDATIONS,
            ],
            max_key_findings=5,
        ),
    )

    # Create sample findings
    findings = [
        ResearchFinding(
            content="Quantum computers use qubits that can exist in superposition",
            source="https://arxiv.org/quantum",
            source_type=SourceType.ACADEMIC,
            relevance=0.95,
            confidence=0.9,
            metadata={"topic": "fundamentals"},
        ),
        ResearchFinding(
            content="Current quantum systems face decoherence challenges",
            source="https://nature.com/quantum",
            source_type=SourceType.ACADEMIC,
            relevance=0.85,
            confidence=0.85,
            metadata={"topic": "challenges"},
        ),
        ResearchFinding(
            content="Near-term applications include optimization and simulation",
            source="https://ibm.com/quantum",
            source_type=SourceType.WEB_SEARCH,
            relevance=0.8,
            confidence=0.8,
            metadata={"topic": "applications"},
        ),
    ]

    print("Synthesizing research report...")
    report = await synthesizer.synthesize_structured(
        question="What is the current state of quantum computing?",
        findings=findings,
    )

    print("\nStructured Report:")
    print(f"   Report ID: {report.report_id}")
    print(f"   Sections: {len(report.sections)}")
    print(f"   Findings: {len(report.findings)}")
    print(f"   Sources: {len(report.sources)}")
    print(f"   Confidence: {report.confidence:.2f}")
    print(f"   Coverage: {report.coverage:.2f}")

    # Generate different formats
    print("\n   Available formats:")
    for fmt in [ReportFormat.MARKDOWN, ReportFormat.JSON, ReportFormat.PLAIN_TEXT]:
        output = synthesizer.format_report(report, fmt)
        print(f"      {fmt.value}: {len(output)} chars")

    print()


# Example 7: Baseline Comparison
async def example_baseline_comparison():
    """Demonstrate baseline comparison."""
    print("\n=== Example 7: Baseline Comparison ===\n")

    comparator = EnhancedBaselineComparator()

    # Register mock baselines
    async def mock_baseline_gpt4(query: str) -> str:
        await asyncio.sleep(0.1)
        return f"GPT-4 response about {query}"

    async def mock_baseline_claude(query: str) -> str:
        await asyncio.sleep(0.1)
        return f"Claude response about {query}"

    comparator.register_baseline("gpt-4", mock_baseline_gpt4)
    comparator.register_baseline("claude", mock_baseline_claude)

    print("Comparing against baselines...")

    # Simulate multiple comparisons
    for i in range(5):
        await comparator.compare_single(
            query=f"Research question {i+1}",
            our_response=f"Our detailed research response about question {i+1}",
            our_score=0.75 + (i * 0.03),  # Improving
        )

    # Get leaderboard
    leaderboard = comparator.get_leaderboard()
    print("\nLeaderboard:")
    for entry in leaderboard:
        print(
            f"   #{entry.rank} {entry.model_name}: {entry.avg_score:.3f} (n={entry.sample_count})"
        )

    # Get statistical comparison
    stats = comparator.get_statistical_comparison("gpt-4")
    if stats:
        print("\nvs GPT-4:")
        print(f"   Improvement: {stats.improvement_mean:.1%}")
        print(f"   Effect size: {stats.effect_size:.3f}")
        print(f"   Significance: {stats.significance.value}")
        print(f"   Win/Loss/Tie: {stats.wins}/{stats.losses}/{stats.ties}\n")


# Example 8: Self-Correction Analytics
async def example_self_correction_analytics():
    """Demonstrate self-correction tracking."""
    print("\n=== Example 8: Self-Correction Analytics ===\n")

    analytics = SelfCorrectionAnalytics()

    # Record sample corrections
    corrections = [
        (CorrectionType.FACTUAL, CorrectionTrigger.FACT_CHECK, 0.6, 0.85),
        (CorrectionType.COMPLETENESS, CorrectionTrigger.SELF_REVIEW, 0.7, 0.8),
        (CorrectionType.COHERENCE, CorrectionTrigger.VALIDATOR, 0.65, 0.75),
        (CorrectionType.SOURCE, CorrectionTrigger.FACT_CHECK, 0.5, 0.9),
    ]

    print("Recording correction events...")
    for i, (corr_type, trigger, orig_conf, new_conf) in enumerate(corrections):
        await analytics.record_correction(
            session_id="session_001",
            agent_id="research_agent",
            correction_type=corr_type,
            trigger=trigger,
            original_content=f"Original content {i}",
            corrected_content=f"Corrected content {i}",
            original_confidence=orig_conf,
            corrected_confidence=new_conf,
            latency_seconds=1.5 + i * 0.5,
            iteration_count=1,
        )

    # Get summary
    summary = analytics.get_summary()

    print("\nAnalytics Summary:")
    print(f"   Total corrections: {summary.total_corrections}")
    print(f"   Success rate: {summary.success_rate:.1%}")
    print(f"   Avg confidence improvement: {summary.avg_confidence_improvement:+.3f}")
    print(f"   Avg latency: {summary.avg_latency:.2f}s")

    print("\n   By type:")
    for type_name, count in summary.corrections_by_type.items():
        print(f"      {type_name}: {count}")

    # Get patterns
    patterns = analytics.get_patterns(min_frequency=1)
    if patterns:
        print("\n   Top patterns:")
        for pattern in patterns[:3]:
            print(f"      {pattern.correction_type.value} via {pattern.trigger.value}")
            print(f"         Frequency: {pattern.frequency}, Success: {pattern.success_rate:.1%}\n")


# Example 9: Complete Research Workflow
async def example_complete_workflow():
    """Demonstrate complete research workflow."""
    print("\n=== Example 9: Complete Research Workflow ===\n")

    # Initialize components
    planner = EnhancedResearchPlanner(llm_caller=mock_llm_caller)
    spawner = SubagentSpawner(max_concurrent=3)
    synthesizer = EnhancedReportSynthesizer(llm_caller=mock_llm_caller)
    fact_checker = FactChecker(llm_caller=mock_llm_caller)
    evaluator = QualityEvaluator(llm_caller=mock_llm_caller)

    question = "What are the implications of quantum computing for cybersecurity?"

    # Step 1: Plan research
    print("Step 1: Planning research...")
    plan = await planner.create_strategic_plan(
        question=question,
        strategy=PlanningStrategy.BALANCED,
    )
    print(f"   Created plan with {len(plan.sub_questions)} sub-questions")

    # Step 2: Execute parallel research
    print("\nStep 2: Executing parallel research...")
    tasks = [
        SubagentTask(
            task_id=f"task_{i}",
            subagent_id="",
            query=sq,
        )
        for i, sq in enumerate(plan.sub_questions[:3])
    ]

    async def research_fn(query: str, context: dict) -> dict:
        await asyncio.sleep(0.2)
        return {"query": query, "findings": [f"Research about {query}"]}

    results = await spawner.spawn_and_execute(tasks, research_fn)
    print(f"   Completed {len(results)} research tasks")

    # Step 3: Aggregate findings
    print("\nStep 3: Aggregating findings...")
    findings = [
        ResearchFinding(
            content=f"Finding from task {t.task_id}",
            source="https://example.com",
            source_type=SourceType.WEB_SEARCH,
            relevance=0.8,
            confidence=0.75,
        )
        for t in results
    ]
    print(f"   Aggregated {len(findings)} findings")

    # Step 4: Fact check
    print("\nStep 4: Fact checking...")
    fact_report = await fact_checker.check("\n".join(f.content for f in findings))
    print(f"   Verified {fact_report.verified_count}/{fact_report.total_claims} claims")

    # Step 5: Synthesize report
    print("\nStep 5: Synthesizing report...")
    report = await synthesizer.synthesize_structured(question, findings, plan)
    print(f"   Generated report with {len(report.sections)} sections")

    # Step 6: Evaluate quality
    print("\nStep 6: Evaluating quality...")
    quality = await evaluator.evaluate(
        query=question,
        answer=report.to_markdown(),
        sources=[f.source for f in findings],
    )
    print(f"   Overall quality: {quality.overall_score:.2f} ({quality.grade.value})")

    print("\n" + "=" * 50)
    print("Research workflow completed successfully!")
    print("=" * 50 + "\n")


# Main execution
async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  Deep Research Workflow - Examples")
    print("=" * 60)

    try:
        await example_research_planning()
        await example_subagent_spawning()
        await example_fact_checking()
        await example_quality_evaluation()
        await example_citation_validation()
        await example_report_synthesis()
        await example_baseline_comparison()
        await example_self_correction_analytics()
        await example_complete_workflow()

        print("\n" + "=" * 60)
        print("  All Examples Completed Successfully!")
        print("=" * 60)
        print("\nKey Components Demonstrated:")
        print("   1. Research Planning - Strategy-aware plan generation")
        print("   2. Subagent Spawning - Parallel research execution")
        print("   3. Fact Checking - Claim verification pipeline")
        print("   4. Quality Evaluation - Multi-dimensional scoring")
        print("   5. Citation Validation - Source verification")
        print("   6. Report Synthesis - Multi-format report generation")
        print("   7. Baseline Comparison - Statistical analysis")
        print("   8. Self-Correction Analytics - Learning tracking")
        print("   9. Complete Workflow - End-to-end research pipeline")
        print()

    except ImportError as e:
        print(f"\nImportError: {e}")
        print("Some modules may not be available. Ensure all dependencies are installed.")

    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
