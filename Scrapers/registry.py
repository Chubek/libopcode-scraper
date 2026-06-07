from __future__ import annotations

from dataclasses import dataclass

from .common.generic_scraper import ArchConfig, GenericArchitectureScraper

ARCHITECTURES = [
    "aarch64","alpha","arc","arm","avr","bfin","bpf","cr16","cris","crx","csky","d10v","d30v","dlx",
    "epiphany","fr30","frv","ft32","h8300","hppa","i386","ia64","ip2k","iq2000","kvx","lm32","loongarch",
    "m32c","m32r","m68hc11","m68k","m10200","m10300","mcore","mep","metag","microblaze","mips","mmix",
    "moxie","msp430","mt","nds32","nfp","ns32k","or1k","pdp11","pj","ppc","pru","riscv","rl78","rx",
    "s12z","s390","score","sh","sparc","spu","tic4x","tic6x","tic30","tic54x","tilegx","tilepro","v850",
    "vax","visium","wasm","xgate","xstormy16","xtensa","z8k","z80",
]

PRETTY_NAMES = {
    "aarch64": "AArch64",
    "i386": "Arch",
    "ia64": "IA64",
    "ppc": "PPC",
    "arm": "ARM",
    "mips": "MIPS",
}

ALIASES = {
    "micromips": "mips",
    "score7": "score",
    "wasm32": "wasm",
}


@dataclass(frozen=True)
class ArchitectureMeta:
    name: str
    pretty_name: str
    tokens: set[str]
    scraper_module: str


def _tokens_for_arch(arch: str) -> set[str]:
    tokens = {arch}
    for alias, owner in ALIASES.items():
        if owner == arch:
            tokens.add(alias)
    if arch == "i386":
        tokens.add("x86")
    if arch == "tic4x":
        tokens.add("tic4")
    if arch == "tic6x":
        tokens.add("tic6")
    if arch == "tic30":
        tokens.add("tic3")
    if arch == "tic54x":
        tokens.add("tic54")
    return tokens


def available_architectures() -> list[str]:
    return ARCHITECTURES[:]


def pretty_name_for(arch: str) -> str:
    return PRETTY_NAMES.get(arch, arch.upper() if len(arch) <= 4 else arch.capitalize())


def architecture_meta(arch: str) -> ArchitectureMeta:
    return ArchitectureMeta(
        name=arch,
        pretty_name=pretty_name_for(arch),
        tokens=_tokens_for_arch(arch),
        scraper_module=f"Scrapers.{arch}.scraper",
    )


def get_scraper(arch: str) -> GenericArchitectureScraper:
    if arch not in ARCHITECTURES:
        raise KeyError(f"Unknown architecture: {arch}")
    meta = architecture_meta(arch)
    config = ArchConfig(arch=meta.name, pretty_name=meta.pretty_name, tokens=meta.tokens)
    return GenericArchitectureScraper(config)
