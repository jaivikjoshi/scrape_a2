#!/usr/bin/env python3
"""
CloudScraper Engine

This module implements a scraper using CloudScraper for bypassing Cloudflare protection.
"""

import logging
import random
import time
from typing import Dict, Any, Optional, List, Union
import os
import json

import cloudscraper
from bs4 import BeautifulSoup
import requests

from scrapers.base_scraper import BaseScraper, ScraperException

# Configure logging
logger = logging.getLogger(__name__)


class CloudScraperEngine(BaseScraper):
    """Scraper implementation using CloudScraper for bypassing Cloudflare protection."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the CloudScraper engine.

        Args:
            config: Configuration dictionary for the scraper.
        """
        super().__init__(config)
        self.config = config or {}
        self.browser = self.config.get('browser', 'chrome')  # chrome, firefox
        self.cipherSuite = self.config.get('cipherSuite', [])
        self.delay = self.config.get('delay', 1000)  # Delay in milliseconds
        self.interpreter = self.config.get('interpreter', 'js2py')  # js2py, nodejs
        self.allow_brotli = self.config.get('allow_brotli', True)
        
        # Initialize CloudScraper
        self._initialize_scraper()
        
        logger.info(f"Initialized CloudScraper engine with {self.browser} browser")

    def _initialize_scraper(self) -> None:
        """Initialize the CloudScraper session."""
        try:
            # Create a CloudScraper instance
            self.scraper = cloudscraper.create_scraper(
                browser={
                    'browser': self.browser,
                    'platform': 'darwin',  # macOS
                    'mobile': False,
                },
                delay=self.delay,
                interpreter=self.interpreter,
                allow_brotli=self.allow_brotli,
                debug=self.config.get('debug', False),
            )
            
            # Set default headers
            self.scraper.headers.update(self.headers)
            
            # Set cookies if any
            if self.cookies:
                for name, value in self.cookies.items():
                    self.scraper.cookies.set(name, value)
            
            # Add common cookies that help bypass Cloudflare
            self.scraper.cookies.set('cf_clearance', '', domain='filmfreeway.com')
            self.scraper.cookies.set('__cf_bm', '', domain='filmfreeway.com')
            
        except Exception as e:
            logger.error(f"Error initializing CloudScraper: {e}")
            raise ScraperException(f"Failed to initialize CloudScraper: {e}")

    def get_page(self, url: str, **kwargs) -> str:
        """Get page content using CloudScraper.

        Args:
            url: URL to fetch.
            **kwargs: Additional keyword arguments.

        Returns:
            Page content as HTML string.
        """
        def _fetch_page(url):
            method = kwargs.get('method', 'GET')
            params = kwargs.get('params', None)
            data = kwargs.get('data', None)
            json_data = kwargs.get('json', None)
            timeout = kwargs.get('timeout', 30)
            proxies = kwargs.get('proxies', None)
            
            # Rotate user agent for each request
            self.rotate_user_agent()
            self.scraper.headers.update({"User-Agent": self.current_user_agent})
            
            # Set the referer to make the request appear more legitimate
            if 'referer' in kwargs:
                self.scraper.headers.update({"Referer": kwargs['referer']})
            elif url.startswith('https://filmfreeway.com/'):
                self.scraper.headers.update({"Referer": "https://filmfreeway.com/"})
            else:
                self.scraper.headers.update({"Referer": "https://www.google.com/"})
            
            # Add a random query parameter to bypass caching
            cache_buster = f"_cb={random.randint(1000000, 9999999)}"
            if '?' in url:
                request_url = f"{url}&{cache_buster}"
            else:
                request_url = f"{url}?{cache_buster}"
            
            # Make the request
            if method.upper() == 'POST':
                response = self.scraper.post(
                    request_url,
                    params=params,
                    data=data,
                    json=json_data,
                    timeout=timeout,
                    proxies=proxies
                )
            else:
                response = self.scraper.get(
                    request_url,
                    params=params,
                    timeout=timeout,
                    proxies=proxies
                )
            
            response.raise_for_status()
            
            # Extract and update cookies
            self.update_cookies(dict(response.cookies))
            
            # Check if we need to reinitialize the scraper due to Cloudflare issues
            if 'CF-RAY' in response.headers and response.status_code == 503:
                logger.warning("Detected Cloudflare challenge, reinitializing scraper...")
                self._initialize_scraper()
                raise ScraperException("Cloudflare challenge detected, retrying...")
            
            return response.text
        
        try:
            # Use retry with backoff for the request
            content = self.retry_with_backoff(_fetch_page, url)
            
            # Random delay to appear more human-like
            self.random_delay(2.0, 5.0)
            
            return content
            
        except Exception as e:
            logger.error(f"Error in get_page: {e}")
            
            # If we've exhausted retries with CloudScraper, try to reinitialize
            self._initialize_scraper()
            
            # Re-raise the exception for the caller to handle
            raise

    def close(self) -> None:
        """Close the scraper and clean up resources."""
        try:
            if self.scraper:
                self.scraper.close()
            logger.info("Closed CloudScraper engine")
        except Exception as e:
            logger.error(f"Error closing CloudScraper engine: {e}")

    def extract_data(self, html: str) -> BeautifulSoup:
        """Extract data from HTML using BeautifulSoup.

        Args:
            html: HTML content to parse.

        Returns:
            BeautifulSoup object.
        """
        return BeautifulSoup(html, 'html.parser')

    def get_cookies(self) -> Dict[str, str]:
        """Get cookies from the current session.

        Returns:
            Dictionary of cookies.
        """
        try:
            if self.scraper:
                # Extract cookies from the cloudscraper session
                cookies = {name: value for name, value in self.scraper.cookies.items()}
                logger.info(f"Retrieved {len(cookies)} cookies from CloudScraperEngine")
                return cookies
            else:
                logger.warning("No active scraper session to get cookies from")
                return {}
        except Exception as e:
            logger.error(f"Error getting cookies from CloudScraperEngine: {e}")
            return {}

    def detect_cloudflare_captcha(self, html: str) -> bool:
        """Detect if the page contains a Cloudflare CAPTCHA.

        Args:
            html: HTML content to check.

        Returns:
            True if a CAPTCHA is detected, False otherwise.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for common Cloudflare CAPTCHA elements
        if soup.select('form[action="/?__cf_chl_captcha_tk="]'):
            return True
        
        if soup.select('form[id="challenge-form"]'):
            return True
        
        if "Cloudflare" in html and "security check" in html.lower():
            return True
        
        if "Just a moment" in html and "cloudflare" in html.lower():
            return True
        
        return False

    def handle_cloudflare_captcha(self, url: str) -> None:
        """Handle Cloudflare CAPTCHA by reinitializing the scraper.

        Args:
            url: URL that triggered the CAPTCHA.
        """
        logger.warning(f"Cloudflare CAPTCHA detected for {url}, reinitializing scraper...")
        
        # Wait a bit longer before retrying
        time.sleep(random.uniform(10, 20))
        
        # Reinitialize the scraper with a new session
        self._initialize_scraper()
        
        # Rotate user agent
        self.rotate_user_agent()
        
        logger.info("Scraper reinitialized after CAPTCHA challenge")
