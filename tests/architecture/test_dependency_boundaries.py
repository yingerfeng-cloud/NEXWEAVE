from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PURE_PACKAGE_ROOTS = [ROOT / "packages/domain/src", ROOT / "packages/contracts/src"]
FORBIDDEN_IMPORT_PREFIXES = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "alembic",
    "temporalio",
    "redis",
    "asyncpg",
    "httpx",
    "boto",
    "rustfs",
    "openai",
    "anthropic",
)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_domain_and_contracts_do_not_depend_on_infrastructure() -> None:
    violations: list[str] = []
    for package_root in PURE_PACKAGE_ROOTS:
        for path in package_root.rglob("*.py"):
            for module in imported_modules(path):
                if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert violations == []
