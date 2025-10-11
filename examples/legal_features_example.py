"""Legal Features Example.

Demonstrates the legal document processing capabilities.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from core.legal import (
    CaseLawSearch,
    CitationExtractor,
    ComplianceChecker,
    ComplianceStandard,
    ContractAnalyzer,
    DocumentParser,
    LegalEntityRecognizer,
)


# Sample legal documents
SAMPLE_CONTRACT = """
SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into as of January 15, 2024,
between Acme Corporation Inc. ("Client") and Tech Solutions LLC ("Provider").

1. SERVICES
Provider shall provide software development services as described in Exhibit A.

2. PAYMENT TERMS
Client agrees to pay Provider $50,000.00 upon execution of this Agreement,
and $25,000.00 monthly thereafter. Payment is due within 30 days of invoice.

3. TERM AND TERMINATION
This Agreement shall commence on the Effective Date and continue for twelve (12)
months. Either party may terminate this Agreement without cause upon thirty (30)
days written notice.

4. CONFIDENTIALITY
Each party agrees to maintain the confidentiality of all Proprietary Information
disclosed by the other party during the term of this Agreement.

5. INTELLECTUAL PROPERTY
All work product created by Provider shall be the exclusive property of Client
upon full payment.

6. LIMITATION OF LIABILITY
In no event shall either party be liable for any indirect, incidental, special,
or consequential damages arising out of this Agreement.

7. INDEMNIFICATION
Each party shall indemnify and hold harmless the other party from any claims
arising from its breach of this Agreement.

8. GOVERNING LAW
This Agreement shall be governed by the laws of the State of California.

9. ENTIRE AGREEMENT
This Agreement constitutes the entire agreement between the parties and supersedes
all prior agreements and understandings.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first
written above.
"""

SAMPLE_PRIVACY_POLICY = """
PRIVACY POLICY

Effective Date: January 1, 2024

1. DATA COLLECTION
We collect personal information including name, email address, and usage data.

2. USE OF INFORMATION
We use your personal information to provide and improve our services.

3. DATA SHARING
We do not sell your personal information to third parties. We may share data
with service providers who assist us in operating our platform.

4. YOUR RIGHTS
You have the right to access your personal data. You have the right to request
deletion of your data. You have the right to opt-out of certain data uses.

5. DATA PORTABILITY
You may request a copy of your data in a machine-readable format.

6. COOKIES
We use cookies to enhance your experience on our website.

7. SECURITY
We implement appropriate technical and organizational measures to protect
your personal information.

