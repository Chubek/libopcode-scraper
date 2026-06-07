from __future__ import annotations

import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from .utils import ensure_dir


def _to_sexpr(value, key: str | None = None) -> str:
    if isinstance(value, dict):
        parts = []
        for item_key in sorted(value.keys()):
            parts.append(_to_sexpr(value[item_key], item_key))
        body = " ".join(parts)
        if key is None:
            return f"({body})"
        return f"({key} {body})"
    if isinstance(value, list):
        body = " ".join(_to_sexpr(item) for item in value)
        if key is None:
            return f"({body})"
        return f"({key} {body})"
    atom = json.dumps(value)
    if key is None:
        return atom
    return f"({key} {atom})"


def _dict_to_xml(parent: Element, key: str, value) -> None:
    if isinstance(value, dict):
        node = SubElement(parent, key)
        for sub_key, sub_val in value.items():
            _dict_to_xml(node, sub_key, sub_val)
        return
    if isinstance(value, list):
        arr = SubElement(parent, key)
        for item in value:
            _dict_to_xml(arr, "item", item)
        return
    node = SubElement(parent, key)
    node.text = "" if value is None else str(value)


def render_payload(payload: dict, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(payload, indent=2, sort_keys=True)
    if fmt == "yaml":
        try:
            import yaml  # type: ignore

            return yaml.safe_dump(payload, sort_keys=True, allow_unicode=False)
        except Exception:
            return json.dumps(payload, indent=2, sort_keys=True)
    if fmt == "xml":
        root = Element("architecture")
        root.attrib["name"] = str(payload.get("name", ""))
        root.attrib["category"] = str(payload.get("category", ""))
        for key, value in payload.items():
            if key in {"name", "category"}:
                continue
            _dict_to_xml(root, key, value)
        return tostring(root, encoding="unicode")
    if fmt == "sexpr":
        return _to_sexpr(payload, "architecture")
    raise ValueError(f"Unsupported format: {fmt}")


def write_output(path: Path, payload: dict, fmt: str) -> None:
    ensure_dir(path.parent)
    rendered = render_payload(payload, fmt)
    path.write_text(rendered + "\n", encoding="utf-8")

