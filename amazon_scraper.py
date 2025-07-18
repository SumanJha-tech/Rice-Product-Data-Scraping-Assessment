import logging
import time
import csv
import json
import random
from datetime import datetime
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class AmazonRiceScraper:
    """
    Scrapes rice product data from Amazon using Selenium WebDriver.
    Handles dynamic content, pagination, and anti-bot measures.
    """
    def __init__(self):
        """Initialize the scraper with Chrome options and logging."""
        self.setup_logging()
        self.setup_driver()
        self.products = []
        self.target_count = 50

    def setup_logging(self):
        """Configure logging for the scraper."""
        # Set up logging to file and console
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('amazon_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Setup Chrome WebDriver with anti-detection options."""
        chrome_options = Options()
        # Anti-detection and headless options
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        self.driver = webdriver.Chrome(options=chrome_options)
        # Hide webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)

    def human_like_delay(self, min_delay=1, max_delay=3):
        """Add random delays to mimic human browsing behavior."""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def scroll_page(self):
        """Scroll the page to trigger dynamic content loading."""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        self.human_like_delay(1, 2)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.human_like_delay(1, 2)

    def extract_price(self, product_element):
        """Extract price information from a product element."""
        price_info = {'current': None, 'original': None, 'discount': None}
        try:
            # Try multiple selectors for price
            price_selectors = [
                '.a-price-whole',
                '.a-price .a-offscreen',
                '.a-price-symbol + .a-price-whole',
                '.a-price-range .a-price .a-offscreen'
            ]
            for selector in price_selectors:
                try:
                    price_element = product_element.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_element.text or price_element.get_attribute('textContent')
                    if price_text:
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price_info['current'] = float(price_match.group())
                            break
                except NoSuchElementException:
                    continue
            # Try to extract original price (if available)
            try:
                original_price_element = product_element.find_element(By.CSS_SELECTOR, '.a-text-price .a-offscreen')
                original_price_text = original_price_element.text
                price_match = re.search(r'[\d,]+', original_price_text.replace(',', ''))
                if price_match:
                    price_info['original'] = float(price_match.group())
            except NoSuchElementException:
                pass
            # Calculate discount if both prices are available
            if price_info['current'] and price_info['original']:
                discount = ((price_info['original'] - price_info['current']) / price_info['original']) * 100
                price_info['discount'] = round(discount, 2)
        except Exception as e:
            self.logger.warning(f"Error extracting price: {e}")
        return price_info

    def extract_rating(self, product_element):
        """Extract rating from a product element."""
        try:
            rating_element = product_element.find_element(By.CSS_SELECTOR, '.a-icon-alt')
            rating_text = rating_element.get_attribute('textContent') or rating_element.text
            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
            if rating_match:
                return float(rating_match.group(1))
        except NoSuchElementException:
            pass
        return None

    def extract_review_count(self, product_element):
        """Extract review count from a product element."""
        try:
            review_selectors = [
                '.a-size-base',
                '.a-link-normal .a-size-base',
                'span[aria-label*="reviews"]'
            ]
            for selector in review_selectors:
                try:
                    review_element = product_element.find_element(By.CSS_SELECTOR, selector)
                    review_text = review_element.text
                    if review_text and ('(' in review_text or 'review' in review_text.lower()):
                        review_match = re.search(r'[\d,]+', review_text.replace(',', ''))
                        if review_match:
                            return int(review_match.group())
                except NoSuchElementException:
                    continue
        except Exception as e:
            pass
        return None

    def extract_product_data(self, product_element):
        """Extract all relevant product data from a product element."""
        try:
            # Product name
            name_element = product_element.find_element(By.CSS_SELECTOR, 'h2 a span, .a-link-normal .a-text-normal')
            product_name = name_element.text.strip()
            # Product URL
            url_element = product_element.find_element(By.CSS_SELECTOR, 'h2 a, .a-link-normal')
            product_url = url_element.get_attribute('href')
            # Brand extraction
            brand = None
            try:
                brand_element = product_element.find_element(By.CSS_SELECTOR, '.a-size-base-plus')
                brand = brand_element.text.strip()
            except NoSuchElementException:
                brand_match = re.search(r'^([A-Za-z\s]+)', product_name)
                if brand_match:
                    brand = brand_match.group(1).strip()
            # Price, rating, reviews
            price_info = self.extract_price(product_element)
            rating = self.extract_rating(product_element)
            review_count = self.extract_review_count(product_element)
            # Image URL
            image_url = None
            try:
                img_element = product_element.find_element(By.CSS_SELECTOR, 'img')
                image_url = img_element.get_attribute('src')
            except NoSuchElementException:
                pass
            # Availability
            availability = price_info['current'] is not None
            # Product ID from URL
            product_id = None
            if product_url:
                id_match = re.search(r'/dp/([A-Z0-9]+)', product_url)
                if id_match:
                    product_id = id_match.group(1)
            product_data = {
                'product_id': product_id,
                'product_name': product_name,
                'brand': brand,
                'price_current': price_info['current'],
                'price_original': price_info['original'],
                'discount_percentage': price_info['discount'],
                'rating': rating,
                'review_count': review_count,
                'availability': availability,
                'image_url': image_url,
                'product_url': product_url,
                'platform': 'Amazon',
                'scraped_at': datetime.now().isoformat()
            }
            return product_data
        except Exception as e:
            self.logger.error(f"Error extracting product data: {e}")
            return None

    def scrape_rice_products(self):
        """Main scraping method for Amazon rice products."""
        try:
            self.logger.info("Starting Amazon rice product scraping...")
            url = "https://www.amazon.com/s?k=rice"
            self.driver.get(url)
            self.human_like_delay(2, 4)
            page_num = 1
            while len(self.products) < self.target_count:
                self.logger.info(f"Scraping page {page_num} - Products collected: {len(self.products)}")
                self.scroll_page()
                try:
                    product_containers = self.wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-component-type="s-search-result"]'))
                    )
                except TimeoutException:
                    self.logger.error("Timeout waiting for product containers")
                    break
                for container in product_containers:
                    if len(self.products) >= self.target_count:
                        break
                    product_data = self.extract_product_data(container)
                    if product_data and product_data['product_name']:
                        if 'rice' in product_data['product_name'].lower():
                            self.products.append(product_data)
                            self.logger.info(f"Extracted: {product_data['product_name'][:50]}...")
                    self.human_like_delay(0.5, 1.5)
                # Pagination
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, '.s-pagination-next')
                    if next_button.is_enabled():
                        self.driver.execute_script("arguments[0].click();", next_button)
                        self.human_like_delay(3, 5)
                        page_num += 1
                    else:
                        self.logger.info("No more pages available")
                        break
                except NoSuchElementException:
                    self.logger.info("Next button not found, ending pagination")
                    break
            self.logger.info(f"Scraping completed. Total products collected: {len(self.products)}")
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
        finally:
            self.driver.quit()

    def save_to_csv(self, filename='amazon_rice_products.csv'):
        """Save scraped products to a CSV file."""
        if not self.products:
            self.logger.warning("No products to save")
            return
        fieldnames = [
            'product_id', 'product_name', 'brand', 'price_current', 'price_original',
            'discount_percentage', 'rating', 'review_count', 'availability',
            'image_url', 'product_url', 'platform', 'scraped_at'
        ]
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.products)
        self.logger.info(f"Data saved to {filename}")

    def save_to_json(self, filename='amazon_rice_products.json'):
        """Save scraped products to a JSON file."""
        if not self.products:
            self.logger.warning("No products to save")
            return
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(self.products, jsonfile, indent=2, ensure_ascii=False)
        self.logger.info(f"Data saved to {filename}") 