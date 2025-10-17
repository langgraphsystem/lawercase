"""
Demo and Test Script for Evidence Researcher Extension

Demonstrates new web research functionality:
- OrganizationProfile research
- CompetitionStats research
- PublicationProfile research
- Evidence enrichment
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from core.memory.memory_manager import MemoryManager
from core.workflows.eb1a.eb1a_coordinator import (
    EB1ACriterion,
    EB1AEvidence,
    EvidenceType,
)
from core.workflows.eb1a.eb1a_workflow.evidence_researcher import (
    EvidenceResearcher,
)


async def demo_organization_research():
    """Demo: Research organization profile."""
    print("=" * 80)
    print("DEMO 1: Organization Profile Research")
    print("=" * 80)

    memory = MemoryManager()
    researcher = EvidenceResearcher(memory)

    # Research prestigious organizations
    organizations = [
        ("IEEE Computer Society", "professional organization computer science"),
        ("National Academy of Sciences", "scientific organization"),
        ("MacArthur Foundation", "fellowship foundation"),
    ]

    for org_name, context in organizations:
        print(f"\n\n{'=' * 80}")
        print(f"Researching: {org_name}")
        print("=" * 80)

        profile = await researcher.research_organization(org_name, context=context)

        print("\n📋 Organization Profile:")
        print(f"  Name: {profile.name}")
        print(f"  Founded: {profile.founded_year or 'Unknown'}")
        print(f"  Location: {profile.location or 'N/A'}")
        print(f"  Members: {profile.member_count or 'N/A'}")
        if profile.acceptance_rate:
            print(f"  Acceptance Rate: {profile.acceptance_rate:.1%}")
        print(f"  Website: {profile.website}")
        print("\n  Selectivity Indicators:")
        for indicator in profile.selectivity_indicators:
            print(f"    • {indicator}")

        prestige_score = profile.get_prestige_score()
        print(f"\n  ⭐ Prestige Score: {prestige_score:.2f}/1.00")

        if prestige_score >= 0.75:
            print("     → Highly prestigious organization!")
        elif prestige_score >= 0.60:
            print("     → Prestigious organization")
        else:
            print("     → Moderately prestigious")


async def demo_competition_research():
    """Demo: Research competition statistics."""
    print("\n\n" + "=" * 80)
    print("DEMO 2: Competition Statistics Research")
    print("=" * 80)

    memory = MemoryManager()
    researcher = EvidenceResearcher(memory)

    competitions = [
        ("Best Paper Award", 2023, "IEEE International Conference on Computer Vision"),
        ("Outstanding Dissertation Award", 2022, "ACM SIGKDD"),
        ("Young Investigator Award", 2023, "National Science Foundation"),
    ]

    for comp_name, year, context in competitions:
        print(f"\n\n{'=' * 80}")
        print(f"Researching: {comp_name} ({year})")
        print("=" * 80)

        stats = await researcher.research_competition_stats(comp_name, year, context=context)

        print("\n🏆 Competition Statistics:")
        print(f"  Competition: {stats.competition_name}")
        print(f"  Year: {stats.year}")
        print(f"  Organizing Body: {stats.organizing_body}")
        print(f"  Geographic Scope: {stats.geographic_scope}")

        if stats.total_entries:
            print(f"  Total Entries: {stats.total_entries:,}")
        if stats.total_winners:
            print(f"  Total Winners: {stats.total_winners}")
        if stats.acceptance_rate:
            print(f"  Acceptance Rate: {stats.acceptance_rate:.2%}")

        print("\n  Selection Criteria:")
        for criterion in stats.selection_criteria:
            print(f"    • {criterion}")

        comp_score = stats.get_competitiveness_score()
        print(f"\n  🎯 Competitiveness Score: {comp_score:.2f}/1.00")

        if comp_score >= 0.80:
            print("     → Highly competitive award!")
        elif comp_score >= 0.65:
            print("     → Competitive award")
        else:
            print("     → Moderately competitive")


async def demo_publication_research():
    """Demo: Research publication profiles."""
    print("\n\n" + "=" * 80)
    print("DEMO 3: Publication Profile Research")
    print("=" * 80)

    memory = MemoryManager()
    researcher = EvidenceResearcher(memory)

    publications = [
        ("Nature", "journal"),
        ("Science", "journal"),
        ("IEEE Conference on Computer Vision and Pattern Recognition", "conference"),
    ]

    for pub_name, pub_type in publications:
        print(f"\n\n{'=' * 80}")
        print(f"Researching: {pub_name}")
        print("=" * 80)

        profile = await researcher.research_publication(pub_name, publication_type=pub_type)

        print("\n📚 Publication Profile:")
        print(f"  Name: {profile.name}")
        print(f"  Type: {profile.publication_type}")

        if profile.impact_factor:
            print(f"  Impact Factor: {profile.impact_factor:.2f}")
        if profile.h5_index:
            print(f"  h5-index: {profile.h5_index}")
        if profile.circulation:
            print(f"  Circulation: {profile.circulation:,}")

        print(f"  Geographic Reach: {profile.geographic_reach}")

        if profile.ranking:
            print(f"  Ranking: {profile.ranking}")


async def demo_evidence_enrichment():
    """Demo: Enrich evidence with research."""
    print("\n\n" + "=" * 80)
    print("DEMO 4: Evidence Enrichment with Research")
    print("=" * 80)

    memory = MemoryManager()
    researcher = EvidenceResearcher(memory)

    # Create sample evidence items
    evidence_items = [
        EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="Best Paper Award",
            description="Received Best Paper Award at IEEE Conference on Computer Vision 2023. "
            "Selected from over 800 submissions.",
            source="IEEE ICCV 2023",
            date=datetime(2023, 10, 15),
        ),
        EB1AEvidence(
            criterion=EB1ACriterion.MEMBERSHIP,
            evidence_type=EvidenceType.MEMBERSHIP_LETTER,
            title="Fellow of ACM",
            description="Elected as Fellow of the Association for Computing Machinery (ACM). "
            "Member of ACM since 2010.",
            source="ACM",
            date=datetime(2023, 1, 1),
        ),
        EB1AEvidence(
            criterion=EB1ACriterion.PRESS,
            evidence_type=EvidenceType.PRESS_ARTICLE,
            title="Breakthrough in AI Research",
            description="Featured article in Scientific American about groundbreaking AI research. "
            "Published in Scientific American in June 2023.",
            source="Scientific American",
            date=datetime(2023, 6, 1),
        ),
    ]

    for i, evidence in enumerate(evidence_items, 1):
        print(f"\n\n{'=' * 80}")
        print(f"Evidence Item {i}: {evidence.title}")
        print("=" * 80)

        print("\n📄 Original Evidence:")
        print(f"  Criterion: {evidence.criterion.value}")
        print(f"  Title: {evidence.title}")
        print(f"  Description: {evidence.description[:100]}...")
        print(f"  Metadata: {len(evidence.metadata)} keys")

        # Enrich with research
        print("\n🔍 Enriching with research...")
        enriched = await researcher.enrich_evidence_with_research(evidence)

        print("\n✨ Enriched Evidence:")
        print(f"  Metadata: {len(enriched.metadata)} keys")

        # Display enriched data
        if "competition_stats" in enriched.metadata:
            stats_data = enriched.metadata["competition_stats"]
            print("\n  📊 Competition Stats:")
            print(
                f"    - Competitiveness Score: {enriched.metadata.get('competitiveness_score', 'N/A'):.2f}"
            )
            if stats_data.get("acceptance_rate"):
                print(f"    - Acceptance Rate: {stats_data['acceptance_rate']:.2%}")
            if stats_data.get("total_entries"):
                print(f"    - Total Entries: {stats_data['total_entries']:,}")

        if "organization_profile" in enriched.metadata:
            org_data = enriched.metadata["organization_profile"]
            print("\n  🏢 Organization Profile:")
            print(f"    - Prestige Score: {enriched.metadata.get('prestige_score', 'N/A'):.2f}")
            if org_data.get("founded_year"):
                print(f"    - Founded: {org_data['founded_year']}")
            if org_data.get("acceptance_rate"):
                print(f"    - Acceptance Rate: {org_data['acceptance_rate']:.1%}")

        if "publication_profile" in enriched.metadata:
            pub_data = enriched.metadata["publication_profile"]
            print("\n  📖 Publication Profile:")
            if pub_data.get("impact_factor"):
                print(f"    - Impact Factor: {pub_data['impact_factor']:.2f}")
            if pub_data.get("circulation"):
                print(f"    - Circulation: {pub_data['circulation']:,}")


async def demo_comprehensive_research_workflow():
    """Demo: Complete research workflow."""
    print("\n\n" + "=" * 80)
    print("DEMO 5: Comprehensive Research Workflow")
    print("=" * 80)

    memory = MemoryManager()
    researcher = EvidenceResearcher(memory)

    print("\n📋 Scenario: Researching evidence for Awards criterion")
    print("\n  Beneficiary: Dr. Jane Smith")
    print("  Award: IEEE Outstanding Achievement Award")
    print("  Organization: IEEE Computer Society")
    print("  Year: 2023")

    # Step 1: Research the awarding organization
    print("\n\n" + "-" * 80)
    print("Step 1: Research Awarding Organization")
    print("-" * 80)

    org_profile = await researcher.research_organization(
        "IEEE Computer Society", context="professional organization computer science engineering"
    )

    print("\n✓ Organization researched:")
    print(f"  - Founded: {org_profile.founded_year}")
    print(f"  - Members: {org_profile.member_count or 'N/A'}")
    print(f"  - Prestige Score: {org_profile.get_prestige_score():.2f}")

    # Step 2: Research competition statistics
    print("\n\n" + "-" * 80)
    print("Step 2: Research Award Statistics")
    print("-" * 80)

    comp_stats = await researcher.research_competition_stats(
        "IEEE Outstanding Achievement Award", year=2023, context="IEEE Computer Society"
    )

    print("\n✓ Competition statistics:")
    print(f"  - Geographic Scope: {comp_stats.geographic_scope}")
    if comp_stats.acceptance_rate:
        print(f"  - Acceptance Rate: {comp_stats.acceptance_rate:.2%}")
    print(f"  - Competitiveness Score: {comp_stats.get_competitiveness_score():.2f}")

    # Step 3: Create comprehensive evidence
    print("\n\n" + "-" * 80)
    print("Step 3: Create Comprehensive Evidence Package")
    print("-" * 80)

    evidence = EB1AEvidence(
        criterion=EB1ACriterion.AWARDS,
        evidence_type=EvidenceType.AWARD_CERTIFICATE,
        title="IEEE Outstanding Achievement Award",
        description=(
            "Received the prestigious IEEE Outstanding Achievement Award from the "
            "IEEE Computer Society in 2023. This award recognizes exceptional contributions "
            "to the field of computer science and engineering."
        ),
        source="IEEE Computer Society",
        date=datetime(2023, 11, 1),
        metadata={
            "organization": "IEEE Computer Society",
            "organization_profile": org_profile.model_dump(),
            "competition_stats": comp_stats.model_dump(),
            "prestige_score": org_profile.get_prestige_score(),
            "competitiveness_score": comp_stats.get_competitiveness_score(),
        },
    )

    print("\n✓ Comprehensive evidence created:")
    print(f"  - Title: {evidence.title}")
    print(f"  - Criterion: {evidence.criterion.value}")
    print(f"  - Metadata keys: {len(evidence.metadata)}")
    print("\n  Strength Indicators:")
    print(f"    • Organization Prestige: {evidence.metadata['prestige_score']:.2f}/1.00")
    print(f"    • Award Competitiveness: {evidence.metadata['competitiveness_score']:.2f}/1.00")

    overall_strength = (
        evidence.metadata["prestige_score"] + evidence.metadata["competitiveness_score"]
    ) / 2

    print(f"\n  🎯 Overall Strength Score: {overall_strength:.2f}/1.00")

    if overall_strength >= 0.75:
        print("     ✓ STRONG evidence - highly likely to meet criterion")
    elif overall_strength >= 0.60:
        print("     ✓ GOOD evidence - should meet criterion")
    else:
        print("     ⚠ MODERATE evidence - consider strengthening")


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("Evidence Researcher Extension - Demo Suite")
    print("=" * 80)

    try:
        await demo_organization_research()
        await demo_competition_research()
        await demo_publication_research()
        await demo_evidence_enrichment()
        await demo_comprehensive_research_workflow()

        print("\n\n" + "=" * 80)
        print("ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 80)

        print("\n\n📚 Summary of Capabilities:")
        print("\n1. Organization Research:")
        print("   - Founded year, location, members")
        print("   - Prestige scoring (0.0-1.0)")
        print("   - Selectivity indicators")

        print("\n2. Competition Statistics:")
        print("   - Entry counts and acceptance rates")
        print("   - Competitiveness scoring (0.0-1.0)")
        print("   - Geographic scope determination")

        print("\n3. Publication Profiles:")
        print("   - Impact factor, h-index")
        print("   - Circulation and reach")
        print("   - Ranking information")

        print("\n4. Evidence Enrichment:")
        print("   - Automatic research type detection")
        print("   - Metadata enrichment")
        print("   - Strength scoring")

        print("\n5. Comprehensive Workflows:")
        print("   - Multi-step research processes")
        print("   - Combined strength assessment")
        print("   - Evidence package creation")

        print("\n" + "=" * 80)
        print("🔄 Integration Points:")
        print("=" * 80)

        print("\nReady for:")
        print("  • Web Search API integration (Google/Bing/DuckDuckGo)")
        print("  • LLM-based data extraction (GPT-4/Claude)")
        print("  • Scraping with Beautiful Soup")
        print("  • Named Entity Recognition")
        print("  • Structured data extraction")

        print("\nTo enable real web search:")
        print("  1. Replace _simulate_web_search() with real API calls")
        print("  2. Integrate LLM for extraction in _extract_org_profile()")
        print("  3. Add API keys to configuration")

    except Exception as e:
        print(f"\n\n❌ Error during demo execution: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
