from __future__ import annotations

from collections import Counter
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
    if len(text) > 120 and " " in text:
        return True
    return False


_MNEMONIC_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.+-]{0,63}$")
_NUMERIC_OPCODE_RE = re.compile(r"^(?:0x[0-9a-f]+|\d+)(?:/[0-9a-f]+)?$", re.IGNORECASE)
_ALNUM_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

_OPERAND_KIND_DESCRIPTIONS = {
    "register": "Architectural register operand.",
    "vector-register": "SIMD/vector register operand class.",
    "system-register": "Architecture-defined system/control register name.",
    "accumulator": "Accumulator-specialized register operand.",
    "register-or-memory": "Operand may be register or memory form.",
    "memory": "Memory addressing operand.",
    "displacement": "Displacement/offset operand.",
    "immediate": "Immediate literal operand.",
    "predicate": "Predicate/mask operand.",
    "condition": "Condition-code selector operand.",
    "flag": "Status/flag operand.",
    "other": "Unclassified but preserved normalized operand token.",
}

_OPCODE_FORM_DESCRIPTIONS = {
    "numeric": "Byte/word opcode value (hex or decimal).",
    "numeric-with-selector": "Numeric opcode with selector/extension (e.g. /digit).",
    "symbolic-call": "Macro/function-style encoding identifier.",
    "symbolic": "Symbolic encoding identifier.",
    "bit-pattern": "Bit-pattern opcode representation.",
}

_OPERAND_ALIAS_NOTES = [
    ("reg*", "Register width shorthand (e.g. reg8/reg16/reg32/reg64)."),
    ("imm*", "Immediate width shorthand (e.g. imm8/imm16/imm32)."),
    ("disp*/dsp*", "Displacement shorthand for offset operands."),
    ("base-index", "Base/index memory addressing form."),
    ("any", "Unspecified operand class/width in source tables."),
]

_ENCODING_FLAG_MARKERS = (
    "modrm",
    "prefix",
    "rex",
    "vex",
    "evex",
    "map",
    "space",
    "opcode",
    "suf",
    "syntax",
    "implicit",
    "stack",
    "size",
    "optimize",
    "constraint",
)

_TOKEN_CANONICAL = {
    "reg": "register",
    "reg8": "reg8",
    "reg16": "reg16",
    "reg32": "reg32",
    "reg64": "reg64",
    "regmem": "reg-or-mem",
    "sreg": "segment-register",
    "control": "control-register",
    "debug": "debug-register",
    "test": "test-register",
    "acc": "accumulator",
    "imm": "immediate",
    "imm8": "imm8",
    "imm16": "imm16",
    "imm32": "imm32",
    "imm64": "imm64",
    "imm8s": "imm8s",
    "imm32s": "imm32s",
    "disp": "displacement",
    "disp8": "disp8",
    "disp16": "disp16",
    "disp32": "disp32",
    "disp64": "disp64",
    "dsp8": "disp8",
    "dsp16": "disp16",
    "baseindex": "base-index",
    "unspecified": "any",
    "memory": "memory",
    "mem": "memory",
    "indirect": "indirect",
    "predicate": "predicate",
    "pred": "predicate",
    "flag": "flag",
    "condition": "condition",
    "cc": "condition",
    "byte": "byte",
    "word": "word",
    "dword": "dword",
    "qword": "qword",
    "xmmword": "xmmword",
    "ymmword": "ymmword",
    "zmmword": "zmmword",
    "tmmword": "tmmword",
}

_WIDTH_LABELS = {"byte", "word", "dword", "qword", "xmmword", "ymmword", "zmmword", "tmmword"}


def _valid_mnemonic(value: str) -> bool:
    text = _clean_text(value)
    if _is_noise(text):
        return False
    return bool(_MNEMONIC_RE.fullmatch(text))


