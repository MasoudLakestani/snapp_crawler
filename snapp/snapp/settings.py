# Scrapy settings for snapp project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "snapp"

SPIDER_MODULES = ["snapp.spiders"]
NEWSPIDER_MODULE = "snapp.spiders"

ADDONS = {}


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "snapp (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Concurrency and throttling settings
#CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 0.5

# Concurrency settings
CONCURRENT_REQUESTS = 5
CONCURRENT_REQUESTS_PER_DOMAIN = 5

# Enable AutoThrottle for adaptive speed control
# AUTOTHROTTLE_ENABLED = True
# AUTOTHROTTLE_START_DELAY = 0.1         
# AUTOTHROTTLE_MAX_DELAY = 3              
# AUTOTHROTTLE_TARGET_CONCURRENCY = 8.0   #
# AUTOTHROTTLE_DEBUG = False

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "snapp.middlewares.SnappSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "snapp.middlewares.SnappDownloaderMiddleware": 543,
#}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    "snapp.pipelines.SnappPipeline": 300,
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "ERROR"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "ERROR"
#
# REDIS_START_URLS_KEY = '%(name)s:start_urls'
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "snapp.dupefilter.NoDupeFilter"
REDIS_URL = 'redis://:rv6e7hya18nPA@62.106.95.202:6379'
# REDIS_URL = 'redis://localhost:6379'
SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.FifoQueue'
MAX_IDLE_TIME_BEFORE_CLOSE = 3600 * 30

ITEM_PIPELINES = {
   'scrapy_redis.pipelines.RedisPipeline': 200,
}

# DOWNLOADER_MIDDLEWARES = {
#     # ...
#     'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
#     'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
#     # ...
# }'

## Tor proxy settings
TOR_PROXY_ENABLED = True

# Optional: Disable other proxy middleware to avoid conflicts
# HTTPPROXY_ENABLED = False

# Recommended: Configure delays to be respectful
# DOWNLOAD_DELAY = 1
# RANDOMIZE_DOWNLOAD_DELAY = 0.5
# AUTOTHROTTLE_ENABLED = True
# AUTOTHROTTLE_START_DELAY = 1
# AUTOTHROTTLE_MAX_DELAY = 10


ROTATING_PROXY_LIST = [
    'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.38:6889',
    'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.42:6889',
    'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.56:6889',
    'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.69:6889',
    'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.75:6889',
    'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.92:6889',
    'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.98:6889',
   #  'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.112:6889',
   #  'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.160:6889',
   #  'http://admin:Ms@r-q2wUD8H!eVW@62.106.95.202:6889',
]