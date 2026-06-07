from __future__ import annotations

import argparse
from pathlib import Path

from .common.emit import write_output
from .common.paths import default_output_dir
from .common.scrape_types import OUTPUT_FORMATS, VALID_CATEGORIES
from .registry import available_architectures, get_scraper, pretty_name_for


def _parse_scrape_args(values: list[str]) -> list[str]:
    selected: list[str] = []
    for token in values:
        token = token.strip()
        if not token.startswith("+"):
            raise ValueError(f"Invalid scrape token: {token}")
        name = token[1:]
        if name not in VALID_CATEGORIES:
            raise ValueError(f"Unsupported scrape category: {name}")
        if name == "all":
            return ["all"]
        selected.append(name)
    if not selected:
        return ["all"]
    return sorted(set(selected))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="Scrapers", description="Architecture metadata scraper")
    parser.add_argument("--arch", required=True, choices=available_architectures())
    parser.add_argument("--output-dir")
    parser.add_argument("--format", required=True, choices=sorted(OUTPUT_FORMATS))
    parser.add_argument("--scrape", nargs="+", default=["+all"])
    return parser


def _output_file_name(arch: str, category: str, fmt: str) -> str:
    pretty = pretty_name_for(arch)
    suffix = "sexp" if fmt == "sexpr" else fmt
    return f"{pretty}.{category}.{suffix}"


def run(arch: str, output_dir: Path | None, fmt: str, scrape_tokens: list[str]) -> list[Path]:
    scraper = get_scraper(arch)
    categories = _parse_scrape_args(scrape_tokens)
    target_dir = output_dir if output_dir is not None else default_output_dir(arch)

    outputs: list[Path] = []
    for category in categories:
        if category == "all":
            payload = scraper.scrape_all()
            out_payload = {
                "name": payload.get("name"),
                "pretty_name": payload.get("pretty_name"),
                "category": "all",
                "data": payload,
                "warnings": payload.get("warnings", []),
            }
        elif category == "dis":
            out_payload = scraper.scrape_dis()
        elif category == "opc":
            out_payload = scraper.scrape_opc()
        elif category == "inst":
            out_payload = scraper.scrape_inst()
        else:
            raise ValueError(category)

        out_path = target_dir / _output_file_name(arch, category, fmt)
        write_output(out_path, out_payload, fmt)
        outputs.append(out_path)
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    run(args.arch, output_dir, args.format, args.scrape)
    return 0

