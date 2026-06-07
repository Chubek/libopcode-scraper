from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


TBL_GRAMMAR = r"""
start: line*
line: directive | record | comment | blank
directive: "%" /[^\n]*/
record: field ("," field)*
field: /[^,\n]+/
comment: /[ \t]*[#;].*/
blank: /[ \t]*/
%import common.NEWLINE
%ignore NEWLINE
"""

OPC_GRAMMAR = r"""
start: line*
line: directive | record | comment | blank
directive: /[ \t]*\.[A-Za-z_][A-Za-z0-9_.-]*/ /[^\n]*/
record: mnemonic sep field*
mnemonic: /[A-Za-z_.$][A-Za-z0-9_.$-]*/
sep: /[ \t,:]+/
field: /[^,\s][^,\n]*/
comment: /[ \t]*[#;].*/
blank: /[ \t]*/
%import common.NEWLINE
%ignore NEWLINE
"""

DEF_GRAMMAR = r"""
start: line*
line: macrodef | record | comment | blank
macrodef: /[ \t]*[A-Za-z_][A-Za-z0-9_]*/ "(" /[^)]*/ ")" /[ \t]*/ ","?
record: field ("," field)*
field: /[^,\n]+/
comment: /[ \t]*[#;].*/
blank: /[ \t]*/
%import common.NEWLINE
%ignore NEWLINE
"""


@dataclass
class LarkParseResult:
    parser: str
    records: list[dict[str, Any]]
    directives: list[str]
    warnings: list[str]


def _build_parser():
    from lark import Lark  # type: ignore

    return {
        "tbl": Lark(TBL_GRAMMAR, parser="lalr", maybe_placeholders=False),
        "opc": Lark(OPC_GRAMMAR, parser="lalr", maybe_placeholders=False),
        "def": Lark(DEF_GRAMMAR, parser="lalr", maybe_placeholders=False),
    }


def parse_special(path: Path) -> LarkParseResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower().lstrip(".")
    try:
        parser_map = _build_parser()
        parser = parser_map.get(suffix, parser_map["tbl"])
        tree = parser.parse(text)
        records: list[dict[str, Any]] = []
        directives: list[str] = []
        for node in tree.children:
            if getattr(node, "data", None) != "line" or not node.children:
                continue
            inner = node.children[0]
            data = getattr(inner, "data", None)
            if data == "directive":
                pieces = [str(part).strip() for part in inner.children]
                directives.append(" ".join(piece for piece in pieces if piece))
            elif data == "macrodef":
                raw = "".join(str(part) for part in inner.children).strip()
                name = raw.split("(", 1)[0].strip()
                arg_blob = raw.split("(", 1)[1].rsplit(")", 1)[0] if "(" in raw and ")" in raw else ""
                fields = [name] + [arg.strip() for arg in arg_blob.split(",") if arg.strip()]
                records.append({"fields": fields, "raw": raw})
            elif data == "record":
                fields = []
                for child in inner.children:
                    if getattr(child, "data", None) == "mnemonic":
                        fields.append("".join(str(part) for part in child.children).strip())
                    elif getattr(child, "data", None) == "field":
                        fields.append("".join(str(part) for part in child.children).strip())
                    else:
                        token = str(child).strip()
                        if token and token not in {",", ":"}:
                            fields.append(token)
                fields = [field for field in fields if field]
                if fields:
                    records.append({"fields": fields, "raw": ",".join(fields)})
        return LarkParseResult(parser=f"lark:{suffix}", records=records, directives=directives, warnings=[])
    except Exception as exc:
        records = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";", "%")):
                continue
            fields = [part.strip() for part in stripped.split(",")]
            records.append({"fields": fields, "raw": stripped})
        return LarkParseResult(
            parser=f"lark_fallback:{suffix}",
            records=records,
            directives=[],
            warnings=[f"Lark parse failed: {exc}"],
        )
