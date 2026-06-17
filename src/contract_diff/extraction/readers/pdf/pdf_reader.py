from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, BinaryIO, cast

import fitz  # type: ignore[import-untyped]

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.extraction.exceptions.extraction import InvalidDocumentError
from contract_diff.extraction.interfaces.reader import DocumentReader
from contract_diff.models.document.block import Block
from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.models.document.extracted_document import ExtractedDocument
from contract_diff.models.document.line import Line
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.models.document.page import Page
from contract_diff.models.document.span import Span


class PdfReader(DocumentReader):
    """
    Reader for PDF documents using PyMuPDF.
    """

    @property
    def supported_format(self) -> DocumentFormat:
        return DocumentFormat.PDF

    def can_read(self, stream: BinaryIO) -> bool:
        position = stream.tell()

        try:
            data = self._read_all(stream)

            with fitz.open(stream=data, filetype="pdf") as document:
                return not bool(getattr(document, "needs_pass", False))

        except Exception:
            return False

        finally:
            stream.seek(position)

    def extract(
        self,
        stream: BinaryIO,
        filename: str,
    ) -> ExtractedDocument:
        position = stream.tell()

        try:
            data = self._read_all(stream)

            try:
                with fitz.open(stream=data, filetype="pdf") as document:
                    return self._extract_document(document, filename, len(data))

            except Exception as exc:
                raise InvalidDocumentError(
                    "PDF document could not be processed."
                ) from exc

        finally:
            stream.seek(position)

    def _extract_document(
        self,
        document: Any,
        filename: str,
        size_bytes: int,
    ) -> ExtractedDocument:
        metadata = cast(Mapping[str, str], document.metadata or {})
        block_index = 1
        line_index = 1
        span_index = 1
        pages: list[Page] = []

        for page_offset in range(document.page_count):
            page = document[page_offset]
            blocks: list[Block] = []
            text_dict = cast(dict[str, Any], page.get_text("dict"))

            for raw_block in text_dict.get("blocks", []):
                block_data = cast(dict[str, Any], raw_block)

                if block_data.get("type") != 0:
                    continue

                for raw_line in block_data.get("lines", []):
                    line_data = cast(dict[str, Any], raw_line)
                    spans: list[Span] = []

                    for raw_span in line_data.get("spans", []):
                        span_data = cast(dict[str, Any], raw_span)
                        text = str(span_data.get("text", ""))

                        if not text:
                            continue

                        spans.append(
                            Span(
                                id=f"span-{span_index}",
                                text=text,
                                bbox=self._bbox(span_data.get("bbox")),
                                font=self._optional_str(span_data.get("font")),
                                font_size=self._optional_float(span_data.get("size")),
                                flags=self._optional_int(span_data.get("flags")),
                            )
                        )
                        span_index += 1

                    if not spans:
                        continue

                    line = Line(
                        id=f"line-{line_index}",
                        bbox=self._bbox(line_data.get("bbox")),
                        spans=tuple(spans),
                    )
                    line_index += 1

                    blocks.append(
                        Block(
                            id=f"block-{block_index}",
                            bbox=line.bbox,
                            lines=(line,),
                        )
                    )
                    block_index += 1

            pages.append(
                Page(
                    id=f"page-{page_offset + 1}",
                    page_number=page_offset + 1,
                    bbox=self._page_bbox(page),
                    blocks=tuple(blocks),
                )
            )

        return ExtractedDocument(
            format=DocumentFormat.PDF,
            metadata=DocumentMetadata(
                filename=filename,
                extension=Path(filename).suffix.lower(),
                size_bytes=size_bytes,
                title=self._metadata_value(metadata, "title"),
                author=self._metadata_value(metadata, "author"),
                creator=self._metadata_value(metadata, "creator"),
                producer=self._metadata_value(metadata, "producer"),
                page_count=document.page_count,
            ),
            pages=tuple(pages),
        )

    def _read_all(self, stream: BinaryIO) -> bytes:
        stream.seek(0)
        return stream.read()

    def _page_bbox(self, page: Any) -> BoundingBox:
        rect = page.rect
        return BoundingBox(
            x0=float(rect.x0),
            y0=float(rect.y0),
            x1=float(rect.x1),
            y1=float(rect.y1),
        )

    def _bbox(self, value: object) -> BoundingBox | None:
        if not isinstance(value, (tuple, list)) or len(value) != 4:
            return None

        return BoundingBox(
            x0=float(value[0]),
            y0=float(value[1]),
            x1=float(value[2]),
            y1=float(value[3]),
        )

    def _metadata_value(
        self,
        metadata: Mapping[str, str],
        key: str,
    ) -> str | None:
        value = metadata.get(key)

        if value is None or not value.strip():
            return None

        return value

    def _optional_str(self, value: object) -> str | None:
        if value is None:
            return None

        return str(value)

    def _optional_float(self, value: object) -> float | None:
        if value is None:
            return None

        if not isinstance(value, (int, float, str)):
            return None

        return float(value)

    def _optional_int(self, value: object) -> int | None:
        if value is None:
            return None

        if not isinstance(value, (int, float, str)):
            return None

        return int(value)
