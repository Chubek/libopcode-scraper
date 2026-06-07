from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def headers_dir() -> Path:
    return project_root() / "LibOpcode-Headers"


def files_dir() -> Path:
    return project_root() / "LibOpcode-Files"


def default_output_dir(arch: str) -> Path:
    return Path.cwd() / "output" / arch

