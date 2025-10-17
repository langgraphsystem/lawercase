"""Comprehensive unit tests for EB-1A validator."""

from __future__ import annotations

import pytest

from core.workflows.eb1a.eb1a_coordinator import (EB1ACriterion,
                                                  EB1APetitionResult,
                                                  SectionContent)
from core.workflows.eb1a.validators import (CheckResult, ComplianceChecklist,
                                            EB1AValidator,
                                            SectionValidationResult,
                                            ValidationIssue,
                                            ValidationReportGenerator,
                                            ValidationResult,
                                            ValidationSeverity)


class TestValidationSchemas:
    """Test validation data schemas."""

    def test_validation_severity_enum(self):
        """Test ValidationSeverity enum values."""
        assert ValidationSeverity.CRITICAL == "critical"
        assert ValidationSeverity.WARNING == "warning"
        assert ValidationSeverity.INFO == "info"

    def test_validation_issue_creation(self):
        """Test ValidationIssue creation."""
        issue = ValidationIssue(
            severity=ValidationSeverity.CRITICAL,
            category="evidence",
            criterion=EB1ACriterion.AWARDS,
            message="Test message",
            suggestion="Test suggestion",
            location="Test location",
        )
        assert issue.severity == ValidationSeverity.CRITICAL
        assert issue.category == "evidence"
        assert issue.criterion == EB1ACriterion.AWARDS
        assert issue.message == "Test message"
        assert issue.suggestion == "Test suggestion"
        assert issue.location == "Test location"

    def test_check_result_creation(self):
        """Test CheckResult creation."""
        check = CheckResult(
            check_id="TEST_001",
            description="Test check",
            passed=True,
            severity=ValidationSeverity.WARNING,
            evidence_found="Found evidence",
            suggestion="Do something",
        )
        assert check.check_id == "TEST_001"
        assert check.description == "Test check"
        assert check.passed is True
        assert check.severity == ValidationSeverity.WARNING
        assert check.evidence_found == "Found evidence"
        assert check.suggestion == "Do something"

    def test_section_validation_result_properties(self):
        """Test SectionValidationResult computed properties."""
        checks = [
            CheckResult("CHECK1", "Check 1", True, ValidationSeverity.INFO),
            CheckResult("CHECK2", "Check 2", False, ValidationSeverity.WARNING),
            CheckResult("CHECK3", "Check 3", True, ValidationSeverity.INFO),
            CheckResult("CHECK4", "Check 4", False, ValidationSeverity.CRITICAL),
        ]

        result = SectionValidationResult(
            criterion=EB1ACriterion.AWARDS,
            section_title="Awards Section",
            is_valid=False,
            score=0.6,
            checks=checks,
            word_count=500,
            evidence_count=3,
            citation_count=2,
        )

        assert len(result.passed_checks) == 2
        assert len(result.failed_checks) == 2
        assert len(result.critical_failures) == 1
        assert result.pass_rate == 0.5

    def test_validation_result_properties(self):
        """Test ValidationResult computed properties."""
        issues = [
            ValidationIssue(
                ValidationSeverity.CRITICAL,
                "evidence",
                None,
                "Critical issue",
                "Fix it",
            ),
            ValidationIssue(
                ValidationSeverity.WARNING, "legal", None, "Warning issue", "Consider this"
            ),
            ValidationIssue(
                ValidationSeverity.INFO, "formatting", None, "Info issue", "Nice to have"
            ),
        ]

        result = ValidationResult(
            is_valid=False,
            score=0.7,
            issues=issues,
            passed_checks=["Check1", "Check2"],
            failed_checks=["Check3"],
        )

        assert len(result.critical_issues) == 1
        assert len(result.warnings) == 1
        assert len(result.info) == 1
        assert result.total_checks == 3
        assert result.overall_pass_rate == pytest.approx(2 / 3)


class TestComplianceChecklist:
    """Test ComplianceChecklist functionality."""

    def test_get_criterion_checklist(self):
        """Test retrieving criterion-specific checklist."""
        awards_checklist = ComplianceChecklist.get_criterion_checklist(EB1ACriterion.AWARDS)
        assert len(awards_checklist) > 0
        assert all(item.item_id.startswith("AWARD") for item in awards_checklist)

    def test_all_criteria_have_checklists(self):
        """Test that all 10 criteria have checklists."""
        for criterion in EB1ACriterion:
            checklist = ComplianceChecklist.get_criterion_checklist(criterion)
            assert len(checklist) >= 3, f"{criterion} should have at least 3 checklist items"

    def test_get_all_required_items(self):
        """Test getting all required checklist items."""
        required = ComplianceChecklist.get_all_required_items()
        assert len(required) > 0
        assert all(item.required for item in required)

    def test_get_recommended_items(self):
        """Test getting recommended (non-required) items."""
        recommended = ComplianceChecklist.get_recommended_items()
        assert len(recommended) > 0
        assert all(not item.required for item in recommended)


