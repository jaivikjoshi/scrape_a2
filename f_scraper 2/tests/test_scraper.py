import sys
import os

# Add parent directory to path so we can import from scrapers
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#!/usr/bin/env python3
"""
Test script for the Filmfreeway scraper.
"""

import logging
import json
import os
import sys
import time
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import the scraper
from scraper import FilmfreewayScraper

# Main festivals listing URL
MAIN_URL = "https://filmfreeway.com/festivals?utf8=✓&config%5B%5D=entry_fees&config%5B%5D=years_running&config%5B%5D=runtime&config%5B%5D=submit&has_query=&ga_search_category=Festival&q=&call_for_entries=1&ft_gold=0&ft_gold=1&ft_ff=0&ft_ff=1&ft_sc=0&ft_audio=0&ft_photo=0&ft_oe=0&project_category%5B%5D=5&fees=0%3B100&years=1%3B20&runtime=Any&inside_or_outside_country=0&countries=&completion_date=&entry_deadline_when=0&entry_deadline=&event_date_when=0&event_date=&sort=years"

def test_main_page_access():
    """Test accessing the main festivals listing page."""
    try:
        # Create a scraper instance
        scraper = FilmfreewayScraper()
        
        # Try to access the main page
        logger.info(f"Testing access to main page: {MAIN_URL}")
        html = scraper._get_page(MAIN_URL)
        
        # Check if we got valid HTML
        if html and len(html) > 1000:  # Simple check for non-empty response
            logger.info(f"Successfully accessed main page. HTML length: {len(html)}")
            
            # Parse the page
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract festival links
            links = scraper._extract_festival_links(soup)
            
            # Print the number of links found
            logger.info(f"Found {len(links)} festival links on the main page")
            
            # Print the first 3 links
            for i, link in enumerate(links[:3]):
                logger.info(f"Link {i+1}: {link}")
            
            # Try to extract details from the first link
            if links:
                try:
                    logger.info(f"Testing extraction from first link: {links[0]}")
                    festival_data = scraper._extract_festival_details(links[0])
                    
                    # Check if we got valid data
                    if festival_data and festival_data.get("festival_name"):
                        logger.info(f"Successfully extracted data from {links[0]}")
                        logger.info(f"Festival name: {festival_data.get('festival_name')}")
                        logger.info(f"Festival info: {festival_data.get('festival_info')[:100]}..." if festival_data.get('festival_info') else "No festival info found")
                        logger.info(f"Deadlines: {festival_data.get('deadlines')}")
                        logger.info(f"Categories: {len(festival_data.get('categories', []))} categories found")
                        logger.info(f"Awards: {len(festival_data.get('awards', []))} awards found")
                        logger.info(f"Important dates: {festival_data.get('important_dates')}")
                        
                        # Write the test result to a file
                        with open("test_result.json", "w") as f:
                            json.dump(festival_data, f, indent=2)
                        
                        logger.info("Test result saved to test_result.json")
                    else:
                        logger.warning(f"Extracted data from {links[0]} but it appears incomplete")
                except Exception as e:
                    logger.warning(f"Error extracting details from {links[0]}: {e}")
            
            return True
        else:
            logger.error("Failed to get valid HTML from main page")
            return False
            
    except Exception as e:
        logger.error(f"Error during main page test: {e}")
        raise

def test_pagination():
    """Test pagination functionality."""
    try:
        # Create a scraper instance
        scraper = FilmfreewayScraper()
        
        # Test collecting festival links
        logger.info("Testing pagination and link collection...")
        
        # Limit the number of pages to check for the test
        original_target = scraper.TARGET_FESTIVALS
        scraper.TARGET_FESTIVALS = 50  # Just collect a few for testing
        
        # Collect links
        scraper._collect_festival_links()
        
        # Restore original target
        scraper.TARGET_FESTIVALS = original_target
        
        # Check if we collected any links
        if scraper.festival_links:
            logger.info(f"Successfully collected {len(scraper.festival_links)} festival links")
            logger.info(f"Sample links: {list(scraper.festival_links)[:3]}")
            return True
        else:
            logger.error("Failed to collect any festival links")
            return False
            
    except Exception as e:
        logger.error(f"Error during pagination test: {e}")
        raise

def main():
    """Run all tests."""
    logger.info("Starting Filmfreeway scraper tests")
    
    # Test accessing the main page and extracting a festival
    main_page_success = test_main_page_access()
    
    if main_page_success:
        # Only run pagination test if the main page test passed
        logger.info("Main page test passed. Testing pagination...")
        pagination_success = test_pagination()
        
        if pagination_success:
            logger.info("All tests passed successfully!")
        else:
            logger.error("Pagination test failed.")
            sys.exit(1)
    else:
        logger.error("Main page test failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
