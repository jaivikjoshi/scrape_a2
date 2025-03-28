import sys
import os

# Add parent directory to path so we can import from scrapers
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#!/usr/bin/env python3
"""
Test script for hybrid Cloudflare bypass using CloudScraperEngine to get cookies
and then passing them to RequestsScraper.
"""

import logging
import json
import time
from scrapers import RequestsScraper, CloudScraperEngine, PlaywrightScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("hybrid_cloudflare_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_cloudflare_cookies():
    """Get Cloudflare cookies using CloudScraperEngine."""
    logger.info("Getting Cloudflare cookies using CloudScraperEngine...")
    
    try:
        # Initialize CloudScraperEngine
        cloud_scraper = CloudScraperEngine()
        
        # Get the homepage to acquire Cloudflare cookies
        url = "https://filmfreeway.com"
        logger.info(f"Fetching {url} with CloudScraperEngine to get cookies")
        
        # Get the page content
        html = cloud_scraper.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with CloudScraperEngine")
            
            # Get the cookies
            cookies = cloud_scraper.get_cookies()
            logger.info(f"Got {len(cookies)} cookies from CloudScraperEngine")
            
            return cookies
        else:
            logger.error("Failed to get valid content from CloudScraperEngine")
            return {}
            
    except Exception as e:
        logger.error(f"Error getting Cloudflare cookies: {e}")
        return {}
    finally:
        if 'cloud_scraper' in locals():
            cloud_scraper.close()

def get_playwright_cookies():
    """Get Cloudflare cookies using PlaywrightScraper."""
    logger.info("Getting Cloudflare cookies using PlaywrightScraper...")
    
    try:
        # Initialize PlaywrightScraper
        playwright_scraper = PlaywrightScraper()
        
        # Get the homepage to acquire Cloudflare cookies
        url = "https://filmfreeway.com"
        logger.info(f"Fetching {url} with PlaywrightScraper to get cookies")
        
        # Get the page content
        html = playwright_scraper.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with PlaywrightScraper")
            
            # Get the cookies
            cookies = playwright_scraper.get_cookies()
            logger.info(f"Got {len(cookies)} cookies from PlaywrightScraper")
            
            return cookies
        else:
            logger.error("Failed to get valid content from PlaywrightScraper")
            return {}
            
    except Exception as e:
        logger.error(f"Error getting Playwright cookies: {e}")
        return {}
    finally:
        if 'playwright_scraper' in locals():
            playwright_scraper.close()

def test_hybrid_cloudflare_bypass():
    """Test the hybrid approach to bypass Cloudflare protection."""
    logger.info("Testing hybrid Cloudflare bypass approach...")
    
    try:
        # First, get Cloudflare cookies using CloudScraperEngine
        cf_cookies = get_cloudflare_cookies()
        
        if not cf_cookies:
            logger.info("Trying with PlaywrightScraper instead...")
            cf_cookies = get_playwright_cookies()
            
        if not cf_cookies:
            logger.error("Failed to get Cloudflare cookies from both engines")
            return False
        
        # Initialize RequestsScraper
        requests_scraper = RequestsScraper()
        
        # Set the cookies from CloudScraperEngine
        for name, value in cf_cookies.items():
            requests_scraper.session.cookies.set(name, value)
            
        logger.info(f"Set {len(cf_cookies)} cookies in RequestsScraper")
        
        # Try to access the festivals page
        url = "https://filmfreeway.com/festivals"
        logger.info(f"Attempting to access {url} with hybrid approach")
        
        # Get the page content
        html = requests_scraper.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with hybrid approach")
            logger.info(f"Response length: {len(html)} characters")
            
            # Extract some data to verify content
            soup = requests_scraper.extract_data(html)
            title = soup.title.text if soup.title else "No title found"
            logger.info(f"Page title: {title}")
            
            # Check for festival cards
            festival_cards = soup.select('.festival-card')
            logger.info(f"Found {len(festival_cards)} festival cards on the page")
            
            # Check for Cloudflare indicators
            if 'cloudflare' in html.lower():
                logger.warning("Cloudflare protection still detected in the response")
            else:
                logger.info("No Cloudflare protection detected in the response")
            
            return True
        else:
            logger.error("Failed to get valid content with hybrid approach")
            return False
            
    except Exception as e:
        logger.error(f"Error testing hybrid approach: {e}")
        return False
    finally:
        if 'requests_scraper' in locals():
            requests_scraper.close()

def test_specific_festival_hybrid():
    """Test accessing a specific festival page with hybrid approach."""
    logger.info("Testing access to a specific festival page with hybrid approach...")
    
    try:
        # First, get Cloudflare cookies using CloudScraperEngine
        cf_cookies = get_cloudflare_cookies()
        
        if not cf_cookies:
            logger.info("Trying with PlaywrightScraper instead...")
            cf_cookies = get_playwright_cookies()
            
        if not cf_cookies:
            logger.error("Failed to get Cloudflare cookies from both engines")
            return False
        
        # Initialize RequestsScraper
        requests_scraper = RequestsScraper()
        
        # Set the cookies from CloudScraperEngine
        for name, value in cf_cookies.items():
            requests_scraper.session.cookies.set(name, value)
            
        logger.info(f"Set {len(cf_cookies)} cookies in RequestsScraper")
        
        # Try to access a specific festival page
        url = "https://filmfreeway.com/AustinFilmFestival"
        logger.info(f"Attempting to access {url} with hybrid approach")
        
        # Get the page content
        html = requests_scraper.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with hybrid approach")
            logger.info(f"Response length: {len(html)} characters")
            
            # Extract some data to verify content
            soup = requests_scraper.extract_data(html)
            title = soup.title.text if soup.title else "No title found"
            logger.info(f"Page title: {title}")
            
            # Check for festival name
            festival_name = soup.select_one('h1.festival-title, h1.festival-header__title')
            if festival_name:
                logger.info(f"Festival name: {festival_name.text.strip()}")
            else:
                logger.warning("Could not find festival name")
            
            # Check for Cloudflare indicators
            if 'cloudflare' in html.lower():
                logger.warning("Cloudflare protection still detected in the response")
            else:
                logger.info("No Cloudflare protection detected in the response")
            
            return True
        else:
            logger.error("Failed to get valid content with hybrid approach")
            return False
            
    except Exception as e:
        logger.error(f"Error testing hybrid approach: {e}")
        return False
    finally:
        if 'requests_scraper' in locals():
            requests_scraper.close()

def main():
    """Run all tests."""
    logger.info("Starting hybrid Cloudflare bypass tests...")
    
    # Test the hybrid approach for bypassing Cloudflare
    festivals_result = test_hybrid_cloudflare_bypass()
    
    # Test accessing a specific festival page with hybrid approach
    festival_page_result = test_specific_festival_hybrid()
    
    # Print summary
    logger.info("\n--- Test Results Summary ---")
    logger.info(f"Hybrid Cloudflare bypass test: {'PASSED' if festivals_result else 'FAILED'}")
    logger.info(f"Specific festival page test: {'PASSED' if festival_page_result else 'FAILED'}")
    
    # Overall result
    if festivals_result and festival_page_result:
        logger.info("All tests PASSED!")
    else:
        logger.info("Some tests FAILED!")

if __name__ == "__main__":
    main()
