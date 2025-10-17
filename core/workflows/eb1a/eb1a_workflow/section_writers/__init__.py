"""Section writers for EB-1A petition criteria.

This module provides specialized writers for each of the 10 EB-1A criteria
defined in 8 CFR Section 204.5(h)(3):

- 2.1: Awards and Prizes (AwardsWriter)
- 2.2: Membership in Associations (MembershipWriter)
- 2.3: Published Material About Beneficiary (PressWriter)
- 2.4: Participation as Judge (JudgingWriter)
- 2.5: Original Contributions of Major Significance (ContributionsWriter)
- 2.6: Authorship of Scholarly Articles (AuthorshipWriter)
- 2.7: Artistic Exhibitions or Showcases (ExhibitionsWriter)
- 2.8: Leading or Critical Role (LeadingRoleWriter)
- 2.9: High Salary or Remuneration (SalaryWriter)
- 2.10: Commercial Success in Performing Arts (CommercialSuccessWriter)

Each writer inherits from BaseSectionWriter and provides criterion-specific
content generation logic, evidence formatting, and legal citation integration.
"""

from __future__ import annotations

from .authorship_writer import AuthorshipWriter
from .awards_writer import AwardsWriter
from .base_writer import BaseSectionWriter
from .commercial_success_writer import CommercialSuccessWriter
from .contributions_writer import ContributionsWriter
from .exhibitions_writer import ExhibitionsWriter
from .judging_writer import JudgingWriter
from .leading_role_writer import LeadingRoleWriter
from .membership_writer import MembershipWriter
from .press_writer import PressWriter
from .salary_writer import SalaryWriter

__all__ = [
    "BaseSectionWriter",
    "AwardsWriter",
    "MembershipWriter",
    "PressWriter",
    "JudgingWriter",
    "ContributionsWriter",
    "AuthorshipWriter",
    "ExhibitionsWriter",
    "LeadingRoleWriter",
    "SalaryWriter",
    "CommercialSuccessWriter",
]
