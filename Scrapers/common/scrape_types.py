from __future__ import annotations

from typing import Literal

ScrapeCategory = Literal["all", "dis", "opc", "inst"]
OUTPUT_FORMATS = {"json", "yaml", "xml", "sexpr"}
VALID_CATEGORIES = {"all", "dis", "opc", "inst"}

