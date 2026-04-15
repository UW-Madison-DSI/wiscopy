import os
import json
import time
import httpx
import logging
import asyncio
import concurrent.futures
import pandas as pd
from tqdm.auto import tqdm
from datetime import datetime, timezone, timedelta
from importlib import resources
from zoneinfo import ZoneInfo
from aiolimiter import AsyncLimiter

from wiscopy.schema import (
    BASE_URL,
    Station,
    Field,
    BulkMeasures,
)
from wiscopy.process import multiple_bulk_measures_to_df

RATE_LIMIT_CALLS = os.environ.get("WISCONET_RATE_LIMIT_CALLS", 20)
RATE_LIMIT_PERIOD = os.environ.get("WISCONET_LIMIT_PERIOD", 20.0)


logger = logging.getLogger(__name__)


def get_cached_fields() -> list[dict[str, int | str]]:
    """Load local cached fields JSON as dict"""
    with (
        resources.files("wiscopy.static").joinpath("cached_fields.json").open("r") as f
    ):
        return json.load(f)


class RetryTransport(httpx.BaseTransport):
    """Sync transport that retries on 429 with Retry-After or exponential backoff."""

    def __init__(self, max_retries: int = 3) -> None:
        self._transport = httpx.HTTPTransport()
        self._max_retries = max_retries

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            response = self._transport.handle_request(request)
            if response.status_code != 429 or attempt == self._max_retries:
                return response
            response.close()
            retry_after = float(response.headers.get("Retry-After", 2**attempt))
            time.sleep(retry_after)

    def close(self) -> None:
        self._transport.close()


class RateLimitedRetryTransport(httpx.AsyncBaseTransport):
    """Async transport that rate-limits requests and retries on 429."""

    def __init__(
        self,
        limits: httpx.Limits | None = None,
        max_retries: int = 3,
    ) -> None:
        limits = limits or httpx.Limits(max_keepalive_connections=5, max_connections=5)
        self._transport = httpx.AsyncHTTPTransport(limits=limits)
        self._limiter = AsyncLimiter(RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD)
        self._max_retries = max_retries

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            async with self._limiter:
                response = await self._transport.handle_async_request(request)
            if response.status_code != 429 or attempt == self._max_retries:
                return response
            await response.aclose()
            retry_after = float(response.headers.get("Retry-After", 2**attempt))
            await asyncio.sleep(retry_after)

    async def aclose(self) -> None:
        await self._transport.aclose()


def all_stations() -> list[Station]:
    """
    Get all current Wisconet stations.
    :return: list of Station objects
    """
    route = "/stations/"
    stations = []
    with httpx.Client(base_url=BASE_URL, transport=RetryTransport()) as client:
        response = client.get(route)
        response.raise_for_status()

    for station in response.json():
        station_tz = station.pop("station_timezone")
        earliest_api_date = datetime.strptime(
            station.pop("earliest_api_date"), "%m/%d/%Y"
        )
        elevation = float(station.pop("elevation"))
        latitude = float(station.pop("latitude"))
        longitude = float(station.pop("longitude"))
        stations.append(
            Station(
                station_timezone=station_tz,
                earliest_api_date=earliest_api_date,
                elevation=elevation,
                latitude=latitude,
                longitude=longitude,
                **station,
            )
        )
    return stations


def station_fields(station_id: str) -> list[Field]:
    """
    Get the Field objects available for a station.
    :param station_id: station_id e.g "ALTN".
    :return: list of Field objects
    """
    route = f"/fields/{station_id}/available_fields"
    with httpx.Client(base_url=BASE_URL, transport=RetryTransport()) as client:
        response = client.get(route)

    if response.status_code != 200:
        logger.warning(
            f"{BASE_URL}{route} returned HTTP {response.status_code}, defaulting to all fields"
        )
        route = "https://wisconet.wisc.edu/api/v1/fields/"
        with httpx.Client(base_url=BASE_URL, transport=RetryTransport()) as client:
            response = client.get(route)

    if response.status_code != 200:
        logger.warning(
            f"{BASE_URL}{route} returned HTTP {response.status_code}, defaulting to all cached fields"
        )
        response_json = get_cached_fields()
        return [Field(**field) for field in response_json]

    return [Field(**field) for field in response.json()]


