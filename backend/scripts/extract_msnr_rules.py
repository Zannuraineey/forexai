"""
MSNR PDF Extractor & Rule Indexer
Extracts Table of Contents, Chapters, and Core Setup Rules (QML, King, Over-Under, SOPs)
from the Malaysian Support & Resistance (MSNR) PDF guide.
"""

import sys
import os
from pathlib import Path

def extract_pdf_info(pdf_path: str, output_dir: str):
    try:
        from pypdf import PdfReader
    except ImportError:
        print("[!] pypdf is not installed. Please run: pip install pypdf")
        sys.exit(1)

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"[!] PDF file not found at: {pdf_file.resolve()}")
        print(f"    Please place your PDF file at: {pdf_file.resolve()}")
        return

    print(f"[*] Reading PDF: {pdf_file.name} ({pdf_file.stat().st_size / (1024*1024):.1f} MB)...")
    reader = PdfReader(str(pdf_file))
    num_pages = len(reader.pages)
    print(f"[*] Total Pages: {num_pages}")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Keywords of interest in MSNR
    keywords = [
        "qml", "quasimodo", "king", "over under", "sop 1", "sop 2", "sop",
        "storyline", "fakeout", "left shoulder", "fresh", "unfresh",
        "rally base rally", "drop base drop", "compression", "cp"
    ]

    matched_pages = {kw: [] for kw in keywords}
    summary_lines = [
        f"# MSNR Rule Extraction Summary",
        f"- **Source File**: `{pdf_file.name}`",
        f"- **File Size**: {pdf_file.stat().st_size / (1024*1024):.2f} MB",
        f"- **Total Pages**: {num_pages}\n",
        "## Key Topics & Page Map\n"
    ]

    extracted_text_file = out_path / "extracted_key_rules.md"

    with open(extracted_text_file, "w", encoding="utf-8") as f_out:
        f_out.write(f"# MSNR Extracted Trading Rules & Patterns\n\n")

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text_lower = text.lower()

            page_hits = []
            for kw in keywords:
                if kw in text_lower:
                    matched_pages[kw].append(i + 1)
                    page_hits.append(kw)

            if page_hits:
                f_out.write(f"--- \n### Page {i + 1} (Tags: {', '.join(page_hits)})\n\n")
                f_out.write(text.strip() + "\n\n")

            if (i + 1) % 50 == 0 or (i + 1) == num_pages:
                print(f"    Processed {i + 1}/{num_pages} pages...")

    for kw, pages in matched_pages.items():
        if pages:
            summary_lines.append(f"- **{kw.upper()}**: Found on {len(pages)} pages (e.g. {pages[:10]}{'...' if len(pages) > 10 else ''})")

    summary_file = out_path / "msnr_toc_summary.md"
    summary_file.write_text("\n".join(summary_lines), encoding="utf-8")
    print("[OK] Extraction complete!")
    print(f"    - Index: {summary_file}")
    print(f"    - Rules text: {extracted_text_file}")

if __name__ == "__main__":
    default_pdf = Path(__file__).resolve().parent.parent.parent / "docs" / "msnr.pdf"
    default_out = Path(__file__).resolve().parent.parent.parent / "docs" / "msnr_rules"

    target_pdf = sys.argv[1] if len(sys.argv) > 1 else str(default_pdf)
    target_out = sys.argv[2] if len(sys.argv) > 2 else str(default_out)

    extract_pdf_info(target_pdf, target_out)
