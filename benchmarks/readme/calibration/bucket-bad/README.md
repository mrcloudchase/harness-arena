# ratelimit

A distributed, thread-safe rate limiter with a Redis backend and sliding windows.

```python
limiter = RateLimiter(redis_url="redis://localhost")
limiter.check("user-1")
```
