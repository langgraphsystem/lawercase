"""
Demo and Test Script for WriterAgent Few-Shot Learning Extension

Демонстрирует новый функционал:
- ExampleLibrary для хранения и выбора примеров
- SectionPatternLibrary для структурных паттернов
- agenerate_legal_section для генерации секций с few-shot learning
"""

from __future__ import annotations

import asyncio

from core.groupagents.writer_agent import WriterAgent


async def demo_basic_section_generation():
    """Базовая демонстрация генерации секции."""
    print("=" * 80)
    print("DEMO 1: Basic Legal Section Generation with Few-Shot Learning")
    print("=" * 80)

    # Инициализация WriterAgent
    writer = WriterAgent()

    # Данные клиента для awards секции
    client_data = {
        "beneficiary_name": "Dr. Elena Rodriguez",
        "field": "Computational Biology",
        "evidence": [
            {
                "title": "NIH Director's Pioneer Award",
                "description": "Received the prestigious NIH Director's Pioneer Award "
                "for groundbreaking research in computational genomics. "
                "This award is granted to fewer than 10 scientists annually "
                "from a pool of thousands of applicants worldwide.",
            },
            {
                "title": "Best Paper Award at ISMB Conference",
                "description": "Awarded Best Paper at the International Conference on "
                "Intelligent Systems for Molecular Biology (ISMB 2023), "
                "selected from over 800 submissions through rigorous peer review.",
            },
            {
                "title": "European Molecular Biology Organization Young Investigator Award",
                "description": "Received EMBO Young Investigator Award, recognizing "
                "exceptional early-career researchers in molecular life sciences. "
                "Fewer than 3% of nominees receive this distinction.",
            },
        ],
    }

    # Генерация секции
    section = await writer.agenerate_legal_section(
        section_type="awards",
        client_data=client_data,
        use_patterns=True,
        user_id="demo_user",
    )

    # Вывод результатов
    print(f"\n{'=' * 80}")
    print(f"Section Type: {section.section_type}")
    print(f"Title: {section.title}")
    print(f"{'=' * 80}\n")
    print(section.content)
    print(f"\n{'=' * 80}")
    print("Metadata:")
    print(f"  - Word Count: {section.word_count}")
    print(f"  - Confidence Score: {section.confidence_score:.2f}")
    print(f"  - Examples Used: {len(section.examples_used)}")
    print(f"  - Patterns Applied: {', '.join(section.patterns_applied)}")
    print("\nSuggestions for Improvement:")
    for i, suggestion in enumerate(section.suggestions, 1):
        print(f"  {i}. {suggestion}")
    print("=" * 80)

    return section


async def demo_multiple_section_types():
    """Демонстрация генерации разных типов секций."""
    print("\n\n" + "=" * 80)
    print("DEMO 2: Multiple Section Types Generation")
    print("=" * 80)

    writer = WriterAgent()

    section_types = ["awards", "press", "judging"]

    for section_type in section_types:
        print(f"\n\n{'=' * 80}")
        print(f"Generating {section_type.upper()} Section")
        print("=" * 80)

        # Общие данные
        client_data = {
            "beneficiary_name": "Prof. Michael Chen",
            "field": "Artificial Intelligence",
            "evidence": [
                {
                    "title": f"Evidence Item 1 for {section_type}",
                    "description": "Detailed description...",
                },
                {
                    "title": f"Evidence Item 2 for {section_type}",
                    "description": "Detailed description...",
                },
                {
                    "title": f"Evidence Item 3 for {section_type}",
                    "description": "Detailed description...",
                },
            ],
        }

        section = await writer.agenerate_legal_section(
            section_type=section_type, client_data=client_data, user_id="demo_user"
        )

        print(f"\n{section.title}")
        print(f"Confidence: {section.confidence_score:.2f} | Words: {section.word_count}")
        print("\nFirst 300 characters of content:")
        print(section.content[:300] + "...")


