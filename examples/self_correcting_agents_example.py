"""Self-Correcting Agents Examples.

This module demonstrates how to use the self-correction system with
confidence scoring, automatic retry, and quality tracking.
"""

from __future__ import annotations

import asyncio

from core.groupagents.self_correcting_mixin import SelfCorrectingAgent, SelfCorrectingMixin
from core.validation import (
    ConfidenceScorer,
    QualityTracker,
    RetryConfig,
    RetryHandler,
    RetryStrategy,
)


# Example 1: Basic Confidence Scoring
def example_confidence_scoring():
    """Demonstrate basic confidence scoring."""
    print("\n=== Example 1: Confidence Scoring ===\n")

    scorer = ConfidenceScorer()

    # High quality output
    metrics1 = scorer.score_output(
        output="The capital of France is Paris. It is located in the north-central "
        "part of the country and serves as a major cultural and economic center.",
        context={"query": "What is the capital of France?"},
    )

    print("✅ High Quality Output:")
    print(f"   Confidence: {metrics1.overall_confidence:.2f}")
    print(f"   Threshold: {metrics1.threshold.value}")
    print(f"   Needs Review: {metrics1.needs_review}")
    print(f"   Needs Correction: {metrics1.needs_correction}\n")

    # Low quality output
    metrics2 = scorer.score_output(
        output="maybe paris?",
        context={"query": "What is the capital of France?"},
    )

    print("❌ Low Quality Output:")
    print(f"   Confidence: {metrics2.overall_confidence:.2f}")
    print(f"   Threshold: {metrics2.threshold.value}")
    print(f"   Needs Review: {metrics2.needs_review}")
    print(f"   Needs Correction: {metrics2.needs_correction}")
    print(f"   Suggestions: {metrics2.suggestions}\n")


# Example 2: Retry Handler
async def example_retry_handler():
    """Demonstrate retry handler with validation."""
    print("\n=== Example 2: Retry Handler ===\n")

    handler = RetryHandler()

    # Simulated agent function that improves over retries
    call_count = 0

    async def mock_agent_function(query: str) -> str:
        nonlocal call_count
        call_count += 1

        print(f"   Attempt {call_count}...")

        if call_count == 1:
            return "short answer"  # Low confidence
        if call_count == 2:
            return f"A better answer to {query}"  # Medium confidence
        return f"A comprehensive and detailed response to {query} with proper structure and formatting."

    # Configure retry
    config = RetryConfig(
        max_retries=3,
        min_confidence=0.7,
        strategy=RetryStrategy.FIXED_DELAY,
        base_delay=0.5,
    )

    print("Starting agent with retry logic...")
    result, metrics, info = await handler.retry_with_validation(
        mock_agent_function,
        config,
        query="What is machine learning?",
        context={"query": "What is machine learning?"},
    )

    print(f"\n✅ Success after {info['attempts']} attempts")
    print(f"   Final Confidence: {metrics.overall_confidence:.2f}")
    print(f"   Total Duration: {info['total_duration']:.2f}s")
    print(f"   Result: {result[:50]}...\n")


