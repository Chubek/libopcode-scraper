from __future__ import annotations

import random
import re
import string
from typing import Any


def _new_id(used: set[str]) -> str:
    letters = string.ascii_uppercase
    while True:
        ident = "".join(random.choice(letters) for _ in range(4))
        if ident not in used:
            used.add(ident)
            return ident


def _normalize_operand(token: str) -> str:
    value = token.strip().lower()
    if not value:
        return ""
    if any(marker in value for marker in ("imm", "#", "immediate")):
        return "imm"
    if any(marker in value for marker in ("mem", "[", "]", "(", ")")):
        return "mem"
    if any(marker in value for marker in ("reg", "r/", "r/m", "xmm", "ymm", "zmm", "ax", "bx", "cx", "dx")):
        return "reg"
    if re.fullmatch(r"[re]?[abcd]x|r\d+[bwd]?|e?[sd]i|e?[sb]p", value):
        return "reg"
    if value.startswith("const") or value.startswith("lit"):
        return "imm"
    if value.startswith("m"):
        return "mem"
    return re.sub(r"[^a-z0-9_]+", "", value)[:24]


def _join_operands(operands: list[str]) -> str:
    cleaned = [_normalize_operand(item) for item in operands]
    cleaned = [item for item in cleaned if item]
    if not cleaned:
        return ""
    return ",".join(cleaned)


def _opcode_from_record(record: dict[str, Any]) -> str:
    candidates = [
        record.get("opcode"),
        record.get("encoding"),
        record.get("mask"),
        record.get("pattern"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _clean_text(value: str) -> str:
    return value.strip().strip('"').strip("'")


def _is_noise(value: str) -> bool:
    text = _clean_text(value)
    if not text:
        return True
    if text.startswith(("//", "#", ";", "/*", "*", "*/")):
        return True
    if "copyright" in text.lower():
        return True
    if len(text) > 80 and " " in text:
        return True
    return False


_MNEMONIC_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,31}$")


def _valid_mnemonic(value: str) -> bool:
    text = _clean_text(value)
    if _is_noise(text):
        return False
    return bool(_MNEMONIC_RE.fullmatch(text))


def _valid_opcode(value: str) -> bool:
    text = _clean_text(value)
    if _is_noise(text):
        return False
    if any(ch.isdigit() for ch in text):
        return True
    lowered = text.lower()
    return any(tag in lowered for tag in ("0x", "opc", "enc", "mask", "op"))


def build_succinct_entries(arch_payload: dict[str, Any]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    used_ids: set[str] = set()

    # Prefer opcode records because they tend to represent exact variants.
    for opc in arch_payload.get("opcodes", []) or []:
        mnemonic = _clean_text(str(opc.get("mnemonic", "")).strip())
        if not _valid_mnemonic(mnemonic):
            continue
        operands = opc.get("operands", [])
        if not isinstance(operands, list):
            operands = [str(operands)]
        opcode = _clean_text(_opcode_from_record(opc))
        if not _valid_opcode(opcode):
            continue
        entries.append(
            {
                "id": _new_id(used_ids),
                "mnemonic": mnemonic,
                "operands": _join_operands([str(item) for item in operands]),
                "opcode": opcode,
            }
        )

    # Fill gaps from instructions only when opcode-like identifier exists.
    for ins in arch_payload.get("instructions", []) or []:
        mnemonic = _clean_text(str(ins.get("mnemonic", "") or ins.get("name", "")).strip())
        if not _valid_mnemonic(mnemonic):
            continue
        opcode = _clean_text(_opcode_from_record(ins))
        if not _valid_opcode(opcode):
            continue
        operands = ins.get("operands", [])
        flat_operands: list[str] = []
        if isinstance(operands, list):
            for item in operands:
                if isinstance(item, dict):
                    flat_operands.append(str(item.get("name", "") or item.get("raw", "")).strip())
                else:
                    flat_operands.append(str(item))
        entries.append(
            {
                "id": _new_id(used_ids),
                "mnemonic": mnemonic,
                "operands": _join_operands(flat_operands),
                "opcode": opcode,
            }
        )

    return entries
