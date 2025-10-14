"""
LLM Integration Demo - All Providers (2025)

Demonstrates how to use all three LLM clients with latest models:
- Anthropic Claude (Sonnet 4.5, Opus 4.1, Haiku 3.5)
- OpenAI GPT (GPT-4.1, o3-mini, gpt-4o)
- Google Gemini (Gemini 2.5 Pro, Flash, Flash-Lite)

Requirements:
1. Set environment variables:
   - ANTHROPIC_API_KEY=your_key_here
   - OPENAI_API_KEY=your_key_here
   - GEMINI_API_KEY=your_key_here (or GOOGLE_API_KEY)

2. Install dependencies:
   pip install anthropic>=0.40.0 openai>=1.58.0 google-generativeai>=0.8.0
"""

from __future__ import annotations

import asyncio
import os

from core.llm_interface.anthropic_client import AnthropicClient
from core.llm_interface.gemini_client import GeminiClient
from core.llm_interface.openai_client import OpenAIClient


async def demo_anthropic_claude():
    """Demo: Anthropic Claude with multiple models"""
    print("\n" + "=" * 80)
    print("DEMO 1: Anthropic Claude API")
    print("=" * 80)

    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set. Skipping Anthropic demo.")
        return

    print("\n--- Model 1: Claude Sonnet 4.5 (Highest Intelligence) ---")
    try:
        client_sonnet = AnthropicClient(
            model=AnthropicClient.CLAUDE_SONNET_4_5,
            temperature=0.7,
            max_tokens=2048,
        )

        prompt = """Write a professional 200-word summary explaining what EB-1A visa is
        and why it's important for extraordinary ability individuals."""

        result = await client_sonnet.acomplete(prompt)

        print(f"✓ Model: {result['model']}")
        print(f"✓ Provider: {result['provider']}")
        print(f"✓ Finish Reason: {result.get('finish_reason', 'N/A')}")
        print(
            f"✓ Tokens (input/output): {result.get('usage', {}).get('input_tokens', 0)}/{result.get('usage', {}).get('output_tokens', 0)}"
        )
        print(f"\n📄 Generated Text:\n{result['output'][:500]}...")

    except Exception as e:
        print(f"❌ Error with Sonnet 4.5: {e}")

    print("\n--- Model 2: Claude Opus 4.1 (Complex Specialized Tasks) ---")
    try:
        client_opus = AnthropicClient(
            model=AnthropicClient.CLAUDE_OPUS_4_1,
            temperature=0.5,
            max_tokens=1024,
        )

        prompt = "List the 10 USCIS criteria for EB-1A visa in bullet points."

        result = await client_opus.acomplete(prompt)

        print(f"✓ Model: {result['model']}")
        print(
            f"✓ Tokens used: {result.get('usage', {}).get('input_tokens', 0) + result.get('usage', {}).get('output_tokens', 0)}"
        )
        print(f"\n📄 Response:\n{result['output'][:500]}...")

    except Exception as e:
        print(f"❌ Error with Opus 4.1: {e}")

    print("\n--- Model 3: Claude Haiku 3.5 (Fast & Cost-Efficient) ---")
    try:
        client_haiku = AnthropicClient(
            model=AnthropicClient.CLAUDE_HAIKU_3_5,
            temperature=0.3,
            max_tokens=512,
        )

        prompt = (
            "What is the difference between EB-1A, EB-1B, and EB-1C visas? Answer in 100 words."
        )

        result = await client_haiku.acomplete(prompt)

        print(f"✓ Model: {result['model']}")
        print("✓ Cost: $0.80/MTok input, $4/MTok output")
        print(f"\n📄 Response:\n{result['output']}")

    except Exception as e:
        print(f"❌ Error with Haiku 3.5: {e}")


