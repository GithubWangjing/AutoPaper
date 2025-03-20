import time
import logging

class RateLimiter:
    def __init__(self, min_request_interval=1.0, max_requests_per_minute=60):
        self.min_request_interval = min_request_interval
        self.max_requests_per_minute = max_requests_per_minute
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()
        self.logger = logging.getLogger(__name__)
        
    def wait(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        
        # Check if we need to wait for minimum interval
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            self.logger.debug(f"Waiting {wait_time:.2f} seconds for minimum interval")
            time.sleep(wait_time)
            current_time = time.time()
            
        # Check if we need to wait for requests per minute limit
        time_in_window = current_time - self.request_window_start
        if time_in_window >= 60:
            # Reset window
            self.request_window_start = current_time
            self.request_count = 0
        elif self.request_count >= self.max_requests_per_minute:
            # Wait until window resets
            wait_time = 60 - time_in_window
            self.logger.debug(f"Waiting {wait_time:.2f} seconds for rate limit window")
            time.sleep(wait_time)
            self.request_window_start = time.time()
            self.request_count = 0
            
        # Update counters
        self.last_request_time = time.time()
        self.request_count += 1 