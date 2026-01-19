"""
PDF Package Generator for EB-1A Petition

Generates a complete PDF package containing:
1. Cover Page with Table of Contents
2. Form G-1145 (e-Notification)
3. Form I-140 (Immigrant Petition)
4. Form I-907 (Premium Processing)
5. Form G-28 (Attorney Appearance) - if applicable
6. Passport copies placeholder
7. Petition Letter (all sections)
8. Statement of Intent
9. List of Exhibits
10. All Exhibits

Uses:
- LaTeX (pdflatex) for document generation
- pypdf for PDF merging
- fillpdf for form filling
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

import structlog

from core.services.latex_generator import LaTeXGenerator

logger = structlog.get_logger(__name__)

# Path to USCIS fillable PDF forms
USCIS_FORMS_DIR = Path("data/uscis_forms/fillable")


class PDFPackageGenerator:
    """
    Generates a complete EB-1A petition PDF package with all forms filled.
    Uses LaTeX for high-quality document generation.
    """

    def __init__(self, output_dir: str = "output/pdf_packages"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.latex = LaTeXGenerator()

    async def generate_package(
        self,
        case_id: str,
        case_data: dict[str, Any],
        user_data: dict[str, Any],
        petition_sections: dict[str, str] | None = None,
        exhibits: list[dict[str, Any]] | None = None,
        include_premium: bool = True,
        include_attorney: bool = False,
    ) -> str:
        """
        Generate complete PDF package for EB-1A petition.

        Args:
            case_id: Unique case identifier
            case_data: Case details (field, criteria, etc.)
            user_data: Beneficiary details (name, DOB, address, etc.)
            petition_sections: Petition letter content by section
            exhibits: List of exhibit files/data
            include_premium: Include I-907 Premium Processing
            include_attorney: Include G-28 Attorney form

        Returns:
            Path to the generated PDF package
        """
        package_dir = self.output_dir / case_id
        package_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating PDF package for case {case_id}")

        try:
            pdf_files = []

            # 1. Generate Cover Page with TOC (LaTeX)
            cover_pdf = await self._generate_cover_page(
                package_dir, case_id, user_data, include_premium, include_attorney
            )
            pdf_files.append(cover_pdf)

            # 2. Fill G-1145 (e-Notification)
            g1145_pdf = await self._fill_g1145(package_dir, user_data)
            pdf_files.append(g1145_pdf)

            # 3. Fill I-140 (Main Petition Form)
            i140_pdf = await self._fill_i140(package_dir, case_data, user_data)
            pdf_files.append(i140_pdf)

            # 4. Fill I-907 (Premium Processing) - if requested
            if include_premium:
                i907_pdf = await self._fill_i907(package_dir, case_data, user_data)
                pdf_files.append(i907_pdf)

            # 5. Fill G-28 (Attorney) - if applicable
            if include_attorney:
                g28_pdf = await self._fill_g28(package_dir, case_data, user_data)
                pdf_files.append(g28_pdf)

            # 6. Generate Passport placeholder page (LaTeX)
            passport_pdf = await self._generate_passport_page(package_dir, user_data)
            pdf_files.append(passport_pdf)

            # 7. Generate Petition Letter PDF (LaTeX)
            petition_pdf = await self._generate_petition_pdf(
                package_dir, case_id, case_data, user_data, petition_sections
            )
            pdf_files.append(petition_pdf)

            # 8. Generate Statement of Intent (LaTeX)
            statement_pdf = await self._generate_statement_page(package_dir, case_data, user_data)
            pdf_files.append(statement_pdf)

            # 9. Generate Exhibits List (LaTeX)
            exhibits_list_pdf = await self._generate_exhibits_list(
                package_dir, exhibits or [], user_data
            )
            pdf_files.append(exhibits_list_pdf)

            # 10. Merge all PDFs into final package
            final_pdf = await self._merge_pdfs(
                pdf_files, package_dir / f"{case_id}_complete_package.pdf"
            )

            logger.info(f"PDF package generated: {final_pdf}")
            return str(final_pdf)

        except Exception as e:
            logger.error(f"Failed to generate PDF package: {e}")
            raise

    async def _generate_cover_page(
        self,
        output_dir: Path,
        case_id: str,
        user_data: dict[str, Any],
        include_premium: bool,
        include_attorney: bool,
        page_info: dict[str, int] | None = None,
    ) -> Path:
        """Generate cover page with table of contents using LaTeX."""
        name = user_data.get("full_name", "Beneficiary")

        # Default page numbers if not provided
        if page_info is None:
            page_info = {
                "passport": 19,
                "petition": 21,
                "statement": 81,
                "exhibits_list": 83,
                "exhibits_start": 93,
                "exhibits_count": 169,
            }

        output_path = output_dir / "00_cover.pdf"

        # Run LaTeX generation in thread pool to not block async
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.latex.generate_cover_page(
                output_path=output_path,
                name=name,
                include_premium=include_premium,
                page_info=page_info,
            ),
        )

        logger.debug(f"Generated cover page: {result}")
        return result

    async def _fill_g1145(self, output_dir: Path, user_data: dict[str, Any]) -> Path:
        """Fill G-1145 e-Notification form."""
        dst = output_dir / "01_g-1145.pdf"

        try:
            from core.services.uscis_forms import fill_g1145_pdf

            fill_g1145_pdf(dst, user_data)
            logger.info(f"Filled G-1145 saved to {dst}")
        except Exception as e:
            logger.warning(f"Could not fill G-1145, copying blank: {e}")
            src = USCIS_FORMS_DIR / "g-1145.pdf"
            if src.exists():
                shutil.copy2(src, dst)
            else:
                # Generate placeholder using LaTeX
                await self._generate_placeholder_page(
                    dst, "Form G-1145", "e-Notification of Application/Petition Acceptance"
                )

        return dst

    async def _fill_i140(
        self, output_dir: Path, case_data: dict[str, Any], user_data: dict[str, Any]
    ) -> Path:
        """Fill I-140 Immigrant Petition form for EB-1A."""
        dst = output_dir / "02_i-140.pdf"

        try:
            from core.services.uscis_forms import fill_i140_pdf

            fill_i140_pdf(dst, case_data, user_data)
            logger.info(f"Filled I-140 saved to {dst}")
        except Exception as e:
            logger.warning(f"Could not fill I-140, copying blank: {e}")
            src = USCIS_FORMS_DIR / "i-140.pdf"
            if src.exists():
                shutil.copy2(src, dst)
            else:
                await self._generate_placeholder_page(
                    dst, "Form I-140", "Immigrant Petition for Alien Workers"
                )

        return dst

    async def _fill_i907(
        self, output_dir: Path, case_data: dict[str, Any], user_data: dict[str, Any]
    ) -> Path:
        """Fill I-907 Premium Processing form."""
        dst = output_dir / "03_i-907.pdf"

        try:
            from core.services.uscis_forms import fill_i907_pdf

            fill_i907_pdf(dst, case_data, user_data)
            logger.info(f"Filled I-907 saved to {dst}")
        except Exception as e:
            logger.warning(f"Could not fill I-907, copying blank: {e}")
            src = USCIS_FORMS_DIR / "i-907.pdf"
            if src.exists():
                shutil.copy2(src, dst)
            else:
                await self._generate_placeholder_page(
                    dst, "Form I-907", "Request for Premium Processing Service"
                )

        return dst

    async def _fill_g28(
        self, output_dir: Path, case_data: dict[str, Any], user_data: dict[str, Any]
    ) -> Path:
        """Fill G-28 Attorney Appearance form."""
        dst = output_dir / "04_g-28.pdf"

        try:
            from core.services.uscis_forms import fill_g28_pdf

            # Attorney data can be provided in case_data
            attorney_data = case_data.get("attorney_data")
            fill_g28_pdf(dst, case_data, user_data, attorney_data)
            logger.info(f"Filled G-28 saved to {dst}")
        except Exception as e:
            logger.warning(f"Could not fill G-28, copying blank: {e}")
            src = USCIS_FORMS_DIR / "g-28.pdf"
            if src.exists():
                shutil.copy2(src, dst)
            else:
                await self._generate_placeholder_page(
                    dst, "Form G-28", "Notice of Entry of Appearance as Attorney"
                )

        return dst

    async def _generate_passport_page(self, output_dir: Path, user_data: dict[str, Any]) -> Path:
        """Generate passport placeholder page using LaTeX."""
        name = user_data.get("full_name", "Beneficiary")
        passport_number = user_data.get("passport_number", "____________________")
        output_path = output_dir / "05_passport.pdf"

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.latex.generate_passport_page(
                output_path=output_path,
                name=name,
                passport_number=passport_number,
            ),
        )

        logger.debug(f"Generated passport page: {result}")
        return result

    async def _generate_petition_pdf(
        self,
        output_dir: Path,
        case_id: str,
        case_data: dict[str, Any],
        user_data: dict[str, Any],
        sections: dict[str, str] | None,
    ) -> Path:
        """Generate petition letter PDF using LaTeX."""
        name = user_data.get("full_name", "Beneficiary")
        field = case_data.get("field", "Sciences")
        output_path = output_dir / "06_petition.pdf"

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.latex.generate_petition_letter(
                output_path=output_path,
                name=name,
                field=field,
                sections=sections,
            ),
        )

        logger.debug(f"Generated petition letter: {result}")
        return result

    async def _generate_statement_page(
        self, output_dir: Path, case_data: dict[str, Any], user_data: dict[str, Any]
    ) -> Path:
        """Generate statement of intent using LaTeX."""
        name = user_data.get("full_name", "Beneficiary")
        field = case_data.get("field", "Sciences")
        output_path = output_dir / "07_statement.pdf"

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.latex.generate_statement_of_intent(
                output_path=output_path,
                name=name,
                field=field,
            ),
        )

        logger.debug(f"Generated statement: {result}")
        return result

    async def _generate_exhibits_list(
        self,
        output_dir: Path,
        exhibits: list[dict[str, Any]],
        user_data: dict[str, Any] | None = None,
    ) -> Path:
        """Generate list of exhibits page using LaTeX."""
        name = user_data.get("full_name", "Beneficiary") if user_data else "Beneficiary"
        output_path = output_dir / "08_exhibits_list.pdf"

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.latex.generate_exhibits_list(
                output_path=output_path,
                name=name,
                exhibits=exhibits if exhibits else None,
            ),
        )

        logger.debug(f"Generated exhibits list: {result}")
        return result

    async def _generate_placeholder_page(
        self, output_path: Path, title: str, subtitle: str
    ) -> Path:
        """Generate a placeholder PDF page using simple LaTeX."""
        tex_content = r"""
