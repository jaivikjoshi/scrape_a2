#!/usr/bin/env python3
"""
Requests Scraper

This module implements a scraper using Requests with rotating proxies for basic pages.
"""

import logging
import random
import time
import json
import re
from typing import Dict, Any, Optional, List, Union
import os
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem

from scrapers.base_scraper import BaseScraper, ScraperException
from scrapers.proxy_manager import ProxyManager, Proxy
from .cloudscraper_engine import CloudScraperEngine  # Import CloudScraperEngine for fallback

# Configure logging
logger = logging.getLogger(__name__)


class RequestsScraper(BaseScraper):
    """Scraper implementation using Requests with rotating proxies for basic pages."""

    def __init__(self, config: Dict[str, Any] = None, proxy_manager: ProxyManager = None):
        """Initialize the Requests scraper.

        Args:
            config: Configuration dictionary for the scraper.
            proxy_manager: Optional proxy manager for IP rotation.
        """
        super().__init__(config)
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30)
        self.verify_ssl = self.config.get('verify_ssl', True)
        self.allow_redirects = self.config.get('allow_redirects', True)
        self.use_proxies = self.config.get('use_proxies', True)
        
        # Initialize proxy manager if provided
        self.proxy_manager = proxy_manager
        
        # Initialize session
        self._initialize_session()
        
        # Enhanced user agent rotation
        self._setup_user_agent_rotator()
        
        # Initialize cloudflare bypass settings
        self._setup_cloudflare_bypass()
        
        # CloudScraperEngine for fallback
        self.cloud_scraper = None
        
        logger.info("Initialized Requests scraper")

    def _initialize_session(self) -> None:
        """Initialize the requests session."""
        try:
            # Create a session
            self.session = requests.Session()
            
            # Set default headers
            self.session.headers.update(self.headers)
            
            # Set cookies if any
            if self.cookies:
                for name, value in self.cookies.items():
                    self.session.cookies.set(name, value)
            
            # Set common cookies that help with scraping
            self.session.cookies.set('visited', '1')
            self.session.cookies.set('locale', 'en')
            self.session.cookies.set('timezone', 'America/New_York')
            
            # Add common browser cookies to appear more legitimate
            self.session.cookies.set('_ga', f"GA1.2.{random.randint(1000000, 9999999)}.{int(time.time())}")
            self.session.cookies.set('_gid', f"GA1.2.{random.randint(1000000, 9999999)}.{int(time.time())}")
            
        except Exception as e:
            logger.error(f"Error initializing Requests session: {e}")
            raise ScraperException(f"Failed to initialize Requests session: {e}")

    def _setup_user_agent_rotator(self) -> None:
        """Set up the user agent rotator for more realistic browser fingerprinting."""
        try:
            # Define the software names and operating systems you want to emulate
            software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value, 
                             SoftwareName.EDGE.value, SoftwareName.SAFARI.value]
            operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.MAC.value,
                                OperatingSystem.LINUX.value]
            
            # Initialize the user agent rotator
            self.user_agent_rotator = UserAgent(software_names=software_names,
                                               operating_systems=operating_systems,
                                               limit=100)
            
            # Extend our user agents list with more realistic ones
            additional_agents = self.user_agent_rotator.get_user_agents()
            self.user_agents.extend([ua['user_agent'] for ua in additional_agents])
            
            logger.debug(f"Added {len(additional_agents)} additional user agents")
            
        except Exception as e:
            logger.warning(f"Error setting up user agent rotator: {e}")
            # Not critical, we can continue with the default user agents

    def _setup_cloudflare_bypass(self) -> None:
        """Set up Cloudflare bypass techniques."""
        # Common Cloudflare clearance cookies (these will be populated during requests)
        self.cf_clearance = None
        self.cf_bm = None
        
        # TLS fingerprinting settings
        self.tls_ciphers = [
            'TLS_AES_128_GCM_SHA256',
            'TLS_AES_256_GCM_SHA384',
            'TLS_CHACHA20_POLY1305_SHA256',
            'ECDHE-ECDSA-AES128-GCM-SHA256',
            'ECDHE-RSA-AES128-GCM-SHA256',
            'ECDHE-ECDSA-AES256-GCM-SHA384',
            'ECDHE-RSA-AES256-GCM-SHA384',
            'ECDHE-ECDSA-CHACHA20-POLY1305',
            'ECDHE-RSA-CHACHA20-POLY1305',
            'ECDHE-RSA-AES128-SHA',
            'ECDHE-RSA-AES256-SHA',
            'AES128-GCM-SHA256',
            'AES256-GCM-SHA384',
            'AES128-SHA',
            'AES256-SHA'
        ]
        
        # HTTP/2 settings
        self.http2 = True
        
        # Browser-like headers that help bypass Cloudflare
        self.cloudflare_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'DNT': '1',
            'Cache-Control': 'max-age=0',
        }

    def _generate_browser_fingerprint(self) -> Dict[str, str]:
        """Generate a realistic browser fingerprint.
        
        Returns:
            Dictionary of browser fingerprint headers.
        """
        # Choose a browser profile (Chrome, Firefox, etc.)
        browsers = ['chrome', 'firefox', 'safari', 'edge']
        browser = random.choice(browsers)
        
        # Base headers
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add browser-specific headers
        if browser == 'chrome':
            chrome_version = f"{random.randint(90, 120)}.0.{random.randint(1000, 9999)}.{random.randint(10, 200)}"
            headers.update({
                'sec-ch-ua': f'"Google Chrome";v="{chrome_version.split(".")[0]}", "Chromium";v="{chrome_version.split(".")[0]}", "Not-A.Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': f'"{random.choice(["Windows", "macOS", "Linux"])}"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            })
        elif browser == 'firefox':
            firefox_version = f"{random.randint(90, 120)}.0"
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'TE': 'trailers',
            })
        elif browser == 'safari':
            safari_version = f"{random.randint(14, 17)}.{random.randint(0, 3)}"
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            })
        elif browser == 'edge':
            edge_version = f"{random.randint(90, 120)}.0.{random.randint(1000, 9999)}.{random.randint(10, 200)}"
            headers.update({
                'sec-ch-ua': f'"Microsoft Edge";v="{edge_version.split(".")[0]}", "Chromium";v="{edge_version.split(".")[0]}", "Not-A.Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            })
        
        return headers

    def _extract_cloudflare_params(self, html: str) -> Dict[str, str]:
        """Extract Cloudflare challenge parameters from HTML.
        
        Args:
            html: HTML content containing Cloudflare challenge.
            
        Returns:
            Dictionary of Cloudflare parameters.
        """
        params = {}
        
        # Extract r parameter
        r_match = re.search(r'name="r" value="([^"]+)"', html)
        if r_match:
            params['r'] = r_match.group(1)
        
        # Extract jschl_vc parameter
        jschl_match = re.search(r'name="jschl_vc" value="([^"]+)"', html)
        if jschl_match:
            params['jschl_vc'] = jschl_match.group(1)
        
        # Extract pass parameter
        pass_match = re.search(r'name="pass" value="([^"]+)"', html)
        if pass_match:
            params['pass'] = pass_match.group(1)
            
        # Extract s parameter (sometimes used in newer CF versions)
        s_match = re.search(r'name="s" value="([^"]+)"', html)
        if s_match:
            params['s'] = s_match.group(1)
            
        return params

    def _handle_cloudflare_challenge(self, response: requests.Response, url: str) -> Optional[str]:
        """Handle Cloudflare challenge if detected.
        
        Args:
            response: Response object that might contain a Cloudflare challenge.
            url: Original URL being accessed.
            
        Returns:
            HTML content if challenge is solved, None otherwise.
        """
        # Check if this is a Cloudflare challenge
        if response.status_code == 403 and 'cloudflare' in response.text.lower():
            logger.info("Cloudflare challenge detected, attempting to solve")
            
            # Extract challenge parameters
            params = self._extract_cloudflare_params(response.text)
            if not params:
                logger.warning("Could not extract Cloudflare parameters")
                return None
                
            # Wait for the challenge timeout (usually 4-5 seconds)
            time.sleep(5)
            
            # Prepare for the challenge submission
            parsed_url = urlparse(url)
            challenge_url = f"{parsed_url.scheme}://{parsed_url.netloc}/cdn-cgi/l/chk_jschl"
            
            # Add the domain to the parameters
            params['domain'] = parsed_url.netloc
            
            # Submit the challenge
            try:
                challenge_response = self.session.get(
                    challenge_url,
                    params=params,
                    headers=self.session.headers,
                    cookies=self.session.cookies,
                    allow_redirects=True,
                    timeout=self.timeout
                )
                
                if challenge_response.status_code == 200:
                    logger.info("Successfully solved Cloudflare challenge")
                    
                    # Update cookies with any new Cloudflare cookies
                    self.update_cookies(dict(challenge_response.cookies))
                    
                    # Store specific Cloudflare cookies
                    if 'cf_clearance' in challenge_response.cookies:
                        self.cf_clearance = challenge_response.cookies['cf_clearance']
                    if '__cf_bm' in challenge_response.cookies:
                        self.cf_bm = challenge_response.cookies['__cf_bm']
                        
                    return challenge_response.text
                else:
                    logger.warning(f"Failed to solve Cloudflare challenge: {challenge_response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error during Cloudflare challenge: {e}")
                
        return None

    def _init_cloud_scraper(self) -> None:
        """Initialize CloudScraperEngine for fallback."""
        if self.cloud_scraper is None:
            logger.info("Initializing CloudScraperEngine for fallback...")
            self.cloud_scraper = CloudScraperEngine()

    def get_page(self, url: str, **kwargs) -> str:
        """Get page content using Requests with proxy rotation.

        Args:
            url: URL to get.
            **kwargs: Additional arguments to pass to requests.

        Returns:
            HTML content of the page.

        Raises:
            Exception: If the page could not be retrieved after retries.
        """
        max_retries = kwargs.get('max_retries', 5)
        retry_delay = kwargs.get('retry_delay', 2)
        method = kwargs.get('method', 'GET')
        data = kwargs.get('data', None)
        params = kwargs.get('params', None)
        timeout = kwargs.get('timeout', 30)
        
        # Add cache buster to avoid caching
        cache_buster = f"_cb={random.randint(1000000, 9999999)}"
        request_url = f"{url}{'&' if '?' in url else '?'}{cache_buster}"
        
        # Try CloudScraperEngine first for known Cloudflare-protected sites
        if 'filmfreeway.com' in url:
            logger.info("Using CloudScraperEngine for Filmfreeway (known Cloudflare-protected site)")
            self._init_cloud_scraper()
            html = self.cloud_scraper.get_page(url)
            if html and len(html) > 1000:
                logger.info("Successfully fetched page using CloudScraperEngine")
                return html
            else:
                logger.warning("CloudScraperEngine failed, falling back to regular flow")
        
        # Regular request flow with retries
        for attempt in range(1, max_retries + 1):
            current_proxy = None
            try:
                # Get a proxy if available
                if self.proxy_manager:
                    current_proxy = self.proxy_manager.get_proxy()
                    proxies = current_proxy.as_dict() if current_proxy else None
                else:
                    proxies = self._get_random_proxy()
                
                # Rotate user agent for each retry
                if attempt > 1:
                    self.rotate_user_agent()
                    self.session.headers.update({"User-Agent": self.current_user_agent})
                
                # Add browser fingerprinting headers
                self._add_browser_fingerprinting()
                
                # Make the request
                if method.upper() == 'POST':
                    response = self.session.post(
                        request_url,
                        data=data,
                        params=params,
                        proxies=proxies,
                        timeout=timeout
                    )
                else:
                    response = self.session.get(
                        request_url,
                        params=params,
                        proxies=proxies,
                        timeout=timeout
                    )
                
                # Check for Cloudflare challenge
                if response.status_code == 403 or self.detect_cloudflare_challenge(response.text):
                    logger.warning(f"Cloudflare protection detected (status code: {response.status_code})")
                    
                    # Try to solve Cloudflare challenge
                    cf_content = self.solve_cloudflare_challenge(url)
                    if cf_content:
                        logger.info("Successfully solved Cloudflare challenge")
                        # Release proxy if it was successful
                        if current_proxy and self.proxy_manager:
                            self.proxy_manager.release_proxy(current_proxy, success=True)
                        return cf_content
                    
                    # If solving challenge failed, use CloudScraperEngine as fallback
                    logger.info("Falling back to CloudScraperEngine")
                    self._init_cloud_scraper()
                    html = self.cloud_scraper.get_page(url)
                    if html and len(html) > 1000:
                        logger.info("Successfully bypassed Cloudflare using CloudScraperEngine")
                        # Release proxy if it was successful
                        if current_proxy and self.proxy_manager:
                            self.proxy_manager.release_proxy(current_proxy, success=True)
                        return html
                    
                    # If CloudScraperEngine also failed, continue with retries
                    logger.warning("CloudScraperEngine fallback failed, continuing with retries")
                    raise Exception("CloudScraperEngine fallback failed")
                
                # If not a Cloudflare challenge or if challenge handling failed, proceed normally
                response.raise_for_status()
                
                # Release proxy if it was successful
                if current_proxy and self.proxy_manager:
                    self.proxy_manager.release_proxy(current_proxy, success=True)
                
                return response.text
                
            except Exception as e:
                # Release proxy with failure status
                if current_proxy and self.proxy_manager:
                    self.proxy_manager.release_proxy(current_proxy, success=False)
                
                logger.warning(f"Attempt {attempt}/{max_retries} failed: {e}")
                
                # Clear cookies and try again with a fresh session if we've had multiple failures
                if attempt % 3 == 0:
                    logger.info("Clearing cookies for fresh session")
                    self.session.cookies.clear()
                    self._initialize_session()
                
                # If this is the last attempt, try CloudScraperEngine as a last resort
                if attempt == max_retries:
                    logger.info("Last attempt failed, trying CloudScraperEngine as last resort")
                    self._init_cloud_scraper()
                    try:
                        html = self.cloud_scraper.get_page(url)
                        if html and len(html) > 1000:
                            logger.info("Successfully bypassed using CloudScraperEngine on last attempt")
                            return html
                    except Exception as cloud_error:
                        logger.error(f"CloudScraperEngine last resort failed: {cloud_error}")
                
                # If we haven't reached the max retries yet, wait and try again
                if attempt < max_retries:
                    # Calculate delay with exponential backoff and jitter
                    current_delay = retry_delay * (1.5 ** (attempt - 1)) * (0.5 + random.random())
                    logger.warning(f"Retrying in {current_delay:.2f} seconds...")
                    time.sleep(current_delay)
        
        # If we get here, all retries failed
        raise Exception(f"Failed after {max_retries} retries")

    def close(self) -> None:
        """Close the scraper and clean up resources."""
        try:
            if self.session:
                self.session.close()
            if self.cloud_scraper:
                self.cloud_scraper.close()
            logger.info("Closed Requests scraper")
        except Exception as e:
            logger.error(f"Error closing Requests scraper: {e}")

    def extract_data(self, html: str) -> BeautifulSoup:
        """Extract data from HTML using BeautifulSoup.

        Args:
            html: HTML content to parse.

        Returns:
            BeautifulSoup object.
        """
        return BeautifulSoup(html, 'html.parser')

    def simulate_human_behavior(self, url: str) -> None:
        """Simulate human-like behavior by making additional requests.

        Args:
            url: Base URL to simulate behavior around.
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # List of common resources to request
            common_resources = [
                "/favicon.ico",
                "/robots.txt",
                "/sitemap.xml",
                "/css/main.css",
                "/js/main.js",
                "/images/logo.png"
            ]
            
            # Randomly select 1-3 resources to request
            resources_to_request = random.sample(
                common_resources, 
                min(random.randint(1, 3), len(common_resources))
            )
            
            for resource in resources_to_request:
                try:
                    resource_url = f"{base_url}{resource}"
                    logger.debug(f"Simulating human behavior: requesting {resource_url}")
                    
                    # Make the request with a short timeout
                    self.session.get(
                        resource_url,
                        timeout=5,
                        allow_redirects=False,
                        verify=self.verify_ssl
                    )
                    
                    # Short delay between requests
                    time.sleep(random.uniform(0.5, 2.0))
                    
                except Exception as e:
                    # Ignore errors, this is just for simulation
                    logger.debug(f"Error during human behavior simulation: {e}")
            
        except Exception as e:
            logger.debug(f"Error simulating human behavior: {e}")
            # Don't raise, this is non-critical
            
    def preload_cookies(self, url: str) -> None:
        """Preload cookies from a site by making a simple request to the homepage.
        
        Args:
            url: URL to preload cookies from.
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            logger.info(f"Preloading cookies from {base_url}")
            
            # First visit the homepage with minimal headers to get initial cookies
            initial_headers = {
                "User-Agent": self.current_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
                "TE": "Trailers",
            }
            
            self.session.headers.update(initial_headers)
            
            # Make a request to the homepage
            response = self.session.get(
                base_url,
                timeout=self.timeout,
                allow_redirects=True,
                verify=self.verify_ssl
            )
            
            # Update cookies
            self.update_cookies(dict(response.cookies))
            
            # Check for Cloudflare
            if 'cloudflare' in response.text.lower():
                logger.info("Cloudflare detected on homepage, attempting to handle")
                self._handle_cloudflare_challenge(response, base_url)
            
            # Wait a bit before proceeding
            time.sleep(random.uniform(2.0, 4.0))
            
            logger.info(f"Preloaded cookies: {json.dumps(dict(self.session.cookies))}")
            
        except Exception as e:
            logger.warning(f"Error preloading cookies: {e}")
            # Not critical, we can continue