def _to_kebab(value: str) -> str:
    text = value.strip().strip("{}[]()")
    text = text.strip('"').strip("'")
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", text)
    text = text.replace("_", "-")
    text = re.sub(r"[^A-Za-z0-9.+-]", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-").lower()


def _split_top_level(value: str, separator: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    escaped = False
    for char in value:
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
            continue
        if char in "([{":
            depth += 1
            current.append(char)
            continue
        if char in ")]}":
            depth = max(0, depth - 1)
            current.append(char)
            continue
        if depth == 0 and char == separator:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items


def _tokenize_blob(value: str) -> list[str]:
    return [item for item in _ALNUM_TOKEN_RE.findall(value) if item]


def _canonical_token(token: str) -> str:
    direct = _TOKEN_CANONICAL.get(token.lower())
    if direct:
        return direct
    clean = _to_kebab(token)
    if not clean:
        return ""
    return _TOKEN_CANONICAL.get(clean, clean)


def _operand_kind(raw: str, options: list[str]) -> str:
    raw_lower = raw.lower()
    option_blob = "|".join(options)
    has_reg = any("reg" in token for token in options) or any(marker in raw_lower for marker in (" r", "reg", "xmm", "ymm", "zmm"))
    has_mem = any(token in {"memory", "base-index", "indirect"} or "mem" in token for token in options)
    has_disp = any(token.startswith(("disp", "dsp")) or token == "displacement" for token in options)
    has_imm = any(token.startswith("imm") or "immediate" in token for token in options)

    if "predicate" in option_blob:
        return "predicate"
    if "accumulator" in option_blob:
        return "accumulator"
    if any(marker in option_blob for marker in ("xmm", "ymm", "zmm", "tmm", "vector")):
        return "vector-register"
    if re.search(r"[_-]el[0-9]", raw_lower) or raw_lower.startswith(("sctlr", "ttbr", "sysreg")):
        return "system-register"
    if has_reg and has_mem:
        return "register-or-memory"
    if has_reg:
        return "register"
    if has_mem and has_disp:
        return "memory"
    if has_mem:
        return "memory"
    if has_disp:
        return "displacement"
    if has_imm:
        return "immediate"
    if "condition" in option_blob:
        return "condition"
    if "flag" in option_blob:
        return "flag"
    return "other"


def _looks_like_encoding_blob(value: str) -> bool:
    lowered = value.lower()
    if "{" in lowered and "}" in lowered:
        return False
    if "|" not in lowered:
        return False
    return any(marker in lowered for marker in _ENCODING_FLAG_MARKERS)


def _extract_braced_operands(values: list[str]) -> list[str]:
    slots: list[str] = []
    for value in values:
        for match in re.findall(r"\{([^{}]+)\}", value):
            for part in _split_top_level(match, ","):
                cleaned = _clean_text(part)
                if cleaned and not _is_noise(cleaned):
                    slots.append(cleaned)
    return slots


def _extract_operand_slots(record: dict[str, Any], opcode_value: str) -> list[str]:
    raw_operands = record.get("operands", [])
    operand_values: list[str] = []
    if isinstance(raw_operands, list):
        for item in raw_operands:
            if isinstance(item, dict):
                value = str(item.get("name", "") or item.get("raw", "")).strip()
            else:
                value = str(item).strip()
            if value:
                operand_values.append(value)
    elif raw_operands:
        operand_values.append(str(raw_operands))

    slots = _extract_braced_operands(operand_values)
    if slots:
        return slots

    extracted: list[str] = []
    for value in operand_values:
        stripped = _clean_text(value)
        if not stripped or stripped == opcode_value:
            continue
        if _looks_like_encoding_blob(stripped):
            continue
        for part in _split_top_level(stripped, ","):
            clean_part = _clean_text(part)
            if not clean_part or _is_noise(clean_part):
                continue
            if _looks_like_encoding_blob(clean_part):
                continue
            extracted.append(clean_part)
    return extracted


def _normalize_operand(raw: str) -> dict[str, Any] | None:
    text = _clean_text(raw)
    if not text or _is_noise(text):
        return None
    if re.fullmatch(r"[0-9]+", text):
        return None
    options: list[str] = []
    if "|" in text:
        for token in text.split("|"):
            clean = _canonical_token(token)
            if clean:
                options.append(clean)
    else:
        clean = _canonical_token(text)
        if clean:
            options.append(clean)
    if not options:
        return None
    deduped = list(dict.fromkeys(options))
    kind = _operand_kind(text, deduped)
    payload: dict[str, Any] = {"kind": kind, "text": " | ".join(deduped)}
    if len(deduped) > 1:
        payload["options"] = deduped
    widths = [item for item in deduped if item in _WIDTH_LABELS]
    qualifiers: dict[str, Any] = {}
    if widths:
        qualifiers["width"] = widths[0] if len(widths) == 1 else widths
    if "implicit" in text.lower():
        qualifiers["implicit"] = True
    if qualifiers:
        payload["qualifiers"] = qualifiers
    return payload


def _candidate_score(value: str) -> int:
    text = _clean_text(value)
    if not text or _is_noise(text):
        return 0
    lowered = text.lower()
    if _NUMERIC_OPCODE_RE.fullmatch(lowered):
        return 10
    if "(" in text and ")" in text and any(ch.isalpha() for ch in text):
        return 9
    if re.fullmatch(r"[01xX? ]{6,}", text):
        return 8
    if any(marker in lowered for marker in ("opcode", "opc", "enc", "pattern")):
        return 7
    if re.fullmatch(r"[A-Z][A-Z0-9_]*(?:\([^\)]*\))?", text):
        return 6
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_./+-]{0,63}", text):
        return 3
    return 1


def _best_opcode_candidate(record: dict[str, Any], operand_slots: list[str]) -> tuple[str, int]:
    direct_candidates: list[str] = []
    for key in ("opcode", "encoding", "pattern"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            direct_candidates.append(value.strip())

    for candidate in direct_candidates:
        score = _candidate_score(candidate)
        if score >= 3:
            return _clean_text(candidate), score

    candidates: list[str] = []
    operands = record.get("operands", [])
    if isinstance(operands, list):
        for item in operands:
            if isinstance(item, dict):
                value = str(item.get("name", "") or item.get("raw", "")).strip()
            else:
                value = str(item).strip()
            if value:
                candidates.append(value)

    best_text = ""
    best_score = 0
    operand_slot_set = {_clean_text(slot) for slot in operand_slots}
    for candidate in candidates:
        if _clean_text(candidate) in operand_slot_set:
            continue
        score = _candidate_score(candidate)
        if score > best_score:
            best_text = _clean_text(candidate)
            best_score = score
    return best_text, best_score


def _split_constraints(value: str) -> list[str]:
    if not value:
        return []
    pieces = re.split(r"[&|]", value)
    results: list[str] = []
    for piece in pieces:
        token = _clean_text(piece)
        if not token or token == "0" or _is_noise(token):
            continue
        results.append(token)
    return list(dict.fromkeys(results))


def _encoding_flags(record: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for item in record.get("flags", []) or []:
        token = _to_kebab(str(item))
        if token:
            found.append(token)

    operands = record.get("operands", [])
    if isinstance(operands, list):
        for value in operands:
            text = str(value)
            if not _looks_like_encoding_blob(text):
                continue
            for token in text.split("|"):
                normalized = _to_kebab(token)
                if not normalized:
                    continue
                if any(marker in normalized for marker in _ENCODING_FLAG_MARKERS) or len(normalized) <= 2:
                    found.append(normalized)

    deduped = list(dict.fromkeys(found))
    return deduped[:12]


def _opcode_form(value: str) -> str:
    text = _clean_text(value)
    lowered = text.lower()
    if "/" in text and _NUMERIC_OPCODE_RE.fullmatch(lowered):
        return "numeric-with-selector"
    if _NUMERIC_OPCODE_RE.fullmatch(lowered):
        return "numeric"
    if re.fullmatch(r"[01xX? ]{6,}", text):
        return "bit-pattern"
    if "(" in text and ")" in text:
        return "symbolic-call"
    return "symbolic"


def _build_opcode(record: dict[str, Any], opcode_text: str) -> dict[str, Any]:
    text = _clean_text(opcode_text)
    base = text
    selector = ""
    if "/" in text and not text.endswith("/"):
        left, right = text.split("/", 1)
        if left and right:
            base = left
            selector = right

    payload: dict[str, Any] = {
        "form": _opcode_form(text),
        "value": base,
    }
    if selector:
        payload["selector"] = selector
    constraints = _split_constraints(str(record.get("mask", "") or ""))
    if constraints:
        payload["constraints"] = constraints
    flags = _encoding_flags(record)
    if flags:
        payload["encoding_flags"] = flags
    table = _clean_text(str(record.get("table", "")))
    if table:
        payload["table"] = table
    return payload


def _entry_signature(entry: dict[str, Any]) -> tuple[str, str, str]:
    mnemonic = str(entry.get("mnemonic", ""))
    opcode = entry.get("opcode", {})
    operands = entry.get("operands", [])
    opcode_sig = repr(sorted(opcode.items())) if isinstance(opcode, dict) else str(opcode)
    operand_sig = "|".join(str(item.get("text", "")) for item in operands if isinstance(item, dict))
    return mnemonic, opcode_sig, operand_sig


def _record_operands(record: dict[str, Any]) -> list[str]:
    values: list[str] = []
    raw_operands = record.get("operands", [])
    if isinstance(raw_operands, list):
        for item in raw_operands:
            if isinstance(item, dict):
                value = str(item.get("name", "") or item.get("raw", "")).strip()
            else:
                value = str(item).strip()
            if value:
                values.append(value)
    elif raw_operands:
        values.append(str(raw_operands))
    return values


_CPENC_RE = re.compile(
    r"^\s*CPENC\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)\s*$",
    re.IGNORECASE,
)


def _decode_cpenc(value: str) -> dict[str, Any] | None:
    match = _CPENC_RE.match(value.strip())
    if not match:
        return None
    op0, op1, crn, crm, op2 = [int(item) for item in match.groups()]
    encoding = ((op0 & 0x3) << 14) | ((op1 & 0x7) << 11) | ((crn & 0xF) << 7) | ((crm & 0xF) << 3) | (op2 & 0x7)
    return {
        "value": f"0x{encoding:04x}",
        "subfields": {"op0": op0, "op1": op1, "crn": crn, "crm": crm, "op2": op2},
    }


def _build_aarch64_sysreg_entry(record: dict[str, Any], used_ids: set[str]) -> dict[str, Any] | None:
    mnemonic = _clean_text(str(record.get("mnemonic", "") or record.get("name", "")))
    if mnemonic.upper() not in {"SYSREG", "SYSREG128"}:
        return None
    operands = _record_operands(record)
    if len(operands) < 2:
        return None

    reg_name = _clean_text(operands[0])
    cpenc = _decode_cpenc(_clean_text(operands[1]))
    if not reg_name or cpenc is None:
        return None

    flags = _to_kebab(_clean_text(operands[2])) if len(operands) > 2 else ""
    features = _to_kebab(_clean_text(operands[3])) if len(operands) > 3 else ""

    entry_operands: list[dict[str, Any]] = [{"kind": "system-register", "text": reg_name}]
    if flags and flags not in {"0", "none"}:
        entry_operands.append({"kind": "flag", "text": flags})
    if features and features not in {"aarch64-no-features", "0", "none"}:
        entry_operands.append({"kind": "other", "text": features})

    opcode: dict[str, Any] = {
        "form": "numeric",
        "value": cpenc["value"],
        "encoding_kind": "cpenc",
        "subfields": cpenc["subfields"],
    }
    return {
        "id": _new_id(used_ids),
        "mnemonic": reg_name,
        "operands": entry_operands,
        "opcode": opcode,
    }


def _is_useful_entry(entry: dict[str, Any]) -> bool:
    opcode = entry.get("opcode", {})
    if not isinstance(opcode, dict):
        return False
    opcode_value = str(opcode.get("value", "")).strip().lower()
    operands = entry.get("operands", [])
    if not isinstance(operands, list):
        return False
    if not operands:
        return opcode_value not in {"", "0", "0x0"}

    kinds = [str(item.get("kind", "")) for item in operands if isinstance(item, dict)]
    texts = [str(item.get("text", "")).strip().lower() for item in operands if isinstance(item, dict)]
    if kinds and all(kind == "other" for kind in kinds):
        if opcode_value in {"0", "0x0"}:
            return False
        if texts and all(re.fullmatch(r"[0-9]+", text or "") for text in texts):
            return False
    if opcode.get("form") == "symbolic" and opcode_value in {"byte", "word", "dword", "qword"}:
        if len(texts) <= 2:
            return False
    return True


def _build_entries(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    used_ids: set[str] = set()

    for record in records:
        mnemonic = _clean_text(str(record.get("mnemonic", "") or record.get("name", "")))
        if not _valid_mnemonic(mnemonic):
            continue

        operand_slots = _extract_operand_slots(record, opcode_value="")
        opcode_text, score = _best_opcode_candidate(record, operand_slots)
        if score < 3:
            continue
        opcode = _build_opcode(record, opcode_text)

        operands: list[dict[str, Any]] = []
        for raw_operand in _extract_operand_slots(record, opcode_value=opcode_text):
            normalized = _normalize_operand(raw_operand)
            if normalized:
                operands.append(normalized)

        entry = {
            "id": _new_id(used_ids),
            "mnemonic": mnemonic,
            "operands": operands,
            "opcode": opcode,
        }
        if not _is_useful_entry(entry):
            continue
        signature = _entry_signature(entry)
        if signature in seen:
            continue
        seen.add(signature)
        entries.append(entry)

    return entries


def _operand_aliases(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    options: set[str] = set()
    for entry in entries:
        for operand in entry.get("operands", []) or []:
            if not isinstance(operand, dict):
                continue
            for option in operand.get("options", []) or []:
                options.add(str(option))

    aliases: list[dict[str, str]] = []
    for label, meaning in _OPERAND_ALIAS_NOTES:
        if label == "reg*" and any(item.startswith("reg") for item in options):
            aliases.append({"label": label, "meaning": meaning})
        if label == "imm*" and any(item.startswith("imm") for item in options):
            aliases.append({"label": label, "meaning": meaning})
        if label == "disp*/dsp*" and any(item.startswith("disp") for item in options):
            aliases.append({"label": label, "meaning": meaning})
        if label == "base-index" and "base-index" in options:
            aliases.append({"label": label, "meaning": meaning})
        if label == "any" and "any" in options:
            aliases.append({"label": label, "meaning": meaning})
    return aliases


def _operand_notes(entries: list[dict[str, Any]]) -> list[str]:
    kinds: set[str] = set()
    implicit_seen = False
    for entry in entries:
        for operand in entry.get("operands", []) or []:
            if not isinstance(operand, dict):
                continue
            kinds.add(str(operand.get("kind", "")))
            qualifiers = operand.get("qualifiers", {})
            if isinstance(qualifiers, dict) and qualifiers.get("implicit") is True:
                implicit_seen = True

    notes: list[str] = []
    if "register-or-memory" in kinds:
        notes.append("register-or-memory denotes table forms that accept either register or memory operands.")
    if "system-register" in kinds:
        notes.append("system-register entries preserve architecture-defined register identifiers.")
    if "predicate" in kinds:
        notes.append("predicate captures mask/predicate operands used for predicated execution.")
    if implicit_seen:
        notes.append("implicit=true marks operands implied by encoding rather than explicit assembly syntax.")
    return notes


def _opcode_notes(entries: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[str], list[str]]:
    forms: set[str] = set()
    has_selector = False
    has_constraints = False
    has_flags = False
    flag_counter: Counter[str] = Counter()

    for entry in entries:
        opcode = entry.get("opcode", {})
        if not isinstance(opcode, dict):
            continue
        form = str(opcode.get("form", ""))
        if form:
            forms.add(form)
        if opcode.get("selector"):
            has_selector = True
        if opcode.get("constraints"):
            has_constraints = True
        flags = opcode.get("encoding_flags", [])
        if isinstance(flags, list) and flags:
            has_flags = True
            for token in flags:
                flag_counter[str(token)] += 1

    observed_forms = [{"form": form, "description": _OPCODE_FORM_DESCRIPTIONS.get(form, "Opcode representation.")} for form in sorted(forms)]
    notes: list[str] = []
    if has_selector:
        notes.append("selector denotes opcode extensions/sub-opcodes (e.g. slash forms).")
    if has_constraints:
        notes.append("constraints capture variant guards such as ISA mode or feature requirements.")
    if has_flags:
        notes.append("encoding_flags capture compact encoding modifiers (prefix/map/modrm/size style tags).")
    common_terms = [item for item, _ in flag_counter.most_common(12)]
    return observed_forms, notes, common_terms


def _build_header(entries: list[dict[str, Any]]) -> dict[str, Any]:
    kind_counter: Counter[str] = Counter()
    for entry in entries:
        for operand in entry.get("operands", []) or []:
            if isinstance(operand, dict):
                kind_counter[str(operand.get("kind", "other"))] += 1

    observed_types = [
        {"kind": kind, "description": _OPERAND_KIND_DESCRIPTIONS.get(kind, "Normalized operand class.")}
        for kind, _ in kind_counter.most_common()
        if kind
    ]
    opcode_forms, opcode_notes, encoding_terms = _opcode_notes(entries)

    operand_model: dict[str, Any] = {
        "item_schema": {
            "kind": "normalized operand class",
            "text": "readable operand representation",
            "options": "optional normalized alternatives",
            "qualifiers": "optional compact details",
        },
        "observed_types": observed_types,
        "aliases": _operand_aliases(entries),
        "normalization_rules": [
            "Packed tokens are decomposed into per-operand records.",
            "Pipe-delimited alternatives are normalized into options lists.",
            "Low-confidence parser scaffolding is omitted rather than emitted.",
        ],
        "architecture_notes": _operand_notes(entries),
    }

    opcode_model: dict[str, Any] = {
        "item_schema": {
            "form": "representation kind",
            "value": "primary opcode value or encoding identifier",
            "selector": "optional opcode extension selector",
            "constraints": "optional variant constraints",
            "encoding_flags": "optional encoding modifiers",
            "subfields": "optional opcode bitfield/subfield mapping",
        },
        "observed_forms": opcode_forms,
        "normalization_rules": [
            "Slash opcode forms are split into value and selector.",
            "Mask/feature guards are emitted as constraints when present.",
            "Encoding-only tags are kept in encoding_flags.",
        ],
        "notes": opcode_notes,
    }
    if encoding_terms:
        opcode_model["encoding_terms"] = encoding_terms
    return {"operand_model": operand_model, "opcode_model": opcode_model}


def build_succinct_payload(arch_payload: dict[str, Any]) -> dict[str, Any]:
    opcode_records = [item for item in (arch_payload.get("opcodes", []) or []) if isinstance(item, dict)]
    instruction_records = [item for item in (arch_payload.get("instructions", []) or []) if isinstance(item, dict)]

    entries = _build_entries(opcode_records)
    if not entries:
        entries = _build_entries(instruction_records)

    if str(arch_payload.get("name", "")).lower() == "aarch64":
        used_ids = {str(item.get("id", "")) for item in entries}
        aarch64_entries: list[dict[str, Any]] = []
        for record in instruction_records:
            parsed = _build_aarch64_sysreg_entry(record, used_ids)
            if not parsed:
                continue
            aarch64_entries.append(parsed)
        if aarch64_entries:
            entries = aarch64_entries

    return {
        "header": _build_header(entries),
        "entries": entries,
    }
