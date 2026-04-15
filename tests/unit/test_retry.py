import asyncio
import pytest
import httpx
from aiolimiter import AsyncLimiter
from unittest.mock import AsyncMock, MagicMock, patch

from wiscopy.data import RetryTransport, RateLimitedRetryTransport


def mock_response(status_code: int, headers: dict | None = None) -> MagicMock:
    """Create a minimal mock transport-level response."""
    resp = MagicMock()
    resp.status_code = status_code
    _headers = headers or {}
    resp.headers.get = lambda key, default=None: _headers.get(key, default)
    resp.aclose = AsyncMock()
    resp.close = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def make_transport(cls, inner_mock, **kwargs):
    """Instantiate a transport class with a mocked inner transport."""
    t = cls.__new__(cls)
    t._transport = inner_mock
    t._max_retries = kwargs.get("max_retries", 3)
    if cls is RateLimitedRetryTransport:
        t._limiter = AsyncLimiter(20, 20)
    return t


# --- RateLimitedRetryTransport (async) ---


@pytest.mark.asyncio
async def test_async_transport_retries_on_429_respects_retry_after():
    inner = MagicMock()
    inner.handle_async_request = AsyncMock(
        side_effect=[
            mock_response(429, {"Retry-After": "0"}),
            mock_response(200),
        ]
    )
    transport = make_transport(RateLimitedRetryTransport, inner)
    request = httpx.Request("GET", "https://example.com/")

    with patch("asyncio.sleep") as mock_sleep:
        response = await transport.handle_async_request(request)

    assert response.status_code == 200
    assert inner.handle_async_request.call_count == 2
    mock_sleep.assert_called_once_with(0.0)


@pytest.mark.asyncio
async def test_async_transport_retry_uses_exponential_backoff():
    """Without Retry-After, backoff is 2**attempt (1 on first retry)."""
    inner = MagicMock()
    inner.handle_async_request = AsyncMock(
        side_effect=[
            mock_response(429),  # no Retry-After
            mock_response(200),
        ]
    )
    transport = make_transport(RateLimitedRetryTransport, inner)
    request = httpx.Request("GET", "https://example.com/")

    with patch("asyncio.sleep") as mock_sleep:
        await transport.handle_async_request(request)

    mock_sleep.assert_called_once_with(1.0)  # 2**0 = 1


@pytest.mark.asyncio
async def test_async_transport_raises_after_max_retries():
    inner = MagicMock()
    inner.handle_async_request = AsyncMock(return_value=mock_response(429))
    transport = make_transport(RateLimitedRetryTransport, inner, max_retries=2)
    request = httpx.Request("GET", "https://example.com/")

    with patch("asyncio.sleep"):
        response = await transport.handle_async_request(request)

    # Exhausted retries: returns the last 429 response for the caller to raise_for_status
    assert response.status_code == 429
    assert inner.handle_async_request.call_count == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_async_transport_closes_429_response_before_retry():
    """Connection must be released (aclose) before each retry."""
    resp_429 = mock_response(429, {"Retry-After": "0"})
    inner = MagicMock()
    inner.handle_async_request = AsyncMock(side_effect=[resp_429, mock_response(200)])
    transport = make_transport(RateLimitedRetryTransport, inner)
    request = httpx.Request("GET", "https://example.com/")

    with patch("asyncio.sleep"):
        await transport.handle_async_request(request)

    resp_429.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_transport_non_429_returned_immediately():
    """500 errors are returned without retry so the caller can raise_for_status."""
    inner = MagicMock()
    inner.handle_async_request = AsyncMock(return_value=mock_response(500))
    transport = make_transport(RateLimitedRetryTransport, inner)
    request = httpx.Request("GET", "https://example.com/")

    response = await transport.handle_async_request(request)

    assert response.status_code == 500
    assert inner.handle_async_request.call_count == 1


# --- RetryTransport (sync) ---


def test_sync_transport_retries_on_429_respects_retry_after():
    inner = MagicMock()
    inner.handle_request.side_effect = [
        mock_response(429, {"Retry-After": "0"}),
        mock_response(200),
    ]
    transport = make_transport(RetryTransport, inner)
    request = httpx.Request("GET", "https://example.com/")

    with patch("time.sleep") as mock_sleep:
        response = transport.handle_request(request)

    assert response.status_code == 200
    assert inner.handle_request.call_count == 2
    mock_sleep.assert_called_once_with(0.0)


def test_sync_transport_raises_after_max_retries():
    inner = MagicMock()
    inner.handle_request.return_value = mock_response(429)
    transport = make_transport(RetryTransport, inner, max_retries=2)
    request = httpx.Request("GET", "https://example.com/")

    with patch("time.sleep"):
        response = transport.handle_request(request)

    assert response.status_code == 429
    assert inner.handle_request.call_count == 3  # initial + 2 retries