8. CONTACT
For questions about this policy, contact our Data Protection Officer at
privacy@example.com.
"""


def demonstrate_document_parsing():
    """Demonstrate document parsing."""
    print("=" * 80)
    print("1. DOCUMENT PARSING")
    print("=" * 80)

    parser = DocumentParser()

    # Parse contract
    print("\n📄 Parsing Service Agreement...")
    contract_doc = parser.parse(SAMPLE_CONTRACT, doc_id="contract_001")

    print(f"   Title: {contract_doc.title}")
    print(f"   Type: {contract_doc.doc_type.value}")
    print(f"   Sections: {len(contract_doc.sections)}")
    print(f"   Parties: {', '.join(contract_doc.parties)}")
    print(f"   Effective Date: {contract_doc.effective_date}")
    print(f"   Jurisdiction: {contract_doc.jurisdiction}")

    # Show sections
    if contract_doc.sections:
        print("\n   Sections:")
        for section in contract_doc.sections[:5]:
            print(f"     {section.section_number}. {section.title}")

    return contract_doc


def demonstrate_contract_analysis(contract_doc):
    """Demonstrate contract analysis."""
    print("\n" + "=" * 80)
    print("2. CONTRACT ANALYSIS")
    print("=" * 80)

    analyzer = ContractAnalyzer()

    print("\n⚖️  Analyzing contract...")
    result = analyzer.analyze(contract_doc)

    print(f"\n   Overall Risk Score: {result.overall_risk_score:.1f}/100")
    print(f"   Clauses Identified: {len(result.clauses)}")

    # Show clause breakdown
    print("\n   Clause Types:")
    clause_types = {}
    for clause in result.clauses:
        clause_types[clause.clause_type.value] = (
            clause_types.get(clause.clause_type.value, 0) + 1
        )

    for clause_type, count in clause_types.items():
        print(f"     - {clause_type}: {count}")

    # Show high-risk clauses
    high_risk = result.get_high_risk_clauses()
    if high_risk:
        print(f"\n   ⚠️  High-Risk Clauses ({len(high_risk)}):")
        for clause in high_risk:
            print(f"     - {clause.title}")
            print(f"       Risk Level: {clause.risk_level.value}")
            for risk in clause.risks:
                print(f"       • {risk}")

    # Show obligations
    if result.obligations:
        print(f"\n   📋 Key Obligations ({len(result.obligations)}):")
        for obligation in result.obligations[:5]:
            print(f"     • {obligation[:80]}...")

    # Show payment terms
    if result.payment_terms.get("amounts"):
        print(f"\n   💰 Payment Terms:")
        print(f"     Amounts: {', '.join(result.payment_terms['amounts'][:3])}")
        if result.payment_terms.get("schedule"):
            print(f"     Schedule: {result.payment_terms['schedule'][:60]}...")

    # Show recommendations
    if result.recommendations:
        print(f"\n   💡 Recommendations ({len(result.recommendations)}):")
        for rec in result.recommendations[:5]:
            print(f"     • {rec}")


def demonstrate_compliance_checking():
    """Demonstrate compliance checking."""
    print("\n" + "=" * 80)
    print("3. COMPLIANCE CHECKING")
    print("=" * 80)

    parser = DocumentParser()
    checker = ComplianceChecker()

    # Parse privacy policy
    print("\n📋 Parsing Privacy Policy...")
    privacy_doc = parser.parse(
        SAMPLE_PRIVACY_POLICY,
        doc_id="privacy_001",
    )

    # Check GDPR compliance
    print("\n🔍 Checking GDPR Compliance...")
    gdpr_result = checker.check_compliance(privacy_doc, ComplianceStandard.GDPR)

    print(f"   Status: {gdpr_result.status.value}")
    print(f"   Compliance Score: {gdpr_result.compliance_score:.1f}%")
    print(f"   Rules Passed: {len(gdpr_result.passed_rules)}")
    print(f"   Rules Failed: {len(gdpr_result.failed_rules)}")

    if gdpr_result.failed_rules:
        print(f"\n   ❌ Failed Rules:")
        for rule_id in gdpr_result.failed_rules:
            print(f"     - {rule_id}")

    if gdpr_result.warnings:
        print(f"\n   ⚠️  Warnings:")
        for warning in gdpr_result.warnings[:5]:
            print(f"     • {warning}")

    if gdpr_result.recommendations:
        print(f"\n   💡 Recommendations:")
        for rec in gdpr_result.recommendations[:5]:
            print(f"     • {rec}")

    # Check CCPA compliance
    print("\n🔍 Checking CCPA Compliance...")
    ccpa_result = checker.check_compliance(privacy_doc, ComplianceStandard.CCPA)

    print(f"   Status: {ccpa_result.status.value}")
    print(f"   Compliance Score: {ccpa_result.compliance_score:.1f}%")
    print(f"   Rules Passed: {len(ccpa_result.passed_rules)}")
    print(f"   Rules Failed: {len(ccpa_result.failed_rules)}")


def demonstrate_citation_extraction():
    """Demonstrate citation extraction."""
    print("\n" + "=" * 80)
    print("4. CITATION EXTRACTION")
    print("=" * 80)

    sample_text = """
    In Smith v. Jones, 123 F.3d 456 (9th Cir. 1995), the court held that
    the defendant violated 42 U.S.C. § 1983. This was consistent with
    earlier precedent in Brown v. Board of Education, 347 U.S. 483 (1954).
    The statute at issue, 15 USC 78, governs securities law.
    """

    extractor = CitationExtractor()

    print("\n📚 Extracting citations from text...")
    citations = extractor.extract(sample_text)

    print(f"   Found {len(citations)} citations:\n")

    for i, citation in enumerate(citations, 1):
        print(f"   {i}. {citation.citation_text}")
        print(f"      Type: {citation.citation_type.value}")
        if citation.volume:
            print(f"      Volume: {citation.volume}")
        if citation.reporter:
            print(f"      Reporter: {citation.reporter}")
        if citation.page:
            print(f"      Page: {citation.page}")
        print()


def demonstrate_entity_recognition():
    """Demonstrate legal entity recognition."""
    print("\n" + "=" * 80)
    print("5. LEGAL ENTITY RECOGNITION")
    print("=" * 80)

    sample_text = """
    The Supreme Court ruled in favor of the plaintiff. The District Court
    for the Southern District of New York had previously dismissed the case.
    The Employment Agreement between the parties contained a Non-Disclosure
    Agreement clause. The matter is governed by 42 U.S.C. § 1983.
    """

    recognizer = LegalEntityRecognizer()

    print("\n🔍 Recognizing legal entities...")
    entities = recognizer.recognize(sample_text)

    print(f"   Found {len(entities)} legal entities:\n")

    # Group by type
    by_type: dict[str, list[str]] = {}
    for entity in entities:
        entity_type = entity.entity_type.value
        if entity_type not in by_type:
            by_type[entity_type] = []
        by_type[entity_type].append(entity.text)

    for entity_type, entity_list in by_type.items():
        print(f"   {entity_type.upper()}:")
        for entity_text in entity_list:
            print(f"     • {entity_text}")


async def demonstrate_case_law_search():
    """Demonstrate case law search."""
    print("\n" + "=" * 80)
    print("6. CASE LAW SEARCH")
    print("=" * 80)

    search = CaseLawSearch()

    print("\n🔎 Searching case law...")
    print("   Query: 'contract breach damages'")
    print("   Jurisdiction: California")

    results = await search.search(
        query="contract breach damages",
        jurisdiction="California",
        limit=5,
    )

    print(f"\n   Found {len(results)} results")
    print("   (Note: Requires integration with case law API)")


def demonstrate_document_summary():
    """Show summary of capabilities."""
    print("\n" + "=" * 80)
    print("7. LEGAL FEATURES SUMMARY")
    print("=" * 80)

    capabilities = [
        ("📄 Document Parsing", "Extract structure from legal documents"),
        ("⚖️ Contract Analysis", "Analyze contracts for risks and obligations"),
        ("📋 Compliance Checking", "Check GDPR, CCPA, HIPAA compliance"),
        ("📚 Citation Extraction", "Extract and parse legal citations"),
        ("🔍 Entity Recognition", "Recognize legal-specific entities"),
        ("🔎 Case Law Search", "Search case law databases"),
    ]

    print("\n   Available Features:")
    for feature, description in capabilities:
        print(f"   {feature}")
        print(f"     {description}")

    print("\n   Supported Document Types:")
    doc_types = [
        "Contracts",
        "Privacy Policies",
        "Terms of Service",
        "Employment Agreements",
        "NDAs",
        "Court Filings",
        "And more...",
    ]
    for doc_type in doc_types:
        print(f"     • {doc_type}")


async def main():
    """Run all demonstrations."""
    print("\n" + "=" * 80)
    print("LEGAL FEATURES DEMONSTRATION")
    print("=" * 80)

    # 1. Document parsing
    contract_doc = demonstrate_document_parsing()

    # 2. Contract analysis
    demonstrate_contract_analysis(contract_doc)

    # 3. Compliance checking
    demonstrate_compliance_checking()

    # 4. Citation extraction
    demonstrate_citation_extraction()

    # 5. Entity recognition
    demonstrate_entity_recognition()

    # 6. Case law search
    await demonstrate_case_law_search()

    # 7. Summary
    demonstrate_document_summary()

    print("\n" + "=" * 80)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
