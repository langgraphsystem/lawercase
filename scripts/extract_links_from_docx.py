from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree
import zipfile


def extract_links_from_docx(docx_path):
    links = []

    if not Path(docx_path).exists():
        print(f"Error: File not found: {docx_path}")
        return []

    try:
        with zipfile.ZipFile(docx_path) as z:
            if "word/_rels/document.xml.rels" in z.namelist():
                xml_content = z.read("word/_rels/document.xml.rels")
                root = ElementTree.fromstring(xml_content)  # noqa: S314

                ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}

                for rel in root.findall("r:Relationship", ns):
                    if (
                        rel.get("Type")
                        == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
                    ):
                        target = rel.get("Target")
                        if target:
                            links.append(target)

    except Exception as e:
        print(f"Error reading docx: {e}")
        return []

    return links


if __name__ == "__main__":
    file_path = "data/link.docx"
    print(f"Extracting links from: {file_path}")
    found_links = extract_links_from_docx(file_path)

    if found_links:
        unique_links = sorted(set(found_links))
        print(f"\nFound {len(unique_links)} unique links.")

        output_path = Path("data") / "extracted_links.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_links, f, indent=2)

        print(f"Saved links to {output_path}")
    else:
        print("\nNo links found.")
