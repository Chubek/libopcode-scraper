from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class SourceFile:
    path: str
    parser: str
    kind: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class Macro:
    name: str
    value: str
    source_files: list[str]
    raw: str = ""


@dataclass
class EnumType:
    name: str
    values: list[str]
    source_files: list[str]
    raw: str = ""


@dataclass
class FunctionRecord:
    name: str
    signature: str
    source_files: list[str]
    raw: str = ""


@dataclass
class TableRecord:
    name: str
    fields: list[str]
    source_files: list[str]
    raw: str = ""


@dataclass
class DecodeRule:
    name: str
    pattern: str
    action: str
    conditions: list[str]
    source_files: list[str]
    raw: str = ""


@dataclass
class Operand:
    name: str
    kind: str = ""
    raw: str = ""


@dataclass
class Instruction:
    name: str
    mnemonic: str
    aliases: list[str]
    operands: list[Operand]
    encoding: str
    flags: list[str]
    source_files: list[str]
    raw: str = ""


@dataclass
class OpcodeRecord:
    mnemonic: str
    opcode: str
    mask: str
    operands: list[str]
    flags: list[str]
    table: str
    source_files: list[str]
    raw: str = ""


@dataclass
class Register:
    name: str
    number: int | None
    reg_class: str
    aliases: list[str]
    source_files: list[str]
    raw: str = ""


@dataclass
class Architecture:
    name: str
    pretty_name: str
    source_files: list[SourceFile] = field(default_factory=list)
    macros: list[Macro] = field(default_factory=list)
    enums: list[EnumType] = field(default_factory=list)
    typedefs: list[TableRecord] = field(default_factory=list)
    structs: list[TableRecord] = field(default_factory=list)
    functions: list[FunctionRecord] = field(default_factory=list)
    tables: list[TableRecord] = field(default_factory=list)
    decode_rules: list[DecodeRule] = field(default_factory=list)
    instructions: list[Instruction] = field(default_factory=list)
    opcodes: list[OpcodeRecord] = field(default_factory=list)
    registers: list[Register] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for entry in payload.get("source_files", []):
            if isinstance(entry.get("path"), Path):
                entry["path"] = str(entry["path"])
        return payload
