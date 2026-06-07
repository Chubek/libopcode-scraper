from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import re

from .paths import files_dir, headers_dir
from .utils import stable_sorted_paths

IGNORE_PREFIXES = ("ChangeLog", "Makefile", "configure", "aclocal.m4", "MAINTAINERS")
IGNORE_EXACT = {
    "sysdep.h",
    "disassemble.c",
    "disassemble.h",
    "dis-init.c",
    "dis-buf.c",
    "opc2c.c",
    "opintl.h",
}


@dataclass(frozen=True)
class DiscoveredFiles:
    headers: list[Path]
    sources: list[Path]
    special: list[Path]

    @property
    def all_files(self) -> list[Path]:
        return stable_sorted_paths([*self.headers, *self.sources, *self.special])


def _should_ignore(path: Path) -> bool:
    name = path.name
    if path.parts and "po" in path.parts:
        return True
    if name in IGNORE_EXACT:
        return True
    if name.startswith("cgen-"):
        return True
    return any(name.startswith(prefix) for prefix in IGNORE_PREFIXES)


def _all_candidates() -> Iterable[Path]:
    for base in (headers_dir(), files_dir()):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and not _should_ignore(path):
                yield path


def discover_arch_files(arch: str, tokens: set[str]) -> DiscoveredFiles:
    headers: list[Path] = []
    sources: list[Path] = []
    special: list[Path] = []
    token_patterns = [
        re.compile(rf"(^|[-_.]){re.escape(token)}([-_.]|$)") for token in sorted(tokens)
    ]
    for path in _all_candidates():
        name = path.name.lower()
        stem = path.stem.lower()
        if not any(pattern.search(name) or pattern.search(stem) for pattern in token_patterns):
            continue
        suffix = path.suffix.lower()
        if suffix in {".h"}:
            headers.append(path)
        elif suffix in {".tbl", ".opc", ".def"}:
            special.append(path)
        else:
            sources.append(path)
    return DiscoveredFiles(
        headers=stable_sorted_paths(headers),
        sources=stable_sorted_paths(sources),
        special=stable_sorted_paths(special),
    )
