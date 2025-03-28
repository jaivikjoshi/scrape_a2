#!/usr/bin/env python3
"""
Playwright Scraper

This module implements a scraper using Playwright for JavaScript-heavy pages.
"""

import logging
import asyncio
import random
import time
from typing import Dict, Any, Optional, List, Union
import os
import json
from pathlib import Path
import re

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Response
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from scrapers.base_scraper import BaseScraper, ScraperException

# Configure logging
logger = logging.getLogger(__name__)

class PlaywrightScraper(BaseScraper):
    """Scraper implementation using Playwright for JavaScript-heavy pages."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the Playwright scraper.

        Args:
            config: Configuration dictionary for the scraper.
        """
        super().__init__(config)
        self.config = config or {}
        self.browser_type = self.config.get('browser_type', 'chromium')  # chromium, firefox, webkit
        self.headless = self.config.get('headless', True)
        self.slow_mo = self.config.get('slow_mo', 50)  # Slow down operations by this amount of ms
        self.viewport = self.config.get('viewport', {'width': 1920, 'height': 1080})
        self.timeout = self.config.get('timeout', 30000)  # 30 seconds
        self.user_data_dir = self.config.get('user_data_dir', None)
        
        # Playwright objects (to be initialized)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize Playwright asynchronously
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self._initialize())
        
        self.logger.info(f"Initialized Playwright scraper with {self.browser_type} browser")

    async def _initialize(self) -> None:
        """Initialize Playwright browser and context."""
        try:
            self.playwright = await async_playwright().start()
            
            # Select browser based on config
            if self.browser_type == 'firefox':
                browser_instance = self.playwright.firefox
            elif self.browser_type == 'webkit':
                browser_instance = self.playwright.webkit
            else:  # default to chromium
                browser_instance = self.playwright.chromium
            
            # Launch browser
            self.browser = await browser_instance.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
            )
            
            # Create a persistent context if user_data_dir is provided
            if self.user_data_dir:
                user_data_path = Path(self.user_data_dir)
                user_data_path.mkdir(parents=True, exist_ok=True)
                
                self.context = await browser_instance.launch_persistent_context(
                    user_data_dir=str(user_data_path),
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                    viewport=self.viewport,
                    user_agent=UserAgent().random,
                    locale='en-US',
                    timezone_id='America/New_York',
                )
                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            else:
                # Create a new context
                self.context = await self.browser.new_context(
                    viewport={'width': random.randint(1050, 1920), 'height': random.randint(800, 1080)},
                    user_agent=UserAgent().random,
                    locale='en-US',
                    timezone_id='America/New_York',
                    geolocation={'longitude': random.uniform(-122.0, -73.0), 'latitude': random.uniform(30.0, 45.0)},
                    permissions=['geolocation'],
                    java_script_enabled=True,
                    bypass_csp=True,
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Cache-Control': 'max-age=0',
                        'Connection': 'keep-alive',
                        'Sec-Ch-Ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1',
                    },
                )
                self.page = await self.context.new_page()
            
            # Set default timeout
            self.page.set_default_timeout(self.timeout)
            
            # Set up event listeners
            self.page.on("response", self._handle_response)
            
            # Add initial cookies if any
            if self.cookies:
                await self.context.add_cookies([
                    {"name": name, "value": value, "domain": "filmfreeway.com", "path": "/"}
                    for name, value in self.cookies.items()
                ])
            
            # Apply stealth techniques
            await self._apply_stealth_techniques()
            
        except Exception as e:
            self.logger.error(f"Error initializing Playwright: {e}")
            raise ScraperException(f"Failed to initialize Playwright: {e}")

    async def _apply_stealth_techniques(self):
        """Apply various stealth techniques to avoid detection."""
        # Override navigator properties to appear more like a real browser
        await self.page.add_init_script("""
        () => {
            // Override properties
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            
            // Prevent detection via plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            name: "Chrome PDF Viewer"
                        },
                        {
                            0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
                            1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable"},
                            description: "Native Client",
                            filename: "internal-nacl-plugin",
                            name: "Native Client"
                        }
                    ];
                }
            });
            
            // Prevent detection via languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override canvas fingerprinting
            const getImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function (x, y, w, h) {
                const imageData = getImageData.call(this, x, y, w, h);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    // Add some random noise to the canvas data
                    data[i] = data[i] + Math.floor(Math.random() * 10) - 5;
                    data[i + 1] = data[i + 1] + Math.floor(Math.random() * 10) - 5;
                    data[i + 2] = data[i + 2] + Math.floor(Math.random() * 10) - 5;
                }
                return imageData;
            };
        }
        """)

    async def _handle_response(self, response: Response) -> None:
        """Handle response events from the browser.

        Args:
            response: Playwright response object.
        """
        # Log response status for debugging
        if response.status >= 400:
            self.logger.warning(f"Error response: {response.status} for {response.url}")
        
        # Extract and store cookies from responses
        if response.status < 400:
            try:
                cookies = await self.context.cookies()
                cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
                self.update_cookies(cookie_dict)
            except Exception as e:
                self.logger.debug(f"Error extracting cookies: {e}")

    async def _get_page_async(self, url: str, **kwargs) -> str:
        """Get page content asynchronously."""
        try:
            # Set default timeout
            timeout = kwargs.get('timeout', 15000)
            
            # First try with a shorter timeout to detect Cloudflare quickly
            await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # Check for Cloudflare challenge
            cf_challenge = await self.page.query_selector('#challenge-running, #cf-challenge-running, .cf-browser-verification, .cf-error-code')
            if cf_challenge:
                logger.warning("Cloudflare challenge detected, waiting longer...")
                
                # Wait for challenge to complete (up to 30 seconds)
                try:
                    await self.page.wait_for_selector('#challenge-running, #cf-challenge-running, .cf-browser-verification, .cf-error-code', state='detached', timeout=30000)
                    logger.info("Cloudflare challenge appears to be solved")
                except Exception as e:
                    logger.warning(f"Timeout waiting for Cloudflare challenge to be solved: {e}")
            
            # Add human-like behavior
            await self._simulate_human_behavior()
            
            # Wait for content to load
            try:
                # Wait for festival-specific selectors
                await self.page.wait_for_selector("div[class*='festival'], div[class*='Festival'], .CuratedSectionTile, a[href^='/festivals/curated/']", timeout=10000)
                logger.info("Found festival-specific content")
            except Exception as e:
                logger.warning(f"Timeout waiting for festival selectors: {e}")
                # Try more general content selectors
                try:
                    await self.page.wait_for_selector(".Content, .container, main, #layout", state='visible', timeout=5000)
                    logger.info("Found general content")
                except Exception as e2:
                    logger.warning(f"Timeout waiting for general content selectors: {e2}")
            
            # Get the page content
            content = await self.page.content()
            
            # Check if content is too small (likely blocked)
            if len(content) < 1000:
                logger.warning(f"Content size is suspiciously small: {len(content)} bytes")
                
                # Get the page title to check if we're blocked
                title = await self.page.title()
                logger.info(f"Page title: {title}")
                
                # If we're getting a Cloudflare page, wait longer
                if "Cloudflare" in content or "cloudflare" in content.lower() or "challenge" in content.lower() or "checking your browser" in content.lower():
                    logger.warning("Cloudflare page detected, waiting longer...")
                    await asyncio.sleep(10)  # Wait 10 seconds
                    content = await self.page.content()
            
            return content
            
        except Exception as e:
            logger.error(f"Error in _get_page_async: {e}")
            raise e

    async def _simulate_human_behavior(self) -> None:
        """Simulate human-like behavior to avoid detection."""
        # Random scrolling
        for _ in range(random.randint(1, 3)):
            await self.page.mouse.wheel(0, random.randint(300, 700))
            await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Random mouse movements
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Sometimes click on a random element
        if random.random() < 0.3:  # 30% chance
            try:
                elements = await self.page.query_selector_all('a, button, input, select')
                if elements and len(elements) > 0:
                    random_element = elements[random.randint(0, min(5, len(elements)-1))]
                    await random_element.hover()
                    # Don't actually click to avoid navigating away
            except Exception as e:
                logger.debug(f"Error during human simulation: {e}")
        
        # Add a random pause
        await asyncio.sleep(random.uniform(1.0, 3.0))

    def get_page(self, url: str, **kwargs) -> str:
        """Get page content using Playwright."""
        try:
            self.logger.info(f"Getting page with Playwright: {url}")
            
            # Run the async method in the event loop
            content = self.loop.run_until_complete(self._get_page_async(url, **kwargs))
            
            # Save content for inspection
            with open("playwright_content.html", "w", encoding="utf-8") as f:
                f.write(content)
                
            return content
        except Exception as e:
            self.logger.error(f"Error fetching page with Playwright: {e}")
            raise e
            
    def extract_festival_links(self, html_content: str) -> List[Dict[str, str]]:
        """Extract festival links from the page content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        festivals = []
        
        # Try different selectors for curated sections
        curated_links = soup.select("a[href^='/festivals/curated/']")
        
        for link in curated_links:
            title = link.get('title', '').replace('View ', '')
            href = link.get('href', '')
            if href and title:
                festivals.append({
                    'name': title,
                    'url': f"https://filmfreeway.com{href}",
                    'type': 'curated'
                })
        
        return festivals

    def extract_festival_details(self, html_content: str) -> Dict[str, Any]:
        """Extract festival details from the festival page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        details = {}
        
        # Try to find the festival name
        name_selectors = [
            "h1.festival-name", 
            "h1.FestivalName", 
            "div.Title", 
            "div[class*='FestivalName']",
            "div[class*='festival-name']",
            "h1", # More generic fallback
            "title" # Last resort
        ]
        
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem:
                name_text = name_elem.get_text(strip=True)
                if name_text and len(name_text) > 3:  # Ensure we have a meaningful name
                    details['festival_name'] = name_text
                    break
        
        # Try to find the festival description/info
        description_selectors = [
            "div.festival-description", 
            "div.Description", 
            "div[class*='Description']",
            "div[class*='festival-description']",
            "div.about",
            "div[class*='about']",
            "p.description",
            "p[class*='description']",
            "meta[name='description']"
        ]
        
        for selector in description_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                if selector == "meta[name='description']":
                    desc_text = desc_elem.get('content', '')
                else:
                    desc_text = desc_elem.get_text(strip=True)
                
                if desc_text and len(desc_text) > 10:  # Ensure we have a meaningful description
                    details['festival_info'] = desc_text
                    break
        
        # Try to find deadlines
        deadline_selectors = [
            "div.deadlines", 
            "div.Deadlines", 
            "div[class*='Deadline']",
            "div[class*='deadline']",
            "span[class*='deadline']",
            "span[class*='Deadline']",
            "div.dates",
            "div[class*='date']"
        ]
        
        deadlines = []
        for selector in deadline_selectors:
            deadline_elems = soup.select(selector)
            for elem in deadline_elems:
                deadline_text = elem.get_text(strip=True)
                if deadline_text and "deadline" in deadline_text.lower():
                    deadlines.append(deadline_text)
        
        # If no specific deadline elements found, try to extract dates that might be deadlines
        if not deadlines:
            date_patterns = [
                r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
                r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
                r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                r"\b\d{4}-\d{2}-\d{2}\b"
            ]
            
            for pattern in date_patterns:
                date_matches = re.findall(pattern, html_content, re.IGNORECASE)
                for date in date_matches:
                    if date not in deadlines:
                        deadlines.append(date)
        
        if deadlines:
            details['deadlines'] = deadlines
        
        # Try to find categories
        category_selectors = [
            "div.categories", 
            "div.Categories", 
            "div[class*='Category']",
            "div[class*='category']",
            "span[class*='category']",
            "span[class*='Category']",
            "div.tags",
            "div[class*='tag']"
        ]
        
        categories = []
        for selector in category_selectors:
            category_elems = soup.select(selector)
            for elem in category_elems:
                category_text = elem.get_text(strip=True)
                if category_text and len(category_text) > 2:
                    categories.append(category_text)
        
        # If no specific category elements found, try to find common festival categories
        if not categories:
            common_categories = [
                "Short", "Feature", "Documentary", "Animation", "Experimental", 
                "Music Video", "Student", "Comedy", "Drama", "Horror", 
                "Sci-Fi", "Fantasy", "LGBTQ", "Women", "Fiction", "Screenplay"
            ]
            
            for category in common_categories:
                if re.search(r'\b' + re.escape(category) + r'\b', html_content, re.IGNORECASE):
                    categories.append(category)
        
        if categories:
            details['categories'] = categories
        
        # Try to find awards
        award_selectors = [
            "div.awards", 
            "div.Awards", 
            "div[class*='Award']",
            "div[class*='award']",
            "span[class*='award']",
            "span[class*='Award']",
            "div.prizes",
            "div[class*='prize']"
        ]
        
        awards = []
        for selector in award_selectors:
            award_elems = soup.select(selector)
            for elem in award_elems:
                award_text = elem.get_text(strip=True)
                if award_text and len(award_text) > 5 and "award" in award_text.lower():
                    awards.append(award_text)
        
        # If no specific award elements found, try to extract text that might be awards
        if not awards:
            award_patterns = [
                r"Best\s+\w+(?:\s+\w+){0,5}",
                r"Grand\s+Prize\s+for\s+\w+(?:\s+\w+){0,5}",
                r"Award\s+for\s+\w+(?:\s+\w+){0,5}"
            ]
            
            for pattern in award_patterns:
                award_matches = re.findall(pattern, html_content, re.IGNORECASE)
                for award in award_matches:
                    if award not in awards:
                        awards.append(award)
        
        if awards:
            details['awards'] = awards
        
        # Try to find important dates
        date_selectors = [
            "div.dates", 
            "div.Dates", 
            "div[class*='Date']",
            "div[class*='date']",
            "span[class*='date']",
            "span[class*='Date']"
        ]
        
        important_dates = []
        for selector in date_selectors:
            date_elems = soup.select(selector)
            for elem in date_elems:
                date_text = elem.get_text(strip=True)
                if date_text and not any(d in date_text for d in deadlines):
                    important_dates.append(date_text)
        
        # If no specific date elements found, try to extract dates that aren't deadlines
        if not important_dates:
            year_pattern = r"\b(19|20)\d{2}\b"
            year_matches = re.findall(year_pattern, html_content)
            for year in year_matches:
                if year not in important_dates and year not in str(deadlines):
                    important_dates.append(year)
        
        if important_dates:
            details['important_dates'] = important_dates
        
        return details

    def close(self) -> None:
        """Close the scraper and clean up resources."""
        try:
            self.loop.run_until_complete(self._close_async())
            self.logger.info("Closed Playwright scraper")
        except Exception as e:
            self.logger.error(f"Error closing Playwright scraper: {e}")

    async def _close_async(self) -> None:
        """Close Playwright resources asynchronously."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            self.logger.error(f"Error closing Playwright resources: {e}")

    async def _get_cookies_async(self) -> Dict[str, str]:
        """Get cookies from the browser context asynchronously.

        Returns:
            Dictionary of cookies.
        """
        try:
            if self.context:
                # Get all cookies from the browser context
                cookies = await self.context.cookies()
                
                # Convert to a simple dictionary format
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                
                self.logger.info(f"Retrieved {len(cookie_dict)} cookies from Playwright browser")
                return cookie_dict
            else:
                self.logger.warning("No active browser context to get cookies from")
                return {}
        except Exception as e:
            self.logger.error(f"Error getting cookies from Playwright browser: {e}")
            return {}

    def get_cookies(self) -> Dict[str, str]:
        """Get cookies from the browser context.

        Returns:
            Dictionary of cookies.
        """
        try:
            # Run the async method in the event loop
            return self.loop.run_until_complete(self._get_cookies_async())
        except Exception as e:
            self.logger.error(f"Error getting cookies from PlaywrightScraper: {e}")
            return {}

    def extract_data(self, html: str) -> BeautifulSoup:
        """Extract data from HTML using BeautifulSoup.

        Args:
            html: HTML content to parse.

        Returns:
            BeautifulSoup object.
        """
        return BeautifulSoup(html, 'html.parser')

    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        try:
            if hasattr(self, 'loop') and self.loop.is_running():
                self.loop.create_task(self._close_async())
            else:
                self.close()
        except Exception:
            pass  # Ignore errors during cleanup
