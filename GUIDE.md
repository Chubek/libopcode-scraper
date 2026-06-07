# Scrapers Framework Guide

## 1. Overview

`Scrapers` is a Python package for extracting architecture-specific opcode/disassembly metadata from two local source trees:

- `LibOpcode-Headers/`
- `LibOpcode-Files/`

It is designed to:

- discover files by architecture;
- parse C-family files primarily with Tree-Sitter C;
- parse table-like non-C formats (`.tbl`, `.opc`, `.def`) with Lark grammars;
- normalize extracted entities into common schema-like records;
- emit structured output in `json`, `yaml`, `xml`, and `sexpr`.

The package is runnable as a module:

```bash
python3 -m Scrapers --arch i386 --format json --scrape +all
```

---

## 2. Directory Layout

### 2.1 Top-level package

- `Scrapers/__init__.py`
- `Scrapers/__main__.py`
- `Scrapers/cli.py`
- `Scrapers/registry.py`

### 2.2 Shared infrastructure

- `Scrapers/common/__init__.py`
- `Scrapers/common/paths.py`
- `Scrapers/common/discovery.py`
- `Scrapers/common/treesitter_c.py`
- `Scrapers/common/lark_parsers.py`
- `Scrapers/common/models.py`
- `Scrapers/common/normalize.py`
- `Scrapers/common/emit.py`
- `Scrapers/common/generic_scraper.py`
- `Scrapers/common/scrape_types.py`
- `Scrapers/common/utils.py`

### 2.3 Architecture packages

One package per architecture, each containing:

- `Scrapers/<arch>/__init__.py`
- `Scrapers/<arch>/scraper.py`

Examples:

- `Scrapers/i386/scraper.py`
- `Scrapers/aarch64/scraper.py`
- `Scrapers/riscv/scraper.py`
- `Scrapers/rx/scraper.py`

---

## 3. Execution Pipeline

The end-to-end flow is:

1. CLI parses arguments and validates selections.
2. Registry resolves architecture metadata (pretty name, ownership tokens).
3. Generic scraper discovers architecture-owned files.
4. Files are routed by extension:
   - C-family (`.c`, `.h`) -> Tree-Sitter parser.
   - Special (`.tbl`, `.opc`, `.def`) -> Lark parser.
5. Parser outputs are normalized into common in-memory model fields.
6. Category payloads (`all`, `dis`, `opc`, `inst`) are assembled.
7. Emitters serialize to selected format and write output files.

Failure policy:

- parse failures are non-fatal by design;
- warnings are recorded in output payloads;
- scraping continues for remaining files.

---

## 4. CLI Reference

## 4.1 Required flags

- `--arch <name>`
- `--format <json|yaml|xml|sexpr>`

## 4.2 Optional flags

- `--output-dir <path>`
- `--scrape <selectors...>` (default: `+all`)

### 4.3 Examples

Scrape all categories for i386 to default output directory:

```bash
python3 -m Scrapers --arch i386 --format json --scrape +all
```

Scrape disassembly and opcode subsets:

```bash
python3 -m Scrapers --arch aarch64 --format yaml --scrape +dis +opc
```

Explicit output directory:

```bash
python3 -m Scrapers --arch rx --output-dir artifacts/rx --format sexpr --scrape +inst
```

### 4.4 Scrape selectors

Supported selectors:

- `+all`
- `+dis`
- `+opc`
- `+inst`

Semantics:

- `all`: full normalized payload.
- `dis`: disassembly-focused records.
- `opc`: opcode/table-focused records.
- `inst`: instruction/register/type-focused records.

---

## 5. Output Naming and Locations

Default output directory:

- `$PWD/output/<arch>`

Output filename pattern:

- `<PrettyName>.<category>.<ext>`

Examples:

- `output/i386/Arch.all.json`
- `output/aarch64/AArch64.dis.yaml`
- `output/rx/RX.inst.sexp`

Extension mapping:

- `json -> .json`
- `yaml -> .yaml`
- `xml -> .xml`
- `sexpr -> .sexp`

---

## 6. Architecture Registry

Registry module:

- `Scrapers/registry.py`

It provides:

- supported architecture list;
- pretty-name mapping;
- alias ownership rules;
- scraper constructor.

Notable pretty names:

- `aarch64 -> AArch64`
- `i386 -> Arch`
- `ia64 -> IA64`
- `ppc -> PPC`
- `arm -> ARM`
- `mips -> MIPS`

Alias ownership rules:

- `micromips-*` belongs to `mips`
- `score7-*` belongs to `score`
- `wasm32-*` belongs to `wasm`

---

## 7. Discovery Rules

Discovery module:

- `Scrapers/common/discovery.py`

It scans:

- `LibOpcode-Headers/`
- `LibOpcode-Files/`

It classifies each file as:

- header;
- source;
- special (`.tbl`, `.opc`, `.def`).

It ignores global/non-architecture infrastructure, including:

- `ChangeLog*`
- `Makefile*`
- `configure*`
- `aclocal.m4`
- `MAINTAINERS`
- `po/` trees
- shared helpers such as:
  - `disassemble.c`
  - `disassemble.h`
  - `dis-init.c`
  - `dis-buf.c`
  - `opc2c.c`
  - `opintl.h`
  - `cgen-*`

Architecture ownership detection uses token-boundary pattern matching on filename/stem to reduce accidental substring collisions.

---

## 8. C-Family Parsing (Tree-Sitter First)

