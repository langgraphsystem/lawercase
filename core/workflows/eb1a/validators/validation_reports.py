"""Validation report generation for EB-1A petitions.

This module provides comprehensive report generation for validation results:
- Plain text summaries
- Markdown reports
- HTML reports with visualization
- JSON export for programmatic access
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..eb1a_coordinator import EB1ACriterion
from .eb1a_validator import (
    SectionValidationResult,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class ValidationReportGenerator:
    """
    Generate comprehensive validation reports in multiple formats.

    Supports:
    - Plain text reports (console output)
    - Markdown reports (documentation)
    - HTML reports (visual presentation)
    - JSON export (programmatic access)

    Example:
        >>> generator = ValidationReportGenerator()
        >>> report = generator.generate_text_report(validation_result)
        >>> print(report)
        >>> # Or save to file
        >>> generator.save_html_report(validation_result, "petition_validation.html")
    """

    def __init__(self):
        """Initialize report generator."""

    def generate_text_report(self, result: ValidationResult) -> str:
        """
        Generate plain text validation report.

        Args:
            result: Validation result to report on

        Returns:
            Plain text report string
        """
        lines: list[str] = []
        lines.append("=" * 80)
        lines.append("EB-1A PETITION VALIDATION REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Overall summary
        lines.append("OVERALL VALIDATION SUMMARY")
        lines.append("-" * 80)
        status = "✓ VALID" if result.is_valid else "✗ INVALID"
        lines.append(f"Status: {status}")
        lines.append(f"Overall Score: {result.score:.2%}")
        lines.append(
            f"Pass Rate: {result.overall_pass_rate:.1%} ({len(result.passed_checks)}/{result.total_checks} checks)"
        )
        lines.append("")

        # Issue summary
        lines.append("ISSUES SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Critical Issues: {len(result.critical_issues)}")
        lines.append(f"Warnings: {len(result.warnings)}")
        lines.append(f"Informational: {len(result.info)}")
        lines.append("")

        # Critical issues (must fix)
        if result.critical_issues:
            lines.append("CRITICAL ISSUES (MUST FIX)")
            lines.append("-" * 80)
            for i, issue in enumerate(result.critical_issues, 1):
                lines.append(f"\n{i}. [{issue.category.upper()}] {issue.message}")
                lines.append(f"   Location: {issue.location or 'General'}")
                if issue.criterion:
                    lines.append(f"   Criterion: {issue.criterion.value}")
                lines.append(f"   → Suggestion: {issue.suggestion}")
            lines.append("")

        # Warnings (should fix)
        if result.warnings:
            lines.append("WARNINGS (SHOULD FIX)")
            lines.append("-" * 80)
            for i, issue in enumerate(result.warnings, 1):
                lines.append(f"\n{i}. [{issue.category.upper()}] {issue.message}")
                lines.append(f"   → Suggestion: {issue.suggestion}")
            lines.append("")

        # Section-by-section analysis
        if result.section_results:
            lines.append("SECTION-BY-SECTION ANALYSIS")
            lines.append("=" * 80)
            for criterion, section_result in result.section_results.items():
                lines.append("")
                lines.append(f"Section: {criterion.value.upper()}")
                lines.append("-" * 80)
                status = "✓ Valid" if section_result.is_valid else "✗ Invalid"
                lines.append(f"Status: {status}")
                lines.append(f"Score: {section_result.score:.2%}")
                lines.append(
                    f"Pass Rate: {section_result.pass_rate:.1%} ({len(section_result.passed_checks)}/{len(section_result.checks)} checks)"
                )
                lines.append(
                    f"Metrics: {section_result.word_count} words, {section_result.evidence_count} exhibits, {section_result.citation_count} citations"
                )

                # Failed checks for this section
                if section_result.failed_checks:
                    lines.append("\nFailed Checks:")
                    for check in section_result.failed_checks:
                        severity_icon = (
                            "✗" if check.severity == ValidationSeverity.CRITICAL else "⚠"
                        )
                        lines.append(f"  {severity_icon} {check.description}")
                        if check.suggestion:
                            lines.append(f"     → {check.suggestion}")

        # Summary recommendations
        lines.append("")
        lines.append("RECOMMENDATIONS")
        lines.append("=" * 80)
        if result.is_valid:
            lines.append("✓ Petition meets minimum validation requirements.")
            lines.append("  Review warnings and informational items for quality improvements.")
        else:
            lines.append("✗ Petition has critical issues that must be addressed before filing.")
            lines.append("  Focus on resolving critical issues first, then address warnings.")
        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_markdown_report(self, result: ValidationResult) -> str:
        """
        Generate Markdown validation report.

        Args:
            result: Validation result to report on

        Returns:
            Markdown report string
        """
        lines: list[str] = []

        # Title and metadata
        lines.append("# EB-1A Petition Validation Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Overall summary
        lines.append("## Overall Summary")
        lines.append("")
        status_emoji = "✅" if result.is_valid else "❌"
        lines.append(f"**Status:** {status_emoji} {'VALID' if result.is_valid else 'INVALID'}")
        lines.append(f"**Overall Score:** {result.score:.2%}")
        lines.append(
            f"**Pass Rate:** {result.overall_pass_rate:.1%} ({len(result.passed_checks)}/{result.total_checks} checks passed)"
        )
        lines.append("")

        # Issue statistics
        lines.append("### Issue Summary")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        lines.append(f"| 🔴 Critical | {len(result.critical_issues)} |")
        lines.append(f"| ⚠️ Warnings | {len(result.warnings)} |")
        lines.append(f"| ℹ️ Info | {len(result.info)} |")
        lines.append("")

        # Critical issues
        if result.critical_issues:
            lines.append("## 🔴 Critical Issues (Must Fix)")
            lines.append("")
            for i, issue in enumerate(result.critical_issues, 1):
                lines.append(f"### {i}. {issue.message}")
                lines.append("")
                lines.append(f"**Category:** {issue.category}")
                if issue.criterion:
                    lines.append(f"**Criterion:** {issue.criterion.value}")
                lines.append(f"**Location:** {issue.location or 'General'}")
                lines.append("")
                lines.append(f"**💡 Suggestion:** {issue.suggestion}")
                lines.append("")

        # Warnings
        if result.warnings:
            lines.append("## ⚠️ Warnings (Should Fix)")
            lines.append("")
            for i, issue in enumerate(result.warnings, 1):
                lines.append(f"### {i}. {issue.message}")
                lines.append("")
                lines.append(f"**💡 Suggestion:** {issue.suggestion}")
                lines.append("")

        # Section results
        if result.section_results:
            lines.append("## Section Analysis")
            lines.append("")
            lines.append("| Criterion | Status | Score | Pass Rate | Evidence | Citations |")
            lines.append("|-----------|--------|-------|-----------|----------|-----------|")
            for criterion, section in result.section_results.items():
                status = "✅" if section.is_valid else "❌"
                lines.append(
                    f"| {criterion.value} | {status} | {section.score:.1%} | "
                    f"{section.pass_rate:.1%} | {section.evidence_count} | {section.citation_count} |"
                )
            lines.append("")

            # Detailed section analysis
            lines.append("### Detailed Section Results")
            lines.append("")
            for criterion, section in result.section_results.items():
                status_emoji = "✅" if section.is_valid else "❌"
                lines.append(f"#### {status_emoji} {criterion.value}")
                lines.append("")
                lines.append(f"- **Score:** {section.score:.2%}")
                lines.append(
                    f"- **Checks:** {len(section.passed_checks)}/{len(section.checks)} passed"
                )
                lines.append(f"- **Word Count:** {section.word_count}")
                lines.append(f"- **Evidence:** {section.evidence_count} exhibits")
                lines.append(f"- **Citations:** {section.citation_count}")
                lines.append("")

                if section.failed_checks:
                    lines.append("**Failed Checks:**")
                    lines.append("")
                    for check in section.failed_checks:
                        icon = "🔴" if check.severity == ValidationSeverity.CRITICAL else "⚠️"
                        lines.append(f"- {icon} {check.description}")
                        if check.suggestion:
                            lines.append(f"  - *Suggestion:* {check.suggestion}")
                    lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        if result.is_valid:
            lines.append("✅ **Petition meets minimum validation requirements.**")
            lines.append("")
            lines.append(
                "Consider addressing warnings and informational items to further strengthen the petition."
            )
        else:
            lines.append("❌ **Petition has critical issues that must be resolved.**")
            lines.append("")
            lines.append("**Action Items:**")
            lines.append("1. Address all critical issues listed above")
            lines.append("2. Review and fix warnings")
            lines.append("3. Re-validate petition before filing")
        lines.append("")

        return "\n".join(lines)

    def generate_html_report(self, result: ValidationResult) -> str:
        """
        Generate HTML validation report with visualization.

        Args:
            result: Validation result to report on

        Returns:
            HTML report string
        """
        html_parts: list[str] = []

        # HTML header and CSS
        html_parts.append(
            """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EB-1A Petition Validation Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0 0 10px 0;
        }
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h3 {
            margin-top: 0;
            color: #333;
        }
        .score {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        .score.valid { color: #10b981; }
        .score.invalid { color: #ef4444; }
        .progress-bar {
            background: #e5e7eb;
            height: 20px;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            transition: width 0.3s ease;
        }
        .issue {
            background: white;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid;
        }
        .issue.critical { border-color: #ef4444; background-color: #fef2f2; }
        .issue.warning { border-color: #f59e0b; background-color: #fffbeb; }
        .issue.info { border-color: #3b82f6; background-color: #eff6ff; }
        .issue-header {
            font-weight: bold;
            margin-bottom: 8px;
        }
        .suggestion {
            margin-top: 10px;
            padding: 10px;
            background: rgba(255,255,255,0.5);
            border-radius: 4px;
            font-size: 0.9em;
        }
        .section-grid {
            display: grid;
            gap: 20px;
            margin-bottom: 30px;
        }
        .section-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .status-badge.valid { background: #d1fae5; color: #065f46; }
        .status-badge.invalid { background: #fee2e2; color: #991b1b; }
        .metrics {
            display: flex;
            gap: 20px;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        .metric {
            flex: 1;
            min-width: 100px;
        }
        .metric-label {
            font-size: 0.85em;
            color: #6b7280;
        }
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #111827;
        }
        .check-list {
            margin-top: 15px;
        }
        .check-item {
            padding: 8px;
            margin-bottom: 5px;
            border-radius: 4px;
        }
        .check-item.passed {
            background: #d1fae5;
            color: #065f46;
        }
        .check-item.failed {
            background: #fee2e2;
            color: #991b1b;
        }
        .recommendations {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        th {
            background: #f9fafb;
            font-weight: 600;
        }
    </style>
</head>
<body>
"""
        )

        # Header
        status_text = "VALID" if result.is_valid else "INVALID"
        html_parts.append(
            f"""
    <div class="header">
        <h1>EB-1A Petition Validation Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""
        )

        # Summary cards
        score_class = "valid" if result.is_valid else "invalid"
        html_parts.append(
            f"""
    <div class="summary-cards">
        <div class="card">
            <h3>Validation Status</h3>
            <div class="score {score_class}">{status_text}</div>
        </div>
        <div class="card">
            <h3>Overall Score</h3>
            <div class="score">{result.score:.1%}</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {result.score * 100}%"></div>
            </div>
        </div>
        <div class="card">
            <h3>Check Pass Rate</h3>
            <div class="score">{result.overall_pass_rate:.1%}</div>
            <p>{len(result.passed_checks)} / {result.total_checks} checks passed</p>
        </div>
        <div class="card">
            <h3>Issues Found</h3>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Critical</div>
                    <div class="metric-value" style="color: #ef4444;">{len(result.critical_issues)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Warnings</div>
                    <div class="metric-value" style="color: #f59e0b;">{len(result.warnings)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Info</div>
                    <div class="metric-value" style="color: #3b82f6;">{len(result.info)}</div>
                </div>
            </div>
        </div>
    </div>
"""
        )

        # Critical issues
        if result.critical_issues:
            html_parts.append("<h2>🔴 Critical Issues (Must Fix)</h2>")
            for issue in result.critical_issues:
                html_parts.append(self._format_issue_html(issue, "critical"))

        # Warnings
        if result.warnings:
            html_parts.append("<h2>⚠️ Warnings (Should Fix)</h2>")
            for issue in result.warnings:
                html_parts.append(self._format_issue_html(issue, "warning"))

        # Section analysis
        if result.section_results:
            html_parts.append("<h2>Section Analysis</h2>")
            html_parts.append('<div class="section-grid">')
            for criterion, section in result.section_results.items():
                html_parts.append(self._format_section_html(criterion, section))
            html_parts.append("</div>")

        # Recommendations
        html_parts.append('<div class="recommendations">')
        html_parts.append("<h2>Recommendations</h2>")
        if result.is_valid:
            html_parts.append(
                "<p>✅ <strong>Petition meets minimum validation requirements.</strong></p>"
            )
            html_parts.append(
                "<p>Consider addressing warnings and informational items to further strengthen the petition.</p>"
            )
        else:
            html_parts.append(
                "<p>❌ <strong>Petition has critical issues that must be resolved before filing.</strong></p>"
            )
            html_parts.append("<ol>")
            html_parts.append("<li>Address all critical issues listed above</li>")
            html_parts.append("<li>Review and fix warnings</li>")
            html_parts.append("<li>Re-validate petition before filing</li>")
            html_parts.append("</ol>")
        html_parts.append("</div>")

        # HTML footer
        html_parts.append(
            """
</body>
</html>
"""
        )

        return "".join(html_parts)

    def _format_issue_html(self, issue: ValidationIssue, severity: str) -> str:
        """Format a single issue as HTML."""
        return f"""
    <div class="issue {severity}">
        <div class="issue-header">{issue.message}</div>
        <p><strong>Category:</strong> {issue.category}</p>
        {f'<p><strong>Criterion:</strong> {issue.criterion.value}</p>' if issue.criterion else ''}
        <p><strong>Location:</strong> {issue.location or 'General'}</p>
        <div class="suggestion">
            <strong>💡 Suggestion:</strong> {issue.suggestion}
        </div>
    </div>
"""

    def _format_section_html(
        self, criterion: EB1ACriterion, section: SectionValidationResult
    ) -> str:
        """Format a section result as HTML."""
        status_class = "valid" if section.is_valid else "invalid"
        status_text = "✅ Valid" if section.is_valid else "❌ Invalid"

        failed_checks_html = ""
        if section.failed_checks:
            failed_checks_html = '<div class="check-list"><h4>Failed Checks:</h4>'
            for check in section.failed_checks:
                check_class = "failed"
                icon = "❌"
                failed_checks_html += (
                    f'<div class="check-item {check_class}">{icon} {check.description}'
                )
                if check.suggestion:
                    failed_checks_html += f"<br><small>→ {check.suggestion}</small>"
                failed_checks_html += "</div>"
            failed_checks_html += "</div>"

        return f"""
    <div class="section-card">
        <div class="section-header">
            <h3>{criterion.value}</h3>
            <span class="status-badge {status_class}">{status_text}</span>
        </div>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Score</div>
                <div class="metric-value">{section.score:.1%}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Pass Rate</div>
                <div class="metric-value">{section.pass_rate:.1%}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Words</div>
                <div class="metric-value">{section.word_count}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Evidence</div>
                <div class="metric-value">{section.evidence_count}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Citations</div>
                <div class="metric-value">{section.citation_count}</div>
            </div>
        </div>
        {failed_checks_html}
    </div>
"""

    def save_html_report(self, result: ValidationResult, output_path: str | Path) -> None:
        """
        Save HTML report to file.

        Args:
            result: Validation result to report on
            output_path: Path to save HTML file
        """
        html_content = self.generate_html_report(result)
        output_file = Path(output_path)
        output_file.write_text(html_content, encoding="utf-8")

    def save_markdown_report(self, result: ValidationResult, output_path: str | Path) -> None:
        """
        Save Markdown report to file.

        Args:
            result: Validation result to report on
            output_path: Path to save Markdown file
        """
        md_content = self.generate_markdown_report(result)
        output_file = Path(output_path)
        output_file.write_text(md_content, encoding="utf-8")

    def print_summary(self, result: ValidationResult) -> None:
        """
        Print concise validation summary to console.

        Args:
            result: Validation result to summarize
        """
        print("\n" + "=" * 80)
        print("EB-1A PETITION VALIDATION SUMMARY")
        print("=" * 80)

        status = "✓ VALID" if result.is_valid else "✗ INVALID"
        print(f"Status: {status}")
        print(f"Score: {result.score:.2%}")
        print(
            f"Pass Rate: {result.overall_pass_rate:.1%} ({len(result.passed_checks)}/{result.total_checks} checks)"
        )

        print(
            f"\nIssues: {len(result.critical_issues)} critical, {len(result.warnings)} warnings, {len(result.info)} info"
        )

        if result.critical_issues:
            print("\nCritical Issues:")
            for i, issue in enumerate(result.critical_issues[:5], 1):  # Show first 5
                print(f"  {i}. {issue.message}")
            if len(result.critical_issues) > 5:
                print(f"  ... and {len(result.critical_issues) - 5} more")

        print("=" * 80 + "\n")
