"""Chain-of-Thought (CoT) prompting templates for enhanced reasoning.

This module provides CoT templates that improve LLM reasoning quality by
explicitly asking models to think step-by-step before answering.

Based on 2025 best practices from:
- OpenAI (GPT-5 reasoning_effort parameter)
- Anthropic (Claude thinking process)
- Google (Gemini step-by-step reasoning)

References:
- Wei et al. (2022): "Chain-of-Thought Prompting Elicits Reasoning in LLMs"
- Kojima et al. (2023): "Large Language Models are Zero-Shot Reasoners"
"""

from __future__ import annotations

from enum import Enum


class CoTTemplate(str, Enum):
    """Chain-of-Thought template types."""

    ZERO_SHOT = "zero_shot"  # "Let's think step by step"
    FEW_SHOT = "few_shot"  # With examples
    STRUCTURED = "structured"  # With explicit steps
    LEGAL = "legal"  # Legal reasoning specific
    ANALYTICAL = "analytical"  # For analysis tasks
    CREATIVE = "creative"  # For generation tasks


# Zero-Shot CoT (most versatile)
ZERO_SHOT_COT = """Let's approach this step-by-step:

1. First, I'll understand what is being asked
2. Then, I'll identify the key information
3. Next, I'll reason through the solution
4. Finally, I'll provide a clear answer

Now, let me work through this:

{task}"""


# Structured CoT (for complex tasks)
STRUCTURED_COT = """I will solve this systematically:

**Step 1: Understand the Goal**
What exactly needs to be accomplished?

**Step 2: Gather Information**
What facts, context, or data are relevant?

**Step 3: Break Down the Problem**
What are the sub-problems or components?

**Step 4: Reason Through Each Part**
How do these components relate?

**Step 5: Synthesize the Solution**
What is the complete answer?

---

Task: {task}

Let me work through each step:"""


# Legal Reasoning CoT
LEGAL_COT = """As a legal analysis system, I will apply rigorous legal reasoning:

**Issue Identification**
What is the legal question or problem?

**Rule Statement**
What laws, regulations, or precedents apply?

**Analysis**
How do the facts align with the legal framework?

**Counterarguments**
What alternative interpretations exist?

**Conclusion**
What is the well-reasoned legal conclusion?

---

Legal Matter: {task}

Detailed Analysis:"""


# Analytical CoT (for evidence/data analysis)
ANALYTICAL_COT = """I will conduct a thorough analytical review:

**Data/Evidence Review**
What information is available?

**Pattern Recognition**
What trends, anomalies, or connections exist?

**Critical Evaluation**
What are the strengths and weaknesses?

**Implications**
What does this mean in context?

**Recommendation**
What action or conclusion follows?

---

Analysis Request: {task}

Systematic Analysis:"""


# Creative CoT (for document generation)
CREATIVE_COT = """I will approach this creative task thoughtfully:

**Purpose & Audience**
Who is this for and what should it achieve?

**Key Messages**
What are the core points to communicate?

**Structure Planning**
How should this be organized?

**Tone & Style**
What voice and approach are appropriate?

**Quality Check**
Does this meet the requirements?

---

Creation Task: {task}

Let me develop this:"""


# Few-Shot CoT Example (for training)
FEW_SHOT_EXAMPLE = """Here are examples of step-by-step reasoning:

**Example 1:**
Question: Does the applicant meet the "published material" criterion for EB-1A?
Reasoning:
1. The criterion requires published material ABOUT the applicant's work
2. Review evidence: 3 news articles, 2 trade publications
3. Check: Do they discuss the applicant's contributions? Yes
4. Check: Are sources credible? All are established publications
5. Conclusion: Criterion satisfied with strong evidence

**Example 2:**
Question: Calculate total citations from provided CV
Reasoning:
1. Identify citation metrics: Google Scholar shows 247 citations
2. Verify: Check for duplicates - none found
3. Context: Field average is ~150 for this career stage
4. Conclusion: 247 citations, exceeds field average by 64%

---

Now, apply the same step-by-step reasoning to this task:

{task}

My reasoning:"""


