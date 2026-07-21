"""Debug script: step-by-step investigation of MCU metadata extraction failure.

Works around cp1252 encoding issues by writing output to a file.
"""

import os
import re
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.doc_resolver import DocumentationResolver
from src.utils.pdf_parser import PdfParser

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
OUT = sys.stdout  # We'll write to a file instead to avoid encoding issues


def eprint(*args, **kwargs):
    """Write to stderr so we can see progress even if stdout encoding fails."""
    print(*args, file=sys.stderr, **kwargs)


def write_both(f, *args, **kwargs):
    """Write to both file and stdout."""
    print(*args, file=f, **kwargs)
    print(*args, file=sys.stderr)


def step1_show_docs(f):
    write_both(f, "=" * 72)
    write_both(f, "STEP 1: Which documents are selected?")
    write_both(f, "=" * 72)
    resolver = DocumentationResolver()
    docs = resolver.resolve(DOCS_DIR)
    if not docs:
        write_both(f, "  No documents resolved.")
        return []
    for d in docs:
        write_both(f, f"  title={d.title!r}, type={d.document_type!r}, path={os.path.basename(d.source_path)}")
    return docs


def step2_show_extracted_text(f, docs):
    write_both(f, "\n" + "=" * 72)
    write_both(f, "STEP 2: First 1000 chars from each document")
    write_both(f, "=" * 72)
    for d in docs:
        write_both(f, f"\n--- Document: {d.title} ({d.document_type}) ---")
        try:
            text = PdfParser.extract_text(d.source_path)
            # Show raw repr to avoid encoding issues
            write_both(f, text[:1000])
        except Exception as e:
            write_both(f, f"  ERROR extracting text: {e}")


def step3_show_context(f, docs, keywords=("Cortex", "Flash", "SRAM", "RAM", "Memory")):
    write_both(f, "\n" + "=" * 72)
    write_both(f, "STEP 3: Context around keywords (repr format to avoid encoding issues)")
    write_both(f, "=" * 72)
    for d in docs:
        write_both(f, f"\n--- Document: {d.title} ({d.document_type}) ---")
        try:
            text = PdfParser.extract_text(d.source_path)
        except Exception as e:
            write_both(f, f"  ERROR: {e}")
            continue
        lower_text = text.lower()
        for kw in keywords:
            lower_kw = kw.lower()
            idx = 0
            found_any = False
            while True:
                pos = lower_text.find(lower_kw, idx)
                if pos == -1:
                    break
                found_any = True
                start = max(0, pos - 100)
                end = min(len(text), pos + len(kw) + 100)
                snippet = text[start:end]
                line_num = text[:pos].count("\n") + 1
                write_both(f, f"\n  [{kw}] at offset {pos}, line ~{line_num}:")
                write_both(f, f"  ---repr---")
                write_both(f, repr(snippet))
                write_both(f, f"  ---end---")
                idx = pos + len(lower_kw)
            if not found_any:
                write_both(f, f"  [{kw}] NOT FOUND in this document")


