from __future__ import annotations

from Scrapers.common.generic_scraper import ArchConfig, GenericArchitectureScraper
from Scrapers.registry import pretty_name_for


class ArchitectureScraper(GenericArchitectureScraper):
    def __init__(self):
        super().__init__(ArchConfig(arch="iq2000", pretty_name=pretty_name_for("iq2000"), tokens={"iq2000"}))