Parser module:

- `Scrapers/common/treesitter_c.py`

Primary strategy:

- use Tree-Sitter C from installed Python environment.

Parser backends attempted:

1. `tree_sitter_languages.get_parser("c")`
2. `tree_sitter` + `tree_sitter_c`
3. regex fallback only if Tree-Sitter is unavailable

Extracted top-level signals include:

- preprocessor macros (`#define`);
- enums;
- typedef definitions;
- struct specifiers;
- function declarations/definitions;
- initializer-backed table candidates.

When exact normalization is difficult, raw text snippets are retained in record `raw` fields.

---

## 9. Special Format Parsing (Lark)

Parser module:

- `Scrapers/common/lark_parsers.py`

Dedicated grammars:

- `TBL_GRAMMAR` for `.tbl`
- `OPC_GRAMMAR` for `.opc`
- `DEF_GRAMMAR` for `.def`

Outputs capture:

- directives;
- row records;
- mnemonic/name field where identifiable;
- raw row text.

If grammar parsing fails:

- line-based fallback extraction still emits records;
- warning is included;
- run continues.

---

## 10. Normalized Model

Model module:

- `Scrapers/common/models.py`

Core entities include:

- `Architecture`
- `SourceFile`
- `Macro`
- `EnumType`
- `FunctionRecord`
- `TableRecord`
- `DecodeRule`
- `Instruction`
- `Operand`
- `OpcodeRecord`
- `Register`

Normalization module:

- `Scrapers/common/normalize.py`

Responsibilities:

- map parser-specific payloads into common entity lists;
- attach provenance (`source_files`, parser kind);
- preserve raw fragments where semantic certainty is low.

---

## 11. Category Payloads

Built by:

- `Scrapers/common/generic_scraper.py`

Category content:

- `all`: full architecture data blob.
- `dis`: functions + decode rules + source/warnings.
- `opc`: opcodes + table records + source/warnings.
- `inst`: instructions + registers + enums + typedefs + structs + source/warnings.

---

## 12. Emitters

Emitter module:

- `Scrapers/common/emit.py`

Format behavior:

- `json`: sorted keys, pretty indented.
- `yaml`: safe dump (falls back to JSON text if `yaml` unavailable).
- `xml`: root `<architecture>` with `name` and `category` attributes.
- `sexpr`: canonical nested list-like S-expression rendering.

All formats are generated from the same in-memory payload to keep output consistency.

---

## 13. Extending the Framework

## 13.1 Add a new architecture

1. Add architecture token to `ARCHITECTURES` in `Scrapers/registry.py`.
2. Optionally add pretty name in `PRETTY_NAMES`.
3. Optionally add alias ownership rule in `ALIASES`.
4. Add wrapper package:
   - `Scrapers/<arch>/__init__.py`
   - `Scrapers/<arch>/scraper.py`

## 13.2 Add new category

1. Add token to `VALID_CATEGORIES` in `Scrapers/common/scrape_types.py`.
2. Extend CLI selector parser in `Scrapers/cli.py`.
3. Add payload assembly logic in `GenericArchitectureScraper._category_payload`.
4. Verify emitter compatibility (usually automatic if payload is dict/list primitives).

## 13.3 Improve parsing depth

C-family:

- expand Tree-Sitter node handling in `treesitter_c.py` for richer declarator semantics.

Special formats:

- add architecture/file-specific post-processors after generic Lark parse.

---

## 14. Troubleshooting

## 14.1 Tree-Sitter not available

Symptoms:

- warnings indicate regex fallback.

Action:

- install compatible Tree-Sitter Python packages in the active environment:
  - `tree_sitter`
  - either `tree_sitter_languages` or `tree_sitter_c`

## 14.2 YAML output appears as JSON text

Cause:

- `yaml` module missing.

Action:

- install PyYAML (`yaml`) in active environment.

## 14.3 Empty output for an architecture

Checklist:

- confirm `--arch` name matches registry entries;
- inspect discovery ownership tokens in `Scrapers/registry.py`;
- verify source files actually contain architecture token patterns;
- check ignored-file filters in `Scrapers/common/discovery.py`.

## 14.4 Partial data only

Normal in early/heterogeneous parsing scenarios. Inspect:

- output `warnings`;
- `source_files` parser attribution;
- retained `raw` fragments for difficult declarations/records.

---

## 15. Development and Validation

Compile sanity check:

```bash
python3 -m py_compile Scrapers/__main__.py Scrapers/cli.py Scrapers/registry.py Scrapers/common/*.py Scrapers/*/scraper.py
```

Representative smoke tests:

```bash
python3 -m Scrapers --arch i386 --format json --scrape +all
python3 -m Scrapers --arch aarch64 --format yaml --scrape +dis +opc
python3 -m Scrapers --arch msp430 --format xml --scrape +opc
python3 -m Scrapers --arch riscv --format json --scrape +dis
python3 -m Scrapers --arch rx --format sexpr --scrape +inst
```

---

## 16. Design Constraints and Tradeoffs

- Priority: deterministic, robust, modular baseline.
- Parsing strategy: Tree-Sitter first for C/H; non-fatal fallback for resilience.
- Grammar strategy: dedicated but permissive Lark grammars to tolerate format variance.
- Normalization strategy: preserve provenance and raw fragments to avoid lossy interpretation.
- Emission strategy: one consistent payload model across all output formats.

This balance favors practical extraction continuity over strict completeness of every architecture-specific dialect.