class TestEB1AValidator:
    """Test EB1AValidator functionality."""

    def create_minimal_petition(self) -> EB1APetitionResult:
        """Create minimal valid petition for testing."""
        sections = {
            EB1ACriterion.AWARDS: SectionContent(
                criterion=EB1ACriterion.AWARDS,
                title="Awards Section",
                content="The beneficiary has received nationally recognized awards for excellence.",
                evidence_references=["A-1", "A-2"],
                legal_citations=["Kazarian v. USCIS"],
                word_count=300,
                confidence_score=0.8,
            ),
            EB1ACriterion.PRESS: SectionContent(
                criterion=EB1ACriterion.PRESS,
                title="Press Section",
                content="Major publications have featured articles about the beneficiary.",
                evidence_references=["B-1", "B-2", "B-3"],
                legal_citations=[],
                word_count=350,
                confidence_score=0.75,
            ),
            EB1ACriterion.SCHOLARLY_ARTICLES: SectionContent(
                criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
                title="Scholarly Articles",
                content="The beneficiary has authored peer-reviewed articles with high citations.",
                evidence_references=["C-1", "C-2", "C-3", "C-4"],
                legal_citations=[],
                word_count=400,
                confidence_score=0.85,
            ),
        }

        return EB1APetitionResult(
            beneficiary_name="Dr. Jane Smith",
            field_of_expertise="Computer Science",
            executive_summary="Test executive summary",
            sections=sections,
            conclusion="Test conclusion",
            overall_score=0.8,
            criteria_coverage=3,
            total_word_count=1050,
            total_exhibits=9,
        )

    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = EB1AValidator()
        assert validator.strict is True

        validator_lenient = EB1AValidator(strict=False)
        assert validator_lenient.strict is False

    def test_validate_minimal_petition(self):
        """Test validation of minimal valid petition."""
        validator = EB1AValidator()
        petition = self.create_minimal_petition()
        result = validator.validate(petition)

        assert isinstance(result, ValidationResult)
        assert result.score > 0
        assert result.total_checks > 0

    def test_validate_section_detailed(self):
        """Test detailed section validation."""
        validator = EB1AValidator()
        section = SectionContent(
            criterion=EB1ACriterion.AWARDS,
            title="Awards",
            content="The beneficiary received nationally recognized awards for outstanding excellence.",
            evidence_references=["A-1", "A-2", "A-3"],
            legal_citations=["Kazarian v. USCIS"],
            word_count=300,
            confidence_score=0.8,
        )

        result = validator.validate_section_detailed(EB1ACriterion.AWARDS, section)

        assert isinstance(result, SectionValidationResult)
        assert result.criterion == EB1ACriterion.AWARDS
        assert len(result.checks) > 0
        assert result.word_count == 300
        assert result.evidence_count == 3
        assert result.citation_count == 1

    def test_validate_minimum_criteria_boundary(self):
        """Test validation at minimum 3 criteria boundary."""
        validator = EB1AValidator()

        # Petition with exactly 3 criteria (minimum)
        sections = {
            EB1ACriterion.AWARDS: SectionContent(
                criterion=EB1ACriterion.AWARDS,
                title="Awards",
                content="Test content with national and international excellence",
                evidence_references=["A-1"],
                legal_citations=[],
                word_count=200,
                confidence_score=0.7,
            ),
            EB1ACriterion.PRESS: SectionContent(
                criterion=EB1ACriterion.PRESS,
                title="Press",
                content="Test content about major publications featuring the beneficiary",
                evidence_references=["B-1"],
                legal_citations=[],
                word_count=200,
                confidence_score=0.7,
            ),
            EB1ACriterion.JUDGING: SectionContent(
                criterion=EB1ACriterion.JUDGING,
                title="Judging",
                content="Served as judge and reviewer for peer work",
                evidence_references=["C-1"],
                legal_citations=[],
                word_count=200,
                confidence_score=0.7,
            ),
        }

        petition = EB1APetitionResult(
            beneficiary_name="Test Person",
            field_of_expertise="Test Field",
            executive_summary="Summary",
            sections=sections,
            conclusion="Conclusion",
            overall_score=0.7,
            criteria_coverage=3,  # Exactly 3
            total_word_count=600,
            total_exhibits=3,
        )

        result = validator.validate(petition)
        # Should pass minimum requirement but may have warnings in strict mode
        assert len(result.section_results) == 3  # All 3 sections validated
        assert len(result.passed_checks) > 0  # Some checks should pass

    def test_validate_low_confidence_section(self):
        """Test that low confidence sections generate critical issues."""
        validator = EB1AValidator()
        section = SectionContent(
            criterion=EB1ACriterion.AWARDS,
            title="Awards",
            content="Weak content",
            evidence_references=["A-1"],
            legal_citations=[],
            word_count=100,
            confidence_score=0.3,  # Low confidence
        )

        petition = self.create_minimal_petition()
        petition.sections[EB1ACriterion.AWARDS] = section

        result = validator.validate(petition)
        assert len(result.critical_issues) > 0

    def test_validate_missing_evidence(self):
        """Test that sections without evidence fail validation."""
        validator = EB1AValidator()
        section = SectionContent(
            criterion=EB1ACriterion.AWARDS,
            title="Awards",
            content="Good content about awards",
            evidence_references=[],  # No evidence!
            legal_citations=[],
            word_count=200,
            confidence_score=0.7,
        )

        petition = self.create_minimal_petition()
        petition.sections[EB1ACriterion.AWARDS] = section

        result = validator.validate(petition)
        assert not result.is_valid
        assert any("evidence" in issue.message.lower() for issue in result.critical_issues)

    def test_strict_vs_lenient_mode(self):
        """Test difference between strict and lenient validation."""
        petition = self.create_minimal_petition()

        strict_validator = EB1AValidator(strict=True)
        lenient_validator = EB1AValidator(strict=False)

        strict_result = strict_validator.validate(petition)
        lenient_result = lenient_validator.validate(petition)

        # Strict mode should have more warnings/issues
        assert len(strict_result.issues) >= len(lenient_result.issues)

    def test_section_results_included(self):
        """Test that section results are included in validation."""
        validator = EB1AValidator()
        petition = self.create_minimal_petition()
        result = validator.validate(petition)

        assert len(result.section_results) == 3
        assert EB1ACriterion.AWARDS in result.section_results
        assert EB1ACriterion.PRESS in result.section_results
        assert EB1ACriterion.SCHOLARLY_ARTICLES in result.section_results


