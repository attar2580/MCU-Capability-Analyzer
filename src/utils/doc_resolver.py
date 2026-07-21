from __future__ import annotations

import os

from .documentation import Documentation


class DocumentationResolver:
    """Scans a directory for PDF documents and creates Documentation objects.

    Version 1 classifies STM32 documentation by filename prefix:
      - UM*, *user_manual*, *user manual*       → "user_manual"
      - DS*, *datasheet*                         → "datasheet"
      - RM*, *reference_manual*, *reference manual* → "reference_manual"
      - everything else                          → "documentation"
    """

    def resolve(self, directory: str) -> list[Documentation]:
        """Scan *directory* for PDFs and return sorted Documentation objects.

        Args:
            directory: Path to a directory containing PDF documentation files.

        Returns:
            A list of Documentation objects, sorted alphabetically by filename.

        Raises:
            FileNotFoundError: If *directory* does not exist.
        """
        if not os.path.isdir(directory):
            raise FileNotFoundError(f"Documentation directory not found: {directory}")

        docs: list[Documentation] = []
        for fname in sorted(os.listdir(directory)):
            if not fname.lower().endswith(".pdf"):
                continue
            path = os.path.join(directory, fname)
            if not os.path.isfile(path):
                continue
            docs.append(Documentation(
                source_path=path,
                document_type=self._classify(fname),
                title=os.path.splitext(fname)[0],
            ))
        return docs

    @staticmethod
    def _classify(filename: str) -> str:
        """Classify a PDF filename into a document type."""
        lower = filename.lower()
        if lower.startswith("um") or "user_manual" in lower or "user manual" in lower:
            return "user_manual"
        if lower.startswith("ds") or "datasheet" in lower:
            return "datasheet"
        if lower.startswith("rm") or "reference_manual" in lower or "reference manual" in lower:
            return "reference_manual"
        return "documentation"
