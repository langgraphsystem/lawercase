"""EB-1A (Extraordinary Ability) Immigration Petition Workflow Package.

This package provides specialized components for generating high-quality EB-1A
petitions with evidence-based arguments, legal citations, and USCIS compliance.

Modules:
    eb1a_coordinator: Main orchestrator for EB-1A petition generation
    section_writers: Specialized writers for each criterion (2.1-2.10)
    templates: Reusable templates and language patterns
    validators: EB-1A specific validation and quality checks
    evidence_researcher: RAG-based evidence gathering and citation
"""

from __future__ import annotations

from .eb1a_coordinator import (EB1ACoordinator, EB1APetitionRequest,
                               EB1APetitionResult)

__all__ = [
    "EB1ACoordinator",
    "EB1APetitionRequest",
    "EB1APetitionResult",
]
