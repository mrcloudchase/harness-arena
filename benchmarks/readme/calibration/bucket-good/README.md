# ratelimit

A small token-bucket rate limiter. The bucket holds up to `capacity` tokens and refills at `rate` tokens per second;
an action costs tokens.

```python
from ratelimit import TokenBucket

bucket = TokenBucket(rate=5, capacity=10)   # 5 tokens/second, bursts of up to 10
if bucket.allow():                          # costs 1 token
    handle(request)
else:
    time.sleep(bucket.wait_time())          # seconds until 1 token is available
```

## API

- `TokenBucket(rate, capacity, clock=time.monotonic)`: starts full. `clock` can be replaced in tests.
- `allow(cost=1) -> bool`: takes `cost` tokens and returns True, or returns False and takes nothing.
- `wait_time(cost=1) -> float`: seconds until `cost` tokens are available; 0.0 if they already are.

It is not thread-safe: guard it with a lock if several threads share one bucket.
