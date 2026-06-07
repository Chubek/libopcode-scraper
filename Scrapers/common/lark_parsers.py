from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


TBL_GRAMMAR = r"""
start: line*
line: COMMENT -> comment
    | directive
    | record
    | BLANK -> blank
directive: PERCENT_TEXT
record: FIELD (SEP FIELD)*
FIELD: /[^,;\n#\/][^\n,;]*/
SEP: /[,;]/
PERCENT_TEXT: /%[^\n]+/
COMMENT: /[ \t]*(#|\/\/)[^\n]*/
BLANK: /[ \t]+/
%import common.NEWLINE
%ignore NEWLINE
"""

OPC_GRAMMAR = r"""
start: line*
line: COMMENT -> comment
    | directive
    | record
    | BLANK -> blank
directive: DOT_TEXT
record: FIELD (SEP FIELD)*
FIELD: /[^,;\n#\/][^\n,;]*/
SEP: /[,;]/
DOT_TEXT: /[ \t]*\.[A-Za-z_][^\n]+/
COMMENT: /[ \t]*(#|\/\/)[^\n]*/
BLANK: /[ \t]+/
%import common.NEWLINE
%ignore NEWLINE
"""

DEF_GRAMMAR = r"""
start: line*
line: COMMENT -> comment
    | record
    | BLANK -> blank
record: FIELD
FIELD: /[^#\/\n][^\n]*/
COMMENT: /[ \t]*(#|\/\/)[^\n]*/
BLANK: /[ \t]+/
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
        "tbl": Lark(TBL_GRAMMAR, parser="lalr", lexer="basic", maybe_placeholders=False),
        "opc": Lark(OPC_GRAMMAR, parser="lalr", lexer="basic", maybe_placeholders=False),
        "def": Lark(DEF_GRAMMAR, parser="lalr", lexer="basic", maybe_placeholders=False),
    }


def _split_fields(raw: str, separators: str = ",;") -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    escaped = False
    for char in raw.strip().rstrip(","):
        if quote:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
        elif char in "([{":
            depth += 1
            current.append(char)
        elif char in ")]}":
            depth = max(0, depth - 1)
            current.append(char)
        elif depth == 0 and char in separators:
            field = "".join(current).strip()
            if field:
                fields.append(field)
            current = []
        else:
            current.append(char)
    field = "".join(current).strip()
    if field:
        fields.append(field)
    return fields


def _strip_inline_comment(line: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(line):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "#":
            return line[:index]
        elif char == "/" and index + 1 < len(line) and line[index + 1] == "/":
            return line[:index]
    return line


def _clean_lines(text: str) -> list[str]:
    kept: list[str] = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if in_block:
            if "*/" in stripped:
                in_block = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block = True
            continue
        stripped = _strip_inline_comment(line).strip()
        if not stripped or stripped.startswith(("#", "/*", "*", "*/")):
            continue
        kept.append(stripped)
    return kept


def _lark_input(text: str, suffix: str) -> str:
    projected: list[str] = []
    for line in _clean_lines(text):
        if line.startswith(("%", ".")):
            projected.append(line)
        elif suffix == "def" and "(" in line and ")" in line:
            name = line.split("(", 1)[0].strip()
            projected.append(f"{name}(1)")
        else:
            projected.append("x,y")
    return "\n".join(projected) or "x,y"


def parse_special(path: Path) -> LarkParseResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower().lstrip(".")
    try:
        parser_map = _build_parser()
        parser = parser_map.get(suffix, parser_map["tbl"])
        parser.parse(_lark_input(text, suffix))
        records: list[dict[str, Any]] = []
        directives: list[str] = []
        for stripped in _clean_lines(text):
            if stripped.startswith(("%", ".")):
                directives.append(stripped)
                continue
            if suffix == "def" and "(" in stripped and ")" in stripped:
                name = stripped.split("(", 1)[0].strip()
                arg_blob = stripped.split("(", 1)[1].rsplit(")", 1)[0]
                fields = [name] + _split_fields(arg_blob, ",")
                records.append({"fields": fields, "raw": stripped})
                continue
            separators = ",;" if suffix in {"tbl", "opc"} else ","
            fields = _split_fields(stripped, separators)
            if fields:
                records.append({"fields": fields, "raw": stripped})
        return LarkParseResult(parser=f"lark:{suffix}", records=records, directives=directives, warnings=[])
    except Exception as exc:
        records = []
        for stripped in _clean_lines(text):
            if stripped.startswith(("%", ".")):
                continue
            fields = _split_fields(stripped, ",;")
            records.append({"fields": fields, "raw": stripped})
        return LarkParseResult(
            parser=f"lark_fallback:{suffix}",
            records=records,
            directives=[],
            warnings=[f"Lark parse failed: {exc}"],
        )
