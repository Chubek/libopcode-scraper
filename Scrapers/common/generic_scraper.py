from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .discovery import discover_arch_files
from .lark_parsers import parse_special
from .models import Architecture
from .normalize import add_c_parse, add_special_parse
from .treesitter_c import parse_c_family


@dataclass(frozen=True)
class ArchConfig:
    arch: str
    pretty_name: str
    tokens: set[str]


class GenericArchitectureScraper:
    def __init__(self, config: ArchConfig):
        self.config = config

    def discover_files(self):
        return discover_arch_files(self.config.arch, self.config.tokens)

    def scrape_all(self) -> dict[str, Any]:
        model = Architecture(name=self.config.arch, pretty_name=self.config.pretty_name)
        files = self.discover_files()
        for path in files.headers + files.sources:
            try:
                parsed = parse_c_family(path)
                add_c_parse(
                    model,
                    source_path=str(path),
                    parser=parsed.parser,
                    payload={
                        "macros": parsed.macros,
                        "enums": parsed.enums,
                        "typedefs": parsed.typedefs,
                        "structs": parsed.structs,
                        "functions": parsed.functions,
                        "tables": parsed.tables,
                        "warnings": parsed.warnings,
                    },
                )
            except Exception as exc:
                model.warnings.append(f"{path}: C parse failed: {exc}")

        for path in files.special:
            try:
                parsed = parse_special(path)
                add_special_parse(
                    model,
                    source_path=str(path),
                    parser=parsed.parser,
                    suffix=path.suffix.lower().lstrip("."),
                    payload={"records": parsed.records, "warnings": parsed.warnings},
                )
            except Exception as exc:
                model.warnings.append(f"{path}: special parse failed: {exc}")
        return model.to_dict()

    def _category_payload(self, category: str) -> dict[str, Any]:
        all_data = self.scrape_all()
        base = {
            "name": all_data.get("name"),
            "pretty_name": all_data.get("pretty_name"),
            "category": category,
            "warnings": all_data.get("warnings", []),
            "source_files": all_data.get("source_files", []),
        }
        if category == "dis":
            base["functions"] = all_data.get("functions", [])
            base["decode_rules"] = all_data.get("decode_rules", [])
        elif category == "opc":
            base["opcodes"] = all_data.get("opcodes", [])
            base["tables"] = all_data.get("tables", [])
        elif category == "inst":
            base["instructions"] = all_data.get("instructions", [])
            base["registers"] = all_data.get("registers", [])
            base["enums"] = all_data.get("enums", [])
            base["typedefs"] = all_data.get("typedefs", [])
            base["structs"] = all_data.get("structs", [])
        else:
            base["all"] = all_data
        return base

    def scrape_dis(self) -> dict[str, Any]:
        return self._category_payload("dis")

    def scrape_opc(self) -> dict[str, Any]:
        return self._category_payload("opc")

    def scrape_inst(self) -> dict[str, Any]:
        return self._category_payload("inst")
