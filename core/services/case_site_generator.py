from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
import structlog

logger = structlog.get_logger(__name__)

# Path to USCIS fillable PDF forms
USCIS_FORMS_DIR = Path("data/uscis_forms/fillable")


# EB-1A Criteria mapping for USCIS 8 CFR 204.5(h)(3)
EB1A_CRITERIA = {
    "awards": {
        "number": 1,
        "title": "Awards",
        "tab": "B",
        "regulatory": "8 CFR 204.5(h)(3)(i)",
    },
    "membership": {
        "number": 2,
        "title": "Membership",
        "tab": "C",
        "regulatory": "8 CFR 204.5(h)(3)(ii)",
    },
    "press": {
        "number": 3,
        "title": "Published Material",
        "tab": "D",
        "regulatory": "8 CFR 204.5(h)(3)(iii)",
    },
    "judging": {
        "number": 4,
        "title": "Judging",
        "tab": "E",
        "regulatory": "8 CFR 204.5(h)(3)(iv)",
    },
    "contribution": {
        "number": 5,
        "title": "Original Contribution",
        "tab": "F",
        "regulatory": "8 CFR 204.5(h)(3)(v)",
    },
    "articles": {
        "number": 6,
        "title": "Scholarly Articles",
        "tab": "G",
        "regulatory": "8 CFR 204.5(h)(3)(vi)",
    },
    "exhibitions": {
        "number": 7,
        "title": "Exhibitions",
        "tab": "J",
        "regulatory": "8 CFR 204.5(h)(3)(vii)",
    },
    "leading_role": {
        "number": 8,
        "title": "Leading Role",
        "tab": "H",
        "regulatory": "8 CFR 204.5(h)(3)(viii)",
    },
    "salary": {
        "number": 9,
        "title": "High Salary",
        "tab": "I",
        "regulatory": "8 CFR 204.5(h)(3)(ix)",
    },
    "commercial": {
        "number": 10,
        "title": "Commercial Success",
        "tab": "J",
        "regulatory": "8 CFR 204.5(h)(3)(x)",
    },
}

# Tab organization for exhibits
EXHIBIT_TABS = {
    "A": {"name": "Identity", "criteria": []},
    "B": {"name": "Awards", "criteria": ["awards"]},
    "C": {"name": "Membership", "criteria": ["membership"]},
    "D": {"name": "Press", "criteria": ["press"]},
    "E": {"name": "Judging", "criteria": ["judging"]},
    "F": {"name": "Contribution", "criteria": ["contribution"]},
    "G": {"name": "Articles", "criteria": ["articles"]},
    "H": {"name": "Role", "criteria": ["leading_role"]},
    "I": {"name": "Salary", "criteria": ["salary"]},
    "J": {"name": "Other", "criteria": ["exhibitions", "commercial"]},
}


