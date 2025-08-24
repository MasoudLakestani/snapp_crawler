import json
import scrapy
import re
from random import sample
from scrapy_redis.spiders import RedisSpider

class NewProductSpider(RedisSpider):
    name = "snappNewProduct"
    def start_requests(self):
        url = "https://apix.snappshop.ir/landing/v2?lat=35.77331&lng=51.418591"
        payload = {
            "render": 20,
            "page_type": "categories"
            }
        headers = {'Content-Type': 'application/json'} 
        yield scrapy.Request(
            url=url,
            body=json.dumps(payload),
            headers=headers,
            method="POST",
            callback=self.parse,
            errback=self.handle_error,
            meta={'handle_httpstatus_all': True}
        )

    def parse(self, response):
        if response.status != 200:
            return
            
        jsonresponse = response.json()
        categories = jsonresponse["data"]["structure"]
        
        slugs = []
        for cat in categories:
            if "items" in cat:
                for item in cat["items"]:
                    href = item.get("href", "")
                    if href.startswith("/category/"):
                        slug = href.replace("/category/", "")
                        slugs.append(slug)
        
        # Now make requests for each category slug
        for slug in slugs:
            yield self.make_category_request(slug, 0)
    
    def make_category_request(self, slug, skip):
        url = "https://apix.snappshop.ir/landing/v2?lat=35.77331&lng=51.418591"
        payload = {
            "slug": slug,
            "render": 4,
            "page_type": "category",
            "skip": skip
        }
        headers = {'Content-Type': 'application/json'}
        
        return scrapy.Request(
            url=url,
            body=json.dumps(payload),
            headers=headers,
            method="POST",
            callback=self.parse_products,
            errback=self.handle_error,
            meta={'handle_httpstatus_all': True, 'slug': slug, 'skip': skip}
        )
    
    def parse_products(self, response):
        proxy_list = self.settings.get("ROTATING_PROXY_LIST")
        if response.status != 200:
            return
            
        slug = response.meta['slug']
        skip = response.meta['skip']
        
        jsonresponse = response.json()
        structure = jsonresponse.get("data", {}).get("structure", [])
        
        # Find the plp section with products
        products = []
        for section in structure:
            if section.get("section_type") == "plp":
                products = section.get("items", [])
                break
        
        if products:
            # Extract product data and hrefs
            for product in products:
                # Extract href and product ID
                href = product.get("href", "")
                if href and href.startswith("/product/snp-"):
                    # Extract ID using regex
                    match = re.search(r'/product/snp-(\d+)', href)
                    if match:
                        product_id = match.group(1)
                        # Build the API URL
                        api_url = f"https://apix.snappshop.ir/products/v2/{product_id}?lat=35.77331&lng=51.418591"
                        
                        # Create request data for Redis
                        request_data = {
                            "url": api_url,
                            "meta": {
                                "request_count": 1,
                                "price_history": None,
                                "created_date": None,
                                "number_of_inactivity": 0,
                                "user_like": 0,
                                "user_dislike": 0,
                                "proxy": sample(proxy_list, 1)[0]
                            }
                        }
                        
                        # Push to Redis with custom key
                        self.server.lpush('snappProduct:first_crawl', json.dumps(request_data))
            
            # Continue with next page
            next_skip = skip + 1
            yield self.make_category_request(slug, next_skip)
        else:
            # No more products, move to next category
            print(f"Finished category: {slug}")
    
    def closed(self, reason):
        # Save all products to JSON file when spider closes
        with open('products.json', 'w', encoding='utf-8') as f:
            json.dump(self.all_products, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(self.all_products)} products to products.json")
    
    def handle_error(self, failure):
        print(f"Request failed: {failure}")
        print(f"Error: {failure.value}")
        print(f"Request: {failure.request}")
