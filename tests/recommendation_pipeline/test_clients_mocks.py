from __future__ import annotations

import httpx
import pytest
import respx

from recommendation_pipeline.clients.adobe_pdf_services_client import \
    AdobePDFServices
from recommendation_pipeline.clients.docraptor_client import (DocRaptorClient,
                                                              DocRaptorError)
from recommendation_pipeline.clients.gemini_ocr_client import (GeminiOCR,
                                                               GeminiOCRError)


@pytest.mark.asyncio
@respx.mock
async def test_docraptor_retries_success() -> None:
    route = respx.post("https://docraptor.com/docs")
    route.side_effect = [
        httpx.Response(500, json={"error": "server"}),
        httpx.Response(200, content=b"%PDF-1.4 content"),
    ]
    client = DocRaptorClient(api_key="test_key")
    pdf = await client.ahtml_to_pdf("<html></html>")
    await client.aclose()
    assert pdf.startswith(b"%PDF")
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_docraptor_client_error() -> None:
    route = respx.post("https://docraptor.com/docs").mock(
        return_value=httpx.Response(422, json={"status": "error"})
    )
    client = DocRaptorClient(api_key="test_key")
    with pytest.raises(DocRaptorError):
        await client.ahtml_to_pdf("<html></html>")
    await client.aclose()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_gemini_ocr_success() -> None:
    respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "Sample text"}]}}]},
        )
    )
    client = GeminiOCR(api_key="gemini_key")
    meta = await client.aanalyze_images([b"\xff\xd8\xff"])
    await client.aclose()
    assert "summary" in meta
    assert meta["summary"] == "Sample text"


@pytest.mark.asyncio
@respx.mock
async def test_gemini_server_error_retry() -> None:
    respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent"
    ).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]},
            ),
        ]
    )
    client = GeminiOCR(api_key="gemini_key")
    meta = await client.aanalyze_images([b"\xff\xd8\xff"])
    await client.aclose()
    assert meta["summary"] == "OK"


@pytest.mark.asyncio
@respx.mock
async def test_adobe_pdf_services_success() -> None:
    respx.post("https://api.pdfservices.adobe.com/operation/ocr").mock(
        return_value=httpx.Response(200, content=b"%PDF-1.4 OCR")
    )
    client = AdobePDFServices(api_key="adobe_key")
    result = await client.aocr_pdf(b"%PDF")
    await client.aclose()
    assert result.startswith(b"%PDF")


@pytest.mark.asyncio
@respx.mock
async def test_gemini_client_error() -> None:
    respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent"
    ).mock(return_value=httpx.Response(403, json={"error": "denied"}))
    client = GeminiOCR(api_key="gemini_key")
    with pytest.raises(GeminiOCRError):
        await client.aanalyze_images([b"\xff\xd8\xff"])
    await client.aclose()
