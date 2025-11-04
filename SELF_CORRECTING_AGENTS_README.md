## Self-Correcting Agents

Comprehensive self-correction system with confidence scoring, automatic retry logic, and quality metrics tracking for intelligent agent systems.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Quick Start](#quick-start)
4. [Architecture](#architecture)
5. [Confidence Scoring](#confidence-scoring)
6. [Retry Handler](#retry-handler)
7. [Quality Metrics](#quality-metrics)
8. [Self-Correcting Mixin](#self-correcting-mixin)
9. [Integration Guide](#integration-guide)
10. [Configuration](#configuration)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The Self-Correcting Agents system provides automatic quality validation and improvement capabilities for AI agents through:

- **Confidence Scoring**: Multi-dimensional quality evaluation (0-1 score)
- **Automatic Retry**: Retry logic with multiple strategies
- **Quality Tracking**: Real-time metrics and trend analysis
- **Self-Correction**: Automatic output improvement

**Status**: ✅ Complete (Phase 3)

---

## Features

### ✅ Confidence Scoring System
- **5 Scoring Dimensions**: Completeness, Relevance, Coherence, Factual, Format
- **Configurable Weights**: Custom weights for each dimension
- **Threshold Levels**: Very Low < Low < Medium < High < Very High
- **Actionable Suggestions**: Specific recommendations for improvement
- **Format Detection**: JSON, Markdown, List format validation

### ✅ Retry Handler
- **4 Retry Strategies**: Exponential Backoff, Fixed Delay, Immediate, No Retry
- **Validation Loops**: Automatic retry until quality threshold met
- **Timeout Management**: Global timeout with per-attempt tracking
- **Parameter Adjustment**: Dynamic parameter tuning on retry
- **Detailed Metrics**: Track attempts, duration, confidence per retry

### ✅ Quality Metrics Tracking
- **Real-time Monitoring**: Track every agent operation
- **Per-agent Statistics**: Individual agent performance metrics
- **Trend Analysis**: Detect improving/declining quality trends
- **Anomaly Detection**: Identify unusual operations
- **Historical Analytics**: Store up to 1000 recent operations

### ✅ Self-Correcting Mixin
- **Easy Integration**: Single mixin class for any agent
- **Automatic Scoring**: Built-in confidence evaluation
- **Retry Logic**: Integrated retry with validation
- **Quality Tracking**: Automatic metrics collection
- **Performance Monitoring**: Real-time health checks

---

## Quick Start

### 1. Install (Already included in requirements)

```bash
# All dependencies are already installed
```

### 2. Basic Usage

```python
from core.validation import ConfidenceScorer

# Score an output
scorer = ConfidenceScorer()
metrics = scorer.score_output(
    output="The capital of France is Paris.",
    context={"query": "What is the capital of France?"}
)

print(f"Confidence: {metrics.overall_confidence:.2f}")
print(f"Needs Review: {metrics.needs_review}")
```

### 3. Add Self-Correction to Your Agent

```python
from core.groupagents.self_correcting_mixin import SelfCorrectingMixin

class MyAgent(SelfCorrectingMixin):
    async def process(self, query: str):
        return await self.with_self_correction(
            self._internal_process,
            query,
            min_confidence=0.8,
            max_retries=3
        )

    async def _internal_process(self, query: str, **kwargs):
        # Your agent logic here
        return f"Processed: {query}"
```

### 4. Run the Example

```bash
python examples/self_correcting_agents_example.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Implementation                      │
│              (Research, Writer, Validator, etc.)             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
         ┌──────────────────────────────────────┐
         │   SelfCorrectingMixin                │
         │   - with_self_correction()           │
         │   - score_output()                   │
         │   - get_quality_stats()              │
         └──────┬──────────┬──────────┬─────────┘
                │          │          │
        ┌───────▼──┐  ┌────▼────┐  ┌─▼────────┐
        │Confidence│  │ Retry   │  │ Quality  │
        │ Scorer   │  │ Handler │  │ Tracker  │
        └──────────┘  └─────────┘  └──────────┘
             │             │             │
             ▼             ▼             ▼
        ┌──────────────────────────────────┐
        │      Metrics & Analytics          │
        │  - Real-time monitoring           │
        │  - Trend analysis                 │
        │  - Anomaly detection              │
        └───────────────────────────────────┘
```

---

## Confidence Scoring

### Scoring Dimensions

#### 1. **Completeness** (Weight: 0.25)
- Checks if output addresses the query
- Evaluates output length vs expected
- Looks for completion indicators

#### 2. **Relevance** (Weight: 0.25)
- Keyword overlap with query
- Direct answer indicators
- Topic alignment

#### 3. **Coherence** (Weight: 0.20)
- Logical flow and structure
- Transition words usage
- Proper sentence structure

#### 4. **Factual** (Weight: 0.20)
- Confidence markers detection
- Uncertainty markers detection
- Citation presence

#### 5. **Format** (Weight: 0.10)
- JSON structure validation
- Markdown elements detection
- List format checking

### Usage Example

```python
from core.validation import ConfidenceScorer, get_confidence_scorer

# Get global instance
scorer = get_confidence_scorer()

# Score an output
metrics = scorer.score_output(
    output="The capital of France is Paris. It is located in the "
           "north-central part of the country.",
    context={
        "query": "What is the capital of France?",
        "sources": ["wikipedia"]
    },
    expected_length=100,
    expected_format="markdown"
)

# Check results
print(f"Overall Confidence: {metrics.overall_confidence:.2f}")
print(f"Threshold: {metrics.threshold.value}")
print(f"Breakdown:")
print(f"  - Completeness: {metrics.completeness_score:.2f}")
print(f"  - Relevance: {metrics.relevance_score:.2f}")
print(f"  - Coherence: {metrics.coherence_score:.2f}")
print(f"  - Factual: {metrics.factual_score:.2f}")
print(f"  - Format: {metrics.format_score:.2f}")

if metrics.needs_correction:
    print("\nSuggestions:")
    for suggestion in metrics.suggestions:
        print(f"  - {suggestion}")
```

### Confidence Thresholds

| Threshold | Range | Action |
|-----------|-------|--------|
| **VERY_LOW** | < 0.3 | Requires regeneration |
| **LOW** | 0.3-0.5 | Requires review |
| **MEDIUM** | 0.5-0.7 | Acceptable with warning |
| **HIGH** | 0.7-0.9 | Good quality |
| **VERY_HIGH** | > 0.9 | Excellent quality |

### Custom Weights

```python
# Create scorer with custom weights
scorer = ConfidenceScorer(
    completeness_weight=0.3,  # Higher importance
    relevance_weight=0.3,     # Higher importance
    coherence_weight=0.2,
    factual_weight=0.15,
    format_weight=0.05        # Lower importance
)
```

---

## Retry Handler

### Retry Strategies

#### 1. **Exponential Backoff** (Recommended)
```python
config = RetryConfig(
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,      # Start with 1 second
    max_delay=30.0       # Cap at 30 seconds
)
# Delays: 1s, 2s, 4s, 8s, 16s, 30s, 30s...
```

#### 2. **Fixed Delay**
```python
config = RetryConfig(
    strategy=RetryStrategy.FIXED_DELAY,
    base_delay=2.0       # Always wait 2 seconds
)
```

#### 3. **Immediate**
```python
config = RetryConfig(
    strategy=RetryStrategy.IMMEDIATE
)
# No delay between retries
```

#### 4. **No Retry**
```python
config = RetryConfig(
    strategy=RetryStrategy.NO_RETRY
)
# Fail immediately if confidence low
```

### Usage Example

```python
from core.validation import RetryHandler, RetryConfig, RetryStrategy

handler = RetryHandler()

async def my_agent_function(query: str) -> str:
    # Your agent logic
    return "response"

# Configure retry
config = RetryConfig(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    min_confidence=0.75,
    timeout=60.0,  # 60 second total timeout
    add_context_on_retry=True
)

# Execute with retry
result, metrics, info = await handler.retry_with_validation(
    my_agent_function,
    config,
    query="What is AI?",
    context={"query": "What is AI?"}
)

print(f"Attempts: {info['attempts']}")
print(f"Duration: {info['total_duration']:.2f}s")
print(f"Final Confidence: {metrics.overall_confidence:.2f}")
```

### Parameter Adjustment on Retry

The retry handler can automatically adjust parameters:

```python
config = RetryConfig(
    add_context_on_retry=True,    # Add retry context
    increase_temperature=True,     # Increase LLM temperature
    use_different_model=False      # Switch models (TODO)
)
```

On each retry:
- Adds `retry_attempt` and `retry_reason` to context
- Increases temperature by 0.1 (if enabled)
- Can switch to fallback model (if configured)

---

## Quality Metrics

### Tracking Operations

```python
from core.validation import QualityTracker, get_quality_tracker

tracker = get_quality_tracker()

# Record an operation
tracker.record_operation(
    agent_name="research_agent",
    confidence_score=0.85,
    retry_count=1,
    duration_seconds=2.5,
    success=True,
    operation_id="op_12345",  # Optional
    user_id="user_123",       # Custom metadata
    query="What is AI?"
)
```

### Agent Statistics

```python
# Get stats for specific agent
stats = tracker.get_agent_stats("research_agent")

print(f"Total Operations: {stats['total_operations']}")
print(f"Success Rate: {stats['success_rate']:.2%}")
print(f"Avg Confidence: {stats['avg_confidence']:.2f}")
print(f"Avg Retries: {stats['avg_retries']:.2f}")
print(f"Avg Duration: {stats['avg_duration']:.2f}s")
```

### Trend Analysis

```python
# Analyze quality trends
trend = tracker.get_quality_trend("research_agent", window_size=100)

print(f"Status: {trend['status']}")
print(f"Operations Analyzed: {trend['operations_count']}")
print(f"Confidence Trend: {trend['confidence_trend']}")  # improving/declining
print(f"Retry Trend: {trend['retry_trend']}")
print(f"Health Status: {trend['health_status']}")        # good/attention_needed
print(f"Health Score: {trend['health_score']:.2f}")      # 0-1
```

### Anomaly Detection

```python
# Detect anomalous operations
anomalies = tracker.detect_anomalies("research_agent", threshold=2.0)

for anomaly in anomalies:
    print(f"Operation: {anomaly['operation_id']}")
    print(f"Reasons: {', '.join(anomaly['reasons'])}")
    # Reasons: unusual_confidence, unusual_duration, excessive_retries
```

### Overall Summary

```python
# Get summary across all agents
summary = tracker.get_summary()

print(f"Total Operations: {summary['total_operations']}")
print(f"Overall Success Rate: {summary['overall_success_rate']:.2%}")
print(f"Avg Confidence: {summary['avg_confidence']:.2f}")
print(f"Active Agents: {len(summary['agents'])}")
```

---

## Self-Correcting Mixin

### Basic Integration

```python
from core.groupagents.self_correcting_mixin import SelfCorrectingMixin

class MyAgent(SelfCorrectingMixin):
    """Your agent with self-correction."""

    async def process_query(self, query: str):
        """Public method with self-correction."""
        return await self.with_self_correction(
            self._internal_process,
            query,
            min_confidence=0.75,
            max_retries=3,
            context={"query": query}
        )

    async def _internal_process(self, query: str, **kwargs):
        """Internal logic (your implementation)."""
        # Your agent processing logic
        result = await self.llm.generate(query)
        return result
```

### Configuration

```python
# Set agent-specific thresholds
agent.set_quality_thresholds(
    min_confidence=0.85,  # Higher quality requirement
    max_retries=5         # More retry attempts
)
```

### Monitoring

```python
# Get agent quality stats
stats = agent.get_quality_stats()
print(f"Avg Confidence: {stats['avg_confidence']:.2f}")

# Get quality trend
trend = agent.get_quality_trend()
print(f"Trend: {trend['confidence_trend']}")

# Detect issues
issues = agent.detect_performance_issues()
if issues:
    print(f"⚠️ Found {len(issues)} performance issues")
```

### Manual Scoring

```python
# Score output without retry
metrics = agent.score_output(
    output="The answer is 42",
    context={"query": "What is the answer?"},
    expected_format="markdown"
)
```

### Validate and Correct

```python
# Validate with optional correction
result = await agent.validate_and_correct(
    output="Short incomplete answer",
    context={"query": "Explain AI in detail"},
    max_corrections=2
)

print(f"Success: {result['success']}")
print(f"Corrections Applied: {result['corrections_applied']}")
```

---

## Integration Guide

### Integrating with Existing Agents

#### Step 1: Add Mixin to Agent Class

```python
# Before
class ResearchAgent:
    async def research(self, topic: str):
        return await self._do_research(topic)

# After
from core.groupagents.self_correcting_mixin import SelfCorrectingMixin

class ResearchAgent(SelfCorrectingMixin):
    async def research(self, topic: str):
        return await self.with_self_correction(
            self._do_research,
            topic,
            min_confidence=0.8
        )
```

#### Step 2: Handle Result Format

```python
result = await agent.research("AI")

if result["success"]:
    # Access the actual result
    data = result["result"]

    # Access confidence metrics
    confidence = result["confidence"]["overall_confidence"]

    # Access retry info
    attempts = result["retry_info"]["attempts"]
else:
    # Handle error
    error = result["error"]
    error_type = result["error_type"]
```

#### Step 3: Monitor Quality

```python
# Periodic quality checks
stats = agent.get_quality_stats()
if stats["avg_confidence"] < 0.7:
    print("⚠️ Agent quality declining")

# Trend analysis
trend = agent.get_quality_trend()
if trend["confidence_trend"] == "declining":
    print("⚠️ Quality trend declining")
```

### Integrating with LangGraph Workflows

```python
from langgraph.graph import StateGraph

class WorkflowState(TypedDict):
    query: str
    result: dict
    confidence: float

def create_workflow_with_self_correction():
    graph = StateGraph(WorkflowState)

    agent = ResearchAgent()  # With SelfCorrectingMixin

    async def research_node(state: WorkflowState):
        result = await agent.research(state["query"])

        return {
            "result": result["result"],
            "confidence": result["confidence"]["overall_confidence"]
        }

    graph.add_node("research", research_node)
    # ... rest of workflow
```

---

## Configuration

### Environment Variables

```bash
# Confidence scoring
CONFIDENCE_MIN_THRESHOLD=0.7
CONFIDENCE_COMPLETENESS_WEIGHT=0.25
CONFIDENCE_RELEVANCE_WEIGHT=0.25

# Retry configuration
RETRY_MAX_ATTEMPTS=3
RETRY_STRATEGY=exponential_backoff
RETRY_BASE_DELAY=1.0
RETRY_MAX_DELAY=30.0

# Quality tracking
QUALITY_HISTORY_SIZE=1000
QUALITY_ANOMALY_THRESHOLD=2.0
```

### Programmatic Configuration

```python
from core.validation import ConfidenceScorer, RetryConfig, QualityTracker

# Custom confidence scorer
scorer = ConfidenceScorer(
    completeness_weight=0.3,
    relevance_weight=0.3,
    coherence_weight=0.2,
    factual_weight=0.15,
    format_weight=0.05
)

# Custom retry config
retry_config = RetryConfig(
    max_retries=5,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=2.0,
    max_delay=60.0,
    min_confidence=0.85,
    timeout=120.0
)

# Custom quality tracker
tracker = QualityTracker(history_size=5000)
```

---

## Best Practices

### 1. Confidence Thresholds

- ✅ **Use 0.7+ for production** - Good balance of quality and retry attempts
- ✅ **Use 0.85+ for critical tasks** - High quality requirement
- ✅ **Use 0.5-0.6 for exploratory** - More permissive
- ❌ **Don't use < 0.5** - Too permissive, low quality

### 2. Retry Strategy

- ✅ **Exponential Backoff for LLM calls** - Handles rate limits well
- ✅ **Immediate for fast operations** - Minimize overhead
- ✅ **Fixed Delay for external APIs** - Predictable timing
- ❌ **Don't use No Retry in production** - Misses improvement opportunities

### 3. Timeout Management

- ✅ **Set reasonable timeouts** - Prevent indefinite hangs
- ✅ **Total timeout < user patience** - Better UX
- ✅ **Per-attempt timeout optional** - Depend on use case
- ❌ **Don't set timeout too short** - Premature failures

### 4. Quality Tracking

- ✅ **Monitor trends regularly** - Catch degradation early
- ✅ **Set up alerts for anomalies** - Proactive issue detection
- ✅ **Review stats weekly** - Identify improvement opportunities
- ❌ **Don't ignore declining trends** - Quality will deteriorate

### 5. Parameter Adjustment

- ✅ **Increase temperature on retry** - More diverse outputs
- ✅ **Add retry context** - Help model improve
- ✅ **Switch models if available** - Fallback options
- ❌ **Don't adjust too aggressively** - May not converge

---

## Troubleshooting

### Low Confidence Scores

**Problem**: Outputs consistently receive low confidence scores

**Solutions**:
1. Check if weights are appropriate for your use case
2. Review output format - ensure it matches expectations
3. Add more context to queries
4. Increase model temperature for more complete outputs
5. Check if expected_length is reasonable

### Too Many Retries

**Problem**: Operations require many retries before success

**Solutions**:
1. Lower min_confidence threshold temporarily
2. Increase base model quality (better model)
3. Improve prompts for better first-try quality
4. Add more context to initial query
5. Check if retry strategy is appropriate

### Timeout Errors

**Problem**: Operations timeout before completion

**Solutions**:
1. Increase timeout value
2. Reduce max_retries
3. Use faster retry strategy (immediate vs exponential)
4. Optimize agent logic for speed
5. Consider async execution

### Quality Degradation

**Problem**: Quality metrics show declining trend

**Solutions**:
1. Review recent changes to agent logic
2. Check if model is experiencing issues
3. Verify context quality hasn't degraded
4. Increase confidence threshold temporarily
5. Review anomalies for patterns

### High Error Rate

**Problem**: Many operations fail despite retries

**Solutions**:
1. Check error_type in quality metrics
2. Review agent logs for exceptions
3. Verify external dependencies (LLM API, etc.)
4. Increase max_retries for specific operations
5. Add custom validation function

---

## Performance Considerations

### Overhead Analysis

| Component | Overhead | Impact |
|-----------|----------|--------|
| Confidence Scoring | ~1-5ms | Negligible |
| Quality Tracking | <1ms | Negligible |
| Single Retry | +100-500ms | Low |
| 3 Retries | +300-1500ms | Medium |

### Optimization Tips

1. **Use appropriate min_confidence** - Higher = more retries
2. **Limit max_retries to 3-5** - Balance quality vs speed
3. **Use immediate retry for fast operations** - Minimize delay
4. **Batch quality tracking writes** - Reduce DB load
5. **Set reasonable timeouts** - Prevent resource waste

---

## API Reference

### ConfidenceScorer

```python
scorer = ConfidenceScorer(
    completeness_weight=0.25,
    relevance_weight=0.25,
    coherence_weight=0.2,
    factual_weight=0.2,
    format_weight=0.1
)

metrics = scorer.score_output(
    output: str,
    context: dict | None = None,
    expected_length: int | None = None,
    expected_format: str | None = None
) -> ConfidenceMetrics
```

### RetryHandler

```python
handler = RetryHandler(confidence_scorer=None)

result, metrics, info = await handler.retry_with_validation(
    func: Callable,
    config: RetryConfig,
    validation_func: Callable | None = None,
    *args,
    **kwargs
) -> tuple[Any, ConfidenceMetrics, dict]
```

### QualityTracker

```python
tracker = QualityTracker(history_size=1000)

tracker.record_operation(
    agent_name: str,
    confidence_score: float,
    retry_count: int,
    duration_seconds: float,
    success: bool,
    operation_id: str | None = None,
    error_type: str | None = None,
    **metadata
)

stats = tracker.get_agent_stats(agent_name: str) -> dict
trend = tracker.get_quality_trend(agent_name: str | None, window_size: int = 100) -> dict
anomalies = tracker.detect_anomalies(agent_name: str | None, threshold: float = 2.0) -> list
```

### SelfCorrectingMixin

```python
class MyAgent(SelfCorrectingMixin):
    async def with_self_correction(
        func: Callable,
        *args,
        min_confidence: float | None = None,
        max_retries: int | None = None,
        retry_strategy: str = "exponential_backoff",
        timeout: float | None = None,
        context: dict | None = None,
        **kwargs
    ) -> dict

    def score_output(output: str, context: dict | None, expected_format: str | None) -> dict
    def get_quality_stats() -> dict
    def get_quality_trend(window_size: int = 100) -> dict
    def detect_performance_issues() -> list
    async def validate_and_correct(...) -> dict
    def set_quality_thresholds(min_confidence: float, max_retries: int)
```

---

## Next Steps

1. ✅ Review examples: `python examples/self_correcting_agents_example.py`
2. ✅ Integrate mixin into your agents
3. ✅ Set up quality monitoring dashboard
4. ✅ Configure confidence thresholds for your use case
5. ✅ Monitor trends and adjust parameters

---

**Status**: ✅ Phase 3 Complete
**Coverage**: Confidence Scoring ✅ | Retry Logic ✅ | Quality Tracking ✅ | Self-Correction ✅
