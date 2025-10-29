# WriterAgent Few-Shot Learning Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          WriterAgent                                      │
│                                                                           │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────┐   │
│  │ Document        │  │ Template         │  │ Approval            │   │
│  │ Generation      │  │ Management       │  │ Workflow            │   │
│  │ (Original)      │  │ (Original)       │  │ (Original)          │   │
│  └─────────────────┘  └──────────────────┘  └─────────────────────┘   │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              Few-Shot Learning Extension (NEW)                     │  │
│  │                                                                     │  │
│  │  ┌──────────────────┐           ┌──────────────────┐             │  │
│  │  │ ExampleLibrary   │           │ PatternLibrary   │             │  │
│  │  ├──────────────────┤           ├──────────────────┤             │  │
│  │  │ • get_examples() │           │ • get_patterns() │             │  │
│  │  │ • add_example()  │           │ • add_pattern()  │             │  │
│  │  │ • stats()        │           │                   │             │  │
│  │  │                  │           │                   │             │  │
│  │  │ Storage:         │           │ Storage:         │             │  │
│  │  │ - 3 defaults     │           │ - 4 patterns     │             │  │
│  │  │ - Custom added   │           │ - Custom added   │             │  │
│  │  │ - Indexed by     │           │ - Indexed by     │             │  │
│  │  │   section_type   │           │   section_type   │             │  │
│  │  └──────────────────┘           └──────────────────┘             │  │
│  │                                                                     │  │
│  │  ┌───────────────────────────────────────────────────────────┐   │  │
│  │  │         agenerate_legal_section()                          │   │  │
│  │  │         Main Few-Shot Generation Method                    │   │  │
│  │  └───────────────────────────────────────────────────────────┘   │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Memory Manager                                  │  │
│  │                    (Audit Logging)                                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Generation Pipeline Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    agenerate_legal_section()                              │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────────┐
        │ 1. Get Few-Shot Examples                   │
        │    _get_few_shot_examples()                │
        │                                             │
        │    Input:  section_type, example_ids       │
        │    Output: List[FewShotExample]            │
        │                                             │
        │    • Auto-select best 3 if no IDs          │
        │    • Filter by quality >= 0.75             │
        │    • Sort by quality + usage               │
        └─────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │ 2. Get Structural Patterns                 │
        │    _section_patterns.get_patterns()        │
        │                                             │
        │    Input:  section_type                    │
        │    Output: List[SectionPattern]            │
        │                                             │
        │    • Opening pattern                       │
        │    • Evidence analysis pattern             │
        │    • Conclusion pattern                    │
        │    • Comparative analysis pattern          │
        └─────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │ 3. Build Context                           │
        │    _build_few_shot_context()               │
        │                                             │
        │    Combines:                               │
        │    • Client data (beneficiary, field)      │
        │    • Evidence items                        │
        │    • Few-shot examples                     │
        │    • Structural patterns                   │
        │    • Section instructions                  │
        │                                             │
        │    Output: Dict[str, Any]                  │
        └─────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │ 4. Build LLM Prompt                        │
        │    _build_generation_prompt()              │
        │                                             │
        │    Creates structured prompt:              │
        │    • System instructions                   │
        │    • Few-shot examples (3)                 │
        │    • Pattern templates (4)                 │
        │    • Client evidence items                 │
        │    • Generation task                       │
        │                                             │
        │    Output: str (prompt)                    │
        └─────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │ 5. Generate Content                        │
        │    _simulate_llm_generation()              │
        │    (or real LLM API call)                  │
        │                                             │
        │    • Apply patterns                        │
        │    • Format evidence                       │
        │    • Include legal citations               │
        │    • Professional tone                     │
        │                                             │
        │    Output: str (content)                   │
        └─────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │ 6. Calculate Quality Metrics               │
        │    _calculate_section_confidence()         │
        │    _generate_section_suggestions()         │
        │                                             │
        │    Scores based on:                        │
        │    • Examples used (+0.2)                  │
        │    • Patterns applied (+0.15)              │
        │    • Content length (+0.1)                 │
        │    • Legal phrases (+0.15)                 │
        │                                             │
        │    Output: confidence_score, suggestions   │
        └─────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │ 7. Create GeneratedSection                 │
        │                                             │
        │    • section_id (UUID)                     │
        │    • section_type                          │
        │    • title                                 │
        │    • content                               │
        │    • evidence_used                         │
        │    • examples_used                         │
        │    • patterns_applied                      │
        │    • confidence_score                      │
        │    • word_count                            │
        │    • suggestions                           │
        │    • metadata                              │
        └─────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────────┐
        │ 8. Save & Log                              │
        │    • Store in _generated_sections          │
        │    • Log via memory.alog_audit()           │
        │    • Update statistics                     │
        └─────────────────┬──────────────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │ Return Section │
                 └────────────────┘
