from __future__ import annotations

import re

from ..models.evidence import Evidence
from ..utils.documentation import Documentation
from ..utils.pdf_parser import PdfParser


class BaseCollector:
    """Shared base for collectors that extract data from documentation."""

    def _iter_texts(
        self, documents: list[Documentation], evidence_list: list[Evidence],
    ):
        """Yield (doc, text) for each successfully loaded document.

        Documents that cannot be read are recorded in evidence_list and skipped.
        """
        for doc in documents:
            try:
                text = PdfParser.extract_text(doc.source_path)
            except FileNotFoundError:
                evidence_list.append(Evidence(
                    source_type=doc.document_type,
                    document=doc.title or doc.source_path,
                    notes="Document file not found",
                ))
                continue
            yield doc, text

    def _iter_texts_with_pages(
        self, documents: list[Documentation], evidence_list: list[Evidence],
    ):
        """Yield (doc, text, pages) for each successfully loaded document.

        *pages* is a list of per-page text strings (1 entry per PDF page)
        suitable for page-number lookup.  Documents that cannot be read
        are recorded in evidence_list and skipped.
        """
        for doc in documents:
            try:
                text = PdfParser.extract_text(doc.source_path)
                pages = PdfParser.extract_pages(doc.source_path)
            except FileNotFoundError:
                evidence_list.append(Evidence(
                    source_type=doc.document_type,
                    document=doc.title or doc.source_path,
                    notes="Document file not found",
                ))
                continue
            yield doc, text, pages

    @staticmethod
    def _find_page_for_pattern(
        pages: list[str], pattern: re.Pattern,
    ) -> str:
        """Return the 1-indexed page number where *pattern* first matches.

        Args:
            pages: Per-page text strings from ``PdfParser.extract_pages()``.
            pattern: Compiled regex to search for.

        Returns:
            Page number as a string (e.g. ``"53"``), or ``""`` if no match.
        """
        for i, page_text in enumerate(pages):
            if pattern.search(page_text):
                return str(i + 1)
        return ""

    @staticmethod
    def _find_page_for_any_pattern(
        pages: list[str], patterns: list[re.Pattern],
    ) -> str:
        """Return the page number for the first pattern that matches.

        Tries each *pattern* in order against all pages and returns the
        page number of the earliest match across all patterns.
        This mirrors the deterministic fallback logic used by extraction
        methods.
        """
        for p in patterns:
            result = BaseCollector._find_page_for_pattern(pages, p)
            if result:
                return result
        return ""

    @staticmethod
    def _merge_resources(
        existing: dict[str, object], new: dict[str, object],
    ) -> dict[str, object]:
        """Merge new resources, preserving existing keys on conflict."""
        merged = dict(existing)
        merged.update({k: v for k, v in new.items() if k not in merged})
        return merged
