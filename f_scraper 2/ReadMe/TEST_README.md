# Test Framework Documentation

This document explains how the test files in the `tests` directory work and how to use them to validate the functionality of the scraper components without violating any terms of service.

## Test Files Overview

The test framework consists of several test files, each focusing on different aspects of the scraping infrastructure:

1. **test_scraper.py**: Basic tests for the core scraper functionality
2. **test_advanced_scraper.py**: Tests for advanced scraping techniques
3. **test_cloudflare_bypass.py**: Tests specifically for Cloudflare protection bypass
4. **test_direct_cloudscraper.py**: Tests for the direct cloudscraper implementation
5. **test_enhanced_requests_scraper.py**: Tests for the enhanced requests scraper
6. **test_hybrid_cloudflare_bypass.py**: Tests for the hybrid approach to bypassing Cloudflare

## Running the Tests

### Prerequisites

Before running the tests, ensure you have installed all the required dependencies:

```bash
pip install -r requirements.txt
```

### Running Individual Tests

You can run individual test files from the project root directory:

```bash
python -m tests.test_advanced_scraper
python -m tests.test_cloudflare_bypass
# etc.
```

Or navigate to the tests directory and run them directly:

```bash
cd tests
python test_advanced_scraper.py
```

### Test Configuration

Each test file is configured to:

1. Add the parent directory to the Python path to ensure proper imports
2. Set up logging to both console and a log file
3. Import the necessary scraper components
4. Run a series of tests on those components

## Test Structure

Each test file follows a similar structure:

1. **Import and Setup**: Imports necessary modules and sets up logging
2. **Individual Test Functions**: Each function tests a specific component or functionality
3. **Main Function**: Orchestrates the running of all tests in the file
4. **Conditional Execution**: Runs the main function when the script is executed directly

Example:

```python
def test_requests_scraper():
    """Test the RequestsScraper."""
    logger.info("Testing RequestsScraper...")
    
    try:
        scraper = RequestsScraper()
        url = "https://example.com"  # Using a safe example URL
        
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
            
            return True
        else:
            logger.error(f"Failed to fetch {url} with RequestsScraper or response too short")
            return False
    except Exception as e:
        logger.error(f"Error testing RequestsScraper: {e}")
        return False
```

## Safe Testing Practices

The test files are designed to be run safely without violating terms of service:

1. **Example URLs**: Tests use example.com or other safe URLs for basic functionality tests
2. **Limited Requests**: Tests are designed to make a minimal number of requests
3. **Throttling**: Tests include delays between requests to avoid overloading servers
4. **Error Handling**: Robust error handling prevents cascading failures
5. **Proxy Support**: Tests can use proxies to distribute request load

## Extending the Tests

To add new tests:

1. Create a new test file in the `tests` directory
2. Import the necessary components from the `scrapers` package
3. Define test functions for each aspect you want to test
4. Create a main function that runs all your tests
5. Add conditional execution at the bottom of the file

Example of a new test file:

```python
#!/usr/bin/env python3
"""
Test for a new scraper component.
"""

import logging
import sys
import os

# Add parent directory to path so we can import from scrapers
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scrapers import NewScraperComponent

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

def test_new_component():
    """Test the new component."""
    # Test implementation
    pass

def main():
    """Run all tests."""
    test_new_component()

if __name__ == "__main__":
    main()
```

## Interpreting Test Results

The tests output detailed logs that can help diagnose issues:

1. **Success Messages**: Indicate that a component is working correctly
2. **Warning Messages**: Highlight potential issues that might need attention
3. **Error Messages**: Indicate failures that need to be addressed
4. **Exception Traces**: Provide detailed information about what went wrong

Check both the console output and the `test_scraper.log` file for complete information.