```

## Data Models Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    _WriterBaseModel                          │
│                    (Pydantic BaseModel)                      │
│                                                               │
│  • model_dump() with JSON mode                              │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────────────────┐
        │                                              │
        ▼                                              ▼
┌──────────────────┐                         ┌──────────────────┐
│  Document Models │                         │ Few-Shot Models  │
│  (Original)      │                         │ (NEW)            │
│                  │                         │                  │
│ • DocumentType   │                         │ • FewShotExample │
│ • DocumentFormat │                         │ • SectionPattern │
│ • Language       │                         │ • GeneratedSection│
│ • ToneStyle      │                         │                  │
│ • DocumentTemplate│                        └──────────────────┘
│ • DocumentRequest│
│ • GeneratedDocument│
│ • ApprovalWorkflow│
└──────────────────┘
```

## Example Library Data Structure

```
ExampleLibrary
├── _examples: Dict[str, FewShotExample]
│   ├── "uuid-1": FewShotExample(
│   │     section_type="awards",
│   │     quality_score=0.90,
│   │     usage_count=5
│   │   )
│   ├── "uuid-2": FewShotExample(
│   │     section_type="press",
│   │     quality_score=0.85,
│   │     usage_count=3
│   │   )
│   └── "uuid-3": FewShotExample(
│         section_type="judging",
│         quality_score=0.88,
│         usage_count=2
│       )
│
└── _examples_by_type: Dict[str, List[str]]
    ├── "awards": ["uuid-1"]
    ├── "press": ["uuid-2"]
    └── "judging": ["uuid-3"]
```

## Pattern Library Data Structure

```
SectionPatternLibrary
├── _patterns: Dict[str, SectionPattern]
│   ├── "pattern-1": SectionPattern(
│   │     pattern_type="opening",
│   │     section_types=["awards", "press", "judging"]
│   │   )
│   ├── "pattern-2": SectionPattern(
│   │     pattern_type="evidence_analysis",
│   │     section_types=["awards", "press"]
│   │   )
│   ├── "pattern-3": SectionPattern(
│   │     pattern_type="conclusion",
│   │     section_types=["awards", "press", "judging"]
│   │   )
│   └── "pattern-4": SectionPattern(
│         pattern_type="comparative_analysis",
│         section_types=["awards", "contributions"]
│       )
│
└── _patterns_by_type: Dict[str, List[str]]
    ├── "awards": ["pattern-1", "pattern-2", "pattern-3", "pattern-4"]
    ├── "press": ["pattern-1", "pattern-2", "pattern-3"]
    └── "judging": ["pattern-1", "pattern-3"]
```

## Context Structure for Generation

```
Context Dictionary
{
  "section_type": "awards",
  "beneficiary": "Dr. Jane Smith",
  "field": "Machine Learning",
  "evidence": [
    {
      "title": "Best Paper Award",
      "description": "IEEE Conference..."
    },
    ...
  ],
  "evidence_count": 3,
  "instructions": "Focus on prestige, competitive selection...",

  "examples": [
    {
      "input": {...},
      "output": "**Awards and Prizes**\n\nDr. Smith has...",
      "quality": 0.90,
      "criterion": "Awards and Prizes"
    },
    ...
  ],

  "patterns": [
    {
      "type": "opening",
      "structure": "{beneficiary} has {achievement_summary}...",
      "phrases": ["has received X awards", ...],
      "legal_hints": ["satisfies regulatory requirements", ...],
      "variables": ["beneficiary", "achievement_summary", ...]
    },
    ...
  ]
}
```

## LLM Prompt Structure

