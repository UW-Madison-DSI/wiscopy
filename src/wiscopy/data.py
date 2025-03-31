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
    """
    Get all current Wisconet stations.
    :return: list of Station objects
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
    """
    Get the Field objects available for a station.
    :param station_id: station_id e.g "ALTN".
    :return: list of Field objects
    """
    route = f"/fields/{station_id}/available_fields"
    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get(route)
        response.raise_for_status()
    return [Field(**field) for field in response.json()]


def datetime_at_station_in_utc(station: Station, dt: datetime) -> datetime:
    """
    Convert a datetime to UTC based on the station's timezone.
    :param station: Station object.
    :param dt: datetime to convert.
    :return: datetime in UTC.
    """
    return (
        dt
        .replace(tzinfo=ZoneInfo(station.station_timezone))
        .astimezone(timezone.utc)
    )
    

def bulk_measures(station_id: str, start_time: datetime, end_time: datetime, fields: list[str] | None = None, timeout: float = 30.0) -> BulkMeasures:
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
    with httpx.Client(base_url=BASE_URL, timeout=timeout) as client:
        response = client.get(route, params=params)
        response.raise_for_status()
    return BulkMeasures(**response.json())


async def async_bulk_measures(
        station_id: str, start_time: datetime, end_time: datetime, client: httpx.AsyncClient, fields: list[str] | None = None) -> BulkMeasures:
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
    
    response = await client.get(route, params=params)
    response.raise_for_status()
    return BulkMeasures(**response.json())


async def gather_async_bulk_measure_data(station_id: str, start_time: datetime, end_time: datetime, duration_days: int, client: httpx.AsyncClient, fields: list[str] | None = None) -> list[BulkMeasures]:
    """
    Get measures for a station between two times.
    :param station_id: Station.station_id e.g "ALTN"
    :param start_time: datetime, fetch start time in UTC.
    :param end_time: datetime fetch end time in UTC
    :param duration_days: int, number of days to fetch data for in each async task.
    :param fields: optional list of Field.standard_name strings of fields to return. If not specified, returns all fields.
    :param timeout: float, httpx timeout.
    :return: BulkMeasures object
    """
    total_time_delta = end_time - start_time
    task_start_and_end_dts = [
        (
            start_time + timedelta(days=i*duration_days), 
            start_time + timedelta(days=(i+1)*duration_days) if start_time + timedelta(days=(i+1)*duration_days) < end_time else end_time
        )
        for i in range(0, total_time_delta.days // duration_days + 1)
        if start_time + timedelta(days=i*duration_days) < end_time
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


def bulk_fetch(station: Station, start_time: datetime, end_time: datetime, fields: list[str] | None = None, duration_days=30, timeout=60.0, limits: httpx.Limits | None = None) -> pd.DataFrame | None:
    """
    Get data for a Station, uses async requests to fetch data in chunks, use this to fetch large amounts of data.
    :param s: Station object.
    :param fields: optional list of Field.standard_name strings of fields to return. If not specified, returns all fields.
    :param timeout: float, httpx timeout.
    :param limits: optional httpx.Limits object for AsyncClient if None defaults to 5 max_keepalive_connections and 5 max_connections
    :return: BulkMeasures object.
    """
    if not limits:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=5)
    client = httpx.AsyncClient(base_url=BASE_URL, timeout=timeout, limits=limits)
    bulk_measures = asyncio.run(
        gather_async_bulk_measure_data(
            station_id=station.station_id,
            start_time=start_time,
            end_time=end_time,
            duration_days=duration_days,
            client=client,
            fields=fields,
        )
    )
    return multiple_bulk_measures_to_df(bulk_measures, tz=station.station_timezone, station_id=station.station_id)


def all_data_for_station(s: Station, fields: list[str] | None = None, duration_days=30, timeout=60.0, limits: httpx.Limits | None = None) -> pd.DataFrame | None:
    """
    Get all available data for a Station.
    :param s: Station object.
    :param fields: optional list of Field.standard_name strings of fields to return. If not specified, returns all fields.
    :param timeout: float, httpx timeout.
    :param limits: optional httpx.Limits object for AsyncClient if None defaults to 5 max_keepalive_connections and 5 max_connections
    :return: BulkMeasures object.
    """

    start_time=datetime_at_station_in_utc(station=s, dt=s.earliest_api_date)
    end_time=datetime_at_station_in_utc(station=s, dt=datetime.now())
    return bulk_fetch(
        station=s, 
        start_time=start_time, 
        end_time=end_time, 
        fields=fields, 
        duration_days=duration_days, 
        timeout=timeout, 
        limits=limits
    )


def fetch_data_multiple_stations(
    stations: list[Station],
    start_time: datetime,
    end_time: datetime,
    fields: list[str],
    limits: httpx.Limits | None = None,
    duration_days: int = 30,
) -> pd.DataFrame:
    """
    Get data from multiple stations.
    :param station_ids: list of station_ids e.g ["ALTN", "ALTN2"]
    :param start_time: datetime, fetch start time in local station time.
    :param end_time: datetime fetch end time in local station time."
    :param fields: list of Field.standard_name strings of fields to return.
    :param limits: optional httpx.Limits object for AsyncClient if None defaults to 5 max_keepalive_connections and 5 max_connections
    :param duration_days: int, number of days to fetch data for in each async task.
    :return: pd.DataFrame or None if no data.
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