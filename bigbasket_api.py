import requests
import json
import time
import logging
import csv
from datetime import datetime
import random
from urllib.parse import urljoin, urlencode
import re

class BigBasketAPI:
    """
    Simulates BigBasket API to retrieve rice product data.
    Handles fallback data generation, logging, and saving.
    """
    def __init__(self, api_key=None):
        """Initialize BigBasket API client and logging."""
        self.base_url = "https://www.bigbasket.com"
        self.api_key = api_key
        self.session = requests.Session()
        self.products = []
        self.target_count = 50
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.bigbasket.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.session.headers.update(self.headers)
        self.setup_logging()

    def setup_logging(self):
        """Configure logging for the API client."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bigbasket_api.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def rate_limit_delay(self, min_delay=1, max_delay=3):
        """Add delays to respect rate limits and mimic human behavior."""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def make_request(self, endpoint, params=None, max_retries=3):
        """Make API request with retry logic and error handling."""
        url = urljoin(self.base_url, endpoint)
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Making request to: {url}")
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    self.logger.warning("Rate limited, waiting...")
                    time.sleep(5 * (attempt + 1))
                    continue
                elif response.status_code == 403:
                    self.logger.error("Access forbidden, might need authentication")
                    return None
                else:
                    self.logger.error(f"HTTP {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
        return None

    def search_products(self, query="rice", page=1, limit=20):
        """Search for products using BigBasket's search API."""
        search_endpoint = "/pb/search"
        params = {
            'q': query,
            'page': page,
            'tab': 'all',
            'sorted_on': 'relevance',
            'listtype': 'pc'
        }
        return self.make_request(search_endpoint, params)

    def get_product_details(self, product_id):
        """Get detailed product information by product ID."""
        detail_endpoint = f"/pb/product/{product_id}"
        return self.make_request(detail_endpoint)

    def get_category_products(self, category_id="rice", page=1):
        """Get products from a specific category."""
        category_endpoint = "/pb/category"
        params = {
            'category': category_id,
            'page': page,
            'sorted_on': 'relevance'
        }
        return self.make_request(category_endpoint, params)

    def extract_price_info(self, product_data):
        """Extract price information from product data."""
        price_info = {
            'current': None,
            'original': None,
            'discount': None
        }
        try:
            # Try different possible price field names
            price_fields = ['sp', 'selling_price', 'price', 'sale_price']
            mrp_fields = ['mrp', 'maximum_retail_price', 'original_price']
            for field in price_fields:
                if field in product_data and product_data[field]:
                    price_info['current'] = float(product_data[field])
                    break
            for field in mrp_fields:
                if field in product_data and product_data[field]:
                    price_info['original'] = float(product_data[field])
                    break
            # Calculate discount if both prices are available
            if price_info['current'] and price_info['original']:
                discount = ((price_info['original'] - price_info['current']) / price_info['original']) * 100
                price_info['discount'] = round(discount, 2)
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Error extracting price: {e}")
        return price_info

    def process_product(self, product_data):
        """Process and normalize individual product data."""
        try:
            product_id = product_data.get('id') or product_data.get('product_id')
            product_name = product_data.get('name') or product_data.get('title', '')
            # Filter for rice products
            if 'rice' not in product_name.lower():
                return None
            brand = product_data.get('brand', {})
            if isinstance(brand, dict):
                brand = brand.get('name', '')
            elif not isinstance(brand, str):
                brand = str(brand) if brand else ''
            price_info = self.extract_price_info(product_data)
            description = product_data.get('description', '') or product_data.get('desc', '')
            category = product_data.get('category', {})
            if isinstance(category, dict):
                category_name = category.get('name', '')
            else:
                category_name = str(category) if category else ''
            stock_info = product_data.get('stock', {})
            if isinstance(stock_info, dict):
                availability = stock_info.get('available', True)
            else:
                availability = product_data.get('available', True)
            image_url = None
            images = product_data.get('images', [])
            if images and isinstance(images, list):
                image_url = images[0].get('url') if isinstance(images[0], dict) else images[0]
            else:
                image_url = product_data.get('image_url') or product_data.get('image')
            product_url = f"https://www.bigbasket.com/pd/{product_id}/" if product_id else None
            processed_product = {
                'product_id': str(product_id) if product_id else None,
                'product_name': product_name,
                'brand': brand,
                'price_current': price_info['current'],
                'price_original': price_info['original'],
                'discount_percentage': price_info['discount'],
                'rating': product_data.get('rating', None),
                'review_count': product_data.get('review_count', None),
                'availability': availability,
                'image_url': image_url,
                'product_url': product_url,
                'platform': 'BigBasket',
                'scraped_at': datetime.now().isoformat(),
                'description': description,
                'category': category_name
            }
            return processed_product
        except Exception as e:
            self.logger.error(f"Error processing product: {e}")
            return None

    def get_rice_products(self):
        """Main method to get rice products from BigBasket API."""
        try:
            self.logger.info("Starting BigBasket rice product collection...")
            search_terms = ['rice', 'basmati rice', 'brown rice', 'rice grains']
            for term in search_terms:
                if len(self.products) >= self.target_count:
                    break
                self.logger.info(f"Searching for: {term}")
                page = 1
                while len(self.products) < self.target_count:
                    response = self.search_products(term, page)
                    if not response or 'products' not in response:
                        self.logger.warning(f"No products found for {term} on page {page}")
                        break
                    products = response.get('products', [])
                    if not products:
                        self.logger.info(f"No more products for {term}")
                        break
                    for product_data in products:
                        if len(self.products) >= self.target_count:
                            break
                        processed_product = self.process_product(product_data)
                        if processed_product:
                            self.products.append(processed_product)
                            self.logger.info(f"Collected: {processed_product['product_name'][:50]}...")
                        self.rate_limit_delay(0.5, 1.5)
                    page += 1
                    self.rate_limit_delay(1, 3)
            self.logger.info(f"Collection completed. Total products: {len(self.products)}")
        except Exception as e:
            self.logger.error(f"Error during product collection: {e}")

    def get_rice_products_fallback(self):
        """Fallback method using direct API simulation to generate rice products."""
        self.logger.info("Using fallback method to simulate BigBasket API...")
        sample_products = [
            {
                'id': 'BB001',
                'name': 'India Gate Basmati Rice - Classic',
                'brand': 'India Gate',
                'sp': 299.0,
                'mrp': 349.0,
                'rating': 4.2,
                'review_count': 1250,
                'available': True,
                'image': 'https://www.bigbasket.com/media/uploads/p/l/40034810_7-india-gate-basmati-rice-classic.jpg',
                'description': 'Premium quality basmati rice with long grains',
                'category': 'Rice & Rice Products'
            },
            {
                'id': 'BB002',
                'name': 'Kohinoor Super Basmati Rice',
                'brand': 'Kohinoor',
                'sp': 189.0,
                'mrp': 210.0,
                'rating': 4.1,
                'review_count': 890,
                'available': True,
                'image': 'https://www.bigbasket.com/media/uploads/p/l/273936_7-kohinoor-super-basmati-rice.jpg',
                'description': 'Aromatic super basmati rice',
                'category': 'Rice & Rice Products'
            },
            {
                'id': 'BB003',
                'name': 'Tilda Pure Basmati Rice',
                'brand': 'Tilda',
                'sp': 449.0,
                'mrp': 499.0,
                'rating': 4.5,
                'review_count': 567,
                'available': True,
                'image': 'https://www.bigbasket.com/media/uploads/p/l/40156557_4-tilda-pure-basmati-rice.jpg',
                'description': 'Premium imported basmati rice',
                'category': 'Rice & Rice Products'
            },
            {
                'id': 'BB004',
                'name': 'Daawat Rozana Gold Basmati Rice',
                'brand': 'Daawat',
                'sp': 279.0,
                'mrp': 320.0,
                'rating': 4.0,
                'review_count': 1100,
                'available': True,
                'image': 'https://www.bigbasket.com/media/uploads/p/l/40034811_8-daawat-rozana-gold-basmati-rice.jpg',
                'description': 'Everyday basmati rice with great taste',
                'category': 'Rice & Rice Products'
            },
            {
                'id': 'BB005',
                'name': 'Aashirvaad Select Sharbati Rice',
                'brand': 'Aashirvaad',
                'sp': 159.0,
                'mrp': 180.0,
                'rating': 3.9,
                'review_count': 750,
                'available': True,
                'image': 'https://www.bigbasket.com/media/uploads/p/l/40034812_6-aashirvaad-select-sharbati-rice.jpg',
                'description': 'Premium sharbati rice for daily meals',
                'category': 'Rice & Rice Products'
            }
        ]
        # Generate more products to reach target count
        base_products = sample_products.copy()
        rice_variants = ['Basmati', 'Brown', 'White', 'Ponni', 'Sona Masuri', 'Jasmine']
        brands = ['India Gate', 'Kohinoor', 'Tilda', 'Daawat', 'Aashirvaad', 'Fortune', 'Lal Qilla']
        i = len(base_products)
        # Add initial sample products
        for product in base_products:
            processed_product = self.process_product(product)
            if processed_product:
                self.products.append(processed_product)
                self.logger.info(f"Generated: {processed_product['product_name']}")
        # Continue generating until we have target_count
        while len(self.products) < self.target_count:
            variant = random.choice(rice_variants)
            brand = random.choice(brands)
            product = {
                'id': f'BB{i+1:03d}',
                'name': f'{brand} {variant} Rice',
                'brand': brand,
                'sp': round(random.uniform(150, 500), 2),
                'mrp': round(random.uniform(200, 600), 2),
                'rating': round(random.uniform(3.5, 4.8), 1),
                'review_count': random.randint(100, 2000),
                'available': random.choice([True, True, True, False]),
                'image': f'https://www.bigbasket.com/media/uploads/p/l/rice_{i+1}.jpg',
                'description': f'High quality {variant.lower()} rice from {brand}',
                'category': 'Rice & Rice Products'
            }
            if product['sp'] >= product['mrp']:
                product['mrp'] = product['sp'] + random.uniform(20, 50)
            processed_product = self.process_product(product)
            if processed_product:
                self.products.append(processed_product)
                self.logger.info(f"Generated: {processed_product['product_name']}")
            i += 1
            time.sleep(0.1)

    def save_to_csv(self, filename='bigbasket_rice_products.csv'):
        """Save products to a CSV file."""
        if not self.products:
            self.logger.warning("No products to save")
            return
        fieldnames = [
            'product_id', 'product_name', 'brand', 'price_current', 'price_original',
            'discount_percentage', 'rating', 'review_count', 'availability',
            'image_url', 'product_url', 'platform', 'scraped_at', 'description', 'category'
        ]
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.products)
        self.logger.info(f"Data saved to {filename}")

    def save_to_json(self, filename='bigbasket_rice_products.json'):
        """Save products to a JSON file."""
        if not self.products:
            self.logger.warning("No products to save")
            return
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(self.products, jsonfile, indent=2, ensure_ascii=False)
        self.logger.info(f"Data saved to {filename}")

    def process_response(self, response):
        """Process API response and extract relevant data."""
        if not response:
            return []
        processed_products = []
        try:
            if isinstance(response, dict):
                if 'products' in response:
                    products = response['products']
                elif 'data' in response:
                    products = response['data']
                else:
                    products = [response]
            else:
                products = response
            for product in products:
                processed_product = self.process_product(product)
                if processed_product:
                    processed_products.append(processed_product)
        except Exception as e:
            self.logger.error(f"Error processing response: {e}")
        return processed_products 