```
┌──────────────────────────────────────────────────────────────┐
│ Generate a {section_type} section for an EB-1A petition.     │
│                                                               │
│ Beneficiary: {name}                                           │
│ Field: {field}                                                │
│ Evidence Count: {count}                                       │
│                                                               │
│ Instructions:                                                 │
│ {section_specific_instructions}                              │
├──────────────────────────────────────────────────────────────┤
│ === EXAMPLES OF HIGH-QUALITY SECTIONS ===                    │
│                                                               │
│ Example 1 (Quality: 0.90):                                   │
│ Input: {...}                                                  │
│ Output:                                                       │
│ **Awards and Prizes**                                        │
│ Dr. Smith has received the prestigious...                   │
│ [Full example text]                                          │
│                                                               │
│ Example 2 (Quality: 0.85):                                   │
│ [Similar structure]                                          │
├──────────────────────────────────────────────────────────────┤
│ === STRUCTURAL PATTERNS TO FOLLOW ===                        │
│                                                               │
│ OPENING Pattern:                                             │
│ Structure: {beneficiary} has {achievement_summary} in...    │
│ Example Phrases: has received X awards, demonstrates...     │
│ Legal Language: satisfies regulatory requirements...        │
│                                                               │
│ EVIDENCE_ANALYSIS Pattern:                                   │
│ [Similar structure]                                          │
│                                                               │
│ CONCLUSION Pattern:                                          │
│ [Similar structure]                                          │
├──────────────────────────────────────────────────────────────┤
│ === CLIENT DATA ===                                          │
│                                                               │
│ Evidence Items: 3                                            │
│                                                               │
│ 1. Best Paper Award                                          │
│    IEEE Conference, 1000+ submissions                        │
│                                                               │
│ 2. Outstanding Researcher Award                              │
│    National Science Foundation                               │
│                                                               │
│ 3. ...                                                        │
├──────────────────────────────────────────────────────────────┤
│ Now generate a high-quality section following the examples   │
│ and patterns above:                                          │
└──────────────────────────────────────────────────────────────┘
```

## Quality Scoring Flow

```
┌─────────────────────────────────────────────────┐
│ Calculate Confidence Score                      │
└──────────────────┬──────────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │ Base Score: 0.5             │
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │ + Examples Bonus            │
    │   • 3 examples: +0.21       │
    │   • Max: +0.20              │
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │ + Patterns Bonus            │
    │   • 4 patterns: +0.15       │
    │   • Max: +0.15              │
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │ + Content Length Bonus      │
    │   • 300-800 words: +0.10    │
    │   • 200-1000 words: +0.05   │
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │ + Legal Phrases Bonus       │
    │   • "8 CFR": +0.04          │
    │   • "Kazarian": +0.04       │
    │   • "regulatory": +0.04     │
    │   • "extraordinary": +0.04  │
    │   • Max: +0.15              │
    └──────────────┬──────────────┘
                   │
    ┌──────────────┴──────────────┐
    │ Final Score: 0.84           │
    │ (Capped at 1.0)             │
    └─────────────────────────────┘
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│                    External Systems                          │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
┌──────────────────┐            ┌──────────────────┐
│ LLM APIs         │            │ Memory Manager   │
│                  │            │                  │
│ • OpenAI GPT-5   │            │ • alog_audit()   │
│ • Anthropic      │            │ • Context store  │
│   Claude         │            │ • Vector search  │
│ • Azure OpenAI   │            │                  │
│                  │            └──────────────────┘
│ Currently:       │
│ _simulate_llm    │
│ _generation()    │
└──────────────────┘

        Ready for integration:
        Just replace _simulate_llm_generation()
        with real LLM API calls
```

## Usage Pattern

```
User Request
     │
     ▼
┌─────────────────────────────────┐
│ Prepare Client Data             │
│ • beneficiary_name              │
│ • field                         │
│ • evidence list                 │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Call agenerate_legal_section()  │
│ • section_type: "awards"        │
│ • client_data                   │
│ • use_patterns: True            │
└────────────┬────────────────────┘
             │
             ▼
    [Generation Pipeline]
        (see above)
             │
             ▼
┌─────────────────────────────────┐
│ Receive GeneratedSection        │
│ • content (full text)           │
│ • confidence_score (0.84)       │
│ • suggestions (list)            │
│ • metadata                      │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Optional: Improve & Re-generate │
│ • Follow suggestions            │
│ • Add more evidence             │
│ • Adjust patterns               │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Optional: Save as Example       │
│ • If quality_score >= 0.9       │
│ • Add to library for future use │
└─────────────────────────────────┘
```

## Performance Characteristics

```
Operation                    Time         Memory
────────────────────────────────────────────────
get_examples()              O(n)         O(1)
get_patterns()              O(n)         O(1)
build_context()             O(e+p)       O(e+p)
generate_section()          ~1s*         O(c)
calculate_score()           O(c)         O(1)
generate_suggestions()      O(c)         O(1)
────────────────────────────────────────────────

Legend:
n = number of examples in library
e = number of examples selected
p = number of patterns selected
c = character count of content
* = with LLM simulation, actual LLM call may vary
```

---

**Note:** This architecture is designed to be modular, extensible, and production-ready. The simulation layer can be easily replaced with real LLM calls without changing the overall structure.
