"""
Scrapers package for industrial-scale web scraping with AI & proxy networks.

This package provides a modular architecture with multiple scraping engines:
- Playwright for JavaScript-heavy pages
- CloudScraper for bypassing Cloudflare protection
- Requests with rotating proxies for basic pages

It also includes IP rotation using:
- requests-ip-rotator for AWS-based IP rotation
- A proxy pool manager for external proxy services

And intelligent retry mechanisms with:
- Exponential backoff
- Automatic switching between scraping engines when one fails
- Session rotation

With enhanced browser fingerprinting evasion:
- Random user agents
- Realistic browser behavior simulation
- Cookie management
"""

from scrapers.base_scraper import BaseScraper, ScraperException
from scrapers.requests_scraper import RequestsScraper
from scrapers.cloudscraper_engine import CloudScraperEngine
from scrapers.playwright_scraper import PlaywrightScraper
from scrapers.proxy_manager import ProxyManager, Proxy
from scrapers.scraper_factory import ScraperFactory

__all__ = [
    'BaseScraper',
    'ScraperException',
    'RequestsScraper',
    'CloudScraperEngine',
    'PlaywrightScraper',
    'ProxyManager',
    'Proxy',
    'ScraperFactory',
]
