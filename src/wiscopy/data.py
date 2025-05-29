"""
This module provides functions for fetching data from the Wisconet API.

It includes utilities for retrieving station information, available data fields,
and observational data, with support for both synchronous and asynchronous
operations, and automatic parsing into Pydantic models or pandas DataFrames.
"""
import httpx
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from wiscopy.schema import (
       BASE_URL, Station, Field, BulkMeasures, 
)
from wiscopy.process import (
    multiple_bulk_measures_to_df
)


def all_stations() -> list[Station]:
    """Retrieves a list of all current Wisconet stations.

    Returns:
        list[Station]: A list of Pydantic `Station` model objects, each representing a station.
    """
    route = "/stations/"
    stations = []
    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get(route)
        response.raise_for_status()
    
    for station in response.json():
        station_tz = station.pop("station_timezone")
        earliest_api_date = datetime.strptime(station.pop("earliest_api_date"), "%m/%d/%Y")
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
    """Retrieves the available measurement fields for a specific station.

    Args:
        station_id (str): The unique identifier for the station (e.g., "ALTN").

    Returns:
        list[Field]: A list of Pydantic `Field` model objects, each describing an available data field.
    """
    route = f"/fields/{station_id}/available_fields"
    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get(route)
        response.raise_for_status()
    return [Field(**field) for field in response.json()]


def datetime_at_station_in_utc(station: Station, dt: datetime | str) -> datetime:
    """Converts a datetime object or ISO-format string to UTC, based on the station's local timezone.

    Args:
        station (Station): The Pydantic `Station` model object, used to determine the local timezone.
        dt (datetime | str): The datetime object or ISO-format string (e.g., "2021-01-01T00:00:00")
            to be converted. This input is assumed to be in the station's local time.

    Returns:
        datetime: A datetime object representing the input time in UTC.
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    return (
        dt
        .replace(tzinfo=ZoneInfo(station.station_timezone))
        .astimezone(timezone.utc)
    )
    

def bulk_measures(
    station_id: str,
    start_time: datetime,
    end_time: datetime,
    fields: list[str] | None = None,
    timeout: float = 30.0
) -> BulkMeasures:
    """Fetches bulk measurement data for a station between two specified UTC datetimes.

    Args:
        station_id (str): The unique identifier for the station (e.g., `Station.station_id`, "ALTN").
        start_time (datetime): The start datetime for the data query, in UTC.
        end_time (datetime): The end datetime for the data query, in UTC.
        fields (list[str], optional): A list of field standard names to retrieve.
            If None, all available fields for the station are returned. Defaults to None.
        timeout (float, optional): The HTTP request timeout in seconds. Defaults to 30.0.

    Returns:
        BulkMeasures: A Pydantic `BulkMeasures` object containing the field list and data.
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
    with httpx.Client(base_url=BASE_URL, timeout=timeout) as client:
        response = client.get(route, params=params)
        response.raise_for_status()
    return BulkMeasures(**response.json())


