import sys
import os

# Add parent directory to path so we can import from scrapers
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#!/usr/bin/env python3
"""
Test script for direct CloudScraperEngine usage to bypass Cloudflare protection.
"""

import logging
import json
import time
from scrapers import CloudScraperEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("direct_cloudscraper_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_direct_cloudscraper():
    """Test using CloudScraperEngine directly to bypass Cloudflare protection."""
    logger.info("Testing direct CloudScraperEngine usage...")
    
    try:
        # Initialize CloudScraperEngine
        scraper = CloudScraperEngine()
        
        # Try to access the festivals page
        url = "https://filmfreeway.com/festivals"
        logger.info(f"Attempting to access {url} with CloudScraperEngine")
        
        # Get the page content
        html = scraper.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with CloudScraperEngine")
            logger.info(f"Response length: {len(html)} characters")
            
            # Extract some data to verify content
            soup = scraper.extract_data(html)
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
            logger.error("Failed to get valid content from CloudScraperEngine")
            return False
            
    except Exception as e:
        logger.error(f"Error testing CloudScraperEngine: {e}")
        return False
    finally:
        if 'scraper' in locals():
            scraper.close()

def test_specific_festival_direct():
    """Test accessing a specific festival page with CloudScraperEngine."""
    logger.info("Testing access to a specific festival page with CloudScraperEngine...")
    
    try:
        # Initialize CloudScraperEngine
        scraper = CloudScraperEngine()
        
        # Try to access a specific festival page
        url = "https://filmfreeway.com/AustinFilmFestival"
        logger.info(f"Attempting to access {url} with CloudScraperEngine")
        
        # Get the page content
        html = scraper.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with CloudScraperEngine")
            logger.info(f"Response length: {len(html)} characters")
            
            # Extract some data to verify content
            soup = scraper.extract_data(html)
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
            logger.error("Failed to get valid content from CloudScraperEngine")
            return False
            
    except Exception as e:
        logger.error(f"Error testing CloudScraperEngine: {e}")
        return False
    finally:
        if 'scraper' in locals():
            scraper.close()

def main():
    """Run all tests."""
    logger.info("Starting direct CloudScraperEngine tests...")
    
    # Test using CloudScraperEngine directly
    festivals_result = test_direct_cloudscraper()
    
    # Test accessing a specific festival page with CloudScraperEngine
    festival_page_result = test_specific_festival_direct()
    
    # Print summary
    logger.info("\n--- Test Results Summary ---")
    logger.info(f"Direct CloudScraperEngine test: {'PASSED' if festivals_result else 'FAILED'}")
    logger.info(f"Specific festival page test: {'PASSED' if festival_page_result else 'FAILED'}")
    
    # Overall result
    if festivals_result and festival_page_result:
        logger.info("All tests PASSED!")
    else:
        logger.info("Some tests FAILED!")

if __name__ == "__main__":
    main()