\documentclass[12pt,letterpaper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage[margin=1in]{geometry}

\begin{document}
\pagestyle{empty}

\vspace*{\fill}
\begin{center}
\fbox{
\begin{minipage}{0.8\textwidth}
\centering
\vspace{2em}
\Large\textbf{<<TITLE>>}\\[1em]
\normalsize <<SUBTITLE>>
\vspace{2em}
\end{minipage}
}
\end{center}
\vspace*{\fill}

\end{document}
"""
        tex_content = tex_content.replace("<<TITLE>>", title)
        tex_content = tex_content.replace("<<SUBTITLE>>", subtitle)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self.latex._compile_latex(tex_content, output_path)
        )
        return result

    async def _merge_pdfs(self, pdf_files: list[Path], output_path: Path) -> Path:
        """Merge multiple PDF files into one."""
        try:
            from pypdf import PdfReader, PdfWriter

            writer = PdfWriter()

            for pdf_file in pdf_files:
                if pdf_file.exists():
                    reader = PdfReader(str(pdf_file))
                    for page in reader.pages:
                        writer.add_page(page)
                    logger.debug(f"Added to merge: {pdf_file}")

            with open(output_path, "wb") as f:
                writer.write(f)

            logger.info(f"Merged PDFs into: {output_path}")
            return output_path

        except ImportError:
            logger.warning("pypdf not available, returning first PDF only")
            if pdf_files:
                shutil.copy2(pdf_files[0], output_path)
            return output_path


# Convenience function for sync usage
def generate_pdf_package(
    case_id: str,
    case_data: dict[str, Any],
    user_data: dict[str, Any],
    petition_sections: dict[str, str] | None = None,
    exhibits: list[dict[str, Any]] | None = None,
    include_premium: bool = True,
    include_attorney: bool = False,
) -> str:
    """Synchronous wrapper for PDF package generation."""
    generator = PDFPackageGenerator()
    return asyncio.run(
        generator.generate_package(
            case_id=case_id,
            case_data=case_data,
            user_data=user_data,
            petition_sections=petition_sections,
            exhibits=exhibits,
            include_premium=include_premium,
            include_attorney=include_attorney,
        )
    )


# Singleton instance
pdf_generator = PDFPackageGenerator()


def test_package_generation():
    """Test full PDF package generation."""
    case_id = "test-latex-package"
    case_data = {
        "field": "Computer Science",
        "criteria": ["awards", "membership", "judging", "contributions"],
    }
    user_data = {
        "full_name": "Ivan Petrov",
        "passport_number": "AB1234567",
        "email": "ivan@example.com",
    }

    print(f"Generating PDF package for {case_id}...")

    try:
        result = generate_pdf_package(
            case_id=case_id,
            case_data=case_data,
            user_data=user_data,
            include_premium=True,
            include_attorney=False,
        )
        print(f"Package generated: {result}")
        print(f"Size: {Path(result).stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_package_generation()