def step4_test_regexes(f, docs):
    write_both(f, "\n" + "=" * 72)
    write_both(f, "STEP 4: Run current regexes and report failures")
    write_both(f, "=" * 72)

    cpu_patterns = [
        ("Arm[\\s\\u00ae]*Cortex[\\s\\u00ae\\-]*M([0-9]+(?:\\+)?)",
         r"Arm[\s\u00ae]*Cortex[\s\u00ae\-]*M([0-9]+(?:\+)?)"),
        ("ARM\\s*Cortex[-\\s]M([0-9]+(?:\\+)?)",
         r"ARM\s*Cortex[-\s]M([0-9]+(?:\+)?)"),
        ("Cortex[-\\s]M([0-9]+(?:\\+)?)",
         r"Cortex[-\s]M([0-9]+(?:\+)?)"),
    ]

    for d in docs:
        write_both(f, f"\n--- Document: {d.title} ({d.document_type}) ---")
        try:
            text = PdfParser.extract_text(d.source_path)
        except Exception as e:
            write_both(f, f"  ERROR: {e}")
            continue
        head = text[:3000]

        # CPU regex comparison
        write_both(f, "\n  -- CPU extraction (head[:3000]) --")
        for label, pat in cpu_patterns:
            m = re.search(pat, head, re.IGNORECASE)
            if m:
                write_both(f, f"  OK   {label}")
                write_both(f, f"       matched: {m.group(0)!r}")
            else:
                write_both(f, f"  FAIL {label}")
                # Show raw bytes around potential Cortex match
                for m2 in re.finditer(r"(?i)\bcortex", head):
                    s = max(0, m2.start() - 20)
                    e = min(len(head), m2.end() + 60)
                    write_both(f, f"       cortex-context: {head[s:e]!r}")
                for m2 in re.finditer(r"(?i)arm", head):
                    s = max(0, m2.start() - 20)
                    e = min(len(head), m2.end() + 60)
                    write_both(f, f"       arm-context: {head[s:e]!r}")

        # Also search full text for patterns (not just head)
        write_both(f, "\n  -- CPU extraction (full text) --")
        for label, pat in cpu_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                write_both(f, f"  OK (full) {label}")
                write_both(f, f"       matched: {m.group(0)!r} at offset {m.start()}")
            else:
                write_both(f, f"  FAIL (full) {label}")

        # Size patterns
        def make_pat_kb(kind):
            return re.compile(
                rf"(?i)(\d+)\s*-?\s*"
                rf"(?:K(?:B|Byte|bytes?))\s*"
                rf"(?:of\s+)?"
                rf"(?:{kind})"
            )

        def make_pat_kb_alt(kind):
            return re.compile(
                rf"(?i)(\d+)\s*-?\s*K\s+(?:of\s+)?(?:{kind})"
            )

        def make_pat_mb(kind):
            return re.compile(
                rf"(?i)(\d+(?:\.\d+)?)\s*MB\s*(?:of\s+)?(?:{kind})",
            )

        # Try different kind patterns for flash
        write_both(f, "\n  -- Flash size extraction --")
        for kind in ("flash",):
            write_both(f, f"\n    Trying kind={kind!r}:")
            for label, pat_fn in [
                ("pat_kb", make_pat_kb),
                ("pat_kb_alt", make_pat_kb_alt),
                ("pat_mb", make_pat_mb),
            ]:
                pat = pat_fn(kind)
                m = pat.search(text)
                if m:
                    write_both(f, f"    OK   {label} -> {m.group(1)} (matched: {m.group(0)!r})")
                else:
                    write_both(f, f"    FAIL {label}")

        # Try different kind patterns for ram
        write_both(f, "\n  -- RAM size extraction --")
        for kind in (r"(?:s)?ram", "ram", "sram"):
            write_both(f, f"\n    Trying kind={kind!r}:")
            for label, pat_fn in [
                ("pat_kb", make_pat_kb),
                ("pat_kb_alt", make_pat_kb_alt),
                ("pat_mb", make_pat_mb),
            ]:
                pat = pat_fn(kind)
                m = pat.search(text)
                if m:
                    write_both(f, f"    OK   {label} -> {m.group(1)} (matched: {m.group(0)!r})")
                else:
                    write_both(f, f"    FAIL {label}")

        # Raw "memory capacity" mentions
        write_both(f, "\n  -- Raw size mentions in text --")
        for kw in ("Flash", "SRAM", "Kbyte", "KByte", "KB", "MB", "flash", "sram"):
            for m in re.finditer(rf"(?i)(.{{0,40}}{re.escape(kw)}.{{0,40}})", text):
                write_both(f, f"  {repr(m.group(1))}")


if __name__ == "__main__":
    with open("debug_mcu_output.txt", "w", encoding="utf-8") as f:
        docs = step1_show_docs(f)
        if not docs:
            write_both(f, "\nNo documents found. Exiting.")
            sys.exit(1)
        step2_show_extracted_text(f, docs)
        step3_show_context(f, docs)
        step4_test_regexes(f, docs)

    eprint("Debug output written to debug_mcu_output.txt")
