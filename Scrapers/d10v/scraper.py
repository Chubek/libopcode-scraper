from __future__ import annotations

from Scrapers.common.generic_scraper import ArchConfig, GenericArchitectureScraper
from Scrapers.registry import pretty_name_for


class ArchitectureScraper(GenericArchitectureScraper):
    def __init__(self):
        super().__init__(ArchConfig(arch="d10v", pretty_name=pretty_name_for("d10v"), tokens={"d10v"}))