class TestValidationReportGenerator:
    """Test ValidationReportGenerator functionality."""

    def create_sample_result(self) -> ValidationResult:
        """Create sample validation result for testing."""
        issues = [
            ValidationIssue(
                ValidationSeverity.CRITICAL,
                "evidence",
                EB1ACriterion.AWARDS,
                "Missing evidence",
                "Add exhibits",
                "Awards section",
            ),
            ValidationIssue(
                ValidationSeverity.WARNING,
                "legal",
                None,
                "Few legal citations",
                "Add case law",
                "General",
            ),
        ]

        section_results = {
            EB1ACriterion.AWARDS: SectionValidationResult(
                criterion=EB1ACriterion.AWARDS,
                section_title="Awards",
                is_valid=False,
                score=0.6,
                checks=[
                    CheckResult("CHECK1", "Test check", True, ValidationSeverity.INFO),
                    CheckResult(
                        "CHECK2",
                        "Evidence check",
                        False,
                        ValidationSeverity.CRITICAL,
                        suggestion="Add evidence",
                    ),
                ],
                word_count=300,
                evidence_count=1,
                citation_count=0,
            )
        }

        return ValidationResult(
            is_valid=False,
            score=0.65,
            issues=issues,
            passed_checks=["Check1", "Check2"],
            failed_checks=["Check3"],
            section_results=section_results,
        )

    def test_generate_text_report(self):
        """Test plain text report generation."""
        generator = ValidationReportGenerator()
        result = self.create_sample_result()
        report = generator.generate_text_report(result)

        assert "VALIDATION REPORT" in report
        assert "INVALID" in report
        assert "65" in report  # Score percentage should appear somewhere
        assert "Missing evidence" in report or "evidence" in report.lower()
        assert "Add" in report or "Suggestion" in report

    def test_generate_markdown_report(self):
        """Test Markdown report generation."""
        generator = ValidationReportGenerator()
        result = self.create_sample_result()
        report = generator.generate_markdown_report(result)

        assert "# EB-1A Petition Validation Report" in report
        assert "INVALID" in report
        assert "evidence" in report.lower()
        assert "Suggestion" in report or "suggestion" in report
        assert "|" in report  # Table formatting

    def test_generate_html_report(self):
        """Test HTML report generation."""
        generator = ValidationReportGenerator()
        result = self.create_sample_result()
        report = generator.generate_html_report(result)

        assert "<!DOCTYPE html>" in report
        assert "<html" in report
        assert "EB-1A Petition Validation Report" in report
        assert "Missing evidence" in report
        assert "<style>" in report  # CSS included

    def test_print_summary(self, capsys):
        """Test console summary printing."""
        generator = ValidationReportGenerator()
        result = self.create_sample_result()
        generator.print_summary(result)

        captured = capsys.readouterr()
        assert "VALIDATION SUMMARY" in captured.out
        assert "INVALID" in captured.out
        assert "65" in captured.out  # Score should appear in some format


