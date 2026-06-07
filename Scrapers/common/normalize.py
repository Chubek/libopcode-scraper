from __future__ import annotations

from .models import (
    Architecture,
    DecodeRule,
    EnumType,
    FunctionRecord,
    Instruction,
    Macro,
    OpcodeRecord,
    Operand,
    Register,
    SourceFile,
    TableRecord,
)


def add_c_parse(arch: Architecture, source_path: str, parser: str, payload: dict) -> None:
    arch.source_files.append(SourceFile(path=source_path, parser=parser, kind="c", warnings=payload.get("warnings", [])))
    for item in payload.get("macros", []):
        arch.macros.append(Macro(name=item.get("name", ""), value=item.get("value", ""), source_files=[source_path], raw=item.get("raw", "")))
    for item in payload.get("enums", []):
        arch.enums.append(EnumType(name=item.get("name", ""), values=item.get("values", []), source_files=[source_path], raw=item.get("raw", "")))
    for item in payload.get("typedefs", []):
        arch.typedefs.append(
            TableRecord(
                name=item.get("name", ""),
                fields=[],
                source_files=[source_path],
                raw=item.get("raw", ""),
            )
        )
    for item in payload.get("structs", []):
        arch.structs.append(
            TableRecord(
                name=item.get("name", ""),
                fields=[],
                source_files=[source_path],
                raw=item.get("raw", ""),
            )
        )
    for item in payload.get("functions", []):
        arch.functions.append(
            FunctionRecord(
                name=item.get("name", ""),
                signature=item.get("signature", ""),
                source_files=[source_path],
                raw=item.get("raw", ""),
            )
        )
    for item in payload.get("tables", []):
        arch.tables.append(TableRecord(name=item.get("name", ""), fields=item.get("fields", []), source_files=[source_path], raw=item.get("raw", "")))


def add_special_parse(arch: Architecture, source_path: str, parser: str, suffix: str, payload: dict) -> None:
    arch.source_files.append(
        SourceFile(path=source_path, parser=parser, kind=suffix, warnings=payload.get("warnings", []))
    )
    for record in payload.get("records", []):
        fields = record.get("fields", [])
        table = TableRecord(name=f"{suffix}_record", fields=fields, source_files=[source_path], raw=record.get("raw", ""))
        arch.tables.append(table)
        mnemonic = fields[0] if fields else ""
        if suffix in {"opc", "tbl"}:
            arch.opcodes.append(
                OpcodeRecord(
                    mnemonic=mnemonic,
                    opcode=fields[1] if len(fields) > 1 else "",
                    mask=fields[2] if len(fields) > 2 else "",
                    operands=fields[3:],
                    flags=[],
                    table=suffix,
                    source_files=[source_path],
                    raw=record.get("raw", ""),
                )
            )
        if suffix == "def":
            arch.decode_rules.append(
                DecodeRule(
                    name=mnemonic,
                    pattern=fields[1] if len(fields) > 1 else "",
                    action=fields[2] if len(fields) > 2 else "",
                    conditions=fields[3:] if len(fields) > 3 else [],
                    source_files=[source_path],
                    raw=record.get("raw", ""),
                )
            )
            if mnemonic:
                arch.registers.append(
                    Register(
                        name=mnemonic,
                        number=None,
                        reg_class="def",
                        aliases=[],
                        source_files=[source_path],
                        raw=record.get("raw", ""),
                    )
                )
        if mnemonic:
            arch.instructions.append(
                Instruction(
                    name=mnemonic,
                    mnemonic=mnemonic,
                    aliases=[],
                    operands=[Operand(name=value, raw=value) for value in fields[1:]],
                    encoding=fields[1] if len(fields) > 1 else "",
                    flags=[],
                    source_files=[source_path],
                    raw=record.get("raw", ""),
                )
            )
