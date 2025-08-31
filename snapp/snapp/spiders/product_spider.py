
import json
import scrapy
import logging
import datetime
from random import sample 
import jdatetime
from snapp.items import *
from scrapy.exceptions import DontCloseSpider
from scrapy_redis.spiders import RedisSpider

class ProductsSpider(RedisSpider):
    name = "snappProduct"
    allowed_domains = ["apix.snappshop.ir"]
    handle_httpstatus_list = [404]
    redis_batch_size = 128
    logger = logging.getLogger()
    redis_key = 'snappProduct:first_crawl'

    def parse(self, response):
        PROXY_LIST = self.settings.get("ROTATING_PROXY_LIST")
        price_history = response.meta.get("price_history")
        request_count = response.meta.get("request_count")
        created_date = response.meta.get("created_date")
        number_of_inactivity = response.meta.get("number_of_inactivity")
        user_like = response.meta.get("user_like")
        user_dislike = response.meta.get("user_dislike")
        proxy = response.meta.get("proxy")

        if response.status==429:
            proxy_list = PROXY_LIST.copy()
            proxy_list = [x for x in PROXY_LIST if proxy.replace("http://", "") not in x]
            new_proxy = sample(proxy_list, 1)[0]
            self.back_to_redis(
                url=response.url,
                request_count=request_count,
                price_history=price_history,
                created_date=created_date,
                number_of_inactivity=number_of_inactivity,
                user_like=user_like,
                user_dislike=user_dislike,
                proxy=new_proxy
            )
        try:
            jsonresponse = response.json()
            

            if not jsonresponse.get("status", False):
                raise DontCloseSpider
            
            data = jsonresponse.get("data", {})
            if not data:
                raise DontCloseSpider
            
            # Check if product is deactivated or has no ID
            page_info = data.get("page", {})
            product_id = data.get("id", "")
            
            # Handle deactivated products or products with no ID
            if (page_info.get("is_deactive", False) or 
                not product_id or 
                page_info.get("status_code") == 301):
                
                # Check if there's a redirect URL we should follow
                redirect_url = page_info.get("redirect_url", "")
                if redirect_url and redirect_url != response.url:
                    # Extract product ID from redirect URL
                    import re
                    match = re.search(r'/product/snp-(\d+)', redirect_url)
                    if match:
                        new_product_id = match.group(1)
                        new_url = f"https://apix.snappshop.ir/products/v2/{new_product_id}"
                        self.logger.info(f"Product redirected from {response.url} to {new_url}")
                        
                        # Make new request with same meta
                        yield scrapy.Request(
                            url=new_url,
                            callback=self.parse,
                            meta=response.meta,
                            dont_filter=True
                        )
            
            product = ProductItem()
            
            # Basic product information
            product["uuid"] = response.url.replace("https://apix.snappshop.ir/products/v2/","").split("?")[0]
            product["dbid"] = f"snp-{product['uuid']}"
            
            # Title information from content section
            content = data.get("content", {})
            product["title_fa"] = content.get("title_fa", "")
            product["title_en"] = content.get("title_en", "")
            
            # Categories from breadcrumb structure
            categories = data.get("categories", [])
            product["supply_category"] = None
            product["category1"] = categories[1].get("title", "") if len(categories) > 1 else ""
            product["category2"] = categories[2].get("title", "") if len(categories) > 2 else ""
            product["category3"] = categories[3].get("title", "") if len(categories) > 3 else ""
            product["category4"] = categories[4].get("title", "") if len(categories) > 4 else ""
            product["category5"] = categories[5].get("title", "") if len(categories) > 5 else ""
            
            # Brand information
            brand = data.get("brand", {})
            product["brand"] = {
                "title_fa": brand.get("title_fa", ""),
                "title_en": brand.get("title_en", ""),
            }
            
            # Product details
            product["description"] = None
            product["is_fake"] = content.get("is_fake", False)
            product["admin_marked_fake"] = False
            
            # URL construction - extract product ID from response URL or meta
            canonical_url = page_info.get("canonical_url")
            if canonical_url:
                product["url"] = canonical_url.replace("https://snappshop.ir/", "/")
            else:
                # Extract from og:url in extra_meta if available
                extra_meta = page_info.get("extra_meta", [])
                og_url = next((meta.get("content") for meta in extra_meta if meta.get("property") == "og:url"), "")
                product["url"] = og_url.replace("https://snappshop.ir/", "/")
            
            product["website"] = {
                "title": "snappshop",
                "url": "www.snappshop.ir"
            }
            
            # Image URL - get first image from images array
            images = data.get("images", [])
            product["image_url"] = [images[0].get("src", "") if images else ""]
            
            # Activity status
            variants = data.get("variants", [])
            product["is_active"] = len(variants) > 0 and any(
                vendor.get("stock", 0) > 0 and vendor.get("is_available_in_vendor_inventory", False)
                for variant in variants
                for vendor in variant.get("vendor", [])
            )
            
            # Timestamps
            product["created_date"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            product["updated_date"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            if created_date:
                product["created_date"] = created_date
            product["user_like"] = user_like or 0
            product["user_dislike"] = user_dislike or 0
            
            # Inactivity counter
            product["number_of_inactivity"] = number_of_inactivity or 0
            if not product["is_active"]:
                product["number_of_inactivity"] += 1
            else:
                product["number_of_inactivity"] = 0
            
            # Pricing information - find cheapest vendor
            all_vendors = []
            for variant in variants:
                all_vendors.extend(variant.get("vendor", []))
            
            if all_vendors:
                # Filter available vendors with stock
                available_vendors = [
                    vendor for vendor in all_vendors 
                    if vendor.get("stock", 0) > 0 and vendor.get("is_available_in_vendor_inventory", False)
                ]
                
                if available_vendors:
                    # Find cheapest vendor (considering special price if available)
                    cheapest_vendor = min(available_vendors, key=lambda x: x.get("special_price", x.get("price", float("inf"))) or x.get("price", float("inf")))
                    
                    selling_price = cheapest_vendor.get("special_price") or cheapest_vendor.get("price")
                    rrp_price = cheapest_vendor.get("price")
                    discount_percent = cheapest_vendor.get("special_price_percent_discount", 0) 
                else:
                    # No available vendors, use first vendor's price
                    first_vendor = all_vendors[0]
                    selling_price = first_vendor.get("special_price") or first_vendor.get("price") * 10
                    rrp_price = first_vendor.get("price") * 10
                    discount_percent = first_vendor.get("special_price_percent_discount", 0)

                product["selling_price"] = selling_price * 10
                product["rrp_price"] = rrp_price * 10
                product["discount_percent"] = discount_percent 
            else:
                product["selling_price"] = None
                product["rrp_price"] = None
                product["discount_percent"] = 0
            
            # Price history calculation
            selling_prices = []
            if price_history:
                for section in ["end_price", "start_price", "middle_prices"]:
                    for date, prices in price_history.get(section, {}).items():
                        if prices and "selling_price" in prices:
                            selling_prices.append(prices["selling_price"])
            
            mean_price = sum(selling_prices) / len(selling_prices) if selling_prices else 0

            today_jdate = jdatetime.date.today()
            today_str = today_jdate.strftime("%Y-%m-%d")
            new_rrp = product["rrp_price"] 
            new_selling = product["selling_price"]

            current_price_data = {
                    "rrp_price": new_rrp, 
                    "selling_price": new_selling,
                    "discount_percent": product["discount_percent"]
                }
                
            if price_history:
                # Get the last recorded price from end_price
                last_date_str = list(price_history.get("end_price", {}).keys())[0]
                last_prices = price_history.get("end_price", {}).get(last_date_str, {})
                
                # Check if price has changed
                price_changed = (new_rrp != last_prices.get("rrp_price") or 
                            new_selling != last_prices.get("selling_price"))
                
                if price_changed:
                    # Move end_price to middle_prices
                    if "middle_prices" not in price_history:
                        price_history["middle_prices"] = {}
                    price_history["middle_prices"][last_date_str] = last_prices
                    price_history["middle_prices"][today_str] = current_price_data
                    
                    # Set new price as end_price
                    price_history["end_price"] = {today_str: current_price_data}
                else:
                    # Price hasn't changed, just update the date in end_price
                    price_history["end_price"] = {today_str: current_price_data}
                
                # Data cleanup: maintain 180+ day window
                start_date_str = list(price_history.get("start_price", {}).keys())[0]
                start_jdate = jdatetime.date(*map(int, start_date_str.split("-")))
                days_diff = (today_jdate - start_jdate).days
                
                if days_diff > 180:
                    # Gap is more than 180 days, need to adjust
                    start_price_data = price_history["start_price"][start_date_str]
                    
                    # Try to use entries from middle_prices first
                    if price_history.get("middle_prices"):
                        # Find a suitable date from middle_prices (within 180-190 days)
                        middle_dates = sorted(price_history["middle_prices"].keys())
                        suitable_date = None
                        
                        for date_str in middle_dates:
                            date_obj = jdatetime.date(*map(int, date_str.split("-")))
                            gap = (today_jdate - date_obj).days
                            
                            if gap > 180:
                                del price_history["middle_prices"][date_str]
                            if gap == 180:
                                suitable_date = date_str
                                break
                        
                        if suitable_date:
                            # Use middle_prices entry as new start_price
                            price_history["start_price"] = {suitable_date: price_history["middle_prices"][suitable_date]}
                            del price_history["middle_prices"][suitable_date]
                        else:
                            # No suitable middle_prices entry, adjust date to 185 days (middle of range)
                            target_days_back = 180
                            new_start_date = today_jdate - datetime.timedelta(days=target_days_back)
                            new_start_date_str = new_start_date.strftime("%Y-%m-%d")
                            price_history["start_price"] = {new_start_date_str: start_price_data}
                    else:
                        # No middle_prices, adjust date to 185 days (middle of range)
                        target_days_back = 180
                        new_start_date = today_jdate - datetime.timedelta(days=target_days_back)
                        new_start_date_str = new_start_date.strftime("%Y-%m-%d")
                        price_history["start_price"] = {new_start_date_str: start_price_data}
            
            else:
                # Initial scrape: create new price_history
                price_history = {
                    "start_price": {today_str: current_price_data},
                    "middle_prices": {},
                    "end_price": {today_str: current_price_data}
                }
            product["price_history"] = price_history
            yield product
            
        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
            self.logger.error(f"Response URL: {response.url}")
            self.logger.error(f"Response status: {response.status}")
            raise DontCloseSpider
    def back_to_redis(
            self, 
            url, 
            request_count, 
            price_history,
            created_date,
            number_of_inactivity,
            user_like,
            user_dislike,
            proxy
            ):
        bcked_url = {
                            "url":url,
                            "meta":{
                                "price_history":price_history,        
                                "request_count": request_count + 1,
                                "created_date":created_date,
                                "number_of_inactivity":number_of_inactivity,
                                "user_like":user_like,
                                "user_dislike":user_dislike,
                                "proxy":proxy
                                }
                        }
        self.server.rpush(' snappProduct:first_crawl', json.dumps(bcked_url)) 