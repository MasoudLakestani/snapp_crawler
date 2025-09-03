import logging
import time
import requests
from scrapy import signals
from scrapy.exceptions import NotConfigured
from stem import Signal
from stem.control import Controller


class TorController:
#     """Simple Tor controller that trusts Tor's circuit management."""
    
    def __init__(self, control_port: int = 9051, socks_port: int = 9050):
        self.control_port = control_port
        self.socks_port = socks_port
        self.last_newnym_time = 0
        self.min_newnym_interval = 15  
        self.circuit_count = 0
        
        # Setup proxy for initial IP check only
        self.socks_proxies = {
            'http': f'socks5://127.0.0.1:{self.socks_port}',
            'https': f'socks5://127.0.0.1:{self.socks_port}'
        }
        
        # Get initial IP for logging
        initial_ip = self._get_ip_for_display()
        if initial_ip:
            logging.info(f"Initial Tor IP: {initial_ip}")
        else:
            logging.warning("Could not get initial IP for display")
    
    def _get_ip_for_display(self) -> str:
        """Get IP for display purposes only - not critical for operation."""
        try:
            response = requests.get(
                'http://icanhazip.com/',
                proxies=self.socks_proxies,
                timeout=10
            )
            if response.ok:
                return response.text.strip()
        except:
            pass
        return ''
    
    def send_newnym_signal(self) -> bool:
        """Send NEWNYM signal with rate limiting."""
        current_time = time.time()
        
        # Enforce minimum interval
        time_since_last = current_time - self.last_newnym_time
        if time_since_last < self.min_newnym_interval:
            wait_time = self.min_newnym_interval - time_since_last
            logging.info(f"Rate limiting: waiting {wait_time:.1f}s before NEWNYM")
            time.sleep(wait_time)
        
        try:
            with Controller.from_port(port=self.control_port) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                self.last_newnym_time = time.time()
                self.circuit_count += 1
                logging.info(f"NEWNYM signal #{self.circuit_count} sent successfully")
                
                # Give Tor time to build new circuit
                time.sleep(3)
                return True
                
        except Exception as e:
            logging.error(f"Failed to send NEWNYM signal: {e}")
            return False
    
    def request_new_circuit(self) -> bool:
        """
        Request new Tor circuit without IP verification.
        Much more reliable than checking if IP actually changed.
        """
        logging.info("Requesting new Tor circuit...")
        
        success = self.send_newnym_signal()
        
        if success:
            logging.info("IP changed - new circuit established")
            return True
        else:
            logging.error("Failed to request new circuit")
            return False