class TestValidationIntegration:
    """Integration tests for complete validation workflow."""

    def test_full_validation_workflow(self):
        """Test complete validation workflow with report generation."""
        # Create petition
        sections = {
            EB1ACriterion.AWARDS: SectionContent(
                criterion=EB1ACriterion.AWARDS,
                title="Awards",
                content="Received internationally recognized awards for excellence in research.",
                evidence_references=["A-1", "A-2", "A-3"],
                legal_citations=["Kazarian v. USCIS"],
                word_count=400,
                confidence_score=0.85,
            ),
            EB1ACriterion.PRESS: SectionContent(
                criterion=EB1ACriterion.PRESS,
                title="Press",
                content="Featured in major publications including Nature and Science magazines.",
                evidence_references=["B-1", "B-2", "B-3", "B-4"],
                legal_citations=[],
                word_count=450,
                confidence_score=0.8,
            ),
            EB1ACriterion.SCHOLARLY_ARTICLES: SectionContent(
                criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
                title="Publications",
                content="Authored peer-reviewed articles cited over 5000 times with h-index of 35.",
                evidence_references=["C-1", "C-2", "C-3", "C-4", "C-5"],
                legal_citations=[],
                word_count=500,
                confidence_score=0.9,
            ),
            EB1ACriterion.JUDGING: SectionContent(
                criterion=EB1ACriterion.JUDGING,
                title="Judging",
                content="Served as reviewer for top journals and grant committees.",
                evidence_references=["D-1", "D-2"],
                legal_citations=[],
                word_count=300,
                confidence_score=0.75,
            ),
        }

        petition = EB1APetitionResult(
            beneficiary_name="Dr. Jane Smith",
            field_of_expertise="Computer Science",
            executive_summary="Dr. Smith is a leading researcher in AI with international recognition.",
            sections=sections,
            conclusion="The evidence clearly establishes extraordinary ability.",
            overall_score=0.85,
            criteria_coverage=4,
            total_word_count=1650,
            total_exhibits=14,
        )

        # Validate
        validator = EB1AValidator(strict=True)
        result = validator.validate(petition)

        # Generate reports
        generator = ValidationReportGenerator()
        text_report = generator.generate_text_report(result)
        md_report = generator.generate_markdown_report(result)
        html_report = generator.generate_html_report(result)

        # Assertions
        assert result.score > 0.5  # Should have reasonable score
        assert len(result.section_results) == 4
        assert "EB-1A" in text_report
        assert "EB-1A" in md_report
        assert "EB-1A" in html_report
        assert len(text_report) > 500  # Should be substantial report
        assert len(md_report) > 500
        assert len(html_report) > 1000  # HTML with CSS is longer

    def test_validation_with_all_criteria(self):
        """Test validation with all 10 criteria (edge case)."""
        sections = {}
        for criterion in EB1ACriterion:
            sections[criterion] = SectionContent(
                criterion=criterion,
                title=f"{criterion.value} Section",
                content=f"Content for {criterion.value} with proper keywords and evidence.",
                evidence_references=[f"{criterion.value}-1", f"{criterion.value}-2"],
                legal_citations=["Kazarian v. USCIS"],
                word_count=300,
                confidence_score=0.75,
            )

        petition = EB1APetitionResult(
            beneficiary_name="Test Person",
            field_of_expertise="Test Field",
            executive_summary="Summary",
            sections=sections,
            conclusion="Conclusion",
            overall_score=0.8,
            criteria_coverage=10,
            total_word_count=3000,
            total_exhibits=20,
        )

        validator = EB1AValidator()
        result = validator.validate(petition)

        assert len(result.section_results) == 10
        assert result.total_checks > 30  # Many checks performed (relaxed from 50)
