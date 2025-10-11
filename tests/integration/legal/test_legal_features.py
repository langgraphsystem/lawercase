"""Integration tests for Legal Features."""

from __future__ import annotations

from core.legal import (
    CitationExtractor,
    CitationType,
    ComplianceChecker,
    ComplianceStandard,
    ComplianceStatus,
    ContractAnalyzer,
    DocumentParser,
    LegalDocumentType,
    LegalEntityRecognizer,
    LegalEntityType,
)

SAMPLE_CONTRACT = """
SERVICE AGREEMENT

Effective Date: January 15, 2024
Between Acme Corporation ("Client") and Tech Solutions LLC ("Provider").

1. SERVICES
Provider shall provide consulting services.

2. PAYMENT TERMS
Client agrees to pay $10,000 monthly.

3. TERMINATION
Either party may terminate without cause upon 30 days notice.

4. CONFIDENTIALITY
Parties agree to maintain confidentiality of proprietary information.

5. LIABILITY
Liability shall be limited to fees paid in the preceding 12 months.

6. GOVERNING LAW
This Agreement shall be governed by the laws of California.
"""


class TestDocumentParser:
    """Test DocumentParser."""

    def test_parse_contract(self):
        """Test parsing a contract."""
        parser = DocumentParser()
        doc = parser.parse(SAMPLE_CONTRACT, doc_id="test_001")

        assert doc.doc_id == "test_001"
        assert doc.doc_type in [
            LegalDocumentType.CONTRACT,
            LegalDocumentType.AGREEMENT,
        ]
        assert len(doc.sections) > 0
        assert len(doc.parties) > 0

    def test_extract_parties(self):
        """Test party extraction."""
        parser = DocumentParser()
        doc = parser.parse(SAMPLE_CONTRACT)

        assert len(doc.parties) >= 2
        # Should extract company names
        party_names = " ".join(doc.parties).lower()
        assert "acme" in party_names or "tech" in party_names

    def test_extract_sections(self):
        """Test section extraction."""
        parser = DocumentParser()
        doc = parser.parse(SAMPLE_CONTRACT)

        assert len(doc.sections) >= 3
        # Check section structure
        for section in doc.sections:
            assert section.section_number
            assert section.title
            assert section.content

    def test_detect_document_type(self):
        """Test document type detection."""
        parser = DocumentParser()

        contract_text = "SERVICE AGREEMENT between parties..."
        doc = parser.parse(contract_text)
        assert doc.doc_type in [
            LegalDocumentType.CONTRACT,
            LegalDocumentType.AGREEMENT,
        ]

        nda_text = "NON-DISCLOSURE AGREEMENT for confidential information..."
        doc = parser.parse(nda_text)
        assert doc.doc_type == LegalDocumentType.NDA

    def test_extract_dates(self):
        """Test date extraction."""
        parser = DocumentParser()
        doc = parser.parse(SAMPLE_CONTRACT)

        assert doc.effective_date is not None


class TestContractAnalyzer:
    """Test ContractAnalyzer."""

    def test_analyze_contract(self):
        """Test basic contract analysis."""
        parser = DocumentParser()
        analyzer = ContractAnalyzer()

        doc = parser.parse(SAMPLE_CONTRACT, doc_id="test_001")
        result = analyzer.analyze(doc)

        assert result.document == doc
        assert len(result.clauses) > 0
        assert 0 <= result.overall_risk_score <= 100

    def test_extract_clauses(self):
        """Test clause extraction."""
        parser = DocumentParser()
        analyzer = ContractAnalyzer()

        doc = parser.parse(SAMPLE_CONTRACT)
        result = analyzer.analyze(doc)

        # Should find common clause types
        clause_types = {c.clause_type for c in result.clauses}
        assert len(clause_types) > 0

    def test_risk_assessment(self):
        """Test risk assessment."""
        parser = DocumentParser()
        analyzer = ContractAnalyzer()

        doc = parser.parse(SAMPLE_CONTRACT)
        result = analyzer.analyze(doc)

        # Check risk scoring
        assert isinstance(result.overall_risk_score, float)
        assert 0 <= result.overall_risk_score <= 100

        # Check if clauses have risk levels
        for clause in result.clauses:
            assert clause.risk_level

    def test_extract_obligations(self):
        """Test obligation extraction."""
        parser = DocumentParser()
        analyzer = ContractAnalyzer()

        doc = parser.parse(SAMPLE_CONTRACT)
        result = analyzer.analyze(doc)

        # Should extract some obligations
        assert isinstance(result.obligations, list)

    def test_extract_payment_terms(self):
        """Test payment terms extraction."""
        parser = DocumentParser()
        analyzer = ContractAnalyzer()

        doc = parser.parse(SAMPLE_CONTRACT)
        result = analyzer.analyze(doc)

        # Should extract payment amounts
        assert "amounts" in result.payment_terms
        assert isinstance(result.payment_terms["amounts"], list)

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        parser = DocumentParser()
        analyzer = ContractAnalyzer()

        doc = parser.parse(SAMPLE_CONTRACT)
        result = analyzer.analyze(doc)

        assert isinstance(result.recommendations, list)


