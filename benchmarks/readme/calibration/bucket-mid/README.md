# ratelimit

Token bucket limiter.

Create `TokenBucket(rate, capacity)` and call `allow()`. It returns True if you may proceed.
There is also `wait_time()`.
