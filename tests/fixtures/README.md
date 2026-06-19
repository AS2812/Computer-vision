# Test fixtures

Unit tests generate deterministic RGB fixtures in memory so the repository does not
need to carry large binary images. Real field-photo smoke fixtures should be added only
with documented licensing and must remain outside the training split.

Run `uv run --project services/api python tests/fixtures/generate_test_images.py` to
create `healthy_synthetic_field.png`. It is intentionally synthetic and tests the real
RGB vegetation-index, bounded tiling, and plant-cluster counting code. It does not
validate disease diagnosis or the experimental agronomy features.

`banana_cordana_public_domain.jpg` is the user's supplied test image, retrieved from its
[public-domain Flickr source](https://www.flickr.com/photos/scotnelson/5680832197).
Its SHA-256 is `f23c9e341f12fa9863c006e1d01f4ae98bd1ecd483142855239c95c481c57d1f`.
The source labels it Cordana leaf spot. It is a real-model functional smoke test, but it
is also duplicated in the model source repository and therefore is not an independent
accuracy benchmark.
