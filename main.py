import argparse
from amazon_scraper import AmazonRiceScraper
from bigbasket_api import BigBasketAPI

def run_amazon_scraper():
    scraper = AmazonRiceScraper()
    try:
        scraper.scrape_rice_products()
        scraper.save_to_csv()
        scraper.save_to_json()
        print(f"\nAmazon Scraping Summary:")
        print(f"Total products scraped: {len(scraper.products)}")
        print(f"Data saved to: amazon_rice_products.csv and amazon_rice_products.json")
    except Exception as e:
        print(f"Error during Amazon scraping: {e}")

def run_bigbasket_api():
    api_client = BigBasketAPI()
    try:
        # api_client.get_rice_products()  # Uncomment if you want to use real API
        api_client.get_rice_products_fallback()
        api_client.save_to_csv()
        api_client.save_to_json()
        print(f"\nBigBasket API Collection Summary:")
        print(f"Total products collected: {len(api_client.products)}")
        print(f"Data saved to: bigbasket_rice_products.csv and bigbasket_rice_products.json")
        if api_client.products:
            print(f"\nSample products:")
            for i, product in enumerate(api_client.products[:3]):
                print(f"{i+1}. {product['product_name']} - ₹{product['price_current']}")
    except Exception as e:
        print(f"Error during BigBasket API collection: {e}")

def main():
    parser = argparse.ArgumentParser(description="Rice Product Data Scraper")
    parser.add_argument('--amazon', action='store_true', help='Run Amazon rice product scraper')
    parser.add_argument('--bigbasket', action='store_true', help='Run BigBasket rice product API collector')
    args = parser.parse_args()

    if not args.amazon and not args.bigbasket:
        parser.print_help()
        return

    if args.amazon:
        run_amazon_scraper()
    if args.bigbasket:
        run_bigbasket_api()

if __name__ == "__main__":
    main() 