class CaseSiteGenerator:
    """
    Generates a static website structure for a specific legal case.
    Creates directories, renders HTML from templates, and sets up assets.
    Follows USCIS Policy Manual structure for EB-1A petitions.
    """

    def __init__(
        self, base_output_dir: str = "sites", template_dir: str = "core/templates/case_site"
    ):
        self.base_output_dir = Path(base_output_dir)
        self.template_dir = Path(template_dir)

        # Initialize Jinja2 environment with autoescape for security
        if self.template_dir.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(["html", "htm", "xml"]),
            )
        else:
            logger.warning(f"Template directory {self.template_dir} not found.")
            self.env = None

    def generate_site(
        self,
        case_id: str,
        case_data: dict[str, Any],
        user_data: dict[str, Any],
        petition_sections: dict[str, str] | None = None,
        exhibits: dict[str, list[dict[str, Any]]] | None = None,
    ) -> str:
        """Generate the full site for a case.

        Args:
            case_id: Unique case identifier
            case_data: Dictionary containing case details (field, criteria, etc.)
            user_data: Dictionary containing user details (name, email, etc.)
            petition_sections: Optional dict mapping section names to HTML content
            exhibits: Optional dict mapping tab names to lists of exhibit dicts

        Returns:
            Path to the generated site root
        """
        site_root = self.base_output_dir / case_id

        try:
            # 1. Create Directory Structure
            self._create_structure(site_root)

            # 2. Prepare Context
            context = self._prepare_context(
                case_id, case_data, user_data, petition_sections, exhibits
            )

            # 3. Render and Write Pages
            if self.env:
                self._render_page("index.html", site_root / "index.html", context, page="index")
                self._render_page(
                    "forms.html", site_root / "forms" / "index.html", context, page="forms"
                )
                self._render_page(
                    "petition.html", site_root / "petition" / "index.html", context, page="petition"
                )
                self._render_page(
                    "exhibits.html", site_root / "exhibits" / "index.html", context, page="exhibits"
                )

            logger.info(f"Case site generated successfully at {site_root}")
            return str(site_root)

        except Exception as e:
            logger.error(f"Failed to generate case site for {case_id}: {e!s}")
            raise

    def _prepare_context(
        self,
        case_id: str,
        case_data: dict[str, Any],
        user_data: dict[str, Any],
        petition_sections: dict[str, str] | None = None,
        exhibits: dict[str, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """Prepare the context dictionary for template rendering.

        Args:
            case_id: Unique case identifier
            case_data: Case details
            user_data: User details
            petition_sections: Generated petition section content
            exhibits: Organized exhibits by tab

        Returns:
            Context dictionary for templates
        """
        # Initialize empty structures if not provided
        sections = petition_sections or {}
        exhibits_data = exhibits or {}

        # Calculate progress based on sections and exhibits
        completed_sections = sum(1 for v in sections.values() if v)
        total_sections = 12  # executive_summary + 10 criteria + conclusion

        total_exhibits = sum(len(v) for v in exhibits_data.values())
        uploaded_count = total_exhibits
        pending_count = max(0, 10 - total_exhibits)  # Assume minimum 10 exhibits needed

        context = {
            "case": {
                "case_id": case_id,
                "case_data": case_data,
                "user_data": user_data,
                "created_at": case_data.get("created_at", "Just now"),
                "status": case_data.get("status", "active"),
            },
            "progress": {
                "petition_percent": int((completed_sections / total_sections) * 100),
                "exhibits_count": total_exhibits,
                "exhibits_target": max(10, total_exhibits),
            },
            # Petition sections content
            "sections": sections,
            "petition_status": "draft" if completed_sections < total_sections else "complete",
            # Exhibits organized by tab
            "exhibits": exhibits_data,
            "total_exhibits": total_exhibits,
            "uploaded_count": uploaded_count,
            "pending_count": pending_count,
            # Criteria metadata
            "criteria": EB1A_CRITERIA,
            "exhibit_tabs": EXHIBIT_TABS,
            # Forms status for forms.html
            "forms_status": {
                "i140": {"filled": 0, "total": 28, "percent": 0},
                "g28": {"filled": 0, "total": 12, "percent": 0},
                "i907": {"filled": 0, "total": 10, "percent": 0},
            },
            "total_fees": "3,520",  # $715 + $2,805
        }

        return context

    def _create_structure(self, site_root: Path):
        """Creates the standard directory layout and copies assets."""
        directories = [
            site_root,
            site_root / "assets" / "css",
            site_root / "assets" / "js",
            site_root / "assets" / "img",
            site_root / "assets" / "forms",
            site_root / "forms",
            site_root / "petition",
            site_root / "exhibits",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        # Copy USCIS PDF forms to site assets
        self._copy_uscis_forms(site_root / "assets" / "forms")

    def _copy_uscis_forms(self, forms_dir: Path):
        """Copy USCIS fillable PDF forms to site assets."""
        if not USCIS_FORMS_DIR.exists():
            logger.warning(f"USCIS forms directory not found: {USCIS_FORMS_DIR}")
            return

        pdf_forms = ["i-140.pdf", "g-28.pdf", "i-907.pdf", "g-1145.pdf"]
        for form_name in pdf_forms:
            src = USCIS_FORMS_DIR / form_name
            dst = forms_dir / form_name
            if src.exists():
                shutil.copy2(src, dst)
                logger.debug(f"Copied {form_name} to {dst}")
            else:
                logger.warning(f"Form not found: {src}")

    def _render_page(
        self, template_name: str, output_path: Path, context: dict[str, Any], page: str
    ):
        """Renders a single Jinja2 template to a file."""
        try:
            template = self.env.get_template(template_name)
            # Add current page to context for active nav highlighting
            page_context = context.copy()
            page_context["page"] = page
            # Add base_path for correct relative navigation from subdirectories
            page_context["base_path"] = "../" if page != "index" else ""

            content = template.render(**page_context)
            output_path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error(f"Error rendering {template_name}: {e}")
            # Fallback for missing templates
            output_path.write_text(f"<h1>Error rendering {template_name}</h1><pre>{e}</pre>")

    def generate_with_petition_data(
        self,
        case_id: str,
        case_data: dict[str, Any],
        user_data: dict[str, Any],
        petition_response: dict[str, Any],
    ) -> str:
        """Generate site with data from petition generator.

        This method takes the output from the EB-1A petition generator
        and creates a site with all sections populated.

        Args:
            case_id: Unique case identifier
            case_data: Case details
            user_data: User details
            petition_response: Response from EB1ACoordinator.generate_petition()

        Returns:
            Path to the generated site root
        """
        # Extract sections from petition response
        sections = {}

        if "executive_summary" in petition_response:
            sections["executive_summary"] = petition_response["executive_summary"]

        if "conclusion" in petition_response:
            sections["conclusion"] = petition_response["conclusion"]

        # Extract individual criterion sections
        if "sections" in petition_response:
            for section in petition_response["sections"]:
                # Map section keys to template keys
                criterion_key = section.get("criterion", "").lower().replace(" ", "_")
                if criterion_key in EB1A_CRITERIA:
                    sections[criterion_key] = section.get("content", "")

        return self.generate_site(
            case_id=case_id,
            case_data=case_data,
            user_data=user_data,
            petition_sections=sections,
        )


# Singleton instance for easy import
site_generator = CaseSiteGenerator()
