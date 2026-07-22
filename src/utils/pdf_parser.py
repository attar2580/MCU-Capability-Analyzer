from __future__ import annotations

import os
from typing import Any

from pypdf import PdfReader


class PdfParser:
    """Utility for extracting text and structure from PDF documents."""

    @staticmethod
    def extract_pages(path: str) -> list[str]:
        """Extract text per page from a PDF file.

        Args:
            path: Path to the PDF file.

        Returns:
            List of page text strings, one entry per page.
            Empty pages are omitted.

        Raises:
            FileNotFoundError: If the PDF file does not exist.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"PDF not found: {path}")

        reader = PdfReader(path)
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return pages

    @staticmethod
    def extract_text(path: str) -> str:
        """Extract all text content from a PDF file.

        Args:
            path: Path to the PDF file.

        Returns:
            Extracted text as a single string with page breaks.

        Raises:
            FileNotFoundError: If the PDF file does not exist.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"PDF not found: {path}")

        reader = PdfReader(path)
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    @staticmethod
    def extract_toc(path: str) -> list[dict[str, object]]:
        """Extract the table of contents from a PDF file.

        Args:
            path: Path to the PDF file.

        Returns:
            List of section entries, each with keys ``title`` and ``page``.

        Raises:
            FileNotFoundError: If the PDF file does not exist.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"PDF not found: {path}")

        reader = PdfReader(path)
        outline = reader.outline
        if not outline:
            return []

        entries: list[dict[str, object]] = []
        PdfParser._flatten_outline(outline, reader, entries)
        return entries

    @staticmethod
    def _flatten_outline(
        items: Any,
        reader: PdfReader,
        entries: list[dict[str, object]],
    ) -> None:
        """Recursively flatten the PDF outline into a list of {title, page}."""
        for item in items:
            if isinstance(item, list):
                PdfParser._flatten_outline(item, reader, entries)
            else:
                try:
                    title = getattr(item, "title", str(item))
                    page_num = reader.get_destination_page_number(item)
                    entries.append({
                        "title": title,
                        "page": page_num,
                    })
                except (AttributeError, KeyError, ValueError):
                    continue
