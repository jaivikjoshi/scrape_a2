#!/usr/bin/env python3
"""
Proxy Manager

This module implements a proxy rotation system for web scraping.
"""

import logging
import random
import time
from typing import Dict, Any, Optional, List, Union, Set
import os
import json
import threading
from datetime import datetime, timedelta
import re
import requests

from requests_ip_rotator import ApiGateway

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("proxy.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProxyException(Exception):
    """Exception for proxy-related errors."""
    pass


class Proxy:
    """Class representing a proxy with its metadata."""

    def __init__(self, host: str, port: int, username: str = None, password: str = None, 
                 protocol: str = 'http', country: str = None, last_used: float = 0,
                 success_count: int = 0, fail_count: int = 0, banned_until: float = 0):
        """Initialize a proxy.

        Args:
            host: Proxy host.
            port: Proxy port.
            username: Optional proxy username.
            password: Optional proxy password.
            protocol: Proxy protocol (http, https, socks4, socks5).
            country: Optional country of the proxy.
            last_used: Timestamp when the proxy was last used.
            success_count: Number of successful requests made with this proxy.
            fail_count: Number of failed requests made with this proxy.
            banned_until: Timestamp until which the proxy is banned.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.protocol = protocol
        self.country = country
        self.last_used = last_used
        self.success_count = success_count
        self.fail_count = fail_count
        self.banned_until = banned_until
        self.in_use = False
        self.last_response_time = 0

    @property
    def url(self) -> str:
        """Get the proxy URL.

        Returns:
            Proxy URL string.
        """
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def is_banned(self) -> bool:
        """Check if the proxy is currently banned.

        Returns:
            True if the proxy is banned, False otherwise.
        """
        return time.time() < self.banned_until

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of the proxy.

        Returns:
            Success rate as a float between 0 and 1.
        """
        total = self.success_count + self.fail_count
        if total == 0:
            return 0
        return self.success_count / total

    def to_dict(self) -> Dict[str, Any]:
        """Convert the proxy to a dictionary.

        Returns:
            Dictionary representation of the proxy.
        """
        return {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'protocol': self.protocol,
            'country': self.country,
            'last_used': self.last_used,
            'success_count': self.success_count,
            'fail_count': self.fail_count,
            'banned_until': self.banned_until,
            'success_rate': self.success_rate
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Proxy':
        """Create a proxy from a dictionary.

        Args:
            data: Dictionary with proxy data.

        Returns:
            Proxy instance.
        """
        return cls(
            host=data['host'],
            port=data['port'],
            username=data.get('username'),
            password=data.get('password'),
            protocol=data.get('protocol', 'http'),
            country=data.get('country'),
            last_used=data.get('last_used', 0),
            success_count=data.get('success_count', 0),
            fail_count=data.get('fail_count', 0),
            banned_until=data.get('banned_until', 0)
        )


class ProxyManager:
    """Manager for rotating proxies."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the proxy manager.

        Args:
            config: Configuration dictionary for the proxy manager.
        """
        self.config = config or {}
        self.proxies: List[Proxy] = []
        self.banned_proxies: Set[str] = set()
        self.proxy_file = self.config.get('proxy_file', 'proxies.json')
        self.min_proxy_count = self.config.get('min_proxy_count', 5)
        self.max_proxy_count = self.config.get('max_proxy_count', 100)
        self.ban_threshold = self.config.get('ban_threshold', 3)
        self.ban_time = self.config.get('ban_time', 3600)  # 1 hour
        self.cooldown_time = self.config.get('cooldown_time', 10)  # 10 seconds
        self.proxy_test_url = self.config.get('proxy_test_url', 'https://httpbin.org/ip')
        self.proxy_test_timeout = self.config.get('proxy_test_timeout', 10)
        self.aws_region = self.config.get('aws_region', 'us-east-1')
        self.target_domains = self.config.get('target_domains', ['filmfreeway.com'])
        
        # AWS IP Rotator
        self.use_aws_gateway = self.config.get('use_aws_gateway', False)
        self.aws_gateways = {}
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Load proxies from file
        self._load_proxies()
        
        # Initialize AWS gateways if enabled
        if self.use_aws_gateway:
            self._initialize_aws_gateways()
        
        logger.info(f"Initialized proxy manager with {len(self.proxies)} proxies")

    def _load_proxies(self) -> None:
        """Load proxies from file."""
        try:
            if os.path.exists(self.proxy_file):
                with open(self.proxy_file, 'r') as f:
                    proxy_data = json.load(f)
                    
                    if isinstance(proxy_data, list):
                        self.proxies = [Proxy.from_dict(p) for p in proxy_data]
                        logger.info(f"Loaded {len(self.proxies)} proxies from {self.proxy_file}")
                    else:
                        logger.warning(f"Invalid proxy data format in {self.proxy_file}")
        except Exception as e:
            logger.error(f"Error loading proxies from {self.proxy_file}: {e}")

    def _save_proxies(self) -> None:
        """Save proxies to file."""
        try:
            with open(self.proxy_file, 'w') as f:
                json.dump([p.to_dict() for p in self.proxies], f, indent=2)
            logger.debug(f"Saved {len(self.proxies)} proxies to {self.proxy_file}")
        except Exception as e:
            logger.error(f"Error saving proxies to {self.proxy_file}: {e}")

    def _initialize_aws_gateways(self) -> None:
        """Initialize AWS API Gateways for IP rotation."""
        if not self.use_aws_gateway:
            return
            
        try:
            for domain in self.target_domains:
                logger.info(f"Initializing AWS API Gateway for {domain}")
                self.aws_gateways[domain] = ApiGateway(
                    domain,
                    regions=[self.aws_region],
                    access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                    access_key_secret=os.environ.get('AWS_SECRET_ACCESS_KEY')
                )
                self.aws_gateways[domain].start()
                logger.info(f"AWS API Gateway for {domain} initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing AWS API Gateway: {e}")
            self.use_aws_gateway = False

    def add_proxy(self, proxy: Proxy) -> None:
        """Add a proxy to the manager.

        Args:
            proxy: Proxy to add.
        """
        with self.lock:
            # Check if the proxy already exists
            for existing_proxy in self.proxies:
                if existing_proxy.host == proxy.host and existing_proxy.port == proxy.port:
                    logger.debug(f"Proxy {proxy.host}:{proxy.port} already exists")
                    return
                    
            self.proxies.append(proxy)
            logger.info(f"Added proxy {proxy.host}:{proxy.port}")
            self._save_proxies()

    def remove_proxy(self, proxy: Proxy) -> None:
        """Remove a proxy from the manager.

        Args:
            proxy: Proxy to remove.
        """
        with self.lock:
            self.proxies = [p for p in self.proxies if p.host != proxy.host or p.port != proxy.port]
            logger.info(f"Removed proxy {proxy.host}:{proxy.port}")
            self._save_proxies()

    def ban_proxy(self, proxy: Proxy, duration: int = None) -> None:
        """Ban a proxy for a specified duration.

        Args:
            proxy: Proxy to ban.
            duration: Ban duration in seconds. If None, use the default ban_time.
        """
        with self.lock:
            ban_duration = duration or self.ban_time
            proxy.banned_until = time.time() + ban_duration
            proxy.fail_count += 1
            self.banned_proxies.add(f"{proxy.host}:{proxy.port}")
            logger.info(f"Banned proxy {proxy.host}:{proxy.port} for {ban_duration} seconds")
            self._save_proxies()

    def unban_proxy(self, proxy: Proxy) -> None:
        """Unban a proxy.

        Args:
            proxy: Proxy to unban.
        """
        with self.lock:
            proxy.banned_until = 0
            proxy_key = f"{proxy.host}:{proxy.port}"
            if proxy_key in self.banned_proxies:
                self.banned_proxies.remove(proxy_key)
            logger.info(f"Unbanned proxy {proxy.host}:{proxy.port}")
            self._save_proxies()

    def get_proxy(self, country: str = None) -> Optional[Proxy]:
        """Get a proxy from the pool.

        Args:
            country: Optional country filter.

        Returns:
            A proxy, or None if no suitable proxy is available.
        """
        with self.lock:
            # Filter available proxies
            available_proxies = [
                p for p in self.proxies 
                if not p.is_banned 
                and not p.in_use 
                and (country is None or p.country == country)
            ]
            
            if not available_proxies:
                logger.warning("No available proxies")
                return None
                
            # Sort by last used time (oldest first) and success rate (highest first)
            available_proxies.sort(key=lambda p: (p.last_used, -p.success_rate))
            
            # Get the best proxy
            proxy = available_proxies[0]
            proxy.in_use = True
            proxy.last_used = time.time()
            logger.debug(f"Selected proxy {proxy.host}:{proxy.port}")
            return proxy

    def release_proxy(self, proxy: Proxy, success: bool = True) -> None:
        """Release a proxy back to the pool.

        Args:
            proxy: Proxy to release.
            success: Whether the request was successful.
        """
        with self.lock:
            proxy.in_use = False
            
            if success:
                proxy.success_count += 1
            else:
                proxy.fail_count += 1
                
                # Ban the proxy if it fails too many times
                if proxy.fail_count >= self.ban_threshold:
                    self.ban_proxy(proxy)
            
            self._save_proxies()

    def get_aws_gateway_session(self, domain: str) -> Optional[requests.Session]:
        """Get a session with AWS API Gateway for IP rotation.

        Args:
            domain: Target domain.

        Returns:
            Session with AWS API Gateway, or None if not available.
        """
        if not self.use_aws_gateway:
            return None
            
        try:
            if domain in self.aws_gateways:
                session = requests.Session()
                self.aws_gateways[domain].attach_session(session)
                return session
                
            # Try to find a matching gateway
            for gateway_domain, gateway in self.aws_gateways.items():
                if domain.endswith(gateway_domain):
                    session = requests.Session()
                    gateway.attach_session(session)
                    return session
                    
            logger.warning(f"No AWS API Gateway available for {domain}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting AWS API Gateway session: {e}")
            return None

    def test_proxy(self, proxy: Proxy) -> bool:
        """Test if a proxy is working.

        Args:
            proxy: Proxy to test.

        Returns:
            True if the proxy is working, False otherwise.
        """
        try:
            start_time = time.time()
            response = requests.get(
                self.proxy_test_url,
                proxies={
                    'http': proxy.url,
                    'https': proxy.url
                },
                timeout=self.proxy_test_timeout
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                proxy.last_response_time = elapsed
                logger.debug(f"Proxy {proxy.host}:{proxy.port} is working (response time: {elapsed:.2f}s)")
                return True
            else:
                logger.warning(f"Proxy {proxy.host}:{proxy.port} returned status code {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Proxy {proxy.host}:{proxy.port} test failed: {e}")
            return False

    def test_all_proxies(self) -> None:
        """Test all proxies in the pool."""
        logger.info("Testing all proxies...")
        
        with self.lock:
            working_proxies = []
            
            for proxy in self.proxies:
                if self.test_proxy(proxy):
                    working_proxies.append(proxy)
                else:
                    self.ban_proxy(proxy)
            
            logger.info(f"Proxy test completed: {len(working_proxies)}/{len(self.proxies)} proxies working")

    def add_proxies_from_url(self, url: str) -> int:
        """Add proxies from a URL.

        Args:
            url: URL to fetch proxies from.

        Returns:
            Number of proxies added.
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse the response
            content = response.text
            
            # Common proxy formats: IP:PORT or IP:PORT:USERNAME:PASSWORD
            proxy_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)(?::([^:]+):([^:]+))?'
            matches = re.findall(proxy_pattern, content)
            
            added_count = 0
            
            for match in matches:
                host, port = match[0], int(match[1])
                username, password = match[2], match[3] if len(match) > 3 else None
                
                proxy = Proxy(
                    host=host,
                    port=port,
                    username=username,
                    password=password
                )
                
                self.add_proxy(proxy)
                added_count += 1
                
            logger.info(f"Added {added_count} proxies from {url}")
            return added_count
            
        except Exception as e:
            logger.error(f"Error adding proxies from {url}: {e}")
            return 0

    def add_proxies_from_file(self, file_path: str) -> int:
        """Add proxies from a file.

        Args:
            file_path: Path to the file.

        Returns:
            Number of proxies added.
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File {file_path} does not exist")
                return 0
                
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Common proxy formats: IP:PORT or IP:PORT:USERNAME:PASSWORD
            proxy_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)(?::([^:]+):([^:]+))?'
            matches = re.findall(proxy_pattern, content)
            
            added_count = 0
            
            for match in matches:
                host, port = match[0], int(match[1])
                username, password = match[2], match[3] if len(match) > 3 else None
                
                proxy = Proxy(
                    host=host,
                    port=port,
                    username=username,
                    password=password
                )
                
                self.add_proxy(proxy)
                added_count += 1
                
            logger.info(f"Added {added_count} proxies from {file_path}")
            return added_count
            
        except Exception as e:
            logger.error(f"Error adding proxies from {file_path}: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the proxy pool.

        Returns:
            Dictionary with proxy pool statistics.
        """
        with self.lock:
            total = len(self.proxies)
            banned = len([p for p in self.proxies if p.is_banned])
            in_use = len([p for p in self.proxies if p.in_use])
            available = total - banned - in_use
            
            success_rates = [p.success_rate for p in self.proxies if p.success_count + p.fail_count > 0]
            avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
            
            response_times = [p.last_response_time for p in self.proxies if p.last_response_time > 0]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                'total': total,
                'banned': banned,
                'in_use': in_use,
                'available': available,
                'avg_success_rate': avg_success_rate,
                'avg_response_time': avg_response_time,
                'aws_gateway_enabled': self.use_aws_gateway,
                'aws_gateways': list(self.aws_gateways.keys()) if self.aws_gateways else []
            }

    def close(self) -> None:
        """Close the proxy manager and clean up resources."""
        try:
            # Save proxies
            self._save_proxies()
            
            # Close AWS gateways
            if self.use_aws_gateway:
                for domain, gateway in self.aws_gateways.items():
                    try:
                        gateway.shutdown()
                        logger.info(f"Closed AWS API Gateway for {domain}")
                    except Exception as e:
                        logger.error(f"Error closing AWS API Gateway for {domain}: {e}")
            
            logger.info("Closed proxy manager")
        except Exception as e:
            logger.error(f"Error closing proxy manager: {e}")

    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors during cleanup
