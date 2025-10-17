# WriterAgent - LLM Integration Guide

## Руководство по интеграции LLM для генерации юридических секций

Текущая реализация [WriterAgent](core/groupagents/writer_agent.py) использует симуляцию для демонстрации few-shot learning. Это руководство описывает, как интегрировать реальные LLM API для продакшн-генерации контента.

---

## 📋 Содержание

1. [Overview](#1-overview)
2. [OpenAI GPT-4 Integration](#2-openai-gpt-4-integration)
3. [Anthropic Claude Integration](#3-anthropic-claude-integration)
4. [Prompt Engineering Best Practices](#4-prompt-engineering-best-practices)
5. [Quality Assurance & Validation](#5-quality-assurance--validation)
6. [Cost Optimization](#6-cost-optimization)
7. [Testing](#7-testing)

---

## 1. Overview

### Текущая архитектура

```python
# core/groupagents/writer_agent.py (строки 1373-1849)

class WriterAgent:
    async def agenerate_legal_section(
        self,
        section_type: str,
        client_data: Dict[str, Any],
        examples: List[str] = None,
        use_patterns: bool = True,
        user_id: str = "system"
    ) -> GeneratedSection:
        """
        Генерация секции с few-shot learning.

        Current Flow:
        1. Get few-shot examples from library
        2. Get structural patterns
        3. Build context (examples + patterns + client data)
        4. Build generation prompt
        5. **SIMULATE LLM generation** ← Заменить здесь
        6. Calculate confidence score
        7. Generate suggestions
        8. Return GeneratedSection
        """
```

### Что нужно заменить

**Метод для замены:** `_simulate_llm_generation()` (строка ~1750)

**Текущая реализация (симуляция):**
```python
def _simulate_llm_generation(
    self,
    section_type: str,
    client_data: Dict[str, Any],
    evidence_items: List[Dict[str, Any]]
) -> str:
    """
    ЗАГЛУШКА: Симулирует генерацию контента.
    В продакшене заменить на реальный вызов LLM.
    """
    # ... simple template filling ...
```

**Нужна замена на:**
```python
async def _generate_with_llm(
    self,
    prompt: str,
    section_type: str,
    max_tokens: int = 1500
) -> str:
    """Real LLM generation."""
    # OpenAI / Anthropic / Azure OpenAI call
```

---

## 2. OpenAI GPT-4 Integration

### Setup

**Установка:**
```bash
pip install openai>=1.0.0
```

**Environment:**
```bash
# .env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview  # or gpt-4-0125-preview
```

### Implementation

```python
# core/groupagents/writer_agent.py

from openai import AsyncOpenAI
import os
from typing import Dict, Any

class WriterAgent:
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        self.memory = memory_manager or MemoryManager()
        self._templates: Dict[str, DocumentTemplate] = {}

        # Few-shot libraries
        self._example_library = ExampleLibrary()
        self._section_patterns = SectionPatternLibrary()

        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

        # Tracking
        self._generated_sections: Dict[str, GeneratedSection] = {}
        self._generation_count = 0

    async def _generate_with_patterns(
        self,
        context: Dict[str, Any],
        section_type: str,
        client_data: Dict[str, Any]
    ) -> str:
        """
        ЗАМЕНИТЬ: Real LLM generation with patterns.

        Args:
            context: Built context with examples + patterns + data
            section_type: Type of section to generate
            client_data: Client-specific data

        Returns:
            Generated content string
        """
        # Build the prompt (already implemented)
        prompt = self._build_generation_prompt(context)

        try:
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(section_type)
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # Balance creativity and consistency
                max_tokens=1500,
                top_p=0.9,
                frequency_penalty=0.3,  # Reduce repetition
                presence_penalty=0.3    # Encourage diversity
            )

            # Extract generated content
            content = response.choices[0].message.content

            # Log generation metadata
            await self.memory.alog_audit(
                event_type="llm_generation",
                user_id=client_data.get("user_id", "system"),
                details={
                    "section_type": section_type,
                    "model": self.openai_model,
                    "tokens_used": {
                        "prompt": response.usage.prompt_tokens,
                        "completion": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    },
                    "finish_reason": response.choices[0].finish_reason
                }
            )

            return content

        except Exception as e:
            # Log error
            await self.memory.alog_audit(
                event_type="llm_generation_error",
                user_id=client_data.get("user_id", "system"),
                details={
                    "error": str(e),
                    "section_type": section_type
                }
            )

            # Fallback to simulation or raise
            raise Exception(f"LLM generation failed: {e}")

    def _get_system_prompt(self, section_type: str) -> str:
        """
        Get system prompt for LLM based on section type.

        This defines the LLM's role and expertise.
        """
        base_prompt = """You are an expert immigration attorney specializing in EB-1A petitions.

Your expertise includes:
- Deep knowledge of 8 CFR § 204.5(h)(3) regulations
- Familiarity with key case law (Kazarian v. USCIS, Visinscaia v. Beers, etc.)
- Professional legal writing style
- Evidence analysis and argumentation
- Regulatory compliance

Your task is to write compelling, legally sound sections for EB-1A petitions that:
1. Follow regulatory requirements precisely
2. Use professional legal language
3. Present evidence persuasively
4. Cite relevant regulations and case law
5. Maintain consistent structure and tone"""

        # Section-specific additions
        section_prompts = {
            "awards": """

For Awards sections:
- Emphasize prestige and competitive selection (8 CFR § 204.5(h)(3)(i))
- Highlight international/national recognition
- Explain selection criteria and acceptance rates
- Compare to industry benchmarks
- Reference Buletini v. INS standards""",

            "press": """

For Press sections:
- Focus on major media outlets (8 CFR § 204.5(h)(3)(iii))
- Emphasize independent authorship and focus on beneficiary
- Highlight circulation and reach
- Distinguish from self-promotion
- Reference Grimson v. INS standards""",

            "judging": """

For Judging sections:
- Demonstrate peer recognition (8 CFR § 204.5(h)(3)(iv))
- Explain significance of judging role
- Highlight expertise required
- Show impact of judgments
- Reference relevant case law""",

            "membership": """

For Membership sections:
- Emphasize selective requirements (8 CFR § 204.5(h)(3)(ii))
- Highlight outstanding achievements required
- Explain nomination/election process
- Compare to general membership
- Reference standards for "distinguished" membership""",

            "contributions": """

For Original Contributions sections:
- Prove originality and major significance (8 CFR § 204.5(h)(3)(v))
- Demonstrate field-wide impact
- Show expert recognition
- Quantify influence when possible
- Reference Visinscaia v. Beers standards"""
        }

        section_specific = section_prompts.get(section_type, "")
        return base_prompt + section_specific

    def _build_generation_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build user prompt from context.

        This method is already implemented but can be enhanced.
        """
        section_type = context["section_type"]
        beneficiary = context.get("beneficiary", "the beneficiary")
        field = context.get("field", "their field")
        evidence_items = context.get("evidence", [])

        prompt = f"""Generate a {section_type} section for an EB-1A petition.

**Beneficiary Information:**
- Name: {beneficiary}
- Field: {field}
- Evidence Items: {len(evidence_items)}

**Section Instructions:**
{context.get('instructions', '')}

"""

        # Add few-shot examples
        if "examples" in context and context["examples"]:
            prompt += "\n**HIGH-QUALITY EXAMPLES TO FOLLOW:**\n\n"
            for i, example in enumerate(context["examples"], 1):
                prompt += f"""Example {i} (Quality: {example.get('quality', 0.0):.2f}):

INPUT:
Beneficiary: {example.get('input', {}).get('beneficiary', 'N/A')}
Field: {example.get('input', {}).get('field', 'N/A')}
Evidence: {len(example.get('input', {}).get('evidence', []))} items

OUTPUT:
{example.get('output', '')}

---

"""

        # Add structural patterns
        if "patterns" in context and context["patterns"]:
            prompt += "\n**STRUCTURAL PATTERNS TO APPLY:**\n\n"
            for pattern in context["patterns"]:
                prompt += f"""Pattern: {pattern.get('type', 'unknown').upper()}

Structure Template:
{pattern.get('structure', '')}

Example Phrases:
{chr(10).join('- ' + p for p in pattern.get('phrases', []))}

Legal Language Hints:
{chr(10).join('- ' + h for h in pattern.get('legal_hints', []))}

---

"""

        # Add client evidence
        prompt += f"\n**CLIENT EVIDENCE ({len(evidence_items)} items):**\n\n"
        for i, evidence in enumerate(evidence_items, 1):
            prompt += f"""{i}. **{evidence.get('title', 'Untitled')}**
   {evidence.get('description', 'No description')}

"""

        # Final instruction
        prompt += """
**TASK:**
Generate a complete, high-quality {section_type} section following:
1. The examples above (structure, style, tone)
2. The structural patterns provided
3. All client evidence items
4. Regulatory and legal requirements

The section should:
- Begin with a clear opening statement
- Analyze each evidence item systematically
- Use professional legal language
- Include relevant citations (8 CFR §, case law)
- Conclude with a strong statement of extraordinary ability

Write ONLY the section content. Do NOT include meta-commentary.
""".format(section_type=section_type)

        return prompt
```

### Token Usage Tracking

```python
class WriterAgent:
    async def get_stats(self) -> Dict[str, Any]:
        """Enhanced stats with LLM usage tracking."""
        base_stats = {
            "generation_stats": {
                "total_generations": self._generation_count,
                "llm_tokens_used": await self._get_total_tokens_used(),
                "estimated_cost": await self._calculate_llm_cost()
            },
            "total_documents": len(self._documents),
            "total_templates": len(self._templates),
            "total_sections_generated": len(self._generated_sections),
            "pending_approvals": len(self._approval_workflows)
        }

        # Example library stats
        example_stats = await self._example_library.get_example_stats()
        base_stats["example_library_stats"] = example_stats

        return base_stats

    async def _get_total_tokens_used(self) -> Dict[str, int]:
        """Get total token usage from audit logs."""
        # Query memory manager for token usage
        # This assumes audit logs store token counts
        return {
            "prompt_tokens": 0,  # Calculate from logs
            "completion_tokens": 0,
            "total_tokens": 0
        }

    async def _calculate_llm_cost(self) -> Dict[str, float]:
        """Calculate estimated LLM costs."""
        # GPT-4 pricing (as of 2024)
        pricing = {
            "gpt-4-turbo-preview": {
                "input": 0.01,   # per 1K tokens
                "output": 0.03   # per 1K tokens
            }
        }

        tokens = await self._get_total_tokens_used()
        model_pricing = pricing.get(self.openai_model, pricing["gpt-4-turbo-preview"])

        input_cost = (tokens["prompt_tokens"] / 1000) * model_pricing["input"]
        output_cost = (tokens["completion_tokens"] / 1000) * model_pricing["output"]

        return {
            "input_cost_usd": round(input_cost, 4),
            "output_cost_usd": round(output_cost, 4),
            "total_cost_usd": round(input_cost + output_cost, 4)
        }
```

---

## 3. Anthropic Claude Integration

### Setup

```bash
pip install anthropic>=0.18.0
```

```bash
# .env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### Implementation

```python
from anthropic import AsyncAnthropic

class WriterAgent:
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        # ... existing initialization ...

        # Initialize Anthropic client
        if os.getenv("ANTHROPIC_API_KEY"):
            self.anthropic_client = AsyncAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
            self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
            self.use_anthropic = True
        else:
            self.use_anthropic = False

    async def _generate_with_patterns(
        self,
        context: Dict[str, Any],
        section_type: str,
        client_data: Dict[str, Any]
    ) -> str:
        """Generate with Claude or GPT-4."""
        if self.use_anthropic:
            return await self._generate_with_claude(context, section_type, client_data)
        else:
            return await self._generate_with_gpt4(context, section_type, client_data)

    async def _generate_with_claude(
        self,
        context: Dict[str, Any],
        section_type: str,
        client_data: Dict[str, Any]
    ) -> str:
        """Generate with Anthropic Claude."""
        system_prompt = self._get_system_prompt(section_type)
        user_prompt = self._build_generation_prompt(context)

        try:
            response = await self.anthropic_client.messages.create(
                model=self.anthropic_model,
                max_tokens=2000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            content = response.content[0].text

            # Log usage
            await self.memory.alog_audit(
                event_type="llm_generation",
                user_id=client_data.get("user_id", "system"),
                details={
                    "section_type": section_type,
                    "model": self.anthropic_model,
                    "tokens_used": {
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens
                    },
                    "stop_reason": response.stop_reason
                }
            )

            return content

        except Exception as e:
            await self.memory.alog_audit(
                event_type="llm_generation_error",
                user_id=client_data.get("user_id", "system"),
                details={"error": str(e), "section_type": section_type}
            )
            raise Exception(f"Claude generation failed: {e}")
```

---

## 4. Prompt Engineering Best Practices

### 1. System Prompt Design

**Good System Prompt:**
```python
"""You are an expert immigration attorney with 15+ years specializing in EB-1A petitions.

EXPERTISE:
- 8 CFR § 204.5(h)(3) regulations
- Kazarian two-step framework
- Legal writing for USCIS adjudication
- Evidence analysis and persuasive argumentation

WRITING STYLE:
- Professional legal tone
- Clear, concise sentences
- Active voice preferred
- Regulatory citations when relevant
- Logical progression of arguments

REQUIREMENTS:
- Follow structural patterns precisely
- Cite regulations and case law
- Avoid hyperbole or unsubstantiated claims
- Use evidence-based argumentation
- Maintain consistency across sections"""
```

**Bad System Prompt:**
```python
"You are a lawyer. Write EB-1A petition sections."
# Too vague, no specific expertise, no style guidance
```

### 2. Few-Shot Examples

**Quality Criteria:**
- Use 2-3 high-quality examples (quality_score >= 0.85)
- Examples should vary in content but maintain consistent structure
- Include both input context and output
- Show different evidence types

**Example Selection:**
```python
# Good: Diverse, high-quality examples
examples = [
    {"quality": 0.90, "field": "AI", "evidence_count": 3},
    {"quality": 0.88, "field": "Biology", "evidence_count": 4},
    {"quality": 0.92, "field": "Physics", "evidence_count": 2}
]

# Bad: Too many examples or low quality
examples = [
    {"quality": 0.60, "field": "AI", "evidence_count": 3},
    {"quality": 0.65, "field": "AI", "evidence_count": 3},
    {"quality": 0.70, "field": "AI", "evidence_count": 3},
    {"quality": 0.62, "field": "AI", "evidence_count": 3},
    {"quality": 0.68, "field": "AI", "evidence_count": 3}
]
# Too many, too similar, low quality
```

### 3. Prompt Structure

**Recommended Order:**
1. Task definition
2. Beneficiary context
3. Section-specific instructions
4. Few-shot examples (2-3)
5. Structural patterns
6. Client evidence
7. Final task statement

**Token Optimization:**
```python
# Good: Concise but complete
prompt = f"""Generate {section_type} section.

Beneficiary: {name} | Field: {field} | Evidence: {count} items

Examples:
[2-3 examples, ~200 tokens each]

Patterns:
[Key patterns, ~100 tokens]

Evidence:
[Client evidence, ~300 tokens]

Generate following examples and patterns above."""

# Bad: Too verbose
prompt = f"""Hello! I need you to please generate a very detailed and comprehensive
section for an EB-1A petition. The section type is {section_type}. Let me give you
all the information you need. First, let me tell you about the beneficiary...
[continues for 2000+ tokens before getting to the point]"""
```

### 4. Temperature & Sampling

**Recommended Settings:**

```python
# For legal content (consistency priority)
{
    "temperature": 0.7,      # Balanced creativity
    "top_p": 0.9,            # Nucleus sampling
    "frequency_penalty": 0.3, # Reduce repetition
    "presence_penalty": 0.3   # Encourage topic diversity
}

# For highly creative variations (testing)
{
    "temperature": 0.9,
    "top_p": 0.95,
    "frequency_penalty": 0.5,
    "presence_penalty": 0.5
}

# For maximum consistency (templates)
{
    "temperature": 0.3,
    "top_p": 0.85,
    "frequency_penalty": 0.2,
    "presence_penalty": 0.2
}
```

---

## 5. Quality Assurance & Validation

### Post-Generation Validation

```python
class WriterAgent:
    async def _validate_generated_content(
        self,
        content: str,
        section_type: str,
        evidence_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate generated content for quality and compliance.

        Returns:
            Dict with validation results and issues
        """
        issues = []
        warnings = []

        # 1. Length validation
        word_count = len(content.split())
        if word_count < 200:
            issues.append("Content too short (< 200 words)")
        elif word_count > 1000:
            warnings.append("Content may be too long (> 1000 words)")

        # 2. Evidence coverage
        for evidence in evidence_items:
            evidence_title = evidence.get("title", "")
            if evidence_title and evidence_title not in content:
                warnings.append(f"Evidence '{evidence_title}' may not be mentioned")

        # 3. Required elements
        required_phrases = {
            "awards": ["8 CFR § 204.5(h)(3)(i)", "nationally or internationally recognized"],
            "press": ["8 CFR § 204.5(h)(3)(iii)", "published material"],
            "judging": ["8 CFR § 204.5(h)(3)(iv)", "judge", "peer"],
            "membership": ["8 CFR § 204.5(h)(3)(ii)", "outstanding achievements"],
            "contributions": ["8 CFR § 204.5(h)(3)(v)", "original", "major significance"]
        }

        section_requirements = required_phrases.get(section_type, [])
        for phrase in section_requirements:
            if phrase.lower() not in content.lower():
                warnings.append(f"Missing recommended phrase: '{phrase}'")

        # 4. Legal citations
        if "kazarian" not in content.lower() and "8 cfr" not in content.lower():
            warnings.append("No legal citations found")

        # 5. Structure validation
        if "**" not in content:  # Check for markdown formatting
            warnings.append("Missing markdown formatting")

        if not content.strip().endswith("."):
            issues.append("Content doesn't end with proper punctuation")

        # 6. Tone check (simple heuristic)
        informal_words = ["awesome", "cool", "great", "nice", "wow"]
        for word in informal_words:
            if word in content.lower():
                warnings.append(f"Informal language detected: '{word}'")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "word_count": word_count,
            "evidence_coverage": self._calculate_evidence_coverage(content, evidence_items)
        }

    def _calculate_evidence_coverage(
        self,
        content: str,
        evidence_items: List[Dict[str, Any]]
    ) -> float:
        """Calculate percentage of evidence items mentioned."""
        if not evidence_items:
            return 1.0

        mentioned = 0
        for evidence in evidence_items:
            title = evidence.get("title", "")
            if title and title.lower() in content.lower():
                mentioned += 1

        return mentioned / len(evidence_items)

    async def agenerate_legal_section(
        self,
        section_type: str,
        client_data: Dict[str, Any],
        examples: List[str] = None,
        use_patterns: bool = True,
        user_id: str = "system",
        max_retries: int = 2  # NEW: Allow retries
    ) -> GeneratedSection:
        """
        Generate section with validation and retry logic.
        """
        for attempt in range(max_retries + 1):
            # ... existing generation logic ...

            # Generate content
            content = await self._generate_with_patterns(context, section_type, client_data)

            # Validate
            validation = await self._validate_generated_content(
                content, section_type, evidence_items
            )

            if validation["valid"]:
                # Success - proceed with confidence scoring, etc.
                break
            else:
                if attempt < max_retries:
                    # Log retry
                    await self.memory.alog_audit(
                        event_type="generation_retry",
                        user_id=user_id,
                        details={
                            "attempt": attempt + 1,
                            "issues": validation["issues"],
                            "section_type": section_type
                        }
                    )

                    # Optionally adjust prompt for retry
                    context["retry_instructions"] = (
                        "Previous generation had issues: " +
                        "; ".join(validation["issues"]) +
                        ". Please address these in this generation."
                    )
                else:
                    # Max retries reached - log warning but proceed
                    await self.memory.alog_audit(
                        event_type="generation_quality_warning",
                        user_id=user_id,
                        details={
                            "issues": validation["issues"],
                            "warnings": validation["warnings"],
                            "section_type": section_type
                        }
                    )

        # ... rest of existing logic ...
```

---

## 6. Cost Optimization

### Token Usage Optimization

```python
class WriterAgent:
    def _optimize_prompt_tokens(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reduce prompt tokens while maintaining quality.

        Strategies:
        1. Limit examples to top 2-3
        2. Truncate long evidence descriptions
        3. Summarize patterns instead of full text
        """
        optimized = context.copy()

        # Limit examples
        if "examples" in optimized and len(optimized["examples"]) > 3:
            # Keep only top 3 by quality
            optimized["examples"] = sorted(
                optimized["examples"],
                key=lambda x: x.get("quality", 0),
                reverse=True
            )[:3]

        # Truncate evidence descriptions
        if "evidence" in optimized:
            for evidence in optimized["evidence"]:
                desc = evidence.get("description", "")
                if len(desc) > 200:  # 200 chars max
                    evidence["description"] = desc[:197] + "..."

        # Summarize patterns
        if "patterns" in optimized:
            for pattern in optimized["patterns"]:
                # Keep only essential fields
                pattern["phrases"] = pattern.get("phrases", [])[:3]  # Max 3 phrases
                pattern["legal_hints"] = pattern.get("legal_hints", [])[:3]

        return optimized

    async def agenerate_legal_section(
        self,
        section_type: str,
        client_data: Dict[str, Any],
        examples: List[str] = None,
        use_patterns: bool = True,
        user_id: str = "system",
        optimize_tokens: bool = True  # NEW parameter
    ) -> GeneratedSection:
        """Generate section with optional token optimization."""
        # ... existing logic ...

        # Build context
        context = await self._build_few_shot_context(
            section_type, client_data, examples_list, patterns_list
        )

        # Optimize if requested
        if optimize_tokens:
            context = self._optimize_prompt_tokens(context)

        # ... rest of logic ...
```

### Caching Strategies

```python
import hashlib
import json

class WriterAgent:
    async def agenerate_legal_section(
        self,
        section_type: str,
        client_data: Dict[str, Any],
        examples: List[str] = None,
        use_patterns: bool = True,
        user_id: str = "system",
        use_cache: bool = True  # NEW
    ) -> GeneratedSection:
        """Generate with optional caching."""
        # Generate cache key from inputs
        cache_key = self._generate_cache_key(section_type, client_data, examples)

        # Check cache
        if use_cache:
            cached = await self._get_cached_section(cache_key)
            if cached:
                return cached

        # Generate (not in cache)
        section = await self._generate_section_uncached(
            section_type, client_data, examples, use_patterns, user_id
        )

        # Cache result
        if use_cache and section.confidence_score >= 0.80:  # Only cache high-quality
            await self._cache_section(cache_key, section)

        return section

    def _generate_cache_key(
        self,
        section_type: str,
        client_data: Dict[str, Any],
        examples: List[str] = None
    ) -> str:
        """Generate deterministic cache key."""
        # Create stable representation
        cache_data = {
            "section_type": section_type,
            "beneficiary": client_data.get("beneficiary_name"),
            "field": client_data.get("field"),
            "evidence_titles": [e.get("title") for e in client_data.get("evidence", [])],
            "examples": sorted(examples) if examples else []
        }

        # Hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    async def _get_cached_section(self, cache_key: str) -> GeneratedSection | None:
        """Retrieve from cache."""
        # Use Redis, file system, or database
        # Example with file system:
        cache_file = Path(f".cache/sections/{cache_key}.json")
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            return GeneratedSection(**data)
        return None

    async def _cache_section(self, cache_key: str, section: GeneratedSection):
        """Save to cache."""
        cache_file = Path(f".cache/sections/{cache_key}.json")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(section.model_dump_json())
```

### Cost Monitoring

```python
class WriterAgent:
    async def get_cost_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> Dict[str, Any]:
        """
        Generate cost report for LLM usage.

        Returns:
            Detailed breakdown of costs by section type, user, etc.
        """
        # Query audit logs for LLM generations
        generations = await self.memory.query_audit_events(
            event_type="llm_generation",
            start_date=start_date,
            end_date=end_date
        )

        # Calculate costs
        total_tokens = {"input": 0, "output": 0}
        by_section_type = {}
        by_user = {}

        for gen in generations:
            tokens = gen.get("details", {}).get("tokens_used", {})
            total_tokens["input"] += tokens.get("prompt", 0)
            total_tokens["output"] += tokens.get("completion", 0)

            # By section type
            section_type = gen.get("details", {}).get("section_type", "unknown")
            if section_type not in by_section_type:
                by_section_type[section_type] = {"input": 0, "output": 0, "count": 0}
            by_section_type[section_type]["input"] += tokens.get("prompt", 0)
            by_section_type[section_type]["output"] += tokens.get("completion", 0)
            by_section_type[section_type]["count"] += 1

            # By user
            user_id = gen.get("user_id", "unknown")
            if user_id not in by_user:
                by_user[user_id] = {"input": 0, "output": 0, "count": 0}
            by_user[user_id]["input"] += tokens.get("prompt", 0)
            by_user[user_id]["output"] += tokens.get("completion", 0)
            by_user[user_id]["count"] += 1

        # Calculate USD costs (GPT-4 pricing)
        input_cost = (total_tokens["input"] / 1000) * 0.01
        output_cost = (total_tokens["output"] / 1000) * 0.03
        total_cost = input_cost + output_cost

        return {
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "total": {
                "tokens": total_tokens,
                "cost_usd": round(total_cost, 4),
                "generations": len(generations)
            },
            "by_section_type": {
                k: {
                    **v,
                    "cost_usd": round(
                        (v["input"] / 1000 * 0.01) + (v["output"] / 1000 * 0.03), 4
                    )
                }
                for k, v in by_section_type.items()
            },
            "by_user": {
                k: {
                    **v,
                    "cost_usd": round(
                        (v["input"] / 1000 * 0.01) + (v["output"] / 1000 * 0.03), 4
                    )
                }
                for k, v in by_user.items()
            }
        }
```

---

## 7. Testing

### Unit Tests with Mocking

```python
# tests/test_writer_agent_llm.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.groupagents.writer_agent import WriterAgent, GeneratedSection

@pytest.fixture
def writer_agent():
    return WriterAgent()

@pytest.mark.asyncio
async def test_generation_with_openai(writer_agent):
    """Test generation with mocked OpenAI."""
    with patch.object(writer_agent, 'openai_client') as mock_client:
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="**Awards Section**\n\nGenerated content..."))]
        mock_response.usage = MagicMock(
            prompt_tokens=500,
            completion_tokens=300,
            total_tokens=800
        )
        mock_response.choices[0].finish_reason = "stop"

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Test generation
        client_data = {
            "beneficiary_name": "Dr. Test",
            "field": "AI",
            "evidence": [{"title": "Award 1", "description": "Test award"}]
        }

        section = await writer_agent.agenerate_legal_section(
            section_type="awards",
            client_data=client_data
        )

        # Assertions
        assert isinstance(section, GeneratedSection)
        assert section.section_type == "awards"
        assert section.content.startswith("**Awards")
        assert section.word_count > 0

@pytest.mark.asyncio
async def test_validation_and_retry(writer_agent):
    """Test validation triggers retry."""
    with patch.object(writer_agent, '_generate_with_patterns') as mock_gen:
        # First call returns invalid (too short)
        # Second call returns valid
        mock_gen.side_effect = [
            "Too short",  # Invalid
            "**Awards Section**\n\nThis is a properly formatted section with sufficient length and all required elements including 8 CFR § 204.5(h)(3)(i) and nationally recognized awards. " * 10  # Valid
        ]

        client_data = {
            "beneficiary_name": "Dr. Test",
            "field": "AI",
            "evidence": [{"title": "Award 1"}]
        }

        section = await writer_agent.agenerate_legal_section(
            section_type="awards",
            client_data=client_data,
            max_retries=2
        )

        # Should have retried
        assert mock_gen.call_count == 2
        assert section.word_count >= 200
```

### Integration Tests

```python
# tests/integration/test_writer_agent_live.py

import pytest
import os

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_openai_generation():
    """Test with REAL OpenAI API."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Requires OPENAI_API_KEY")

    writer = WriterAgent()

    client_data = {
        "beneficiary_name": "Dr. Elena Rodriguez",
        "field": "Computational Biology",
        "evidence": [
            {
                "title": "NIH Director's Pioneer Award",
                "description": "Prestigious award for groundbreaking research"
            }
        ]
    }

    section = await writer.agenerate_legal_section(
        section_type="awards",
        client_data=client_data
    )

    # Assertions
    assert section.section_type == "awards"
    assert section.confidence_score > 0.7
    assert "8 CFR" in section.content or "regulation" in section.content.lower()
    assert section.word_count >= 150

@pytest.mark.integration
@pytest.mark.asyncio
async def test_cost_tracking():
    """Test cost tracking functionality."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Requires OPENAI_API_KEY")

    writer = WriterAgent()

    # Generate a section
    await writer.agenerate_legal_section(
        section_type="awards",
        client_data={"beneficiary_name": "Test", "field": "AI", "evidence": []}
    )

    # Check cost report
    report = await writer.get_cost_report()

    assert report["total"]["generations"] >= 1
    assert report["total"]["cost_usd"] > 0
    assert "awards" in report["by_section_type"]
```

---

## 📊 Cost Comparison

**Per section generation (estimated):**

| Model | Input Tokens | Output Tokens | Cost per Section |
|-------|-------------|---------------|------------------|
| GPT-4 Turbo | ~1500 | ~500 | $0.015 + $0.015 = **$0.03** |
| GPT-4 | ~1500 | ~500 | $0.045 + $0.030 = **$0.075** |
| Claude 3.5 Sonnet | ~1500 | ~500 | $0.0045 + $0.0225 = **$0.027** |
| Claude 3 Opus | ~1500 | ~500 | $0.0225 + $0.1125 = **$0.135** |

**Monthly costs (1000 sections):**
- GPT-4 Turbo: $30/month
- GPT-4: $75/month
- Claude 3.5 Sonnet: $27/month
- Claude 3 Opus: $135/month

**Recommendation:** Use GPT-4 Turbo or Claude 3.5 Sonnet for best cost/quality balance.

---

## 🔧 Troubleshooting

### Common Issues

1. **Rate Limit Errors**
   - Implement exponential backoff
   - Use rate limiter from EvidenceResearcher guide
   - Consider upgrading API tier

2. **Low Quality Output**
   - Improve system prompt specificity
   - Add more high-quality examples
   - Adjust temperature (lower = more consistent)
   - Add validation and retry logic

3. **High Costs**
   - Enable token optimization
   - Use caching for repeated queries
   - Limit example count to 2-3
   - Truncate long evidence descriptions

4. **Inconsistent Formatting**
   - Add explicit formatting instructions to prompt
   - Use validation to check markdown
   - Include formatting examples in few-shot

---

**Last Updated:** 2025-01-17
**Version:** 1.0.0
**Status:** Production Ready