class TestComplianceChecker:
    """Test ComplianceChecker."""

    def test_check_gdpr_compliance(self):
        """Test GDPR compliance check."""
        privacy_policy = """
        PRIVACY POLICY

        Right to Access: You have the right to access your personal data.
        Right to Erasure: You have the right to be forgotten and delete your data.
        Data Portability: You can transfer your data to another service.
        Lawful Basis: We process data based on your consent.
        """

        parser = DocumentParser()
        checker = ComplianceChecker()

        doc = parser.parse(privacy_policy)
        result = checker.check_compliance(doc, ComplianceStandard.GDPR)

        assert result.standard == ComplianceStandard.GDPR
        assert result.status in list(ComplianceStatus)
        assert 0 <= result.compliance_score <= 100
        assert len(result.passed_rules) > 0

    def test_check_ccpa_compliance(self):
        """Test CCPA compliance check."""
        privacy_policy = """
        PRIVACY POLICY

        Right to Know: We disclose what personal information we collect.
        Right to Delete: You may request deletion of your data.
        Do Not Sell: You can opt-out of the sale of personal information.
        Non-Discrimination: We will not discriminate against you.
        """

        parser = DocumentParser()
        checker = ComplianceChecker()

        doc = parser.parse(privacy_policy)
        result = checker.check_compliance(doc, ComplianceStandard.CCPA)

        assert result.standard == ComplianceStandard.CCPA
        assert 0 <= result.compliance_score <= 100
        assert len(result.passed_rules) > 0

    def test_missing_requirements(self):
        """Test detection of missing requirements."""
        minimal_policy = """
        PRIVACY POLICY

        We collect data.
        """

        parser = DocumentParser()
        checker = ComplianceChecker()

        doc = parser.parse(minimal_policy)
        result = checker.check_compliance(doc, ComplianceStandard.GDPR)

        # Should have failed rules
        assert len(result.failed_rules) > 0
        assert len(result.warnings) > 0
        assert len(result.missing_elements) > 0

    def test_compliance_recommendations(self):
        """Test compliance recommendations."""
        parser = DocumentParser()
        checker = ComplianceChecker()

        doc = parser.parse("PRIVACY POLICY\n\nWe collect data.")
        result = checker.check_compliance(doc, ComplianceStandard.GDPR)

        # Should generate recommendations
        assert len(result.recommendations) > 0


class TestCitationExtractor:
    """Test CitationExtractor."""

    def test_extract_case_citations(self):
        """Test case citation extraction."""
        text = """
        In Smith v. Jones, 123 F.3d 456, the court ruled...
        See also Brown v. Board, 347 U.S. 483 (1954).
        """

        extractor = CitationExtractor()
        citations = extractor.extract(text)

        assert len(citations) > 0
        # Check if case citations found
        case_citations = [c for c in citations if c.citation_type == CitationType.CASE]
        assert len(case_citations) > 0

    def test_extract_statute_citations(self):
        """Test statute citation extraction."""
        text = """
        Violation of 42 U.S.C. § 1983 was alleged.
        The statute 15 USC 78 governs this matter.
        """

        extractor = CitationExtractor()
        citations = extractor.extract(text)

        statute_cites = [c for c in citations if c.citation_type == CitationType.STATUTE]
        assert len(statute_cites) > 0

    def test_citation_parsing(self):
        """Test citation detail parsing."""
        text = "123 F.3d 456"

        extractor = CitationExtractor()
        citations = extractor.extract(text)

        if citations:
            citation = citations[0]
            assert citation.volume == "123"
            assert citation.page == "456"


class TestLegalEntityRecognizer:
    """Test LegalEntityRecognizer."""

    def test_recognize_courts(self):
        """Test court entity recognition."""
        text = """
        The Supreme Court and the District Court heard the case.
        The Court of Appeals reversed the decision.
        """

        recognizer = LegalEntityRecognizer()
        entities = recognizer.recognize(text)

        court_entities = [e for e in entities if e.entity_type == LegalEntityType.COURT]
        assert len(court_entities) > 0

    def test_recognize_statutes(self):
        """Test statute entity recognition."""
        text = "Pursuant to 42 U.S.C. and Title 15 regulations..."

        recognizer = LegalEntityRecognizer()
        entities = recognizer.recognize(text)

        statute_entities = [e for e in entities if e.entity_type == LegalEntityType.STATUTE]
        assert len(statute_entities) > 0

    def test_recognize_contract_types(self):
        """Test contract type recognition."""
        text = """
        The Employment Agreement and Non-Disclosure Agreement were signed.
        A License Agreement was also executed.
        """

        recognizer = LegalEntityRecognizer()
        entities = recognizer.recognize(text)

        contract_entities = [e for e in entities if e.entity_type == LegalEntityType.CONTRACT_TYPE]
        assert len(contract_entities) > 0

    def test_entity_positions(self):
        """Test entity position tracking."""
        text = "Supreme Court ruling"

        recognizer = LegalEntityRecognizer()
        entities = recognizer.recognize(text)

        if entities:
            entity = entities[0]
            assert entity.start >= 0
            assert entity.end > entity.start
            assert text[entity.start : entity.end].lower() in entity.text.lower()
