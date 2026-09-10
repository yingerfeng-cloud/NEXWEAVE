"""M8 read-only Connector providers with explicit allowlist enforcement."""
# ruff: noqa: E501

from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from nexweave_api.errors import ApiProblem
from nexweave_application import ObjectStoragePort

_CONTENT_TYPES = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_: Any, **__: Any) -> None:
        return None


def _inside(path: Path, roots: tuple[str, ...]) -> bool:
    return any(path.is_relative_to(Path(root).resolve()) for root in roots)


def _content_type(filename: str, configured: Any) -> str:
    if isinstance(configured, str) and configured in _CONTENT_TYPES.values():
        return configured
    return _CONTENT_TYPES.get(
        Path(filename).suffix.casefold(),
        mimetypes.guess_type(filename)[0] or "application/octet-stream",
    )


class ReadOnlyConnectorProvider:
    def __init__(self, object_storage: ObjectStoragePort, maximum_bytes: int) -> None:
        self._object_storage = object_storage
        self._maximum_bytes = maximum_bytes

    async def read(self, context: dict[str, Any]) -> tuple[str, str, bytes, dict[str, Any]]:
        kind, config, allowlist = (
            str(context["kind"]),
            dict(context["config"]),
            tuple(str(item) for item in context["allowlist"]),
        )
        if kind == "FILESYSTEM":
            return await self._filesystem(config, allowlist)
        if kind == "S3":
            return await self._s3(config, allowlist)
        if kind == "WEB_REST":
            return await self._web(config, allowlist)
        if kind == "GIT":
            return await self._git(config, allowlist)
        raise ApiProblem(
            422,
            "CONNECTOR_KIND_UNSUPPORTED",
            "Connector kind unavailable",
            "The configured Connector kind is not supported.",
        )

    async def _filesystem(
        self, config: dict[str, Any], allowlist: tuple[str, ...]
    ) -> tuple[str, str, bytes, dict[str, Any]]:
        path = Path(str(config.get("path", ""))).resolve()
        if not path.is_file() or not _inside(path, allowlist):
            raise ApiProblem(
                403,
                "CONNECTOR_ALLOWLIST_DENIED",
                "Connector path denied",
                "The filesystem path is not an allowlisted regular file.",
            )
        content = await asyncio.to_thread(path.read_bytes)
        return (
            path.name,
            _content_type(path.name, config.get("content_type")),
            self._bounded(content),
            {"path": str(path)},
        )

    async def _s3(
        self, config: dict[str, Any], allowlist: tuple[str, ...]
    ) -> tuple[str, str, bytes, dict[str, Any]]:
        key = str(config.get("object_key", ""))
        target = f"s3://{config.get('bucket', 'nexweave-dev')}/{key}"
        if not key or not any(
            target.startswith(prefix.rstrip("/") + "/") or target == prefix.rstrip("/")
            for prefix in allowlist
        ):
            raise ApiProblem(
                403,
                "CONNECTOR_ALLOWLIST_DENIED",
                "Connector object denied",
                "The S3 object is not in an allowlisted development endpoint prefix.",
            )
        content = self._bounded(await self._object_storage.get(key=key))
        return (
            Path(key).name,
            _content_type(key, config.get("content_type")),
            content,
            {"object_key": key},
        )

    async def _web(
        self, config: dict[str, Any], allowlist: tuple[str, ...]
    ) -> tuple[str, str, bytes, dict[str, Any]]:
        url = str(config.get("url", ""))
        parts = urlsplit(url)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.netloc
            or not any(url.startswith(prefix) for prefix in allowlist)
        ):
            raise ApiProblem(
                403,
                "CONNECTOR_ALLOWLIST_DENIED",
                "Connector URL denied",
                "The REST URL is not an allowlisted HTTP target.",
            )

        def fetch() -> tuple[bytes, str]:
            try:
                response = build_opener(_NoRedirect()).open(  # noqa: S310 - scheme/allowlist validated above
                    Request(url, method="GET"),  # noqa: S310 - scheme/allowlist validated above
                    timeout=10,
                )
                with response:
                    content = response.read(self._maximum_bytes + 1)
                    return content, str(response.headers.get_content_type())
            except (HTTPError, URLError, OSError) as exc:
                raise ApiProblem(
                    503,
                    "CONNECTOR_DEPENDENCY_UNAVAILABLE",
                    "Connector request failed",
                    "The allowlisted REST target could not be read.",
                ) from exc

        content, content_type = await asyncio.to_thread(fetch)
        filename = Path(parts.path).name or "resource"
        return (
            filename,
            _content_type(filename, config.get("content_type") or content_type),
            self._bounded(content),
            {"url": url},
        )

    async def _git(
        self, config: dict[str, Any], allowlist: tuple[str, ...]
    ) -> tuple[str, str, bytes, dict[str, Any]]:
        repository = Path(str(config.get("repository_path", ""))).resolve()
        relative_path = str(config.get("path", ""))
        if (
            not repository.is_dir()
            or not _inside(repository, allowlist)
            or not relative_path
            or Path(relative_path).is_absolute()
            or ".." in Path(relative_path).parts
        ):
            raise ApiProblem(
                403,
                "CONNECTOR_ALLOWLIST_DENIED",
                "Connector repository denied",
                "The Git repository or file path is not allowlisted.",
            )
        revision = str(config.get("revision", "HEAD"))
        process = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            str(repository),
            "show",
            f"{revision}:{relative_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await process.communicate()
        if process.returncode != 0:
            raise ApiProblem(
                422,
                "CONNECTOR_RESOURCE_UNAVAILABLE",
                "Git resource unavailable",
                "The allowlisted Git revision or path is unavailable.",
            )
        return (
            Path(relative_path).name,
            _content_type(relative_path, config.get("content_type")),
            self._bounded(stdout),
            {"repository_path": str(repository), "revision": revision, "path": relative_path},
        )

    def _bounded(self, content: bytes) -> bytes:
        if not content or len(content) > self._maximum_bytes:
            raise ApiProblem(
                413,
                "CONNECTOR_RESOURCE_LIMIT_EXCEEDED",
                "Connector object rejected",
                "The connector response exceeds the configured Raw size limit.",
            )
        return content
