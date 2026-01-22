"""LaTeX PDF Generator Service.

Generates high-quality PDF documents using LaTeX (pdflatex).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class LaTeXGenerator:
    """Generates PDF documents using LaTeX."""

    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates" / "latex"
        self._pdflatex_path = None

    def _find_pdflatex(self) -> str:
        """Find pdflatex executable."""
        if self._pdflatex_path:
            return self._pdflatex_path

        # Check common locations
        possible_paths = [
            "pdflatex",  # In PATH
            r"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe",
            r"C:\Users\Etsy\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe",
            r"C:\texlive\2024\bin\windows\pdflatex.exe",
        ]

        for path in possible_paths:
            if shutil.which(path):
                self._pdflatex_path = path
                return path

            if Path(path).exists():
                self._pdflatex_path = path
                return path

        raise RuntimeError("pdflatex not found. Please install MiKTeX or TeX Live.")

    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters in text."""
        if not text:
            return ""
        # Order matters: escape backslash first
        replacements = [
            ("\\", r"\textbackslash{}"),
            ("&", r"\&"),
            ("%", r"\%"),
            ("$", r"\$"),
            ("#", r"\#"),
            ("_", r"\_"),
            ("{", r"\{"),
            ("}", r"\}"),
            ("~", r"\textasciitilde{}"),
            ("^", r"\textasciicircum{}"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _format_name_with_title(self, name: str) -> str:
        """Add Mr./Ms. prefix if not present."""
        if not name.startswith(("Mr.", "Ms.", "Mrs.", "Dr.")):
            return f"Mr. {name}"
        return name

    def _compile_latex(self, tex_content: str, output_path: Path) -> Path:
        """Compile LaTeX content to PDF."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tex_file = temp_path / "document.tex"
            tex_file.write_text(tex_content, encoding="utf-8")

            pdflatex = self._find_pdflatex()

            # Run pdflatex twice for proper references
            for _ in range(2):
                result = subprocess.run(
                    [
                        pdflatex,
                        "-interaction=nonstopmode",
                        "-output-directory",
                        str(temp_path),
                        str(tex_file),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=temp_path,
                )

            pdf_file = temp_path / "document.pdf"
            if not pdf_file.exists():
                raise RuntimeError(f"LaTeX compilation failed:\n{result.stdout}\n{result.stderr}")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(pdf_file, output_path)

        return output_path

    def generate_cover_page(
        self,
        output_path: Path,
        name: str,
        include_premium: bool = True,
        page_info: dict[str, int] | None = None,
    ) -> Path:
        """Generate cover page (Table of Contents) using LaTeX."""
        if page_info is None:
            page_info = {
                "passport": 19,
                "petition": 21,
                "statement": 81,
                "exhibits_list": 83,
                "exhibits_start": 93,
                "exhibits_count": 169,
            }

        name_escaped = self._escape_latex(name)
        name_with_title = self._format_name_with_title(name_escaped)

        template_path = self.templates_dir / "cover_page.tex"
        template_content = template_path.read_text(encoding="utf-8")

        # Premium processing item
        if include_premium:
            premium_item = r"\item Form I-907, Request for Premium Processing Service, with the \$2805 filing fee."
        else:
            premium_item = ""

        replacements = {
            "<<CLIENT_NAME>>": name_escaped,
            "<<CLIENT_NAME_TITLE>>": name_with_title,
            "<<PASSPORT_PAGE>>": str(page_info.get("passport", 19)),
            "<<PETITION_PAGE>>": str(page_info.get("petition", 21)),
            "<<STATEMENT_PAGE>>": str(page_info.get("statement", 81)),
            "<<EXHIBITS_LIST_PAGE>>": str(page_info.get("exhibits_list", 83)),
            "<<EXHIBITS_START_PAGE>>": str(page_info.get("exhibits_start", 93)),
            "<<EXHIBITS_COUNT>>": str(page_info.get("exhibits_count", 169)),
            "<<PREMIUM_ITEM>>": premium_item,
        }

        for placeholder, value in replacements.items():
            template_content = template_content.replace(placeholder, value)

        return self._compile_latex(template_content, output_path)

    def generate_petition_letter(
        self,
        output_path: Path,
        name: str,
        field: str,
        sections: dict[str, str] | None = None,
    ) -> Path:
        """Generate the petition letter using LaTeX."""
        if sections is None:
            sections = {}

        name_escaped = self._escape_latex(name)
        name_with_title = self._format_name_with_title(name_escaped)
        field_escaped = self._escape_latex(field)

        template_path = self.templates_dir / "petition_letter.tex"
        template_content = template_path.read_text(encoding="utf-8")

        # Default section content
        default_sections = {
            "summary": "[Summary content to be added]",
            "awards": "[Awards evidence to be added]",
            "membership": "[Membership evidence to be added]",
            "press": "[Published material to be added]",
            "judging": "[Judging evidence to be added]",
            "contributions": "[Original contributions to be added]",
            "scholarly": "[Scholarly articles to be added]",
            "exhibitions": "[Exhibitions evidence to be added]",
            "leading_role": "[Leading role evidence to be added]",
            "salary": "[High salary evidence to be added]",
            "final_merits": "[Final merits determination to be added]",
            "national_importance": "[National importance content to be added]",
        }

        replacements = {
            "<<CLIENT_NAME>>": name_escaped,
            "<<CLIENT_NAME_TITLE>>": name_with_title,
            "<<CLIENT_FIELD>>": field_escaped,
            "<<SECTION_SUMMARY>>": self._escape_latex(
                sections.get("summary", default_sections["summary"])
            ),
            "<<SECTION_AWARDS>>": self._escape_latex(
                sections.get("awards", default_sections["awards"])
            ),
            "<<SECTION_MEMBERSHIP>>": self._escape_latex(
                sections.get("membership", default_sections["membership"])
            ),
            "<<SECTION_PRESS>>": self._escape_latex(
                sections.get("press", default_sections["press"])
            ),
            "<<SECTION_JUDGING>>": self._escape_latex(
                sections.get("judging", default_sections["judging"])
            ),
            "<<SECTION_CONTRIBUTIONS>>": self._escape_latex(
                sections.get("contributions", default_sections["contributions"])
            ),
            "<<SECTION_SCHOLARLY>>": self._escape_latex(
                sections.get("scholarly", default_sections["scholarly"])
            ),
            "<<SECTION_EXHIBITIONS>>": self._escape_latex(
                sections.get("exhibitions", default_sections["exhibitions"])
            ),
            "<<SECTION_LEADING_ROLE>>": self._escape_latex(
                sections.get("leading_role", default_sections["leading_role"])
            ),
            "<<SECTION_SALARY>>": self._escape_latex(
                sections.get("salary", default_sections["salary"])
            ),
            "<<SECTION_FINAL_MERITS>>": self._escape_latex(
                sections.get("final_merits", default_sections["final_merits"])
            ),
            "<<SECTION_NATIONAL_IMPORTANCE>>": self._escape_latex(
                sections.get("national_importance", default_sections["national_importance"])
            ),
        }

        for placeholder, value in replacements.items():
            template_content = template_content.replace(placeholder, value)

        return self._compile_latex(template_content, output_path)

    def generate_statement_of_intent(
        self,
        output_path: Path,
        name: str,
        field: str,
        additional_statement: str = "",
    ) -> Path:
        """Generate statement of intent to work in the US."""
        name_escaped = self._escape_latex(name)
        name_with_title = self._format_name_with_title(name_escaped)
        field_escaped = self._escape_latex(field)

        template_path = self.templates_dir / "statement_of_intent.tex"
        template_content = template_path.read_text(encoding="utf-8")

        replacements = {
            "<<CLIENT_NAME>>": name_escaped,
            "<<CLIENT_NAME_TITLE>>": name_with_title,
            "<<CLIENT_FIELD>>": field_escaped,
            "<<ADDITIONAL_STATEMENT>>": self._escape_latex(additional_statement),
        }

        for placeholder, value in replacements.items():
            template_content = template_content.replace(placeholder, value)

        return self._compile_latex(template_content, output_path)

    def generate_exhibits_list(
        self,
        output_path: Path,
        name: str,
        exhibits: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Generate list of exhibits page."""
        name_escaped = self._escape_latex(name)
        name_with_title = self._format_name_with_title(name_escaped)

        template_path = self.templates_dir / "exhibits_list.tex"
        template_content = template_path.read_text(encoding="utf-8")

        # Default exhibits if none provided
        if not exhibits:
            exhibits = [
                {"number": 1, "title": "Resume of Beneficiary", "page": ""},
                {"number": 2, "title": "Educational Credentials", "page": ""},
                {"number": 3, "title": "Employment Verification Letters", "page": ""},
                {"number": 4, "title": "Award Certificates", "page": ""},
                {"number": 5, "title": "Recommendation Letters", "page": ""},
                {"number": 6, "title": "Salary Documentation", "page": ""},
            ]

        # Build exhibits rows
        exhibits_rows = []
        for ex in exhibits:
            num = ex.get("number", "")
            title = self._escape_latex(str(ex.get("title", "")))
            page = ex.get("page", "")
            exhibits_rows.append(f"Exhibit {num} & {title} & {page} \\\\")

        replacements = {
            "<<CLIENT_NAME>>": name_escaped,
            "<<CLIENT_NAME_TITLE>>": name_with_title,
            "<<EXHIBITS_ROWS>>": "\n\\hline\n".join(exhibits_rows),
        }

        for placeholder, value in replacements.items():
            template_content = template_content.replace(placeholder, value)

        return self._compile_latex(template_content, output_path)

    def generate_passport_page(
        self,
        output_path: Path,
        name: str,
        passport_number: str = "____________________",
    ) -> Path:
        """Generate passport placeholder page."""
        name_escaped = self._escape_latex(name)
        name_with_title = self._format_name_with_title(name_escaped)

        template_path = self.templates_dir / "passport_page.tex"
        template_content = template_path.read_text(encoding="utf-8")

        replacements = {
            "<<CLIENT_NAME>>": name_escaped,
            "<<CLIENT_NAME_TITLE>>": name_with_title,
            "<<PASSPORT_NUMBER>>": self._escape_latex(passport_number),
        }

        for placeholder, value in replacements.items():
            template_content = template_content.replace(placeholder, value)

        return self._compile_latex(template_content, output_path)


# Singleton instance
latex_generator = LaTeXGenerator()


def test_latex():
    """Test LaTeX PDF generation for all templates."""
    generator = LaTeXGenerator()

    output_dir = Path("output/pdf_packages/latex_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    test_name = "Ivan Petrov"
    test_field = "Computer Science"

    print("Testing LaTeX generation...")

    # Test cover page
    try:
        result = generator.generate_cover_page(
            output_path=output_dir / "cover_page_latex.pdf",
            name=test_name,
            include_premium=True,
        )
        print(f"Cover page: {result} ({result.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"Cover page ERROR: {e}")

    # Test petition letter
    try:
        result = generator.generate_petition_letter(
            output_path=output_dir / "petition_letter_latex.pdf",
            name=test_name,
            field=test_field,
            sections={"summary": "This is a test summary of achievements."},
        )
        print(f"Petition letter: {result} ({result.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"Petition letter ERROR: {e}")

    # Test statement of intent
    try:
        result = generator.generate_statement_of_intent(
            output_path=output_dir / "statement_latex.pdf",
            name=test_name,
            field=test_field,
        )
        print(f"Statement: {result} ({result.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"Statement ERROR: {e}")

    # Test exhibits list
    try:
        result = generator.generate_exhibits_list(
            output_path=output_dir / "exhibits_list_latex.pdf",
            name=test_name,
            exhibits=[
                {"number": 1, "title": "Resume", "page": 93},
                {"number": 2, "title": "Diploma", "page": 95},
                {"number": 3, "title": "Award Certificate", "page": 97},
            ],
        )
        print(f"Exhibits list: {result} ({result.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"Exhibits list ERROR: {e}")

    # Test passport page
    try:
        result = generator.generate_passport_page(
            output_path=output_dir / "passport_latex.pdf",
            name=test_name,
            passport_number="AB1234567",
        )
        print(f"Passport page: {result} ({result.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"Passport page ERROR: {e}")

    print(f"\nAll files saved to: {output_dir.absolute()}")


if __name__ == "__main__":
    test_latex()