def test_sync_transport_closes_429_response_before_retry():
    resp_429 = mock_response(429, {"Retry-After": "0"})
    inner = MagicMock()
    inner.handle_request.side_effect = [resp_429, mock_response(200)]
    transport = make_transport(RetryTransport, inner)
    request = httpx.Request("GET", "https://example.com/")

    with patch("time.sleep"):
        transport.handle_request(request)

    resp_429.close.assert_called_once()


def test_sync_transport_non_429_returned_immediately():
    inner = MagicMock()
    inner.handle_request.return_value = mock_response(500)
    transport = make_transport(RetryTransport, inner)
    request = httpx.Request("GET", "https://example.com/")

    response = transport.handle_request(request)

    assert response.status_code == 500
    assert inner.handle_request.call_count == 1


# --- Rate limiting enforcement ---


@pytest.mark.asyncio
async def test_rate_limiter_enforces_max_calls_per_period():
    """No more than max_calls requests should execute within any period-second window."""
    max_calls = 3
    period = 0.2
    n_requests = 7

    loop = asyncio.get_running_loop()
    timestamps: list[float] = []

    inner = MagicMock()

    async def record_and_respond(request):
        timestamps.append(loop.time())
        return mock_response(200)

    inner.handle_async_request = record_and_respond

    transport = RateLimitedRetryTransport.__new__(RateLimitedRetryTransport)
    transport._transport = inner
    transport._max_retries = 0
    transport._limiter = AsyncLimiter(max_calls, period)

    request = httpx.Request("GET", "https://example.com/")
    await asyncio.gather(
        *[transport.handle_async_request(request) for _ in range(n_requests)]
    )

    assert len(timestamps) == n_requests
    # AsyncLimiter (leaky bucket) allows an initial burst of max_calls requests before
    # throttling. After the burst, each additional request waits period/max_calls.
    # Check that the total span from first to last timestamp reflects the throttled tail.
    token_interval = period / max_calls
    min_total_span = (n_requests - max_calls) * token_interval
    actual_span = max(timestamps) - min(timestamps)
    assert actual_span >= min_total_span * 0.9, (
        f"Expected span >= {min_total_span:.3f}s for throttled tail, got {actual_span:.3f}s"
    )


@pytest.mark.asyncio
async def test_rate_limiter_delays_requests_over_limit():
    """Requests beyond max_calls must wait at least one token interval (period/max_calls)."""
    max_calls = 2
    period = 0.3
    # Fire max_calls + 1 concurrently: the extra request must be deferred
    n_requests = max_calls + 1

    loop = asyncio.get_running_loop()
    timestamps: list[float] = []

    inner = MagicMock()

    async def record_and_respond(request):
        timestamps.append(loop.time())
        return mock_response(200)

    inner.handle_async_request = record_and_respond

    transport = RateLimitedRetryTransport.__new__(RateLimitedRetryTransport)
    transport._transport = inner
    transport._max_retries = 0
    transport._limiter = AsyncLimiter(max_calls, period)

    request = httpx.Request("GET", "https://example.com/")
    t0 = loop.time()
    await asyncio.gather(
        *[transport.handle_async_request(request) for _ in range(n_requests)]
    )
    elapsed = loop.time() - t0

    # AsyncLimiter (leaky bucket) fires the first max_calls requests as a burst, then
    # throttles at period/max_calls per request. The (max_calls+1)th request waits
    # one token interval (period/max_calls), not a full period.
    token_interval = period / max_calls
    assert elapsed >= token_interval * 0.9, (
        f"Expected at least {token_interval:.2f}s elapsed for {n_requests} requests "
        f"at {max_calls}/{period}s limit, got {elapsed:.3f}s"
    )


@pytest.mark.asyncio
async def test_env_vars_configure_rate_limit(monkeypatch):
    """RATE_LIMIT_CALLS/PERIOD module constants (sourced from env vars) are picked up
    by RateLimitedRetryTransport.__init__ and the new rate is actually enforced."""
    # --- Assemble ---
    import wiscopy.data as data_module

    new_calls = 2
    new_period = 0.4
    monkeypatch.setattr(data_module, "RATE_LIMIT_CALLS", new_calls)
    monkeypatch.setattr(data_module, "RATE_LIMIT_PERIOD", new_period)

    loop = asyncio.get_running_loop()

    inner = MagicMock()

    async def record_and_respond(_request):
        return mock_response(200)

    inner.handle_async_request = record_and_respond

    transport = RateLimitedRetryTransport()
    transport._transport = inner
    transport._max_retries = 0

    request = httpx.Request("GET", "https://example.com/")
    n_requests = new_calls + 1  # one beyond the burst limit

    # --- Act ---
    t0 = loop.time()
    await asyncio.gather(
        *[transport.handle_async_request(request) for _ in range(n_requests)]
    )
    elapsed = loop.time() - t0

    # --- Assert ---
    assert transport._limiter.max_rate == new_calls
    assert transport._limiter.time_period == new_period
    token_interval = new_period / new_calls
    assert elapsed >= token_interval * 0.9, (
        f"Expected >= {token_interval:.3f}s for {n_requests} requests at "
        f"{new_calls}/{new_period}s; got {elapsed:.3f}s"
    )