async def demo_openai_gpt():
    """Demo: OpenAI GPT with multiple models"""
    print("\n" + "=" * 80)
    print("DEMO 2: OpenAI GPT API")
    print("=" * 80)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set. Skipping OpenAI demo.")
        return

    print("\n--- Model 1: GPT-4.1 (Latest with 1M context) ---")
    try:
        client_gpt41 = OpenAIClient(
            model=OpenAIClient.GPT_4_1,
            temperature=0.7,
            max_completion_tokens=2048,
            top_p=0.9,
        )

        prompt = """Generate a professional recommendation letter opening paragraph
        for an EB-1A petition in the field of artificial intelligence research."""

        result = await client_gpt41.acomplete(prompt)

        print(f"✓ Model: {result['model']}")
        print(f"✓ Provider: {result['provider']}")
        print(f"✓ Finish Reason: {result.get('finish_reason', 'N/A')}")
        print(
            f"✓ Tokens (prompt/completion/total): {result.get('usage', {}).get('prompt_tokens', 0)}/{result.get('usage', {}).get('completion_tokens', 0)}/{result.get('usage', {}).get('total_tokens', 0)}"
        )
        print(f"\n📄 Generated Text:\n{result['output']}")

    except Exception as e:
        print(f"❌ Error with GPT-4.1: {e}")

    print("\n--- Model 2: o3-mini (Reasoning Model with STEM focus) ---")
    try:
        client_o3 = OpenAIClient(
            model=OpenAIClient.O3_MINI,
            max_completion_tokens=1024,
            reasoning_effort="high",  # high reasoning for complex legal analysis
        )

        prompt = """Analyze: A researcher has 15 peer-reviewed publications with 500+ citations,
        2 patents, and serves as a reviewer for 3 top-tier journals. Which EB-1A criteria does this satisfy?"""

        result = await client_o3.acomplete(prompt)

        print(f"✓ Model: {result['model']} (Reasoning Model)")
        print("✓ Reasoning Effort: high")
        print("✓ Note: No temperature/top_p for reasoning models")
        print(f"\n📄 Analysis:\n{result['output'][:500]}...")

    except Exception as e:
        print(f"❌ Error with o3-mini: {e}")

    print("\n--- Model 3: GPT-4o-mini (Cost-Efficient Multimodal) ---")
    try:
        client_4o_mini = OpenAIClient(
            model=OpenAIClient.GPT_4O_MINI,
            temperature=0.5,
            max_completion_tokens=512,
            frequency_penalty=0.3,  # Reduce repetition
        )

        prompt = "List 5 USCIS-approved keywords for the 'Awards' criterion in EB-1A."

        result = await client_4o_mini.acomplete(prompt)

        print(f"✓ Model: {result['model']}")
        print("✓ Features: Text, vision, audio support")
        print(f"\n📄 Keywords:\n{result['output']}")

    except Exception as e:
        print(f"❌ Error with GPT-4o-mini: {e}")


async def demo_google_gemini():
    """Demo: Google Gemini with multiple models"""
    print("\n" + "=" * 80)
    print("DEMO 3: Google Gemini API")
    print("=" * 80)

    # Check API key
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        print("❌ GEMINI_API_KEY or GOOGLE_API_KEY not set. Skipping Gemini demo.")
        return

    print("\n--- Model 1: Gemini 2.5 Pro (Most Powerful, 1M context) ---")
    try:
        client_pro = GeminiClient(
            model=GeminiClient.GEMINI_2_5_PRO,
            temperature=0.8,
            max_output_tokens=2048,
            top_p=0.95,
            top_k=40,
        )

        prompt = """Create a 150-word paragraph explaining the 'Original Contribution'
        criterion for EB-1A visa, using USCIS-approved terminology."""

        result = await client_pro.acomplete(prompt)

        print(f"✓ Model: {result['model']}")
        print(f"✓ Provider: {result['provider']}")
        print("✓ Context: 1M tokens")
        print(f"✓ Finish Reason: {result.get('finish_reason', 'N/A')}")
        print(f"✓ Tokens: {result.get('usage', {}).get('total_tokens', 'N/A')}")
        print(f"\n📄 Generated Text:\n{result['output'][:500]}...")

    except Exception as e:
        print(f"❌ Error with Gemini 2.5 Pro: {e}")

    print("\n--- Model 2: Gemini 2.5 Flash (Best Price-Performance) ---")
    try:
        client_flash = GeminiClient(
            model=GeminiClient.GEMINI_2_5_FLASH,
            temperature=0.6,
            max_output_tokens=1024,
        )

        prompt = "What documents are typically required for an EB-1A petition? List 10 key items."

        result = await client_flash.acomplete(prompt)

        print(f"✓ Model: {result['model']}")
        print("✓ Best for: Large-scale processing, high throughput")
        print(f"\n📄 Document List:\n{result['output']}")

    except Exception as e:
        print(f"❌ Error with Gemini 2.5 Flash: {e}")

    print("\n--- Model 3: Gemini 2.5 Flash-Lite (Ultra Cost-Efficient) ---")
    try:
        client_lite = GeminiClient(
            model=GeminiClient.GEMINI_2_5_FLASH_LITE,
            temperature=0.4,
            max_output_tokens=512,
        )

        prompt = "What does 'sustained national acclaim' mean in EB-1A context? 50 words."

        result = await client_lite.acomplete(prompt)

        print(f"✓ Model: {result['model']}")
        print("✓ Best for: Cost efficiency, high throughput")
        print(f"\n📄 Definition:\n{result['output']}")

    except Exception as e:
        print(f"❌ Error with Gemini 2.5 Flash-Lite: {e}")


