#!/usr/bin/env python3
"""
Base Scraper Class

This module defines the base scraper class that serves as the foundation for all
specialized scrapers in the system.
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
import json
import os

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


class ScraperException(Exception):
    """Base exception for all scraper-related errors."""
    pass


class BaseScraper(ABC):
    """Base class for all scrapers in the system."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the base scraper.

        Args:
            config: Configuration dictionary for the scraper.
        """
        self.config = config or {}
        self.max_retries = self.config.get('max_retries', 5)
        self.retry_delay = self.config.get('retry_delay', 2)
        self.user_agents = self._load_user_agents()
        self.current_user_agent = self._get_random_user_agent()
        self.cookies = {}
        self.headers = self._get_default_headers()
        self.session = None  # To be initialized by subclasses
        self.success_rate = 0.0
        self.request_count = 0
        self.success_count = 0
        
        # Initialize stats tracking
        self.stats = {
            'requests': 0,
            'success': 0,
            'failures': 0,
            'retries': 0,
            'total_time': 0,
            'avg_response_time': 0,
        }

    def _load_user_agents(self) -> List[str]:
        """Load a list of user agents from file or use defaults.

        Returns:
            List of user agent strings.
        """
        try:
            # Try to load from file
            if os.path.exists('user_agents.json'):
                with open('user_agents.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading user agents from file: {e}")
        
        # Default user agents (modern browsers)
        return [
            # Chrome
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            # Mobile
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Android 11; Mobile; rv:68.0) Gecko/68.0 Firefox/88.0",
        ]

    def _get_random_user_agent(self) -> str:
        """Get a random user agent from the list.

        Returns:
            Random user agent string.
        """
        return random.choice(self.user_agents)

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for HTTP requests.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "User-Agent": self.current_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "DNT": "1",  # Do Not Track
        }

    def rotate_user_agent(self) -> None:
        """Rotate the user agent and update headers."""
        self.current_user_agent = self._get_random_user_agent()
        self.headers["User-Agent"] = self.current_user_agent
        if self.session:
            self.session.headers.update({"User-Agent": self.current_user_agent})
        logger.debug(f"Rotated user agent to: {self.current_user_agent}")

    def update_cookies(self, cookies: Dict[str, str]) -> None:
        """Update the cookies for the scraper.

        Args:
            cookies: Dictionary of cookies to update.
        """
        self.cookies.update(cookies)
        if self.session:
            for key, value in cookies.items():
                self.session.cookies.set(key, value)
        logger.debug(f"Updated cookies: {cookies}")

    def random_delay(self, min_delay: float = 1.0, max_delay: float = 5.0) -> None:
        """Wait for a random amount of time to avoid detection.

        Args:
            min_delay: Minimum delay in seconds.
            max_delay: Maximum delay in seconds.
        """
        # Use a non-uniform distribution to make delays appear more human-like
        # More weight towards shorter delays, but occasional longer ones
        delay = min_delay + (max_delay - min_delay) * (random.random() ** 2)
        time.sleep(delay)

    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Retry a function with exponential backoff.

        Args:
            func: Function to retry.
            *args: Arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Result of the function.

        Raises:
            ScraperException: If all retries fail.
        """
        retries = 0
        while retries < self.max_retries:
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # Update stats
                self.stats['requests'] += 1
                self.stats['success'] += 1
                self.stats['total_time'] += elapsed
                self.stats['avg_response_time'] = self.stats['total_time'] / self.stats['success']
                
                # Update success rate
                self.request_count += 1
                self.success_count += 1
                self.success_rate = self.success_count / self.request_count
                
                return result
            except Exception as e:
                self.stats['failures'] += 1
                self.stats['retries'] += 1
                self.request_count += 1
                self.success_rate = self.success_count / self.request_count
                
                wait_time = self.retry_delay * (2 ** retries) + random.uniform(0, 1)
                logger.warning(f"Attempt {retries + 1}/{self.max_retries} failed: {e}. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                retries += 1
                
                # Rotate user agent on retry
                self.rotate_user_agent()
                
                # If we've retried multiple times, try clearing cookies
                if retries > self.max_retries // 2:
                    logger.info("Clearing cookies for fresh session")
                    self.cookies = {}
                    if self.session:
                        self.session.cookies.clear()
        
        raise ScraperException(f"Failed after {self.max_retries} retries")

    @abstractmethod
    def get_page(self, url: str, **kwargs) -> str:
        """Get page content.

        Args:
            url: URL to fetch.
            **kwargs: Additional keyword arguments.

        Returns:
            Page content as HTML string.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the scraper and clean up resources."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics.

        Returns:
            Dictionary of scraper statistics.
        """
        return {
            **self.stats,
            'success_rate': self.success_rate,
        }
