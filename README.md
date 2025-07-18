# Rice Product Data Scraping Project

## Overview
This project scrapes rice product data from Amazon using Selenium and simulates BigBasket API data. It is designed for clean, robust, and efficient data extraction, with a focus on code quality, error handling, and documentation.

## Features
- **Amazon Scraper**: Uses Selenium to extract rice product data from Amazon, handling dynamic content and anti-bot measures.
- **BigBasket Fallback**: Simulates BigBasket API to generate realistic rice product data.
- **Robust Logging**: Logs all actions and errors to log files and the console.
- **Configurable**: Easily adjust the number of products to scrape.
- **Well-Documented**: Clear docstrings, inline comments, and a comprehensive README.

## Setup
1. **Clone the repository** and navigate to the project folder.
2. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```
   If you encounter issues with pandas/numpy on Windows, install them first:
   ```sh
   pip install numpy pandas
   pip install -r requirements.txt
   ```
3. **Ensure Google Chrome is installed** (for Amazon scraping).

## Usage
- **Amazon Scraper**:
  ```sh
  python main.py --amazon
  ```
- **BigBasket Fallback**:
  ```sh
  python main.py --bigbasket
  ```
- **Both Scrapers**:
  ```sh
  python main.py --amazon --bigbasket
  ```

Output files:
- `amazon_rice_products.csv` / `.json`
- `bigbasket_rice_products.csv` / `.json`

## Code Quality
- **Readability**: All code is organized into classes with clear responsibilities.
- **Documentation**: Every method has a docstring. Key logic is explained with inline comments.
- **Naming**: Variables and methods use descriptive names.

## Error Handling
- **Try/Except**: All scraping and data extraction logic is wrapped in try/except blocks.
- **Logging**: Errors and warnings are logged to both file and console for easy debugging.
- **Graceful Exit**: The script handles interruptions and unexpected errors without crashing.

## Performance
- **Efficient Extraction**: Uses Selenium waits and only scrapes required elements.
- **Human-like Delays**: Randomized delays mimic human browsing to avoid detection and reduce server load.
- **Batch Processing**: Scrapes multiple products per page and paginates efficiently.

## Code Comments
- **Docstrings**: Every class and method is documented.
- **Inline Comments**: Key logic and decisions are explained in the code.

## Challenges & Solutions
- **Selenium Headless Chrome Crash**: Fixed by using `--headless=new` and removing problematic user-data-dir on Windows.
- **API Simulation**: Ensured exactly 50 products are always generated in fallback mode, even with filtering.
- **Dependency Issues on Windows**: Provided clear instructions for installing pandas/numpy before other requirements.

