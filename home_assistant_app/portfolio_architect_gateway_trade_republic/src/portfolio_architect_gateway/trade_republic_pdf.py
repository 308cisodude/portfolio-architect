"""Bounded text-PDF extraction shared by Trade Republic statement families."""

from __future__ import annotations

from io import BytesIO
from typing import Final

from pypdf import PdfReader

MAX_PDF_BYTES: Final = 5 * 1024 * 1024
MAX_PDF_PAGES: Final = 32
MAX_PAGE_CONTENT_BYTES: Final = 2 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS: Final = 512 * 1024


class TradeRepublicPdfError(ValueError):
    """A bounded, privacy-safe reason for rejecting one uploaded PDF."""


def extract_bounded_pdf_text(data: bytes) -> str:
    """Extract a bounded text layer without retaining the uploaded PDF."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_PDF_BYTES:
        raise TradeRepublicPdfError("PDF is empty or exceeds the 5 MiB import limit")
    if not data.startswith(b"%PDF-"):
        raise TradeRepublicPdfError("Uploaded file is not a PDF document")
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise TradeRepublicPdfError("Encrypted PDF statements are not supported")
        page_count = len(reader.pages)
        if not 1 <= page_count <= MAX_PDF_PAGES:
            raise TradeRepublicPdfError("PDF page count is outside the supported range")
        page_texts: list[str] = []
        total_chars = 0
        for page in reader.pages:
            contents = page.get_contents()
            if contents is not None:
                decoded = contents.get_data()
                if len(decoded) > MAX_PAGE_CONTENT_BYTES:
                    raise TradeRepublicPdfError("PDF page content exceeds the import safety limit")
            text = page.extract_text(
                extraction_mode="layout",
                layout_mode_space_vertically=False,
            )
            if not isinstance(text, str) or not text.strip():
                raise TradeRepublicPdfError("PDF does not contain an extractable text layer")
            total_chars += len(text)
            if total_chars > MAX_EXTRACTED_TEXT_CHARS:
                raise TradeRepublicPdfError("Extracted PDF text exceeds the import safety limit")
            page_texts.append(text)
    except TradeRepublicPdfError:
        raise
    except Exception as err:
        raise TradeRepublicPdfError("PDF could not be parsed safely") from err
    return "\n".join(page_texts)
