from __future__ import annotations

import io
import logging
from typing import Any, Dict

logger = logging.getLogger("finanalyzer.tools")

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Robust UTF-8 text extraction using pypdf; falls back to pdfplumber if available.
    Returns: {'text': str, 'pages': int}
    """
    text = ""
    pages = 0
    # Primary: pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pages = len(reader.pages)
        chunks = []
        for i, page in enumerate(reader.pages):
            try:
                chunks.append(page.extract_text() or "")
            except Exception as e:
                logger.warning("pypdf failed on page %d: %s", i, e)
                chunks.append("")
        text = "\n".join(chunks)
    except Exception as e_pypdf:
        logger.warning("pypdf failed (%s). Trying pdfplumber.", e_pypdf)
        # Fallback: pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages = len(pdf.pages)
                tchunks = []
                for i, p in enumerate(pdf.pages):
                    try:
                        tchunks.append(p.extract_text() or "")
                    except Exception as e:
                        logger.warning("pdfplumber failed on page %d: %s", i, e)
                        tchunks.append("")
                text = "\n".join(tchunks)
        except Exception as e_plumb:
            raise RuntimeError(
                "PDF extraction requires pypdf (recommended) or pdfplumber. "
                "Install with: pip install pypdf pdfplumber"
            ) from e_plumb

    # Normalize to UTF-8
    if not isinstance(text, str):
        text = str(text)
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    return {"text": text, "pages": pages}