def datetime_at_station_in_utc(station: Station, dt: datetime | str) -> datetime:
    """
    Convert a datetime to UTC based on the station's timezone.
    :param station: Station object.
    :param dt: datetime or iso-format datetime string to convert e.g. "2021-01-01T00:00:00"
    :return: datetime in UTC.
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    return dt.replace(tzinfo=ZoneInfo(station.station_timezone)).astimezone(
        timezone.utc
    )


def bulk_measures(
    station_id: str,
    start_time: datetime,
    end_time: datetime,
    fields: list[str] | None = None,
    timeout: float = 30.0,
) -> BulkMeasures:
    """
    Get measures for a station between two times.
    :param station_id: Station.station_id e.g "ALTN".
    :param start_time: datetime, fetch start time in UTC.
    :param end_time: datetime fetch end time in UTC
    :param fields: optional list of Field.standard_name strings of fields to return. If not specified, returns all fields.
    :param timeout: float, httpx timeout.
    :return: BulkMeasures object
    """
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())
    route = f"/stations/{station_id}/measures"
    params = {
        "start_time": start_time_epoch,
        "end_time": end_time_epoch,
    }
    if fields:
        params["fields"] = ",".join(fields)
    with httpx.Client(
        base_url=BASE_URL, timeout=timeout, transport=RetryTransport()
    ) as client:
        response = client.get(route, params=params)
        response.raise_for_status()
    return BulkMeasures(**response.json())


async def async_bulk_measures(
    station_id: str,
    start_time: datetime,
    end_time: datetime,
    client: httpx.AsyncClient,
    fields: list[str] | None = None,
) -> BulkMeasures:
    """
    Get measures for a station between two times.
    :param station_id: Station.station_id e.g "ALTN".
    :param start_time: datetime, fetch start time in UTC.
    :param end_time: datetime fetch end time in UTC
    :param fields: optional list of Field.standard_name strings of fields to return. If not specified, returns all fields.
    :return: BulkMeasures object
    """
    start_time_epoch = int(start_time.timestamp())
    end_time_epoch = int(end_time.timestamp())
    route = f"/stations/{station_id}/measures"
    params = {
        "start_time": start_time_epoch,
        "end_time": end_time_epoch,
    }
    if fields:
        params["fields"] = ",".join(fields)

    response = await client.get(route, params=params)
    response.raise_for_status()
    return BulkMeasures(**response.json())


async def gather_async_bulk_measure_data(
    station_id: str,
    start_time: datetime,
    end_time: datetime,
    chunk_days: int,
    client: httpx.AsyncClient,
    fields: list[str] | None = None,
) -> list[BulkMeasures]:
    """
    Async fetch measures for a station between two times by splitting a measures request into chunks, and async fetching all the chunks simultaneously.
    :param station_id: Station.station_id e.g "ALTN"
    :param start_time: datetime, fetch start time in UTC.
    :param end_time: datetime fetch end time in UTC
    :param chunk_days: int, number of days to fetch data for in each async task/chunk.
    :param fields: optional list of Field.standard_name strings of fields to return. If not specified, returns all fields.
    :return: list of BulkMeasures objects
    """
    total_time_delta = end_time - start_time
    task_start_and_end_dts = [
        (
            start_time + timedelta(days=i * chunk_days),
            start_time + timedelta(days=(i + 1) * chunk_days)
            if start_time + timedelta(days=(i + 1) * chunk_days) < end_time
            else end_time,
        )
        for i in range(0, total_time_delta.days // chunk_days + 1)
        if start_time + timedelta(days=i * chunk_days) < end_time
    ]
    return await asyncio.gather(
        *[
            async_bulk_measures(
                station_id=station_id,
                start_time=start_time,
                end_time=end_time,
                client=client,
                fields=fields,
            )
            for start_time, end_time in task_start_and_end_dts
        ]
    )


async def _fetch_chunks(
    station_id: str,
    start_time_utc: datetime,
    end_time_utc: datetime,
    chunk_days: int,
    fields: list[str] | None,
    timeout: float,
    limits: httpx.Limits | None,
) -> list[BulkMeasures]:
    transport = RateLimitedRetryTransport(limits=limits)
    client = httpx.AsyncClient(base_url=BASE_URL, timeout=timeout, transport=transport)
    return await gather_async_bulk_measure_data(
        station_id=station_id,
        start_time=start_time_utc,
        end_time=end_time_utc,
        chunk_days=chunk_days,
        client=client,
        fields=fields,
    )


def bulk_fetch(
    station: Station,
    start_time: datetime,
    end_time: datetime,
    fields: list[str] | None = None,
    duration_days=30,
    timeout=60.0,
    limits: httpx.Limits | None = None,
) -> pd.DataFrame | None:
    """
    Get data for a Station, uses async requests to fetch data in chunks, use this to fetch large amounts of data.
    :param station: Station object.
    :param fields: optional list of Field.standard_name strings of fields to return. If not specified, returns all fields.
    :param timeout: float, httpx timeout.
    :param limits: optional httpx.Limits object; defaults to 5 max_keepalive_connections and 5 max_connections.
    :return: DataFrame or None.
    """
    start_time_utc = datetime_at_station_in_utc(station=station, dt=start_time)
    end_time_utc = datetime_at_station_in_utc(station=station, dt=end_time)

    def _run():
        # Use new_event_loop + run_until_complete instead of asyncio.run() to bypass
        # nest_asyncio's global patch, which reroutes asyncio.run() back to the outer
        # notebook loop and causes sniffio/anyio failures.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                _fetch_chunks(
                    station.station_id,
                    start_time_utc,
                    end_time_utc,
                    duration_days,
                    fields,
                    timeout,
                    limits,
                )
            )
        finally:
            loop.close()

    try:
        asyncio.get_running_loop()
        # Inside a running event loop (e.g. Jupyter): run in a thread with its own
        # fresh event loop to avoid nest_asyncio/anyio CancelScope conflicts.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            bulk_measures_list = pool.submit(_run).result()
    except RuntimeError:
        bulk_measures_list = asyncio.run(
            _fetch_chunks(
                station.station_id,
                start_time_utc,
                end_time_utc,
                duration_days,
                fields,
                timeout,
                limits,
            )
        )
    return multiple_bulk_measures_to_df(
        bulk_measures_list, tz=station.station_timezone, station_id=station.station_id
    )


def all_data_for_station(
    s: Station,
    fields: list[str] | None = None,
    duration_days=30,
    timeout=60.0,
    limits: httpx.Limits | None = None,
) -> pd.DataFrame | None:
    """
    Get all available data for a Station.
    :param s: Station object.
    :param fields: optional list of Field.standard_name strings of fields to return. If not specified, returns all fields.
    :param timeout: float, httpx timeout.
    :param limits: optional httpx.Limits object; defaults to 5 max_keepalive_connections and 5 max_connections.
    :return: DataFrame or None.
    """
    start_time = datetime_at_station_in_utc(station=s, dt=s.earliest_api_date)
    end_time = datetime_at_station_in_utc(station=s, dt=datetime.now())
    return bulk_fetch(
        station=s,
        start_time=start_time,
        end_time=end_time,
        fields=fields,
        duration_days=duration_days,
        timeout=timeout,
        limits=limits,
    )


def fetch_data_multiple_stations(
    stations: list[Station],
    start_time: datetime | str,
    end_time: datetime | str,
    fields: list[str],
    limits: httpx.Limits | None = None,
    duration_days: int = 30,
    timeout: float = 60.0,
) -> pd.DataFrame:
    """
    Get data from multiple stations.
    :param stations: list of Station objects.
    :param start_time: datetime, fetch start time in local station time.
    :param end_time: datetime fetch end time in local station time.
    :param fields: list of Field.standard_name strings of fields to return.
    :param limits: optional httpx.Limits object; defaults to 5 max_keepalive_connections and 5 max_connections.
    :param duration_days: int, number of days to fetch data for in each async task.
    :return: pd.DataFrame or None if no data.
    """
    station_dfs = []
    for station in tqdm(stations, desc="Fetching data", unit="station"):
        station_df = bulk_fetch(
            station=station,
            start_time=start_time,
            end_time=end_time,
            fields=fields,
            duration_days=duration_days,
            timeout=timeout,
            limits=limits,
        )
        if station_df is not None:
            station_dfs.append(station_df)

    return pd.concat(station_dfs) if station_dfs else None
