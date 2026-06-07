from __future__ import annotations

from Scrapers.common.generic_scraper import ArchConfig, GenericArchitectureScraper
from Scrapers.registry import pretty_name_for


class ArchitectureScraper(GenericArchitectureScraper):
    def __init__(self):
        super().__init__(ArchConfig(arch="s12z", pretty_name=pretty_name_for("s12z"), tokens={"s12z"}))
