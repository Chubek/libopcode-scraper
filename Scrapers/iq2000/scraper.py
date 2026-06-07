from __future__ import annotations

from Scrapers.common.generic_scraper import ArchConfig, GenericArchitectureScraper
from Scrapers.registry import architecture_meta


class ArchitectureScraper(GenericArchitectureScraper):
    def __init__(self):
        meta = architecture_meta("iq2000")
        super().__init__(ArchConfig(arch=meta.name, pretty_name=meta.pretty_name, tokens=meta.tokens))
