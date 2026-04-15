# Change Log

## v0.2.0
### added
1. Respects rate limiting by default (20 calls per 20 second period) configurable by environment vars: `WISCONET_RATE_LIMIT_CALLS` (int), `WISCONET_LIMIT_PERIOD` (float: seconds)
2. Retry on HTTP 429, and respect any `Retry-After`. Manages any additional API rate limiting with exponential back off.
3. Wisconet.get_data() now reports progress per station with tqdm.auto progress bar
4. now able to run in notebook without `nest_asyncio`
3. now supports `osx-arm64` platform
4. defined new `ci-test` pixi feature and `clean-room` pixi environment for ```pixi run -e clean-room test-wheel``` to build and test package in clean environment locally
5. code now `ruff` formatted and linted
6. additional dev install instructions in `README.md`
7. `CHANGELOG.md`


### fixed
1. resolved bug where getting all fields for a station required a response from the API {station}/fields route. Now falls back to API /fields route, and if that fails, uses a locally cached fields list.

### removed
1. `notebook` environment