# Example 3: Quality Tracking
def example_quality_tracking():
    """Demonstrate quality metrics tracking."""
    print("\n=== Example 3: Quality Tracking ===\n")

    tracker = QualityTracker()

    # Simulate several agent operations
    print("Simulating 10 agent operations...")
    for i in range(10):
        tracker.record_operation(
            agent_name="research_agent",
            confidence_score=0.7 + (i * 0.03),  # Improving trend
            retry_count=max(0, 2 - i // 3),  # Decreasing retries
            duration_seconds=2.0 + (i * 0.1),
            success=True,
        )

    # Get statistics
    stats = tracker.get_agent_stats("research_agent")
    print("\n📊 Agent Statistics:")
    print(f"   Total Operations: {stats['total_operations']}")
    print(f"   Success Rate: {stats['success_rate']:.2%}")
    print(f"   Avg Confidence: {stats['avg_confidence']:.2f}")
    print(f"   Avg Retries: {stats['avg_retries']:.2f}")
    print(f"   Avg Duration: {stats['avg_duration']:.2f}s")

    # Analyze trends
    trend = tracker.get_quality_trend("research_agent")
    print("\n📈 Quality Trends:")
    print(f"   Confidence Trend: {trend['confidence_trend']}")
    print(f"   Retry Trend: {trend['retry_trend']}")
    print(f"   Health Status: {trend['health_status']}")
    print(f"   Health Score: {trend['health_score']:.2f}\n")


# Example 4: Self-Correcting Mixin
class MyResearchAgent(SelfCorrectingMixin):
    """Example research agent with self-correction."""

    def __init__(self):
        super().__init__()
        self.research_depth = "standard"

    async def research_topic(self, topic: str, depth: str = "standard") -> str:
        """Research a topic with self-correction."""
        self.research_depth = depth

        return await self.with_self_correction(
            self._do_research,
            topic,
            min_confidence=0.75,
            max_retries=3,
            context={"query": f"Research {topic}", "depth": depth},
        )

    async def _do_research(self, topic: str, **kwargs) -> str:
        """Internal research logic."""
        await asyncio.sleep(0.1)  # Simulate work

        if self.research_depth == "basic":
            return f"{topic} is a topic in technology."

        if self.research_depth == "standard":
            return f"{topic} is an important concept in modern technology. It has various applications and implications."

        return (
            f"{topic} is a comprehensive field that encompasses multiple dimensions. "
            f"It has significant implications for modern technology and society. "
            f"Recent developments have shown promising applications in various domains."
        )


async def example_self_correcting_mixin():
    """Demonstrate self-correcting mixin usage."""
    print("\n=== Example 4: Self-Correcting Mixin ===\n")

    agent = MyResearchAgent()

    # Research with different depths
    print("🔍 Researching with basic depth...")
    result1 = await agent.research_topic("Artificial Intelligence", depth="basic")

    print(f"   Success: {result1['success']}")
    print(f"   Confidence: {result1['confidence']['overall_confidence']:.2f}")
    print(f"   Retries: {result1['retry_info']['attempts'] - 1}\n")

    print("🔍 Researching with deep depth...")
    result2 = await agent.research_topic("Machine Learning", depth="deep")

    print(f"   Success: {result2['success']}")
    print(f"   Confidence: {result2['confidence']['overall_confidence']:.2f}")
    print(f"   Retries: {result2['retry_info']['attempts'] - 1}\n")

    # Get agent quality stats
    stats = agent.get_quality_stats()
    print("📊 Agent Quality Stats:")
    print(f"   Total Operations: {stats.get('total_operations', 0)}")
    print(f"   Avg Confidence: {stats.get('avg_confidence', 0):.2f}\n")


# Example 5: Validate and Correct
async def example_validate_and_correct():
    """Demonstrate validation with correction."""
    print("\n=== Example 5: Validate and Correct ===\n")

    agent = MyResearchAgent()

    # Validate a short output
    print("Validating incomplete output...")
    result = await agent.validate_and_correct(
        output="AI is important",
        context={"query": "Explain artificial intelligence in detail"},
        max_corrections=2,
    )

    print(f"   Success: {result['success']}")
    print(f"   Corrections Applied: {result['corrections_applied']}")
    print(f"   Confidence: {result['confidence']['overall_confidence']:.2f}")

    if not result["success"] and "suggestions" in result:
        print("   Suggestions:")
        for suggestion in result["suggestions"]:
            print(f"      - {suggestion}\n")


# Example 6: Quality Anomaly Detection
def example_anomaly_detection():
    """Demonstrate anomaly detection."""
    print("\n=== Example 6: Anomaly Detection ===\n")

    tracker = QualityTracker()

    # Simulate normal operations
    print("Simulating normal operations...")
    for _ in range(20):
        tracker.record_operation(
            agent_name="writer_agent",
            confidence_score=0.8,
            retry_count=1,
            duration_seconds=2.0,
            success=True,
        )

    # Simulate anomalous operations
    print("Simulating anomalous operations...\n")
    tracker.record_operation(
        agent_name="writer_agent",
        confidence_score=0.2,  # Very low!
        retry_count=5,  # Too many!
        duration_seconds=15.0,  # Too slow!
        success=False,
    )

    # Detect anomalies
    anomalies = tracker.detect_anomalies("writer_agent")

    print(f"🚨 Detected {len(anomalies)} anomalies:")
    for anomaly in anomalies:
        print(f"   Operation: {anomaly['operation_id']}")
        print(f"   Confidence: {anomaly['confidence_score']:.2f}")
        print(f"   Duration: {anomaly['duration_seconds']:.2f}s")
        print(f"   Retries: {anomaly['retry_count']}")
        print(f"   Reasons: {', '.join(anomaly['reasons'])}\n")


# Example 7: Standalone Self-Correcting Agent
async def example_standalone_agent():
    """Demonstrate standalone self-correcting agent."""
    print("\n=== Example 7: Standalone Agent ===\n")

    agent = SelfCorrectingAgent()

    print("Processing query with standalone agent...")
    result = await agent.process_query(
        "What are the benefits of self-correcting agents?",
        min_confidence=0.6,
    )

    print("✅ Result:")
    print(f"   Success: {result['success']}")
    print(f"   Confidence: {result['confidence']['overall_confidence']:.2f}")
    print(f"   Duration: {result['duration_seconds']:.2f}s\n")


# Example 8: Custom Confidence Weights
def example_custom_confidence_weights():
    """Demonstrate custom confidence scoring weights."""
    print("\n=== Example 8: Custom Confidence Weights ===\n")

    # Default weights
    scorer1 = ConfidenceScorer()
    metrics1 = scorer1.score_output(
        "The answer is 42.",
        context={"query": "What is the answer?"},
    )

    print("Default Weights:")
    print(f"   Confidence: {metrics1.overall_confidence:.2f}\n")

    # Custom weights (prioritize relevance and factual accuracy)
    scorer2 = ConfidenceScorer(
        completeness_weight=0.1,
        relevance_weight=0.4,
        coherence_weight=0.1,
        factual_weight=0.35,
        format_weight=0.05,
    )
    metrics2 = scorer2.score_output(
        "The answer is 42.",
        context={"query": "What is the answer?"},
    )

    print("Custom Weights (prioritize relevance & factual):")
    print(f"   Confidence: {metrics2.overall_confidence:.2f}\n")


# Main execution
async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  Self-Correcting Agents - Examples")
    print("=" * 60)

    # Synchronous examples
    example_confidence_scoring()
    example_quality_tracking()
    example_anomaly_detection()
    example_custom_confidence_weights()

    # Asynchronous examples
    await example_retry_handler()
    await example_self_correcting_mixin()
    await example_validate_and_correct()
    await example_standalone_agent()

    print("\n" + "=" * 60)
    print("  All Examples Completed Successfully! ✅")
    print("=" * 60)
    print("\n💡 Key Takeaways:")
    print("   1. Confidence scoring helps identify output quality")
    print("   2. Retry logic automatically improves low-quality outputs")
    print("   3. Quality tracking provides insights into agent performance")
    print("   4. Self-correcting mixin is easy to integrate with any agent")
    print("   5. Anomaly detection helps identify performance issues")
    print()


if __name__ == "__main__":
    asyncio.run(main())
