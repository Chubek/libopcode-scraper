from __future__ import annotations

from pathlib import Path
from typing import Iterable


def ext(path: Path) -> str:
    return path.suffix.lower()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def stable_sorted_paths(paths: Iterable[Path]) -> list[Path]:
    return sorted(paths, key=lambda value: str(value).lower())

