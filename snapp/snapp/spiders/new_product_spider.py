import json
import scrapy
import re
from scrapy_redis.spiders import RedisSpider
from scrapy import Selector

class NewProductSpider(RedisSpider):
    name = "snappNewProduct"
    def start_requests(self):
        sitemap_url = "https://snappshop.ir/sitemap.xml"
        yield scrapy.Request(
            url=sitemap_url,
            callback=self.parse_sitemap_index,
            errback=self.handle_error,
            meta={'handle_httpstatus_all': True}
        )

    def parse_sitemap_index(self, response):
        if response.status != 200:
            return
            
        selector = Selector(response)
        
        # Remove namespace prefix to simplify XPath queries
        selector.remove_namespaces()
        
        # Extract all sitemap URLs that contain 'product' in their path
        sitemap_urls = selector.xpath('//sitemap/loc[contains(text(), "product")]/text()').getall()
        print(f"Found {len(sitemap_urls)} product sitemaps")
        # Make requests to each product sitemap
        for sitemap_url in sitemap_urls:
            yield scrapy.Request(
                url=sitemap_url,
                callback=self.parse_product_sitemap,
                errback=self.handle_error,
                meta={'handle_httpstatus_all': True}
            )
    
    def parse_product_sitemap(self, response):
        if response.status != 200:
            print(f"Failed to fetch sitemap: {response.url} (status: {response.status})")
            return
            
        selector = Selector(response)
        
        # Remove namespace prefix to simplify XPath queries
        selector.remove_namespaces()
        
        # Extract all product URLs from the sitemap
        product_urls = selector.xpath('//url/loc/text()').getall()
        print(f"Found {len(product_urls)} product URLs in {response.url}")
        
        if not product_urls:
            print(f"No product URLs found. Response sample: {response.text[:500]}")
        
        matched_products = 0
        for product_url in product_urls:
            # Extract product ID from URL like https://snappshop.ir/product/snp-2142388586
            match = re.search(r'/product/snp-(\d+)', product_url)
            if match:
                matched_products += 1
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
                    }
                }
                
                # Push to Redis with custom key
                self.server.lpush('snappProduct:first_crawl', json.dumps(request_data))
                
        print(f"Matched {matched_products} product URLs and pushed to Redis from {response.url}")
    
    def closed(self, reason):
        print(f"Spider closed with reason: {reason}")
    
    def handle_error(self, failure):
        print(f"Request failed: {failure}")
        print(f"Error: {failure.value}")
        print(f"Request: {failure.request}")