def get_cot_prompt(template: CoTTemplate, task: str) -> str:
    """Get Chain-of-Thought prompt for given template and task.

    Args:
        template: CoT template type to use
        task: The actual task/question to reason through

    Returns:
        Formatted CoT prompt ready for LLM

    Example:
        >>> prompt = get_cot_prompt(CoTTemplate.ZERO_SHOT, "Analyze this evidence")
        >>> response = await llm.acomplete(prompt)
    """
    templates = {
        CoTTemplate.ZERO_SHOT: ZERO_SHOT_COT,
        CoTTemplate.STRUCTURED: STRUCTURED_COT,
        CoTTemplate.LEGAL: LEGAL_COT,
        CoTTemplate.ANALYTICAL: ANALYTICAL_COT,
        CoTTemplate.CREATIVE: CREATIVE_COT,
        CoTTemplate.FEW_SHOT: FEW_SHOT_EXAMPLE,
    }

    template_str = templates.get(template, ZERO_SHOT_COT)
    return template_str.format(task=task)


def apply_cot(task: str, template: CoTTemplate = CoTTemplate.ZERO_SHOT) -> str:
    """Apply Chain-of-Thought prompting to a task.

    Convenience function that wraps get_cot_prompt.

    Args:
        task: The task/question to enhance with CoT
        template: CoT template to use (default: zero-shot)

    Returns:
        CoT-enhanced prompt

    Example:
        >>> enhanced = apply_cot("What is the legal precedent?", CoTTemplate.LEGAL)
    """
    return get_cot_prompt(template, task)


def select_cot_template(command_type: str, action: str) -> CoTTemplate:
    """Automatically select appropriate CoT template based on command.

    Uses heuristics to match command types to optimal CoT templates.

    Args:
        command_type: Command type (e.g., "ask", "generate", "validate")
        action: Specific action being performed

    Returns:
        Recommended CoT template

    Example:
        >>> template = select_cot_template("validate", "check_evidence")
        >>> # Returns CoTTemplate.ANALYTICAL
    """
    command_lower = command_type.lower()
    action_lower = action.lower()

    # Legal commands
    if any(
        kw in command_lower or kw in action_lower
        for kw in ["legal", "petition", "criterion", "uscis", "immigration"]
    ):
        return CoTTemplate.LEGAL

    # Analysis commands
    if any(
        kw in command_lower or kw in action_lower
        for kw in ["analyze", "validate", "review", "evaluate", "assess"]
    ):
        return CoTTemplate.ANALYTICAL

    # Creative/generation commands
    if any(
        kw in command_lower or kw in action_lower
        for kw in ["generate", "write", "create", "draft", "compose"]
    ):
        return CoTTemplate.CREATIVE

    # Complex multi-step tasks
    if any(kw in command_lower or kw in action_lower for kw in ["workflow", "case", "eb1"]):
        return CoTTemplate.STRUCTURED

    # Default to zero-shot for simple queries
    return CoTTemplate.ZERO_SHOT


# Utility for backward compatibility
def enhance_prompt_with_cot(
    prompt: str, command_type: str | None = None, action: str | None = None
) -> str:
    """Enhance an existing prompt with Chain-of-Thought reasoning.

    Automatically selects template if command type provided, otherwise uses zero-shot.

    Args:
        prompt: Original prompt text
        command_type: Optional command type for template selection
        action: Optional action for template selection

    Returns:
        CoT-enhanced prompt

    Example:
        >>> original = "Analyze this evidence for EB-1A criterion"
        >>> enhanced = enhance_prompt_with_cot(original, "validate", "criterion")
    """
    if command_type and action:
        template = select_cot_template(command_type, action)
    else:
        template = CoTTemplate.ZERO_SHOT

    return get_cot_prompt(template, prompt)