async def async_bulk_measures(
    station_id: str,
    start_time: datetime,
    end_time: datetime,
    client: httpx.AsyncClient,
    fields: list[str] | None = None
) -> BulkMeasures:
    """Asynchronously fetches bulk measurement data for a station using a provided HTTP client.

    Args:
        station_id (str): The unique identifier for the station (e.g., `Station.station_id`, "ALTN").
        start_time (datetime): The start datetime for the data query, in UTC.
        end_time (datetime): The end datetime for the data query, in UTC.
        client (httpx.AsyncClient): An active `httpx.AsyncClient` instance to use for the request.
        fields (list[str], optional): A list of field standard names to retrieve.
            If None, all available fields for the station are returned. Defaults to None.

    Returns:
        BulkMeasures: A Pydantic `BulkMeasures` object containing the field list and data.
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
    fields: list[str] | None = None
) -> list[BulkMeasures]:
    """Asynchronously fetches data in chunks for a station and gathers the results.

    Splits the total time range into smaller chunks defined by `chunk_days`
    and fetches them concurrently using the provided HTTP client.

    Args:
        station_id (str): The station identifier (e.g., `Station.station_id`, "ALTN").
        start_time (datetime): The overall start datetime for the data query, in UTC.
        end_time (datetime): The overall end datetime for the data query, in UTC.
        chunk_days (int): The number of days to include in each asynchronous data fetching chunk.
        client (httpx.AsyncClient): An active `httpx.AsyncClient` instance.
        fields (list[str], optional): Field standard names to retrieve. Defaults to None (all fields).

    Returns:
        list[BulkMeasures]: A list of `BulkMeasures` objects, one for each successfully fetched chunk.
    """
    total_time_delta = end_time - start_time
    task_start_and_end_dts = [
        (
            start_time + timedelta(days=i*chunk_days), 
            start_time + timedelta(days=(i+1)*chunk_days) if start_time + timedelta(days=(i+1)*chunk_days) < end_time else end_time
        )
        for i in range(0, total_time_delta.days // chunk_days + 1)
        if start_time + timedelta(days=i*chunk_days) < end_time
    ]
    return await asyncio.gather(
        *[async_bulk_measures(
                station_id=station_id, 
                start_time=start_time, 
                end_time=end_time, 
                client=client, 
                fields=fields, 
            ) 
          for start_time, end_time in task_start_and_end_dts]
    )


def bulk_fetch(
    station: Station,
    start_time: datetime,
    end_time: datetime,
    fields: list[str] | None = None,
    duration_days: int = 30,
    timeout: float = 60.0,
    limits: httpx.Limits | None = None
) -> pd.DataFrame | None:
    """Fetches a large volume of data for a station by chunking requests asynchronously.

    This function is suitable for retrieving data over extended periods. Times are
    interpreted as local to the station.

    Args:
        station (Station): The Pydantic `Station` model object for which to fetch data.
        start_time (datetime): The start datetime for the data query (station local time).
        end_time (datetime): The end datetime for the data query (station local time).
        fields (list[str], optional): Field standard names to retrieve. Defaults to None (all fields).
        duration_days (int, optional): Number of days per asynchronous chunk. Defaults to 30.
        timeout (float, optional): HTTP request timeout for each chunk. Defaults to 60.0.
        limits (httpx.Limits, optional): `httpx.Limits` for the `AsyncClient`.
            Defaults to 5 max keepalive connections and 5 max connections.

    Returns:
        pd.DataFrame | None: A pandas DataFrame containing the data, with a DatetimeIndex
        localized to the station's timezone. Returns None if no data is found.
    """
    start_time_utc = datetime_at_station_in_utc(station=station, dt=start_time)
    end_time_utc = datetime_at_station_in_utc(station=station, dt=end_time)
    if not limits:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=5)
    client = httpx.AsyncClient(base_url=BASE_URL, timeout=timeout, limits=limits)
    bulk_measures = asyncio.run(
        gather_async_bulk_measure_data(
            station_id=station.station_id,
            start_time=start_time_utc,
            end_time=end_time_utc,
            chunk_days=duration_days,
            client=client,
            fields=fields,
        )
    )
    return multiple_bulk_measures_to_df(bulk_measures, tz=station.station_timezone, station_id=station.station_id)


def all_data_for_station(
    station: Station,
    fields: list[str] | None = None,
    duration_days: int = 30,
    timeout: float = 60.0,
    limits: httpx.Limits | None = None
) -> pd.DataFrame | None:
    """Fetches all available historical data for a given station.

    Retrieves data from the station's `earliest_api_date` up to the current time.
    Uses `bulk_fetch` internally for efficient chunked downloading.

    Args:
        station (Station): The Pydantic `Station` model object.
        fields (list[str], optional): Field standard names to retrieve. Defaults to None (all fields).
        duration_days (int, optional): Number of days per asynchronous chunk. Defaults to 30.
        timeout (float, optional): HTTP request timeout for each chunk. Defaults to 60.0.
        limits (httpx.Limits, optional): `httpx.Limits` for the `AsyncClient`.
            Defaults to 5 max keepalive connections and 5 max connections.

    Returns:
        pd.DataFrame | None: A pandas DataFrame with all available data, localized to the
        station's timezone. Returns None if no data is found.
    """

    start_time=datetime_at_station_in_utc(station=station, dt=station.earliest_api_date)
    end_time=datetime_at_station_in_utc(station=station, dt=datetime.now())
    return bulk_fetch(
        station=station,
        start_time=start_time,
        end_time=end_time,
        fields=fields,
        duration_days=duration_days,
        timeout=timeout,
        limits=limits
    )


def fetch_data_multiple_stations(
    stations: list[Station],
    start_time: datetime | str,
    end_time: datetime | str,
    fields: list[str],
    limits: httpx.Limits | None = None,
    duration_days: int = 30,
) -> pd.DataFrame | None:
    """Fetches data from multiple stations for a specified time range.

    Times are interpreted as local to each respective station. Data is fetched
    concurrently for each station using `bulk_fetch`.

    Args:
        stations (list[Station]): A list of Pydantic `Station` model objects.
        start_time (datetime | str): The start datetime or ISO-format string for the query
            (interpreted as local time for each station).
        end_time (datetime | str): The end datetime or ISO-format string for the query
            (interpreted as local time for each station).
        fields (list[str]): A list of field standard names to retrieve.
        limits (httpx.Limits, optional): `httpx.Limits` for underlying `AsyncClient`s.
            Defaults to 5 max keepalive connections and 5 max connections.
        duration_days (int, optional): Number of days per asynchronous chunk for each station.
            Defaults to 30.

    Returns:
        pd.DataFrame | None: A concatenated pandas DataFrame containing data from all stations
        that returned data. Timestamps are localized to each station's timezone.
        Returns None if no data is found for any of the stations.
    """
    if not limits:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=5)
    
    station_dfs = []
    for station in stations:
        station_df = bulk_fetch(
            station=station,
            start_time=start_time,
            end_time=end_time,
            fields=fields,
            duration_days=duration_days,
            timeout=60.0,
            limits=limits,
        )
        if station_df is not None:
            station_dfs.append(station_df)
    
    return pd.concat(station_dfs) if station_dfs else None