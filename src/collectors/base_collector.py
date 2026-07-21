from __future__ import annotations

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

    @staticmethod
    def _merge_resources(
        existing: dict[str, object], new: dict[str, object],
    ) -> dict[str, object]:
        """Merge new resources, preserving existing keys on conflict."""
        merged = dict(existing)
        merged.update({k: v for k, v in new.items() if k not in merged})
        return merged
