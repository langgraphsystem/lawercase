from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = structlog.get_logger(__name__)


class CaseSiteGenerator:
    """
    Generates a static website structure for a specific legal case.
    Creates directories, renders HTML from templates, and sets up assets.
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
        self, case_id: str, case_data: dict[str, Any], user_data: dict[str, Any]
    ) -> str:
        """Generate the full site for a case.

        Args:
            case_id: Unique case identifier
            case_data: Dictionary containing case details (field, criteria, etc.)
            user_data: Dictionary containing user details (name, email, etc.)

        Returns:
            Path to the generated site root
        """
        site_root = self.base_output_dir / case_id

        try:
            # 1. Create Directory Structure
            self._create_structure(site_root)

            # 2. Prepare Context
            context = {
                "case": {
                    "case_id": case_id,
                    "case_data": case_data,
                    "user_data": user_data,
                    "created_at": "Just now",  # In real app, pass datetime
                    "status": "active",
                },
                "progress": {"petition_percent": 10, "exhibits_count": 0, "exhibits_target": 10},
            }

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

    def _create_structure(self, site_root: Path):
        """Creates the standard directory layout."""
        directories = [
            site_root,
            site_root / "assets" / "css",
            site_root / "assets" / "js",
            site_root / "assets" / "img",
            site_root / "forms",
            site_root / "petition",
            site_root / "exhibits",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _render_page(
        self, template_name: str, output_path: Path, context: dict[str, Any], page: str
    ):
        """Renders a single Jinja2 template to a file."""
        try:
            template = self.env.get_template(template_name)
            # Add current page to context for active nav highlighting
            page_context = context.copy()
            page_context["page"] = page

            content = template.render(**page_context)
            output_path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error(f"Error rendering {template_name}: {e}")
            # Fallback for missing templates
            output_path.write_text(f"<h1>Error rendering {template_name}</h1><pre>{e}</pre>")


# Singleton instance for easy import
site_generator = CaseSiteGenerator()
