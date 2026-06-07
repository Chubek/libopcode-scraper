from __future__ import annotations

from Scrapers.common.generic_scraper import ArchConfig, GenericArchitectureScraper
from Scrapers.registry import pretty_name_for


class ArchitectureScraper(GenericArchitectureScraper):
    def __init__(self):
        super().__init__(ArchConfig(arch="tic6x", pretty_name=pretty_name_for("tic6x"), tokens={"tic6x"}))
