#!/usr/bin/env python3
"""
Scraper Factory

This module implements a factory for creating and managing different scraper engines.
"""

import logging
import random
import time
from typing import Dict, Any, Optional, List, Union, Type
import os
import json
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper, ScraperException
from scrapers.requests_scraper import RequestsScraper
from scrapers.cloudscraper_engine import CloudScraperEngine
from scrapers.playwright_scraper import PlaywrightScraper
from scrapers.proxy_manager import ProxyManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScraperFactory:
    """Factory for creating and managing different scraper engines."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the scraper factory.

        Args:
            config: Configuration dictionary for the factory.
        """
        self.config = config or {}
        self.proxy_manager = None
        self.scrapers = {}
        self.default_engine = self.config.get('default_engine', 'requests')
        self.fallback_order = self.config.get('fallback_order', ['requests', 'cloudscraper', 'playwright'])
        self.max_retries = self.config.get('max_retries', 5)
        self.retry_delay = self.config.get('retry_delay', 2)
        self.success_threshold = self.config.get('success_threshold', 0.7)  # 70% success rate
        
        # Initialize proxy manager if enabled
        if self.config.get('use_proxies', True):
            self._initialize_proxy_manager()
        
        # Initialize scrapers
        self._initialize_scrapers()
        
        logger.info(f"Initialized scraper factory with default engine: {self.default_engine}")

    def _initialize_proxy_manager(self) -> None:
        """Initialize the proxy manager."""
        try:
            proxy_config = self.config.get('proxy_config', {})
            self.proxy_manager = ProxyManager(proxy_config)
            logger.info("Initialized proxy manager")
        except Exception as e:
            logger.error(f"Error initializing proxy manager: {e}")
            self.proxy_manager = None

    def _initialize_scrapers(self) -> None:
        """Initialize all scraper engines."""
        try:
            # Initialize Requests scraper
            if 'requests' in self.fallback_order:
                requests_config = self.config.get('requests_config', {})
                self.scrapers['requests'] = RequestsScraper(requests_config, self.proxy_manager)
                logger.info("Initialized Requests scraper")
            
            # Initialize CloudScraper engine
            if 'cloudscraper' in self.fallback_order:
                cloudscraper_config = self.config.get('cloudscraper_config', {})
                self.scrapers['cloudscraper'] = CloudScraperEngine(cloudscraper_config)
                logger.info("Initialized CloudScraper engine")
            
            # Initialize Playwright scraper
            if 'playwright' in self.fallback_order:
                playwright_config = self.config.get('playwright_config', {})
                self.scrapers['playwright'] = PlaywrightScraper(playwright_config)
                logger.info("Initialized Playwright scraper")
            
        except Exception as e:
            logger.error(f"Error initializing scrapers: {e}")
            raise

    def get_scraper(self, engine: str = None) -> BaseScraper:
        """Get a scraper engine.

        Args:
            engine: Name of the scraper engine to get. If None, use the default engine.

        Returns:
            Scraper engine.

        Raises:
            ScraperException: If the requested engine is not available.
        """
        engine = engine or self.default_engine
        
        if engine not in self.scrapers:
            raise ScraperException(f"Scraper engine '{engine}' not available")
        
        return self.scrapers[engine]

    def get_best_scraper(self) -> BaseScraper:
        """Get the best performing scraper based on success rate.

        Returns:
            Best performing scraper engine.
        """
        best_scraper = None
        best_success_rate = -1
        
        for name, scraper in self.scrapers.items():
            success_rate = scraper.success_rate
            
            if success_rate > best_success_rate:
                best_success_rate = success_rate
                best_scraper = scraper
        
        # If no scraper has a good success rate, use the default
        if best_success_rate < self.success_threshold:
            return self.get_scraper()
        
        return best_scraper

    def get_page(self, url: str, **kwargs) -> str:
        """Get page content using the best scraper with fallback.

        Args:
            url: URL to fetch.
            **kwargs: Additional keyword arguments.

        Returns:
            Page content as HTML string.

        Raises:
            ScraperException: If all scrapers fail.
        """
        # Get the preferred engine from kwargs or use the best scraper
        preferred_engine = kwargs.pop('engine', None)
        
        if preferred_engine:
            scrapers_to_try = [preferred_engine] + [e for e in self.fallback_order if e != preferred_engine]
        else:
            # Start with the best scraper and then try others in fallback order
            best_scraper = self.get_best_scraper()
            for name, scraper in self.scrapers.items():
                if scraper == best_scraper:
                    scrapers_to_try = [name] + [e for e in self.fallback_order if e != name]
                    break
            else:
                scrapers_to_try = self.fallback_order
        
        # Try each scraper in order
        last_exception = None
        
        for engine_name in scrapers_to_try:
            if engine_name not in self.scrapers:
                continue
                
            scraper = self.scrapers[engine_name]
            
            try:
                logger.info(f"Trying to fetch {url} with {engine_name} engine")
                content = scraper.get_page(url, **kwargs)
                
                # Check if the content is valid
                if content and len(content) > 100:  # Arbitrary minimum length
                    logger.info(f"Successfully fetched {url} with {engine_name} engine")
                    return content
                else:
                    logger.warning(f"Empty or very short content from {engine_name} engine")
                    
            except Exception as e:
                logger.warning(f"Error fetching {url} with {engine_name} engine: {e}")
                last_exception = e
                
                # Wait before trying the next engine
                time.sleep(random.uniform(1, 3))
        
        # If we get here, all scrapers failed
        error_msg = f"All scrapers failed to fetch {url}"
        if last_exception:
            error_msg += f": {last_exception}"
            
        logger.error(error_msg)
        raise ScraperException(error_msg)

    def extract_data(self, html: str) -> BeautifulSoup:
        """Extract data from HTML using BeautifulSoup.

        Args:
            html: HTML content to parse.

        Returns:
            BeautifulSoup object.
        """
        return BeautifulSoup(html, 'html.parser')

    def close(self) -> None:
        """Close all scrapers and clean up resources."""
        try:
            for name, scraper in self.scrapers.items():
                try:
                    scraper.close()
                    logger.info(f"Closed {name} scraper")
                except Exception as e:
                    logger.error(f"Error closing {name} scraper: {e}")
            
            if self.proxy_manager:
                self.proxy_manager.close()
                
            logger.info("Closed scraper factory")
        except Exception as e:
            logger.error(f"Error closing scraper factory: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about all scrapers.

        Returns:
            Dictionary with scraper statistics.
        """
        stats = {}
        
        for name, scraper in self.scrapers.items():
            stats[name] = scraper.get_stats()
        
        if self.proxy_manager:
            stats['proxy_manager'] = self.proxy_manager.get_stats()
        
        return stats

    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors during cleanup
