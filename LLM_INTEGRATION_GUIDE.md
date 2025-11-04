# LLM Integration Guide - Complete Implementation (2025)

## Overview

This guide documents the complete LLM integration for the MegaAgent Pro system, featuring the latest models from all major providers as of 2025:

- **Anthropic Claude**: Sonnet 4.5, Opus 4.1, Haiku 3.5
- **OpenAI GPT**: GPT-5, GPT-5-mini, GPT-5-nano, o3-mini, o4-mini
- **Google Gemini**: Gemini 2.5 Pro, Flash, Flash-Lite

All three clients implement a unified `acomplete()` async interface for seamless integration.

---

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [API Keys Configuration](#api-keys-configuration)
3. [Anthropic Claude](#anthropic-claude)
4. [OpenAI GPT](#openai-gpt)
5. [Google Gemini](#google-gemini)
6. [EB-1A Document Generation](#eb-1a-document-generation)
7. [Usage Examples](#usage-examples)
8. [Model Selection Guide](#model-selection-guide)
9. [Pricing Comparison](#pricing-comparison)
10. [Troubleshooting](#troubleshooting)

---

## Installation & Setup

### 1. Install Required Packages

```bash
pip install -r requirements.txt
```

Key dependencies:
- `anthropic>=0.40.0` - Anthropic Claude API
- `openai>=1.58.0` - OpenAI GPT API
- `google-generativeai>=0.8.0` - Google Gemini API

### 2. Verify Installation

```python
# Test imports
from core.llm_interface.anthropic_client import AnthropicClient
from core.llm_interface.openai_client import OpenAIClient
from core.llm_interface.gemini_client import GeminiClient
```

---

## API Keys Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-api03-...

# OpenAI GPT
OPENAI_API_KEY=sk-proj-...

# Google Gemini (either variable works)
GEMINI_API_KEY=AIzaSy...
# OR
GOOGLE_API_KEY=AIzaSy...
```

### Get API Keys

- **Anthropic**: https://console.anthropic.com/
- **OpenAI**: https://platform.openai.com/api-keys
- **Google**: https://makersuite.google.com/app/apikey

---

## Anthropic Claude

### Supported Models (2025)

| Model ID | Name | Context | Max Output | Cost (Input/Output) | Best For |
|----------|------|---------|------------|---------------------|----------|
| `claude-sonnet-4-5-20250929` | Sonnet 4.5 | 200K (1M beta) | 64K tokens | $3/$15 per MTok | Highest intelligence, complex reasoning |
| `claude-opus-4-1-20250805` | Opus 4.1 | 200K | 32K tokens | $15/$75 per MTok | Specialized complex tasks |
| `claude-3-5-haiku-20241022` | Haiku 3.5 | 200K | 8K tokens | $0.80/$4 per MTok | Fast, cost-efficient |

### API Parameters

- **temperature** (0.0-1.0): Randomness. Use 0.0 for analytical tasks, 1.0 for creative.
- **max_tokens** (int): Maximum tokens to generate (required, up to 64K for Sonnet 4.5)
- **top_p** (0.0-1.0): Nucleus sampling (alternative to temperature)
- **top_k** (int): Top-K sampling
- **stop_sequences** (list[str]): Stop generation sequences

**Important**: Use either `temperature` OR `top_p`, not both (enforced by Sonnet 4.5).

### Usage Example

```python
from core.llm_interface.anthropic_client import AnthropicClient

# Initialize client
client = AnthropicClient(
    model=AnthropicClient.CLAUDE_SONNET_4_5,
    temperature=0.7,
    max_tokens=4096,
)

# Generate completion
result = await client.acomplete(
    prompt="Write a professional EB-1A visa overview.",
    temperature=0.5,  # Override default
    max_tokens=2048,
)

print(result['output'])
print(f"Tokens used: {result['usage']['input_tokens']} + {result['usage']['output_tokens']}")
```

### All Available Models

```python
# Highest intelligence - best for EB-1A legal documents
client_sonnet = AnthropicClient(model=AnthropicClient.CLAUDE_SONNET_4_5)

# Complex specialized tasks
client_opus = AnthropicClient(model=AnthropicClient.CLAUDE_OPUS_4_1)

# Fast and cost-efficient
client_haiku = AnthropicClient(model=AnthropicClient.CLAUDE_HAIKU_3_5)
```

---

## OpenAI GPT

### Supported Models (2025)

| Model ID | Name | Context | Parameters | Cost | Best For |
|----------|------|---------|------------|------|----------|
| `gpt-5` | GPT-5 | 400K tokens | Standard | See pricing | Coding, instruction, long context |
| `gpt-5-mini` | GPT-5 Mini | 400K tokens | Standard | See pricing | Balanced price/performance |
| `gpt-5-nano` | GPT-5 Nano | 400K tokens | Standard | See pricing | Low cost, high throughput |
| `o3-mini` | O3-Mini | - | Reasoning | TBD | STEM reasoning, math, coding |
| `o4-mini` | O4-Mini | - | Reasoning | TBD | Next-gen reasoning |


### API Parameters

**Standard Models (GPT-5 family):**
- **temperature** (0.0-2.0): Randomness
- **max_tokens** (int): Maximum tokens in completion
- **top_p** (0.0-1.0): Nucleus sampling
- **frequency_penalty** (-2.0 to 2.0): Reduce repetition
- **presence_penalty** (-2.0 to 2.0): Encourage topic diversity
- **stop** (str or list[str]): Stop sequences

**Reasoning Models (o3-mini, o4-mini):**
- **max_tokens**: Only supported token-control parameter
- **reasoning_effort**: "low", "medium", or "high"
- ❌ No temperature, top_p, or penalties

### Usage Example

```python
from core.llm_interface.openai_client import OpenAIClient

# Standard model
client_gpt = OpenAIClient(
    model=OpenAIClient.GPT_5,
    temperature=0.7,
    max_tokens=4096,
)

result = await client_gpt.acomplete(
    prompt="Generate an EB-1A recommendation letter opening.",
)

# Reasoning model (for complex legal analysis)
client_o3 = OpenAIClient(
    model=OpenAIClient.O3_MINI,
    reasoning_effort="high",
    max_tokens=2048,
)

result = await client_o3.acomplete(
    prompt="Analyze which EB-1A criteria this evidence satisfies: [...]",
)
```

### All Available Models

```python
# Latest GPT-5 with 400K context
client_gpt5 = OpenAIClient(model=OpenAIClient.GPT_5)

# Cost-efficient variant
client_gpt5_mini = OpenAIClient(model=OpenAIClient.GPT_5_MINI)

# Reasoning model (STEM focus)
client_o3 = OpenAIClient(
    model=OpenAIClient.O3_MINI,
    reasoning_effort="high"
)

# Next-gen reasoning
client_o4 = OpenAIClient(model=OpenAIClient.O4_MINI)

# (Multimodal examples removed; use Gemini section for vision/audio)
```

---

## Google Gemini

### Supported Models (2025)

| Model ID | Name | Context | Max Output | Best For |
|----------|------|---------|------------|----------|
| `gemini-2.5-pro` | Gemini 2.5 Pro | 1M tokens | 65,536 | Complex reasoning, long context |
| `gemini-2.5-flash` | Gemini 2.5 Flash | 1M tokens | 65,536 | Best price-performance |
| `gemini-2.5-flash-lite` | Gemini 2.5 Flash-Lite | 1M tokens | 65,536 | Cost efficiency, high throughput |
| `gemini-2.0-flash` | Gemini 2.0 Flash | 1M tokens | - | Next-gen features, tool use |

### API Parameters

- **temperature** (0.0-2.0): Randomness (default 1.0)
- **max_output_tokens** (int): Maximum tokens to generate
- **top_p** (0.0-1.0): Nucleus sampling (default 0.95)
- **top_k** (int): Top-K sampling (default 40)
- **stop_sequences** (list[str]): Stop generation sequences

### Multimodal Support

Gemini models support:
- ✅ Text inputs
- ✅ Image inputs (PNG, JPEG, WEBP)
- ✅ Video inputs (MP4, MOV, AVI)
- ✅ Audio inputs (MP3, WAV)
- ✅ PDF inputs

### Usage Example

```python
from core.llm_interface.gemini_client import GeminiClient

# Most powerful model
client = GeminiClient(
    model=GeminiClient.GEMINI_2_5_PRO,
    temperature=0.8,
    max_output_tokens=8192,
    top_p=0.95,
    top_k=40,
)

result = await client.acomplete(
    prompt="Explain the 'Original Contribution' criterion for EB-1A.",
)

print(result['output'])
print(f"Tokens: {result['usage']['total_tokens']}")
```

### All Available Models

```python
# Most powerful, complex reasoning
client_pro = GeminiClient(model=GeminiClient.GEMINI_2_5_PRO)

# Best price-performance
client_flash = GeminiClient(model=GeminiClient.GEMINI_2_5_FLASH)

# Ultra cost-efficient
client_lite = GeminiClient(model=GeminiClient.GEMINI_2_5_FLASH_LITE)

# Next-gen features
client_2_0 = GeminiClient(model=GeminiClient.GEMINI_2_0_FLASH)
```

---

## EB-1A Document Generation

### Complete Integration

The `EB1DocumentProcessor` now supports all three LLM providers through a unified interface.

```python
from core.groupagents.eb1_document_processor import EB1DocumentProcessor
from core.llm_interface.anthropic_client import AnthropicClient

# Initialize LLM client
llm_client = AnthropicClient(
    model=AnthropicClient.CLAUDE_SONNET_4_5,
    temperature=0.3,  # Low temperature for precise legal documents
    max_tokens=8192,   # Long documents (2-3 pages)
)

# Initialize document processor
processor = EB1DocumentProcessor(llm_client=llm_client)

# Generate recommendation letter
generated_doc = await processor.generate_recommendation_letter(
    letter_data=recommendation_data,
    petition=petition_data,
)

print(generated_doc.content)  # Full letter with USCIS keywords
```

### How It Works

1. **Prompt Building**: `_build_recommendation_letter_prompt()` creates comprehensive prompt with:
   - Beneficiary information
   - Recommender credentials
   - Supporting EB-1A criteria
   - Required USCIS keywords
   - Specific achievements and impact statements

2. **LLM Generation**: `_generate_with_llm()` calls the LLM client with:
   - Temperature: 0.3 (precise, consistent legal text)
   - Max tokens: 8192 (2-3 page letters)
   - Unified error handling

3. **Fallback**: If LLM fails or is not configured, falls back to template-based generation

### Switching Providers

```python
# Option 1: Anthropic Claude (best for legal documents)
llm_client = AnthropicClient(
    model=AnthropicClient.CLAUDE_SONNET_4_5,
    temperature=0.3,
    max_tokens=8192,
)

# Option 2: OpenAI GPT-5 (strong at instruction following)
llm_client = OpenAIClient(
    model=OpenAIClient.GPT_5,
    temperature=0.3,
    max_tokens=8192,
)

# Option 3: Google Gemini (good price-performance)
llm_client = GeminiClient(
    model=GeminiClient.GEMINI_2_5_PRO,
    temperature=0.3,
    max_output_tokens=8192,
)

# Use any client with same interface
processor = EB1DocumentProcessor(llm_client=llm_client)
```

---

## Usage Examples

### Complete Demo Script

Run the comprehensive demo:

```bash
# Set API keys first
export ANTHROPIC_API_KEY=your_key
export OPENAI_API_KEY=your_key
export GEMINI_API_KEY=your_key

# Run demo
python llm_demo.py
```

The demo includes:
1. ✅ All Anthropic Claude models (Sonnet 4.5, Opus 4.1, Haiku 3.5)
2. ✅ All OpenAI GPT models (GPT-5 family, o3-mini, o4-mini)
3. ✅ All Google Gemini models (2.5 Pro, Flash, Flash-Lite)
4. ✅ Complete EB-1A document generation workflow

### Quick Start: Generate EB-1A Letter

```python
import asyncio
from core.llm_interface.anthropic_client import AnthropicClient
from core.groupagents.eb1_document_processor import EB1DocumentProcessor

async def generate_eb1a_letter():
    # Initialize LLM
    llm = AnthropicClient(
        model=AnthropicClient.CLAUDE_SONNET_4_5,
        temperature=0.3,
        max_tokens=8192,
    )

    # Initialize processor
    processor = EB1DocumentProcessor(llm_client=llm)

    # Create letter data (see eb1_documents.py for full structure)
    letter_data = RecommendationLetterData(
        candidate_name="Dr. Jane Smith",
        candidate_field="AI Research",
        recommender_name="Prof. John Doe",
        recommender_title="Department Chair",
        recommender_organization="MIT",
        recommender_credentials="PhD, Fellow of ACM",
        recommender_relationship="PhD advisor",
        years_known=10,
        supporting_criteria=[EB1Criterion.CONTRIBUTION, EB1Criterion.SCHOLARLY],
        specific_achievements=[
            "Developed groundbreaking ML algorithm",
            "Published 30+ papers in top venues",
            "Algorithm adopted by 20+ hospitals"
        ],
        impact_statements=[
            "Her work revolutionized medical AI",
            "Globally recognized expert"
        ],
        keywords_for_criteria={
            "contribution": ["original contribution", "major significance"],
            "scholarly": ["scholarly articles", "peer-reviewed"]
        }
    )

    # Generate letter
    doc = await processor.generate_recommendation_letter(letter_data, petition)

    print(doc.content)

asyncio.run(generate_eb1a_letter())
```

---

## Model Selection Guide

### By Use Case

| Use Case | Recommended Model | Reason |
|----------|------------------|---------|
| **EB-1A Legal Documents** | Claude Sonnet 4.5 | Highest intelligence, best at following complex instructions |
| **Complex Legal Analysis** | GPT-5 or o3-mini | Strong reasoning, long context |
| **High Volume Processing** | Gemini 2.5 Flash | Best price-performance, fast |
| **Cost Optimization** | Claude Haiku 3.5 or Gemini Flash-Lite | Lowest cost per token |
| **Multimodal (images/video)** | Gemini 2.5 Pro | Native multimodal support |
| **Mathematical/STEM Analysis** | o3-mini (high reasoning) | Specialized reasoning model |

### By Budget

**Premium** (highest quality):
- Claude Opus 4.1: $15/$75 per MTok
- Claude Sonnet 4.5: $3/$15 per MTok

**Balanced** (quality + cost):
- GPT-5: Competitive pricing, 400K context
- Gemini 2.5 Pro: Good balance

**Budget** (cost-optimized):
- Claude Haiku 3.5: $0.80/$4 per MTok
- Gemini 2.5 Flash-Lite: Ultra low cost

---

## Pricing Comparison

### Anthropic Claude (2025)

| Model | Input (per MTok) | Output (per MTok) |
|-------|------------------|-------------------|
| Sonnet 4.5 | $3 | $15 |
| Opus 4.1 | $15 | $75 |
| Haiku 3.5 | $0.80 | $4 |

### OpenAI GPT (2025)

Pricing varies by model. Check: https://openai.com/api/pricing/

### Google Gemini (2025)

Check latest pricing: https://ai.google.dev/pricing

### Cost Example: EB-1A Recommendation Letter

Typical letter: ~1,500 input tokens + ~3,000 output tokens

| Provider | Model | Estimated Cost |
|----------|-------|----------------|
| Anthropic | Sonnet 4.5 | $0.0045 + $0.045 = **$0.0495** |
| Anthropic | Opus 4.1 | $0.0225 + $0.225 = **$0.2475** |
| Anthropic | Haiku 3.5 | $0.0012 + $0.012 = **$0.0132** |

---

## Troubleshooting

### Common Issues

#### 1. Import Error

```
ImportError: anthropic package not installed
```

**Solution**:
```bash
pip install anthropic>=0.40.0
```

#### 2. API Key Not Found

```
ValueError: Anthropic API key required
```

**Solution**: Set environment variable or pass to constructor:
```python
client = AnthropicClient(api_key="sk-ant-...")
```

#### 3. Temperature and top_p Conflict (Claude)

```
Error: Cannot specify both temperature and top_p for Sonnet 4.5
```

**Solution**: Use one or the other:
```python
# Option 1: Use temperature only
client.acomplete(prompt, temperature=0.7)

# Option 2: Use top_p only
client.acomplete(prompt, top_p=0.9, temperature=None)
```

#### 4. Reasoning Model Parameter Error (OpenAI)

```
Error: o3-mini does not support temperature parameter
```

**Solution**: Use `max_tokens` and `reasoning_effort` only:
```python
client = OpenAIClient(model=OpenAIClient.O3_MINI)
result = await client.acomplete(
    prompt,
    max_tokens=2048,
    reasoning_effort="high"
)
```

#### 5. Gemini Synchronous Call Warning

```
Note: google-generativeai doesn't have async methods by default
```

**Solution**: Current implementation uses synchronous calls. For true async, wrap with `asyncio.to_thread()`:

```python
import asyncio

async def acomplete(self, prompt: str, **params):
    response = await asyncio.to_thread(
        self.client.generate_content,
        prompt,
        generation_config=config
    )
    return response
```

---

## Testing

### Unit Tests

Test each client individually:

```python
import pytest
from core.llm_interface.anthropic_client import AnthropicClient

@pytest.mark.asyncio
async def test_anthropic_sonnet():
    client = AnthropicClient(
        model=AnthropicClient.CLAUDE_SONNET_4_5,
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    result = await client.acomplete("Hello, how are you?")

    assert result['provider'] == 'anthropic'
    assert result['model'] == 'claude-sonnet-4-5-20250929'
    assert len(result['output']) > 0
```

### Integration Tests

Test EB-1A document generation:

```python
@pytest.mark.asyncio
async def test_eb1_document_generation():
    llm = AnthropicClient(model=AnthropicClient.CLAUDE_SONNET_4_5)
    processor = EB1DocumentProcessor(llm_client=llm)

    doc = await processor.generate_recommendation_letter(
        letter_data,
        petition
    )

    assert doc.document_type == EB1DocumentType.RECOMMENDATION_LETTER
    assert len(doc.content) > 1000  # 2-3 pages
    assert "sustained national acclaim" in doc.content.lower()
```

---

## API Reference

### Unified Interface

All three clients implement the same async interface:

```python
async def acomplete(
    self,
    prompt: str,
    **params: Any
) -> dict[str, Any]:
    """
    Returns:
        dict with keys:
        - model: str (model identifier)
        - prompt: str (original prompt)
        - output: str (generated text)
        - provider: str (anthropic/openai/gemini)
        - usage: dict (token counts)
        - finish_reason: str (completion reason)
    """
```

### Return Format

```python
{
    "model": "claude-sonnet-4-5-20250929",
    "prompt": "Write an EB-1A overview",
    "output": "The EB-1A visa is...",
    "provider": "anthropic",
    "usage": {
        "input_tokens": 150,
        "output_tokens": 450
    },
    "finish_reason": "end_turn"
}
```

---

## Changelog

### 2025-10-12

- ✅ Implemented Anthropic Claude client (Sonnet 4.5, Opus 4.1, Haiku 3.5)
- ✅ Implemented OpenAI GPT client (GPT-5 family, o3-mini, o4-mini)
- ✅ Implemented Google Gemini client (Gemini 2.5 Pro, Flash, Flash-Lite)
- ✅ Integrated LLM generation into EB1DocumentProcessor
- ✅ Created comprehensive demo script (llm_demo.py)
- ✅ Added unified error handling and fallback logic
- ✅ Updated requirements.txt with latest SDK versions

---

## Additional Resources

### Documentation Links

- **Anthropic Claude**: https://docs.claude.com/en/docs/about-claude/models
- **OpenAI GPT**: https://platform.openai.com/docs/models/
- **Google Gemini**: https://ai.google.dev/gemini-api/docs/models

### Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [llm_demo.py](llm_demo.py) examples
3. Consult official provider documentation

---

**Last Updated**: 2025-10-12
**Version**: 1.0.0
**Status**: Production-Ready ✅