class TorProxyMiddleware:
    """
    Simple Tor proxy middleware that focuses on reliability over perfect IP tracking.
    Sends NEWNYM signals but doesn't get stuck trying to verify IP changes.
    """
    
    def __init__(self, max_requests_per_ip: int = 1000, control_port: int = 9051, 
                 socks_port: int = 9050, privoxy_port: int = 8118, use_privoxy: bool = True):
        
        self.max_requests_per_ip = max_requests_per_ip
        self.requests_count = 0
        self.use_privoxy = use_privoxy
        self.consecutive_failures = 0
        self.max_consecutive_failures = 2  # Reduced from 3
        self.last_failure_time = 0
        self.failure_cooldown = 180  # 3 minutes instead of 5
        self.total_circuit_changes = 0
        
        # Initialize Tor controller
        self.tor_controller = TorController(
            control_port=control_port,
            socks_port=socks_port
        )
        
        # Set proxy URL
        if self.use_privoxy:
            self.proxy_url = f'http://127.0.0.1:{privoxy_port}'
        else:
            self.proxy_url = f'socks5://127.0.0.1:{socks_port}'
        
        logging.info(f"SimpleTorProxyMiddleware initialized")
        logging.info(f"Proxy: {self.proxy_url}")
        logging.info(f"Circuit change interval: {max_requests_per_ip} requests")
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware instance from crawler."""
        if not crawler.settings.getbool('TOR_PROXY_ENABLED', False):
            raise NotConfigured('SimpleTorProxyMiddleware is not enabled')
        
        settings = crawler.settings
        return cls(
            max_requests_per_ip=settings.getint('TOR_PROXY_CHANGE_AFTER', 1000),
            control_port=settings.getint('TOR_CONTROL_PORT', 9051),
            socks_port=settings.getint('TOR_SOCKS_PORT', 9050),
            privoxy_port=settings.getint('TOR_PRIVOXY_PORT', 8118),
            use_privoxy=settings.getbool('TOR_USE_PRIVOXY', True)
        )
    
    def spider_opened(self, spider):
        """Called when spider opens."""
        spider.logger.info('SimpleTorProxyMiddleware started')
        spider.logger.info(f'Will change circuits every {self.max_requests_per_ip} requests')
    
    def spider_closed(self, spider):
        """Called when spider closes."""
        spider.logger.info(f'Total requests processed: {self.requests_count}')
        spider.logger.info(f'Total circuit changes: {self.total_circuit_changes}')
        spider.logger.info(f'Circuit change failures: {self.consecutive_failures}')
    
    def should_attempt_circuit_change(self) -> bool:
        """Determine if circuit change should be attempted."""
        # Don't try if too many recent failures
        if self.consecutive_failures >= self.max_consecutive_failures:
            time_since_failure = time.time() - self.last_failure_time
            if time_since_failure < self.failure_cooldown:
                return False
            else:
                # Reset after cooldown
                logging.info("Failure cooldown expired - will retry circuit changes")
                self.consecutive_failures = 0
        
        return self.requests_count >= self.max_requests_per_ip
    
    def attempt_circuit_change(self, spider):
        """Attempt to change Tor circuit."""
        spider.logger.info(f'Requesting new Tor circuit after {self.requests_count} requests')
        
        try:
            success = self.tor_controller.request_new_circuit()
            
            if success:
                spider.logger.info('Circuit change successful')
                self.requests_count = 0
                self.consecutive_failures = 0
                self.total_circuit_changes += 1
                return True
            else:
                self.consecutive_failures += 1
                self.last_failure_time = time.time()
                spider.logger.error(f'Circuit change failed (failure #{self.consecutive_failures})')
                
                if self.consecutive_failures >= self.max_consecutive_failures:
                    spider.logger.error(f'Too many failures - will retry after {self.failure_cooldown}s cooldown')
                
                return False
                
        except Exception as e:
            self.consecutive_failures += 1
            self.last_failure_time = time.time()
            spider.logger.error(f'Circuit change exception: {e}')
            return False
    
    def process_request(self, request, spider):
        """Process request through Tor proxy."""
        # Attempt circuit change if needed and allowed
        if self.should_attempt_circuit_change():
            success = self.attempt_circuit_change(spider)
            if not success:
                spider.logger.info("Continuing with current circuit after failed change")
        
        # Always set proxy
        request.meta['proxy'] = self.proxy_url
        
        # Increment counter
        self.requests_count += 1
        
        # Periodic logging
        if self.requests_count % 50 == 0:
            spider.logger.info(f'Processed {self.requests_count} requests on current circuit')
        
        return None


# Even simpler version - just routes through Tor without any circuit changes
class BasicTorProxyMiddleware:
    """
    Basic Tor proxy - just routes requests through Tor.
    No circuit changes, no IP rotation, maximum reliability.
    """
    
    def __init__(self, privoxy_port: int = 8118, socks_port: int = 9050, use_privoxy: bool = True):
        self.use_privoxy = use_privoxy
        if use_privoxy:
            self.proxy_url = f'http://127.0.0.1:{privoxy_port}'
        else:
            self.proxy_url = f'socks5://127.0.0.1:{socks_port}'
        
        logging.info(f"BasicTorProxyMiddleware initialized with: {self.proxy_url}")
        logging.info("No circuit rotation - maximum stability")
    
    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('TOR_PROXY_ENABLED', False):
            raise NotConfigured('BasicTorProxyMiddleware is not enabled')
        
        privoxy_port = crawler.settings.getint('TOR_PRIVOXY_PORT', 8118)
        socks_port = crawler.settings.getint('TOR_SOCKS_PORT', 9050)
        use_privoxy = crawler.settings.getbool('TOR_USE_PRIVOXY', True)
        
        return cls(privoxy_port=privoxy_port, socks_port=socks_port, use_privoxy=use_privoxy)
    
    def process_request(self, request, spider):
        request.meta['proxy'] = self.proxy_url
        return None


class HighPerformanceProxyMiddleware:
    """High-performance proxy middleware with fast failover."""
    
    def __init__(self):
        self.proxy_index = 0
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls()
    
    def process_request(self, request, spider):
        """Set proxy with fast failover logic."""
        proxy_list = spider.settings.get('ROTATING_PROXY_LIST', [])
        if not proxy_list:
            return None
        
        # Set proxy in request meta (Scrapy way)
        proxy = proxy_list[self.proxy_index % len(proxy_list)]
        request.meta['proxy'] = proxy
        request.meta['download_timeout'] = 1  # 1 second timeout
        request.meta['request_start_time'] = time.time()
        
        self.proxy_index += 1
        return None
    
    def process_exception(self, request, exception, spider):
        """Handle proxy failures by trying next proxy."""
        proxy_list = spider.settings.get('ROTATING_PROXY_LIST', [])
        if not proxy_list:
            return None
            
        current_proxy = request.meta.get('proxy', '')
        retry_count = request.meta.get('proxy_retry_count', 0)
        max_retries = len(proxy_list)
        
        if retry_count < max_retries:
            # Try next proxy
            next_proxy = proxy_list[self.proxy_index % len(proxy_list)]
            self.proxy_index += 1
            
            spider.logger.warning(f"Proxy {current_proxy} failed, trying {next_proxy}")
            
            # Create new request with next proxy
            new_request = request.copy()
            new_request.meta['proxy'] = next_proxy
            new_request.meta['proxy_retry_count'] = retry_count + 1
            new_request.meta['download_timeout'] = 1
            new_request.meta['request_start_time'] = time.time()
            new_request.dont_filter = True
            
            return new_request
        else:
            spider.logger.error(f"All proxies failed for {request.url}")
            return None