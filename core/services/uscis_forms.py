"""
USCIS Forms Service - Handles official immigration forms for EB-1A petitions.

Supports:
- I-140: Immigrant Petition for Alien Workers
- G-28: Notice of Entry of Appearance as Attorney or Accredited Representative
- I-907: Request for Premium Processing Service
- ETA-9089: Application for Permanent Employment Certification (if needed)

Features:
- Form field definitions with validation
- PDF filling and generation
- Auto-population from case data
- Form state persistence
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class FormType(Enum):
    """USCIS Form types for EB-1A."""

    I_140 = "I-140"
    G_28 = "G-28"
    I_907 = "I-907"
    ETA_9089 = "ETA-9089"


class FieldType(Enum):
    """Form field types."""

    TEXT = "text"
    DATE = "date"
    CHECKBOX = "checkbox"
    SELECT = "select"
    TEXTAREA = "textarea"
    PHONE = "phone"
    EMAIL = "email"
    SSN = "ssn"
    ALIEN_NUMBER = "alien_number"
    MONEY = "money"


@dataclass
class FormField:
    """Definition of a form field."""

    id: str
    label: str
    field_type: FieldType
    required: bool = False
    section: str = ""
    help_text: str = ""
    options: list[str] = field(default_factory=list)  # For SELECT type
    max_length: int | None = None
    pdf_field_name: str | None = None  # Mapping to PDF form field


# I-140 Form Field Definitions
I140_FIELDS = [
    # Part 1 - Information About This Petition
    FormField(
        id="petition_type",
        label="Petition Type",
        field_type=FieldType.SELECT,
        required=True,
        section="Part 1. Information About This Petition",
        options=[
            "An alien of extraordinary ability (E11)",
            "An outstanding professor or researcher (E12)",
            "A multinational manager or executive (E13)",
            "A member of the professions holding an advanced degree (E21)",
            "An alien of exceptional ability (E21)",
            "A skilled worker (E31)",
            "A professional (E32)",
            "An unskilled worker (EW3)",
        ],
        pdf_field_name="Pt1Line1_Classification",
    ),
    # Part 2 - Information About Petitioner
    FormField(
        id="petitioner_type",
        label="Petitioner Type",
        field_type=FieldType.SELECT,
        required=True,
        section="Part 2. Information About Petitioner",
        options=["Employer", "Self-petitioner"],
        pdf_field_name="Pt2Line1_PetitionerType",
    ),
    FormField(
        id="petitioner_name",
        label="Petitioner Legal Business Name",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Information About Petitioner",
        max_length=100,
        pdf_field_name="Pt2Line2_LegalName",
    ),
    FormField(
        id="petitioner_address_street",
        label="Street Number and Name",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Information About Petitioner",
        pdf_field_name="Pt2Line3_StreetNumberName",
    ),
    FormField(
        id="petitioner_address_apt",
        label="Apt/Ste/Flr",
        field_type=FieldType.TEXT,
        section="Part 2. Information About Petitioner",
        pdf_field_name="Pt2Line3_AptSteFlr",
    ),
    FormField(
        id="petitioner_address_city",
        label="City or Town",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Information About Petitioner",
        pdf_field_name="Pt2Line3_CityTown",
    ),
    FormField(
        id="petitioner_address_state",
        label="State",
        field_type=FieldType.SELECT,
        required=True,
        section="Part 2. Information About Petitioner",
        options=[
            "AL",
            "AK",
            "AZ",
            "AR",
            "CA",
            "CO",
            "CT",
            "DE",
            "FL",
            "GA",
            "HI",
            "ID",
            "IL",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MD",
            "MA",
            "MI",
            "MN",
            "MS",
            "MO",
            "MT",
            "NE",
            "NV",
            "NH",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "PA",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WA",
            "WV",
            "WI",
            "WY",
            "DC",
            "PR",
            "VI",
            "GU",
            "AS",
            "MP",
        ],
        pdf_field_name="Pt2Line3_State",
    ),
    FormField(
        id="petitioner_address_zip",
        label="ZIP Code",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Information About Petitioner",
        max_length=10,
        pdf_field_name="Pt2Line3_ZipCode",
    ),
    FormField(
        id="petitioner_ein",
        label="IRS Tax Number (EIN)",
        field_type=FieldType.TEXT,
        section="Part 2. Information About Petitioner",
        help_text="9-digit Employer Identification Number",
        max_length=10,
        pdf_field_name="Pt2Line6_IRSTaxNumber",
    ),
    # Part 3 - Information About Beneficiary
    FormField(
        id="beneficiary_alien_number",
        label="Alien Registration Number (A-Number)",
        field_type=FieldType.ALIEN_NUMBER,
        section="Part 3. Information About Beneficiary",
        help_text="If applicable",
        pdf_field_name="Pt3Line1_AlienNumber",
    ),
    FormField(
        id="beneficiary_uscis_number",
        label="USCIS Online Account Number",
        field_type=FieldType.TEXT,
        section="Part 3. Information About Beneficiary",
        max_length=12,
        pdf_field_name="Pt3Line2_USCISNumber",
    ),
    FormField(
        id="beneficiary_ssn",
        label="U.S. Social Security Number",
        field_type=FieldType.SSN,
        section="Part 3. Information About Beneficiary",
        help_text="If applicable",
        pdf_field_name="Pt3Line3_SSN",
    ),
    FormField(
        id="beneficiary_family_name",
        label="Family Name (Last Name)",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line4a_FamilyName",
    ),
    FormField(
        id="beneficiary_given_name",
        label="Given Name (First Name)",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line4b_GivenName",
    ),
    FormField(
        id="beneficiary_middle_name",
        label="Middle Name",
        field_type=FieldType.TEXT,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line4c_MiddleName",
    ),
    FormField(
        id="beneficiary_dob",
        label="Date of Birth",
        field_type=FieldType.DATE,
        required=True,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line7_DOB",
    ),
    FormField(
        id="beneficiary_country_birth",
        label="Country of Birth",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line5_CountryBirth",
    ),
    FormField(
        id="beneficiary_country_citizenship",
        label="Country of Citizenship",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line6_CountryCitizenship",
    ),
    FormField(
        id="beneficiary_current_address_street",
        label="Current Address - Street",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line8_StreetNumberName",
    ),
    FormField(
        id="beneficiary_current_address_city",
        label="Current Address - City",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line8_CityTown",
    ),
    FormField(
        id="beneficiary_current_address_country",
        label="Current Address - Country",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line8_Country",
    ),
    FormField(
        id="beneficiary_email",
        label="Email Address",
        field_type=FieldType.EMAIL,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line15_Email",
    ),
    FormField(
        id="beneficiary_phone",
        label="Daytime Phone Number",
        field_type=FieldType.PHONE,
        section="Part 3. Information About Beneficiary",
        pdf_field_name="Pt3Line14_DaytimePhone",
    ),
    # Part 5 - Additional Information About Beneficiary
    FormField(
        id="current_nonimmigrant_status",
        label="Current Nonimmigrant Status",
        field_type=FieldType.TEXT,
        section="Part 5. Additional Information About Beneficiary",
        help_text="e.g., F-1, H-1B, O-1",
        pdf_field_name="Pt5Line1_NonimmigrantStatus",
    ),
    FormField(
        id="date_status_expires",
        label="Date Status Expires",
        field_type=FieldType.DATE,
        section="Part 5. Additional Information About Beneficiary",
        pdf_field_name="Pt5Line2_StatusExpires",
    ),
    # Part 6 - Basic Information About Proposed Employment
    FormField(
        id="job_title",
        label="Job Title",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 6. Basic Information About Proposed Employment",
        pdf_field_name="Pt6Line1_JobTitle",
    ),
    FormField(
        id="soc_code",
        label="SOC/O*NET Code",
        field_type=FieldType.TEXT,
        section="Part 6. Basic Information About Proposed Employment",
        help_text="Standard Occupational Classification code",
        pdf_field_name="Pt6Line3_SOCCode",
    ),
    FormField(
        id="wage_offered",
        label="Wage Offered (per year)",
        field_type=FieldType.MONEY,
        required=True,
        section="Part 6. Basic Information About Proposed Employment",
        pdf_field_name="Pt6Line5_WagePerYear",
    ),
]

# G-28 Form Field Definitions
G28_FIELDS = [
    # Part 1 - Notice of Appearance
    FormField(
        id="appearance_for",
        label="This appearance is for",
        field_type=FieldType.SELECT,
        required=True,
        section="Part 1. Notice of Appearance",
        options=[
            "A petitioner/applicant",
            "A respondent",
            "A beneficiary of a petition",
        ],
        pdf_field_name="Pt1Line1_AppearanceFor",
    ),
    # Part 2 - Information About Attorney or Accredited Representative
    FormField(
        id="attorney_name_last",
        label="Attorney Family Name (Last Name)",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line1a_FamilyName",
    ),
    FormField(
        id="attorney_name_first",
        label="Attorney Given Name (First Name)",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line1b_GivenName",
    ),
    FormField(
        id="attorney_firm_name",
        label="Law Firm/Organization Name",
        field_type=FieldType.TEXT,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line3_FirmName",
    ),
    FormField(
        id="attorney_address_street",
        label="Street Number and Name",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line4_StreetNumberName",
    ),
    FormField(
        id="attorney_address_city",
        label="City or Town",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line4_CityTown",
    ),
    FormField(
        id="attorney_address_state",
        label="State",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line4_State",
    ),
    FormField(
        id="attorney_address_zip",
        label="ZIP Code",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line4_ZipCode",
    ),
    FormField(
        id="attorney_phone",
        label="Phone Number",
        field_type=FieldType.PHONE,
        required=True,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line5_Phone",
    ),
    FormField(
        id="attorney_email",
        label="Email Address",
        field_type=FieldType.EMAIL,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line7_Email",
    ),
    FormField(
        id="attorney_bar_number",
        label="Bar Number",
        field_type=FieldType.TEXT,
        section="Part 2. Attorney Information",
        pdf_field_name="Pt2Line8_BarNumber",
    ),
    FormField(
        id="attorney_licensing_authority",
        label="Licensing Authority",
        field_type=FieldType.TEXT,
        section="Part 2. Attorney Information",
        help_text="State Bar or other licensing authority",
        pdf_field_name="Pt2Line9_LicensingAuthority",
    ),
    # Part 3 - Information About Client
    FormField(
        id="client_name_last",
        label="Client Family Name (Last Name)",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Client Information",
        pdf_field_name="Pt3Line1a_FamilyName",
    ),
    FormField(
        id="client_name_first",
        label="Client Given Name (First Name)",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Client Information",
        pdf_field_name="Pt3Line1b_GivenName",
    ),
    FormField(
        id="client_alien_number",
        label="Client A-Number",
        field_type=FieldType.ALIEN_NUMBER,
        section="Part 3. Client Information",
        pdf_field_name="Pt3Line3_AlienNumber",
    ),
]

# I-907 Form Field Definitions
I907_FIELDS = [
    # Part 1 - Information About Petitioner/Applicant
    FormField(
        id="petitioner_name",
        label="Petitioner/Applicant Name",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 1. Petitioner/Applicant Information",
        pdf_field_name="Pt1Line1_Name",
    ),
    FormField(
        id="petitioner_address_street",
        label="Street Address",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 1. Petitioner/Applicant Information",
        pdf_field_name="Pt1Line2_StreetAddress",
    ),
    FormField(
        id="petitioner_address_city",
        label="City",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 1. Petitioner/Applicant Information",
        pdf_field_name="Pt1Line2_City",
    ),
    FormField(
        id="petitioner_address_state",
        label="State",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 1. Petitioner/Applicant Information",
        pdf_field_name="Pt1Line2_State",
    ),
    FormField(
        id="petitioner_address_zip",
        label="ZIP Code",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 1. Petitioner/Applicant Information",
        pdf_field_name="Pt1Line2_ZipCode",
    ),
    FormField(
        id="petitioner_phone",
        label="Phone Number",
        field_type=FieldType.PHONE,
        section="Part 1. Petitioner/Applicant Information",
        pdf_field_name="Pt1Line3_Phone",
    ),
    FormField(
        id="petitioner_email",
        label="Email Address",
        field_type=FieldType.EMAIL,
        section="Part 1. Petitioner/Applicant Information",
        pdf_field_name="Pt1Line4_Email",
    ),
    # Part 2 - Information About Form Being Requested
    FormField(
        id="form_type",
        label="Form Type",
        field_type=FieldType.SELECT,
        required=True,
        section="Part 2. Form Being Requested",
        options=[
            "I-129 (H-1B)",
            "I-129 (L)",
            "I-129 (O)",
            "I-129 (P)",
            "I-129 (Q)",
            "I-129 (R)",
            "I-129 (TN)",
            "I-129 (E-1/E-2)",
            "I-140",
            "I-539",
        ],
        pdf_field_name="Pt2Line1_FormType",
    ),
    FormField(
        id="receipt_number",
        label="USCIS Receipt Number (if upgrading)",
        field_type=FieldType.TEXT,
        section="Part 2. Form Being Requested",
        help_text="If requesting premium processing for a pending case",
        pdf_field_name="Pt2Line2_ReceiptNumber",
    ),
    # Part 3 - Beneficiary Information
    FormField(
        id="beneficiary_name_last",
        label="Beneficiary Family Name",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Beneficiary Information",
        pdf_field_name="Pt3Line1a_FamilyName",
    ),
    FormField(
        id="beneficiary_name_first",
        label="Beneficiary Given Name",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Beneficiary Information",
        pdf_field_name="Pt3Line1b_GivenName",
    ),
    FormField(
        id="beneficiary_dob",
        label="Beneficiary Date of Birth",
        field_type=FieldType.DATE,
        required=True,
        section="Part 3. Beneficiary Information",
        pdf_field_name="Pt3Line2_DOB",
    ),
    FormField(
        id="beneficiary_country_birth",
        label="Beneficiary Country of Birth",
        field_type=FieldType.TEXT,
        required=True,
        section="Part 3. Beneficiary Information",
        pdf_field_name="Pt3Line3_CountryBirth",
    ),
]

# Form definitions registry
FORM_DEFINITIONS: dict[FormType, list[FormField]] = {
    FormType.I_140: I140_FIELDS,
    FormType.G_28: G28_FIELDS,
    FormType.I_907: I907_FIELDS,
}

# USCIS PDF URLs (for download reference)
USCIS_FORM_URLS = {
    FormType.I_140: "https://www.uscis.gov/sites/default/files/document/forms/i-140.pdf",
    FormType.G_28: "https://www.uscis.gov/sites/default/files/document/forms/g-28.pdf",
    FormType.I_907: "https://www.uscis.gov/sites/default/files/document/forms/i-907.pdf",
}

# Form filing fees (as of 2024)
FORM_FEES = {
    FormType.I_140: 715,
    FormType.G_28: 0,  # No filing fee
    FormType.I_907: 2805,  # Premium processing fee
}


class USCISFormsService:
    """Service for managing USCIS forms."""

    def __init__(self, forms_dir: str = "data/forms"):
        """Initialize forms service.

        Args:
            forms_dir: Directory for storing form data and PDFs
        """
        self.forms_dir = Path(forms_dir)
        self.forms_dir.mkdir(parents=True, exist_ok=True)

    def get_form_definition(self, form_type: FormType) -> dict[str, Any]:
        """Get form definition with all fields.

        Args:
            form_type: Type of USCIS form

        Returns:
            Dictionary with form metadata and field definitions
        """
        fields = FORM_DEFINITIONS.get(form_type, [])

        # Group fields by section
        sections: dict[str, list[dict[str, Any]]] = {}
        for field_def in fields:
            section_name = field_def.section or "General"
            if section_name not in sections:
                sections[section_name] = []
            sections[section_name].append(
                {
                    "id": field_def.id,
                    "label": field_def.label,
                    "type": field_def.field_type.value,
                    "required": field_def.required,
                    "help_text": field_def.help_text,
                    "options": field_def.options,
                    "max_length": field_def.max_length,
                }
            )

        return {
            "form_type": form_type.value,
            "title": self._get_form_title(form_type),
            "description": self._get_form_description(form_type),
            "fee": FORM_FEES.get(form_type, 0),
            "pdf_url": USCIS_FORM_URLS.get(form_type),
            "sections": sections,
            "total_fields": len(fields),
            "required_fields": sum(1 for f in fields if f.required),
        }

    def _get_form_title(self, form_type: FormType) -> str:
        """Get human-readable form title."""
        titles = {
            FormType.I_140: "I-140 - Immigrant Petition for Alien Workers",
            FormType.G_28: "G-28 - Notice of Entry of Appearance as Attorney",
            FormType.I_907: "I-907 - Request for Premium Processing Service",
            FormType.ETA_9089: "ETA-9089 - Application for Permanent Employment Certification",
        }
        return titles.get(form_type, form_type.value)

    def _get_form_description(self, form_type: FormType) -> str:
        """Get form description."""
        descriptions = {
            FormType.I_140: (
                "Used by employers or self-petitioners to classify aliens as "
                "employment-based immigrants, including EB-1A extraordinary ability."
            ),
            FormType.G_28: (
                "Filed by an attorney or accredited representative to notify USCIS "
                "of their representation of a petitioner, applicant, or beneficiary."
            ),
            FormType.I_907: (
                "Used to request 15-day premium processing for certain employment-based "
                "petitions and applications. Additional fee of $2,805 required."
            ),
            FormType.ETA_9089: (
                "Application for labor certification filed with DOL. Required for "
                "EB-2 and EB-3 categories, but NOT for EB-1A self-petitions."
            ),
        }
        return descriptions.get(form_type, "")

    def save_form_data(
        self, case_id: str, form_type: FormType, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Save form data for a case.

        Args:
            case_id: Case identifier
            form_type: Type of form
            data: Form field values

        Returns:
            Save result with file path
        """
        case_forms_dir = self.forms_dir / case_id
        case_forms_dir.mkdir(parents=True, exist_ok=True)

        file_path = case_forms_dir / f"{form_type.value.lower().replace('-', '_')}.json"

        form_data = {
            "form_type": form_type.value,
            "case_id": case_id,
            "data": data,
            "last_updated": date.today().isoformat(),
            "completion_status": self._calculate_completion(form_type, data),
        }

        file_path.write_text(json.dumps(form_data, indent=2, ensure_ascii=False))

        logger.info(
            "uscis_forms.saved",
            case_id=case_id,
            form_type=form_type.value,
            completion=form_data["completion_status"],
        )

        return {
            "success": True,
            "file_path": str(file_path),
            "completion_status": form_data["completion_status"],
        }

    def load_form_data(self, case_id: str, form_type: FormType) -> dict[str, Any] | None:
        """Load saved form data for a case.

        Args:
            case_id: Case identifier
            form_type: Type of form

        Returns:
            Form data or None if not found
        """
        file_path = self.forms_dir / case_id / f"{form_type.value.lower().replace('-', '_')}.json"

        if file_path.exists():
            return json.loads(file_path.read_text())
        return None

    def _calculate_completion(self, form_type: FormType, data: dict[str, Any]) -> dict[str, Any]:
        """Calculate form completion percentage.

        Args:
            form_type: Type of form
            data: Form field values

        Returns:
            Completion statistics
        """
        fields = FORM_DEFINITIONS.get(form_type, [])

        total_required = sum(1 for f in fields if f.required)
        filled_required = sum(1 for f in fields if f.required and data.get(f.id))

        total_optional = sum(1 for f in fields if not f.required)
        filled_optional = sum(1 for f in fields if not f.required and data.get(f.id))

        return {
            "required_filled": filled_required,
            "required_total": total_required,
            "optional_filled": filled_optional,
            "optional_total": total_optional,
            "percent_required": (
                int((filled_required / total_required) * 100) if total_required > 0 else 100
            ),
            "percent_total": (
                int(((filled_required + filled_optional) / len(fields)) * 100) if fields else 100
            ),
            "is_complete": filled_required == total_required,
        }

    def auto_populate_from_case(
        self, form_type: FormType, case_data: dict[str, Any], user_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Auto-populate form fields from case data.

        Args:
            form_type: Type of form
            case_data: Case information
            user_data: User/beneficiary information

        Returns:
            Pre-filled form data
        """
        data = {}

        # Common beneficiary fields
        if "full_name" in user_data:
            name_parts = user_data["full_name"].split()
            if len(name_parts) >= 2:
                data["beneficiary_given_name"] = name_parts[0]
                data["beneficiary_family_name"] = name_parts[-1]
                if len(name_parts) > 2:
                    data["beneficiary_middle_name"] = " ".join(name_parts[1:-1])

                # G-28 client fields
                data["client_name_first"] = name_parts[0]
                data["client_name_last"] = name_parts[-1]

                # I-907 beneficiary
                data["beneficiary_name_first"] = name_parts[0]
                data["beneficiary_name_last"] = name_parts[-1]

        if "email" in user_data:
            data["beneficiary_email"] = user_data["email"]

        if "phone" in user_data:
            data["beneficiary_phone"] = user_data["phone"]

        if "date_of_birth" in user_data:
            data["beneficiary_dob"] = user_data["date_of_birth"]

        if "country_of_birth" in user_data:
            data["beneficiary_country_birth"] = user_data["country_of_birth"]
            data["beneficiary_country_citizenship"] = user_data.get(
                "country_of_citizenship", user_data["country_of_birth"]
            )

        if "current_address" in user_data:
            addr = user_data["current_address"]
            data["beneficiary_current_address_street"] = addr.get("street", "")
            data["beneficiary_current_address_city"] = addr.get("city", "")
            data["beneficiary_current_address_country"] = addr.get("country", "")

        # I-140 specific
        if form_type == FormType.I_140:
            # Default to EB-1A extraordinary ability
            data["petition_type"] = "An alien of extraordinary ability (E11)"
            data["petitioner_type"] = "Self-petitioner"

            if "job_title" in case_data:
                data["job_title"] = case_data["job_title"]

            if "salary" in case_data:
                data["wage_offered"] = str(case_data["salary"])

        # I-907 specific
        if form_type == FormType.I_907:
            data["form_type"] = "I-140"

        return data

    def get_all_forms_status(self, case_id: str) -> list[dict[str, Any]]:
        """Get status of all forms for a case.

        Args:
            case_id: Case identifier

        Returns:
            List of form statuses
        """
        statuses = []

        for form_type in [FormType.I_140, FormType.G_28, FormType.I_907]:
            form_data = self.load_form_data(case_id, form_type)

            if form_data:
                statuses.append(
                    {
                        "form_type": form_type.value,
                        "title": self._get_form_title(form_type),
                        "status": (
                            "in_progress"
                            if not form_data["completion_status"]["is_complete"]
                            else "complete"
                        ),
                        "completion": form_data["completion_status"],
                        "last_updated": form_data.get("last_updated"),
                        "fee": FORM_FEES.get(form_type, 0),
                    }
                )
            else:
                statuses.append(
                    {
                        "form_type": form_type.value,
                        "title": self._get_form_title(form_type),
                        "status": "not_started",
                        "completion": {
                            "percent_required": 0,
                            "percent_total": 0,
                            "is_complete": False,
                        },
                        "fee": FORM_FEES.get(form_type, 0),
                    }
                )

        return statuses


# Global instance
_forms_service: USCISFormsService | None = None


def get_forms_service() -> USCISFormsService:
    """Get or create global forms service instance."""
    global _forms_service
    if _forms_service is None:
        _forms_service = USCISFormsService()
    return _forms_service


# =============================================================================
# PDF Form Filling Functions (using pymupdf/fitz)
# =============================================================================

# Path to USCIS fillable PDF forms
USCIS_FORMS_DIR = Path("data/uscis_forms/fillable")


def _parse_name(full_name: str) -> dict[str, str]:
    """Parse full name into family, given, and middle names."""
    parts = full_name.strip().split()
    if len(parts) >= 3:
        return {
            "family": parts[-1],
            "given": parts[0],
            "middle": " ".join(parts[1:-1]),
        }
    if len(parts) == 2:
        return {"family": parts[-1], "given": parts[0], "middle": ""}
    if len(parts) == 1:
        return {"family": parts[0], "given": "", "middle": ""}
    return {"family": "", "given": "", "middle": ""}


def _parse_address(address: str) -> dict[str, str]:
    """Parse address string into components."""
    # Simple parser - expects format: "123 Main St, City, State ZIP"
    result = {
        "street": "",
        "city": "",
        "state": "",
        "zip": "",
        "apt": "",
    }

    if not address:
        return result

    parts = [p.strip() for p in address.split(",")]

    if len(parts) >= 1:
        result["street"] = parts[0]

    if len(parts) >= 2:
        result["city"] = parts[1]

    if len(parts) >= 3:
        # Parse "State ZIP" or just "State"
        state_zip = parts[2].strip().split()
        if len(state_zip) >= 1:
            result["state"] = state_zip[0]
        if len(state_zip) >= 2:
            result["zip"] = state_zip[-1]

    return result


def _format_date(date_str: str | None) -> str:
    """Format date to MM/DD/YYYY format."""
    if not date_str:
        return ""

    try:
        from datetime import datetime as dt

        # Try parsing various formats
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
            try:
                parsed = dt.strptime(date_str, fmt)
                return parsed.strftime("%m/%d/%Y")
            except ValueError:
                continue
        return date_str
    except Exception:
        return date_str


def fill_g1145_pdf(
    output_path: Path,
    user_data: dict[str, Any],
) -> Path:
    """
    Fill G-1145 e-Notification form.

    Args:
        output_path: Path to save the filled PDF
        user_data: User data containing name, email, phone

    Returns:
        Path to the filled PDF
    """
    try:
        import fitz
    except ImportError:
        logger.error("pymupdf not installed")
        raise ImportError("pymupdf is required for PDF form filling")

    src_path = USCIS_FORMS_DIR / "g-1145.pdf"
    if not src_path.exists():
        raise FileNotFoundError(f"G-1145 form not found at {src_path}")

    # Parse name
    name = _parse_name(user_data.get("full_name", ""))

    # Field mappings for G-1145
    field_data = {
        "form1[0].#subform[0].LastName[0]": name["family"],
        "form1[0].#subform[0].FirstName[0]": name["given"],
        "form1[0].#subform[0].MiddleName[0]": name["middle"],
        "form1[0].#subform[0].Email[0]": user_data.get("email", ""),
        "form1[0].#subform[0].MobilePhoneNumber[0]": user_data.get("phone", ""),
    }

    # Open and fill the form
    doc = fitz.open(str(src_path))

    for page in doc:
        for widget in page.widgets():
            field_name = widget.field_name
            if field_name in field_data:
                widget.field_value = field_data[field_name]
                widget.update()

    doc.save(str(output_path))
    doc.close()

    logger.info(f"Filled G-1145 saved to {output_path}")
    return output_path


def fill_i140_pdf(
    output_path: Path,
    case_data: dict[str, Any],
    user_data: dict[str, Any],
) -> Path:
    """
    Fill I-140 Immigrant Petition form for EB-1A.

    Args:
        output_path: Path to save the filled PDF
        case_data: Case data containing field, job info
        user_data: User data containing personal info

    Returns:
        Path to the filled PDF
    """
    try:
        import fitz
    except ImportError:
        raise ImportError("pymupdf is required for PDF form filling")

    src_path = USCIS_FORMS_DIR / "i-140.pdf"
    if not src_path.exists():
        raise FileNotFoundError(f"I-140 form not found at {src_path}")

    # Parse name and address
    name = _parse_name(user_data.get("full_name", ""))
    address = _parse_address(user_data.get("address", ""))

    # For EB-1A self-petition, petitioner = beneficiary
    # Field mappings for I-140
    field_data = {
        # Part 1: Petitioner Info (for self-petition, same as beneficiary)
        "form1[0].#subform[0].Pt1Line1a_FamilyName[0]": name["family"],
        "form1[0].#subform[0].Pt1Line1b_GivenName[0]": name["given"],
        "form1[0].#subform[0].Pt1Line1c_MiddleName[0]": name["middle"],
        "form1[0].#subform[0].Line6a_InCareofName[0]": "",
        "form1[0].#subform[0].Line6b_StreetNumberName[0]": address["street"],
        "form1[0].#subform[0].Line6c_AptSteFlrNumber[0]": address["apt"],
        "form1[0].#subform[0].Line6d_CityOrTown[0]": address["city"],
        "form1[0].#subform[0].Line6e_State[0]": address["state"],
        "form1[0].#subform[0].Line6f_ZipCode[0]": address["zip"],
        "form1[0].#subform[0].Line6i_Country[0]": "United States",
        # Part 3: Beneficiary Info (same as petitioner for self-petition)
        "form1[0].#subform[1].Pt3Line1a_FamilyName[0]": name["family"],
        "form1[0].#subform[1].Pt3Line1b_GivenName[0]": name["given"],
        "form1[0].#subform[1].Pt3Line1c_MiddleName[0]": name["middle"],
        "form1[0].#subform[1].Line2a_InCareofName[0]": "",
        "form1[0].#subform[1].Line2b_StreetNumberName[0]": address["street"],
        "form1[0].#subform[1].Line2c_AptSteFlrNumber[0]": address["apt"],
        "form1[0].#subform[1].Line2d_CityOrTown[0]": address["city"],
        "form1[0].#subform[1].Line2e_State[0]": address["state"],
        "form1[0].#subform[1].Line2f_ZipCode[0]": address["zip"],
        "form1[0].#subform[1].Line2i_Country[0]": "United States",
        # Beneficiary personal info
        "form1[0].#subform[1].Line5_DateOfBirth[0]": _format_date(user_data.get("date_of_birth")),
        "form1[0].#subform[1].Line6_CityTownOfBirth[0]": user_data.get("city_of_birth", ""),
        "form1[0].#subform[1].Line8_Country[0]": user_data.get("country_of_birth", ""),
        "form1[0].#subform[1].Line9_Country[0]": user_data.get("country_of_citizenship", ""),
        "form1[0].#subform[1].Line14b_Passport[0]": user_data.get("passport_number", ""),
        "form1[0].#subform[1].Line14d_CountryOfIssuance[0]": user_data.get("passport_country", ""),
        "form1[0].#subform[1].Line14e_ExpDate[0]": _format_date(user_data.get("passport_expiry")),
        # Part 5: Job Info
        "form1[0].#subform[3].Line1_JobTitle[0]": case_data.get(
            "job_title", user_data.get("job_title", "")
        ),
        "form1[0].#subform[3].Line3_JobDescription[0]": case_data.get("job_description", ""),
        "form1[0].#subform[3].Line3a_Occupation[0]": case_data.get("field", "Software Development"),
        "form1[0].#subform[3].Line8_Wages[0]": str(user_data.get("salary", "")),
        "form1[0].#subform[3].Line8_Per[0]": "Year",
    }

    # Checkboxes for EB-1A self-petition
    checkbox_fields = {
        # Part 2: E11 Extraordinary ability checkbox
        "form1[0].#subform[0].prt2PetitionType[0]": True,
        # Part 4: Self-petition checkbox
        "form1[0].#subform[2].Line1b_Self[0]": True,
    }

    # Open and fill the form
    doc = fitz.open(str(src_path))

    for page in doc:
        for widget in page.widgets():
            field_name = widget.field_name
            if field_name in field_data:
                widget.field_value = str(field_data[field_name])
                widget.update()
            elif checkbox_fields.get(field_name):
                widget.field_value = True
                widget.update()

    doc.save(str(output_path))
    doc.close()

    logger.info(f"Filled I-140 saved to {output_path}")
    return output_path


def fill_i907_pdf(
    output_path: Path,
    case_data: dict[str, Any],
    user_data: dict[str, Any],
) -> Path:
    """
    Fill I-907 Premium Processing form.

    Args:
        output_path: Path to save the filled PDF
        case_data: Case data
        user_data: User data containing personal info

    Returns:
        Path to the filled PDF
    """
    try:
        import fitz
    except ImportError:
        raise ImportError("pymupdf is required for PDF form filling")

    src_path = USCIS_FORMS_DIR / "i-907.pdf"
    if not src_path.exists():
        raise FileNotFoundError(f"I-907 form not found at {src_path}")

    # Parse name and address
    name = _parse_name(user_data.get("full_name", ""))
    address = _parse_address(user_data.get("address", ""))

    # Field mappings for I-907
    field_data = {
        # Part 1: Requestor Info
        "form1[0].#subform[0].Pt1Line3_FamilyName[0]": name["family"],
        "form1[0].#subform[0].Pt1Line3_GivenName[0]": name["given"],
        "form1[0].#subform[0].Pt1Line3_MiddleName[0]": name["middle"],
        "form1[0].#subform[0].Part1_Line5_MailingAddress_StreetNumberName[0]": address["street"],
        "form1[0].#subform[0].Part1_Line5_MailingAddress_CityTown[0]": address["city"],
        "form1[0].#subform[0].Part1_Line5_MailingAddress_State[0]": address["state"],
        "form1[0].#subform[0].Part1_Line5_MailingAddress_ZipCode[0]": address["zip"],
        "form1[0].#subform[0].Part1_Line5_MailingAddress_Country[0]": "United States",
        # Part 2: Form being filed
        "form1[0].#subform[1].P2_Line1_FormNumberof[0]": "I-140",
        "form1[0].#subform[1].P2_Line2_ClassorEligRequested[0]": "E11 - Extraordinary Ability",
        # Petitioner/Applicant name (same person for self-petition)
        "form1[0].#subform[1].Part2_Line4_PetitionerApplicantFamilyName[0]": name["family"],
        "form1[0].#subform[1].Part2_Line4_PetitionerApplicantGivenName[0]": name["given"],
        "form1[0].#subform[1].Part2_Line4_PetitionerApplicantMiddleName[0]": name["middle"],
        # Beneficiary name (same person for self-petition)
        "form1[0].#subform[1].Line_FamilyName[0]": name["family"],
        "form1[0].#subform[1].Line_GivenName[0]": name["given"],
        "form1[0].#subform[1].Line_MiddleName[0]": name["middle"],
        # Part 3: Contact info
        "form1[0].#subform[2].P3_Line4_DaytimeTelePhoneNumber[0]": user_data.get("phone", ""),
        "form1[0].#subform[2].P3_Line6_Email[0]": user_data.get("email", ""),
    }

    # Checkboxes
    checkbox_fields = {
        # Part 1 Line 6 - Petitioner/Applicant checkbox
        "form1[0].#subform[0].Part1Line6_Checkbox[0]": True,
    }

    # Open and fill the form
    doc = fitz.open(str(src_path))

    for page in doc:
        for widget in page.widgets():
            field_name = widget.field_name
            if field_name in field_data:
                widget.field_value = str(field_data[field_name])
                widget.update()
            elif checkbox_fields.get(field_name):
                widget.field_value = True
                widget.update()

    doc.save(str(output_path))
    doc.close()

    logger.info(f"Filled I-907 saved to {output_path}")
    return output_path


def fill_g28_pdf(
    output_path: Path,
    case_data: dict[str, Any],
    user_data: dict[str, Any],
    attorney_data: dict[str, Any] | None = None,
) -> Path:
    """
    Fill G-28 Attorney Appearance form.

    Args:
        output_path: Path to save the filled PDF
        case_data: Case data
        user_data: User data (client info)
        attorney_data: Attorney information

    Returns:
        Path to the filled PDF
    """
    try:
        import fitz
    except ImportError:
        raise ImportError("pymupdf is required for PDF form filling")

    src_path = USCIS_FORMS_DIR / "g-28.pdf"
    if not src_path.exists():
        raise FileNotFoundError(f"G-28 form not found at {src_path}")

    # Default attorney data if not provided
    if attorney_data is None:
        attorney_data = {}

    # Parse names
    client_name = _parse_name(user_data.get("full_name", ""))
    client_address = _parse_address(user_data.get("address", ""))

    # Field mappings for G-28
    field_data = {
        # Part 1: Client Info
        "form1[0].#subform[0].Pt1Line2a_FamilyName[0]": client_name["family"],
        "form1[0].#subform[0].Pt1Line2b_GivenName[0]": client_name["given"],
        "form1[0].#subform[0].Pt1Line2c_MiddleName[0]": client_name["middle"],
        "form1[0].#subform[0].Line3a_StreetNumber[0]": client_address["street"],
        "form1[0].#subform[0].Line3b_AptSteFlrNumber[0]": client_address["apt"],
        "form1[0].#subform[0].Line3c_CityOrTown[0]": client_address["city"],
        "form1[0].#subform[0].Line3d_State[0]": client_address["state"],
        "form1[0].#subform[0].Line3e_ZipCode[0]": client_address["zip"],
        "form1[0].#subform[0].Line3h_Country[0]": "United States",
        "form1[0].#subform[0].Line4_DaytimeTelephoneNumber[0]": user_data.get("phone", ""),
        "form1[0].#subform[0].Line6_EMail[0]": user_data.get("email", ""),
        # Part 2: Attorney Info
        "form1[0].#subform[0].Line3_NameofAttorneyOrRep[0]": attorney_data.get("full_name", ""),
        "form1[0].#subform[0].Pt2Line1a_LicensingAuthority[0]": attorney_data.get(
            "licensing_authority", ""
        ),
        "form1[0].#subform[0].Pt2Line1b_BarNumber[0]": attorney_data.get("bar_number", ""),
        "form1[0].#subform[0].Pt2Line1d_NameofFirmOrOrganization[0]": attorney_data.get(
            "firm_name", ""
        ),
        # Part 3: Representation scope
        "form1[0].#subform[1].Line1b_ListFormNumber[0]": "I-140",
        # Client name again in Part 3
        "form1[0].#subform[1].Pt3Line5a_FamilyName[0]": client_name["family"],
        "form1[0].#subform[1].Pt3Line5b_GivenName[0]": client_name["given"],
        "form1[0].#subform[1].Pt3Line5c_MiddleName[0]": client_name["middle"],
    }

    # Checkboxes
    checkbox_fields = {
        "form1[0].#subform[0].CheckBox1[0]": True,  # Attorney checkbox
        "form1[0].#subform[1].Line1a_USCIS[0]": True,  # USCIS checkbox
    }

    # Open and fill the form
    doc = fitz.open(str(src_path))

    for page in doc:
        for widget in page.widgets():
            field_name = widget.field_name
            if field_name in field_data:
                widget.field_value = str(field_data[field_name])
                widget.update()
            elif checkbox_fields.get(field_name):
                widget.field_value = True
                widget.update()

    doc.save(str(output_path))
    doc.close()

    logger.info(f"Filled G-28 saved to {output_path}")
    return output_path


def copy_blank_form(form_name: str, output_path: Path) -> Path:
    """
    Copy a blank USCIS form (fallback when filling fails).

    Args:
        form_name: Name of the form (g-1145, i-140, i-907, g-28)
        output_path: Path to save the copy

    Returns:
        Path to the copied form
    """
    import shutil

    src_path = USCIS_FORMS_DIR / f"{form_name}.pdf"
    if src_path.exists():
        shutil.copy2(src_path, output_path)
        logger.info(f"Copied blank {form_name} to {output_path}")
    else:
        raise FileNotFoundError(f"Form {form_name} not found at {src_path}")
    return output_path
