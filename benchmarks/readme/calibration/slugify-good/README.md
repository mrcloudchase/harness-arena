# slugify

Turn any text into a URL-safe slug: lowercase ASCII letters and digits joined by a separator.

## Use

Copy `slugify.py` into your project (no dependencies beyond the standard library).

```python
from slugify import slugify, unslugify

slugify("Héllo, Wörld! 2024")            # 'hello-world-2024'
slugify("Hello World", sep="_")          # 'hello_world'
slugify("A very long title indeed", max_len=10)   # 'a-very'
unslugify("hello-world")                 # 'Hello World'
```

## API

- `slugify(text, sep="-", max_len=None)`: accents are folded to ASCII and characters with no ASCII form are dropped;
  every run of other characters becomes one `sep`; `sep` is trimmed from both ends. With `max_len`, the slug is cut
  to that length and a trailing `sep` removed.
- `unslugify(slug, sep="-")`: replaces `sep` with spaces and title-cases the result. It is lossy: it cannot restore
  punctuation or the original case.
