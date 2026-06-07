from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CParseResult:
    parser: str
    macros: list[dict[str, Any]]
    enums: list[dict[str, Any]]
    typedefs: list[dict[str, Any]]
    structs: list[dict[str, Any]]
    functions: list[dict[str, Any]]
    tables: list[dict[str, Any]]
    warnings: list[str]


def _load_c_parser():
    try:
        from tree_sitter_languages import get_parser  # type: ignore

        return get_parser("c"), "tree_sitter_languages"
    except Exception:
        tree_sitter_languages_unavailable = True
    try:
        from tree_sitter import Language, Parser  # type: ignore
        import tree_sitter_c  # type: ignore

        parser = Parser()
        parser.language = Language(tree_sitter_c.language())
        return parser, "tree_sitter_c"
    except Exception:
        _ = tree_sitter_languages_unavailable
        return None, "fallback_regex"


def _node_text(blob: bytes, start: int, end: int) -> str:
    return blob[start:end].decode("utf-8", errors="replace").strip()


def _walk(node):
    stack = [node]
    while stack:
        cur = stack.pop()
        yield cur
        stack.extend(reversed(cur.children))


def _fallback_parse(content: str) -> CParseResult:
    macros = []
    enums = []
    typedefs = []
    structs = []
    functions = []
    tables = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#define "):
            parts = stripped.split(maxsplit=2)
            name = parts[1] if len(parts) > 1 else ""
            value = parts[2] if len(parts) > 2 else ""
            macros.append({"name": name, "value": value, "raw": stripped})
    for match in re.finditer(r"\benum\s+([A-Za-z_]\w*)?\s*\{", content):
        enums.append({"name": match.group(1) or "", "values": [], "raw": match.group(0)})
    for match in re.finditer(r"\btypedef\b[^;]*;", content):
        raw = match.group(0).strip()
        tail = raw.rsplit(" ", 1)[-1].rstrip(";")
        typedefs.append({"name": tail, "raw": raw})
    for match in re.finditer(r"\bstruct\s+([A-Za-z_]\w*)?\s*\{", content):
        structs.append({"name": match.group(1) or "", "raw": match.group(0)})
    for match in re.finditer(r"\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(\{|;)", content):
        name = match.group(1)
        functions.append({"name": name, "signature": match.group(0), "raw": match.group(0)})
    for match in re.finditer(r"\b([A-Za-z_]\w*)\s*(\[[^\]]*\])?\s*=\s*\{", content):
        tables.append({"name": match.group(1), "fields": [], "raw": match.group(0)})
    return CParseResult(
        parser="regex_fallback",
        macros=macros,
        enums=enums,
        typedefs=typedefs,
        structs=structs,
        functions=functions,
        tables=tables,
        warnings=["Tree-Sitter parser unavailable; used regex fallback"],
    )


def parse_c_family(path: Path) -> CParseResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    parser, parser_name = _load_c_parser()
    if parser is None:
        return _fallback_parse(text)

    blob = text.encode("utf-8", errors="replace")
    tree = parser.parse(blob)
    root = tree.root_node

    macros: list[dict[str, Any]] = []
    enums: list[dict[str, Any]] = []
    typedefs: list[dict[str, Any]] = []
    structs: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    warnings: list[str] = []

    for node in _walk(root):
        if node.type == "preproc_def":
            raw = _node_text(blob, node.start_byte, node.end_byte)
            parts = raw.split(maxsplit=2)
            name = parts[1] if len(parts) > 1 else ""
            value = parts[2] if len(parts) > 2 else ""
            macros.append({"name": name, "value": value, "raw": raw})
        elif node.type == "enum_specifier":
            raw = _node_text(blob, node.start_byte, node.end_byte)
            head = raw.split("{", 1)[0].replace("enum", "").strip()
            values = []
            body = raw.split("{", 1)[1].rsplit("}", 1)[0] if "{" in raw and "}" in raw else ""
            for item in body.split(","):
                name = item.strip().split("=", 1)[0].strip()
                if name:
                    values.append(name)
            enums.append({"name": head, "values": values, "raw": raw})
        elif node.type == "struct_specifier":
            raw = _node_text(blob, node.start_byte, node.end_byte)
            header = raw.split("{", 1)[0].replace("struct", "").strip()
            structs.append({"name": header, "raw": raw[:2000]})
        elif node.type == "type_definition":
            raw = _node_text(blob, node.start_byte, node.end_byte)
            name = ""
            tokens = raw.replace(";", " ").split()
            if tokens:
                name = tokens[-1]
            typedefs.append({"name": name, "raw": raw[:2000]})
        elif node.type in {"function_definition", "declaration"}:
            raw = _node_text(blob, node.start_byte, node.end_byte)
            if "(" in raw and ")" in raw:
                name = raw.split("(", 1)[0].strip().split()[-1]
                functions.append({"name": name, "signature": raw[:300], "raw": raw[:2000]})
        elif node.type == "init_declarator":
            raw = _node_text(blob, node.start_byte, node.end_byte)
            if "=" in raw and "{" in raw:
                left = raw.split("=", 1)[0].strip()
                name = left.split()[-1].split("[", 1)[0]
                tables.append({"name": name, "fields": [], "raw": raw[:2000]})

    if root.has_error:
        warnings.append("Tree-Sitter reported parse errors; partial data extracted")

    return CParseResult(
        parser=f"treesitter:{parser_name}",
        macros=macros,
        enums=enums,
        typedefs=typedefs,
        structs=structs,
        functions=functions,
        tables=tables,
        warnings=warnings,
    )