async def demo_add_custom_example():
    """Демонстрация добавления пользовательского примера."""
    print("\n\n" + "=" * 80)
    print("DEMO 3: Adding Custom Few-Shot Example")
    print("=" * 80)

    writer = WriterAgent()

    # Создаём новый высококачественный пример
    custom_example_data = {
        "section_type": "contributions",
        "criterion_name": "Original Contributions of Major Significance",
        "input_data": {
            "beneficiary": "Dr. Sarah Johnson",
            "field": "Renewable Energy",
            "contributions": [
                {
                    "title": "Revolutionary Solar Cell Design",
                    "impact": "30% efficiency improvement over existing technology",
                }
            ],
        },
        "generated_content": """**Original Contributions of Major Significance**

Dr. Johnson has made groundbreaking contributions to renewable energy through her
revolutionary solar cell design, which achieves a 30% efficiency improvement over
existing photovoltaic technology. This innovation has been recognized by leading
experts in the field and has been adopted by major solar manufacturers worldwide.

The significance of Dr. Johnson's contributions is evidenced by:

1. **Technological Impact:** The new design has enabled commercial solar installations
   to achieve unprecedented energy conversion rates, directly contributing to global
   renewable energy goals.

2. **Industry Adoption:** Within 18 months of publication, Dr. Johnson's design has
   been licensed by three Fortune 500 companies, demonstrating its practical value
   and commercial viability.

3. **Expert Recognition:** The contribution has been cited in over 200 peer-reviewed
   publications and has been featured in presentations at major international conferences.

**Conclusion**

Per 8 CFR § 204.5(h)(3)(v) and *Visinscaia v. Beers*, Dr. Johnson's contributions
constitute original work of major significance in renewable energy. The widespread
adoption and recognition by experts in the field clearly establish extraordinary ability.""",
        "quality_score": 0.95,
        "tags": ["contributions", "renewable_energy", "high_quality"],
    }

    # Добавляем пример в библиотеку
    example_id = await writer.aadd_example(custom_example_data, user_id="demo_user")

    print("\n✓ Custom example added successfully!")
    print(f"  Example ID: {example_id}")
    print(f"  Section Type: {custom_example_data['section_type']}")
    print(f"  Quality Score: {custom_example_data['quality_score']}")

    # Теперь используем этот пример при генерации
    print("\n\nGenerating new section using the custom example...")

    new_client_data = {
        "beneficiary_name": "Dr. Robert Kim",
        "field": "Quantum Computing",
        "evidence": [
            {
                "title": "Novel Quantum Error Correction Algorithm",
                "description": "Developed revolutionary algorithm reducing error rates by 40%",
            }
        ],
    }

    section = await writer.agenerate_legal_section(
        section_type="contributions",
        client_data=new_client_data,
        examples=[example_id],
        user_id="demo_user",
    )

    print(f"\n{'=' * 80}")
    print("Generated Section using Custom Example")
    print(f"{'=' * 80}")
    print(f"Confidence Score: {section.confidence_score:.2f}")
    print(f"Word Count: {section.word_count}")
    print("\nContent Preview (first 400 chars):")
    print(section.content[:400] + "...")


async def demo_library_statistics():
    """Демонстрация статистики библиотек."""
    print("\n\n" + "=" * 80)
    print("DEMO 4: Example Library Statistics")
    print("=" * 80)

    writer = WriterAgent()

    # Получаем статистику
    stats = await writer.get_stats()

    print("\nWriterAgent Statistics:")
    print(f"  Total Documents Generated: {stats['total_documents']}")
    print(f"  Total Sections Generated: {stats['total_sections_generated']}")
    print(f"  Total Templates: {stats['total_templates']}")
    print(f"  Pending Approvals: {stats['pending_approvals']}")

    print("\nExample Library Statistics:")
    example_stats = stats["example_library_stats"]
    print(f"  Total Examples: {example_stats['total_examples']}")
    print(f"  Average Quality: {example_stats['average_quality']:.2f}")

    print("\n  Examples by Type:")
    for section_type, count in example_stats["examples_by_type"].items():
        print(f"    - {section_type}: {count} examples")

    print("\n  Most Used Examples:")
    for i, example in enumerate(example_stats["most_used"][:3], 1):
        print(f"    {i}. {example.section_type} (used {example.usage_count} times)")


async def demo_pattern_based_generation():
    """Демонстрация генерации с акцентом на паттернах."""
    print("\n\n" + "=" * 80)
    print("DEMO 5: Pattern-Based Generation")
    print("=" * 80)

    writer = WriterAgent()

    # Получаем доступные паттерны для awards
    patterns = await writer._section_patterns.get_patterns("awards")

    print(f"\nAvailable Patterns for 'awards' section: {len(patterns)}")
    for pattern in patterns:
        print(f"\n  Pattern Type: {pattern.pattern_type}")
        print(f"  Applicable Sections: {', '.join(pattern.section_types)}")
        print(f"  Example Phrases: {len(pattern.example_phrases)}")
        print(f"  Legal Hints: {len(pattern.legal_language_hints)}")

    # Генерация с использованием паттернов
    client_data = {
        "beneficiary_name": "Dr. Lisa Anderson",
        "field": "Neuroscience",
        "evidence": [
            {
                "title": "MacArthur Fellowship (Genius Grant)",
                "description": "Awarded MacArthur Fellowship for exceptional creativity and potential",
            },
            {
                "title": "National Academy of Sciences Member",
                "description": "Elected to National Academy of Sciences, one of highest honors in science",
            },
        ],
    }

    section = await writer.agenerate_legal_section(
        section_type="awards", client_data=client_data, use_patterns=True, user_id="demo_user"
    )

    print(f"\n{'=' * 80}")
    print("Generated Section with Pattern Application")
    print(f"{'=' * 80}")
    print(f"\nPatterns Applied: {', '.join(section.patterns_applied)}")
    print(f"Confidence Score: {section.confidence_score:.2f}\n")
    print(section.content)


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("WriterAgent Few-Shot Learning Extension - Demo Suite")
    print("=" * 80)

    try:
        # Run demos sequentially
        await demo_basic_section_generation()
        await demo_multiple_section_types()
        await demo_add_custom_example()
        await demo_library_statistics()
        await demo_pattern_based_generation()

        print("\n\n" + "=" * 80)
        print("ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 80)

    except Exception as e:
        print(f"\n\n❌ Error during demo execution: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