async def demo_eb1_document_generation():
    """Demo: Complete EB-1A document generation with LLM"""
    print("\n" + "=" * 80)
    print("DEMO 4: EB-1A Document Generation (Full Integration)")
    print("=" * 80)

    from core.groupagents.eb1_document_processor import EB1DocumentProcessor
    from core.groupagents.eb1_documents import RecommendationLetterData
    from core.groupagents.eb1_models import (
        EB1Criterion,
        EB1FieldOfExpertise,
        EB1PersonalInfo,
        EB1PetitionData,
        EB1PetitionStatus,
    )

    # Choose provider based on available API keys
    llm_client = None
    if os.getenv("ANTHROPIC_API_KEY"):
        print("✓ Using Anthropic Claude Sonnet 4.5 for document generation")
        llm_client = AnthropicClient(
            model=AnthropicClient.CLAUDE_SONNET_4_5, temperature=0.3, max_tokens=8192
        )
    elif os.getenv("OPENAI_API_KEY"):
        print("✓ Using OpenAI GPT-4.1 for document generation")
        llm_client = OpenAIClient(
            model=OpenAIClient.GPT_4_1, temperature=0.3, max_completion_tokens=8192
        )
    elif os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        print("✓ Using Google Gemini 2.5 Pro for document generation")
        llm_client = GeminiClient(
            model=GeminiClient.GEMINI_2_5_PRO, temperature=0.3, max_output_tokens=8192
        )
    else:
        print("❌ No LLM API keys found. Using template-based generation as fallback.")

    # Initialize document processor
    processor = EB1DocumentProcessor(llm_client=llm_client)

    # Create sample petition data
    petition = EB1PetitionData(
        petition_id="demo_petition_001",
        user_id="demo_user",
        status=EB1PetitionStatus.IN_PROGRESS,
        personal_info=EB1PersonalInfo(
            full_name="Dr. Jane Smith",
            date_of_birth="1985-03-15",
            country_of_birth="Canada",
            current_country="USA",
            email="jane.smith@example.com",
        ),
        field_of_expertise=EB1FieldOfExpertise(
            field="Artificial Intelligence Research",
            years_of_experience=12,
            specialization="Machine Learning for Healthcare",
        ),
        criteria_evidence={},
        criteria_met_count=0,
        eligibility_score=0.0,
    )

    # Create recommendation letter data
    letter_data = RecommendationLetterData(
        candidate_name="Dr. Jane Smith",
        candidate_field="Artificial Intelligence Research",
        recommender_name="Prof. Robert Johnson",
        recommender_title="Professor and Department Chair",
        recommender_organization="Stanford University",
        recommender_credentials="PhD in Computer Science, Fellow of ACM",
        recommender_relationship="PhD advisor and research collaborator",
        years_known=10,
        supporting_criteria=[EB1Criterion.CONTRIBUTION, EB1Criterion.SCHOLARLY],
        specific_achievements=[
            "Developed novel deep learning algorithm reducing medical diagnosis errors by 40%",
            "Published 25+ papers in top-tier venues (NeurIPS, ICML, Nature Medicine)",
            "Algorithm adopted by 15+ hospitals internationally",
        ],
        collaboration_examples=[
            "Co-authored 5 papers together on ML healthcare applications",
            "Joint grant: $2M NIH R01 on AI-assisted diagnosis",
        ],
        impact_statements=[
            "Her work has fundamentally changed how AI is applied in clinical settings",
            "Recognized globally as a leading expert in medical AI",
        ],
        keywords_for_criteria={
            "contribution": [
                "original contribution",
                "major significance",
                "widely adopted",
                "groundbreaking",
            ],
            "scholarly": [
                "scholarly articles",
                "peer-reviewed publications",
                "top-tier journals",
                "high citation count",
            ],
        },
    )

    print("\n--- Generating Recommendation Letter ---")
    print(f"Candidate: {letter_data.candidate_name}")
    print(f"Recommender: {letter_data.recommender_name} ({letter_data.recommender_title})")
    print(f"Supporting Criteria: {', '.join(c.value for c in letter_data.supporting_criteria)}")

    try:
        generated_doc = await processor.generate_recommendation_letter(letter_data, petition)

        print("\n✓ Document Generated Successfully!")
        print(f"✓ Document ID: {generated_doc.document_id}")
        print(f"✓ Template Used: {generated_doc.template_used}")
        print(f"✓ Generated at: {generated_doc.generated_at}")
        print("\n📄 Generated Letter (first 800 characters):")
        print("-" * 80)
        print(generated_doc.content[:800])
        print("-" * 80)
        print("... [truncated]")

    except Exception as e:
        print(f"❌ Error generating document: {e}")


async def main():
    """Run all demos"""
    print("🚀 LLM Integration Demo - All Providers (2025)")
    print("Python version: 3.11+")
    print("Required packages: anthropic>=0.40.0, openai>=1.58.0, google-generativeai>=0.8.0")

    # Run demos
    await demo_anthropic_claude()
    await demo_openai_gpt()
    await demo_google_gemini()
    await demo_eb1_document_generation()

    print("\n" + "=" * 80)
    print("✅ All demos completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
