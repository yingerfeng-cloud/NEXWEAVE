from uuid import uuid4

import pytest

from nexweave_api.errors import ApiProblem
from nexweave_api.source_routes import (
    _download_content_disposition,
    _filter_sources_by_content_type,
    _read_bounded_upload,
    _validate_controlled_type,
)


class SourceDetailsStub:
    def __init__(self, details: dict[str, dict[str, object]]) -> None:
        self.details = details
        self.requested: list[str] = []

    async def get_source(self, *, principal: object, source_id: object) -> dict[str, object]:
        del principal
        key = str(source_id)
        self.requested.append(key)
        return self.details[key]


class StreamingRequestStub:
    def __init__(self, chunks: tuple[bytes, ...], content_length: str | None = None) -> None:
        self._chunks = chunks
        self.headers = {"content-length": content_length} if content_length is not None else {}

    async def stream(self):  # type: ignore[no-untyped-def]
        for chunk in self._chunks:
            yield chunk


@pytest.mark.asyncio
async def test_content_type_filter_returns_each_source_once() -> None:
    matching_id, other_id = str(uuid4()), str(uuid4())
    repository = SourceDetailsStub(
        {
            matching_id: {
                "versions": [
                    {"content_type": "text/plain"},
                    {"content_type": "text/plain"},
                ]
            },
            other_id: {"versions": [{"content_type": "application/pdf"}]},
        }
    )
    matching = {"id": matching_id, "display_name": "matching"}
    other = {"id": other_id, "display_name": "other"}

    result = await _filter_sources_by_content_type(  # type: ignore[arg-type]
        repository,
        principal=object(),
        items=[matching, other],
        content_type="text/plain",
    )

    assert result == [matching]
    assert repository.requested == [matching_id, other_id]


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("renamed.txt", "application/pdf", b"%PDF-1.7"),
        ("spoofed.pdf", "application/pdf", b"not-a-pdf"),
        ("binary.txt", "text/plain", b"text\x00binary"),
        (
            "spoofed.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"not-zip",
        ),
    ],
)
def test_controlled_type_validation_rejects_extension_or_magic_mismatch(
    filename: str, content_type: str, content: bytes
) -> None:
    with pytest.raises(ApiProblem) as error:
        _validate_controlled_type(filename, content_type, content)

    assert error.value.code == "SOURCE_TYPE_UNSUPPORTED"


@pytest.mark.asyncio
async def test_streamed_upload_fails_before_buffering_past_controlled_limit() -> None:
    request = StreamingRequestStub((b"1234", b"5678"))

    with pytest.raises(ApiProblem) as error:
        await _read_bounded_upload(  # type: ignore[arg-type]
            request, expected_size=6, maximum_size=10
        )

    assert error.value.status == 413
    assert error.value.code == "PARSER_RESOURCE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_declared_oversized_upload_is_rejected_before_stream_read() -> None:
    request = StreamingRequestStub((b"not-consumed",), content_length="11")

    with pytest.raises(ApiProblem) as error:
        await _read_bounded_upload(  # type: ignore[arg-type]
            request, expected_size=10, maximum_size=10
        )

    assert error.value.status == 413


def test_download_disposition_removes_control_characters_and_encodes_utf8() -> None:
    value = _download_content_disposition('../报告\r\nX-Injected: true".pdf')

    assert "\r" not in value and "\n" not in value
    assert "X-Injected: true" in value
    assert "filename*=UTF-8''" in value
    assert "%E6%8A%A5%E5%91%8A" in value
