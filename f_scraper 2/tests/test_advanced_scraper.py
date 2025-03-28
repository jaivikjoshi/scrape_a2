#!/usr/bin/env python3
"""
Test script for the advanced Filmfreeway scraper.
"""

import logging
import json
import sys
import os

# Add parent directory to path so we can import from scrapers
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scrapers import ScraperFactory, RequestsScraper, CloudScraperEngine, PlaywrightScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "..", "test_scraper.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_requests_scraper():
    """Test the RequestsScraper."""
    logger.info("Testing RequestsScraper...")
    
    try:
        scraper = RequestsScraper()
        url = "https://filmfreeway.com/festivals"
        
        logger.info(f"Fetching {url} with RequestsScraper")
        html = scraper.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with RequestsScraper")
            logger.info(f"Response length: {len(html)} characters")
            
            # Extract some data to verify content
            soup = scraper.extract_data(html)
            title = soup.title.text if soup.title else "No title found"
            logger.info(f"Page title: {title}")
            
            festival_count = len(soup.select('.festival-card'))
            logger.info(f"Found {festival_count} festival cards on the page")
            
            return True
        else:
            logger.error("Failed to get valid content from RequestsScraper")
            return False
            
    except Exception as e:
        logger.error(f"Error testing RequestsScraper: {e}")
        return False
    finally:
        if 'scraper' in locals():
            scraper.close()

def test_cloudscraper_engine():
    """Test the CloudScraperEngine."""
    logger.info("Testing CloudScraperEngine...")
    
    try:
        scraper = CloudScraperEngine()
        url = "https://filmfreeway.com/festivals"
        
        logger.info(f"Fetching {url} with CloudScraperEngine")
        html = scraper.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with CloudScraperEngine")
            logger.info(f"Response length: {len(html)} characters")
            
            # Extract some data to verify content
            soup = scraper.extract_data(html)
            title = soup.title.text if soup.title else "No title found"
            logger.info(f"Page title: {title}")
            
            festival_count = len(soup.select('.festival-card'))
            logger.info(f"Found {festival_count} festival cards on the page")
            
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

def test_playwright_scraper():
    """Test the PlaywrightScraper."""
    logger.info("Testing PlaywrightScraper...")
    
    try:
        scraper = PlaywrightScraper()
        url = "https://filmfreeway.com/festivals"
        
        logger.info(f"Fetching {url} with PlaywrightScraper")
        html = scraper.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with PlaywrightScraper")
            logger.info(f"Response length: {len(html)} characters")
            
            # Extract some data to verify content
            soup = scraper.extract_data(html)
            title = soup.title.text if soup.title else "No title found"
            logger.info(f"Page title: {title}")
            
            festival_count = len(soup.select('.festival-card'))
            logger.info(f"Found {festival_count} festival cards on the page")
            
            return True
        else:
            logger.error("Failed to get valid content from PlaywrightScraper")
            return False
            
    except Exception as e:
        logger.error(f"Error testing PlaywrightScraper: {e}")
        return False
    finally:
        if 'scraper' in locals():
            scraper.close()

def test_scraper_factory():
    """Test the ScraperFactory."""
    logger.info("Testing ScraperFactory...")
    
    try:
        factory = ScraperFactory()
        url = "https://filmfreeway.com/festivals"
        
        logger.info(f"Fetching {url} with ScraperFactory")
        html = factory.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url} with ScraperFactory")
            logger.info(f"Response length: {len(html)} characters")
            
            # Extract some data to verify content
            soup = factory.extract_data(html)
            title = soup.title.text if soup.title else "No title found"
            logger.info(f"Page title: {title}")
            
            festival_count = len(soup.select('.festival-card'))
            logger.info(f"Found {festival_count} festival cards on the page")
            
            # Get stats from the factory
            stats = factory.get_stats()
            logger.info(f"ScraperFactory stats: {json.dumps(stats, indent=2)}")
            
            return True
        else:
            logger.error("Failed to get valid content from ScraperFactory")
            return False
            
    except Exception as e:
        logger.error(f"Error testing ScraperFactory: {e}")
        return False
    finally:
        if 'factory' in locals():
            factory.close()

def test_festival_extraction():
    """Test extracting details from a specific festival page."""
    logger.info("Testing festival details extraction...")
    
    try:
        factory = ScraperFactory()
        # Use a specific festival URL
        url = "https://filmfreeway.com/AustinFilmFestival"
        
        logger.info(f"Fetching festival details from {url}")
        html = factory.get_page(url)
        
        # Check if we got a valid response
        if html and len(html) > 1000:
            logger.info(f"Successfully fetched {url}")
            logger.info(f"Response length: {len(html)} characters")
            
            # Extract some data to verify content
            soup = factory.extract_data(html)
            
            # Extract festival name
            name_element = soup.select_one('h1.festival-title, h1.festival-header__title')
            festival_name = name_element.text.strip() if name_element else "No festival name found"
            logger.info(f"Festival name: {festival_name}")
            
            # Extract festival info
            info_element = soup.select_one('.festival-about__description, .festival-about__text, .festival-description')
            festival_info = info_element.text.strip() if info_element else "No festival info found"
            logger.info(f"Festival info: {festival_info[:100]}...")  # Show first 100 chars
            
            # Extract deadlines
            deadline_elements = soup.select('.festival-deadlines__item, .festival-deadline')
            deadlines = [el.text.strip() for el in deadline_elements if el.text.strip()]
            logger.info(f"Found {len(deadlines)} deadlines")
            
            # Extract categories
            category_elements = soup.select('.festival-categories__item, .festival-categories__name, .festival-category')
            categories = [el.text.strip() for el in category_elements if el.text.strip()]
            logger.info(f"Found {len(categories)} categories")
            
            return True
        else:
            logger.error("Failed to get valid content for festival details")
            return False
            
    except Exception as e:
        logger.error(f"Error testing festival details extraction: {e}")
        return False
    finally:
        if 'factory' in locals():
            factory.close()

def main():
    """Run all tests."""
    logger.info("Starting scraper tests...")
    
    results = {
        "requests_scraper": test_requests_scraper(),
        "cloudscraper_engine": test_cloudscraper_engine(),
        "playwright_scraper": test_playwright_scraper(),
        "scraper_factory": test_scraper_factory(),
        "festival_extraction": test_festival_extraction()
    }
    
    # Print summary
    logger.info("\n--- Test Results Summary ---")
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    # Overall result
    if all(results.values()):
        logger.info("All tests PASSED!")
    else:
        logger.info("Some tests FAILED!")

if __name__ == "__main__":
    main()
