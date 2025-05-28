import httpx
from math import (pi, sin, cos, sqrt, atan2)
import pandas as pd
from datetime import datetime

from wiscopy.schema import Station, Field
from wiscopy.data import (
    all_stations,
    datetime_at_station_in_utc,
    station_fields,
    bulk_measures,
    all_data_for_station,
    fetch_data_multiple_stations,
)
from wiscopy.process import (
    bulk_measures_to_df
)


NO_DATA_STATION_IDS = [
    "WNTEST1",
    "MITEST1",
]


class WisconetStation:
    """
    A class to represent a Wisconet station.

    Provides methods to access station-specific data and metadata.
    """
    def __init__(self, station: Station):
        """Initializes the WisconetStation.

        Args:
            station (Station): A Pydantic Station model object containing metadata for this station.
        """
        self.station: Station = station
        self._fields: list[Field] | None = None

    def fields(self) -> list[Field]:
        """Retrieves all available measurement fields for this station.

        Returns:
            list[Field]: A list of Pydantic Field model objects, each describing an available data field.
        """
        if not self._fields:
            self._fields = station_fields(self.station.station_id)
        return self._fields

    def get_field_names(self, filter: str | None = None) -> list[str]:
        """Gets a list of standard names for all available fields at the station.

        Args:
            filter (str, optional): A substring to filter field names by.
                If None, all field names are returned. Defaults to None.

        Returns:
            list[str]: A list of field standard names.
        """
        if filter is None:
            return [field.standard_name for field in self.fields()]
        else:
            return [field.standard_name for field in self.fields() if filter in field.standard_name]
    
    def fetch_data(self, start_time: datetime | str, end_time: datetime | str, fields: list[str], timeout: float = 30.0) -> pd.DataFrame | None:
        """
        Fetches data for specified fields from this station within a given time range.

        The start and end times are interpreted as being in the station's local timezone.
        The returned DataFrame will also have its timestamps localized to the station's timezone.

        Args:
            start_time (datetime | str): The start datetime or ISO-format string for the data query
                (e.g., "2025-01-01T00:00:00"). Interpreted as station local time.
            end_time (datetime | str): The end datetime or ISO-format string for the data query
                (e.g., "2025-02-01T00:00:00"). Interpreted as station local time.
            fields (list[str]): A list of field standard names (e.g., "60min_air_temp_f_avg")
                to retrieve. These should come from `get_field_names()`.
            timeout (float, optional): The HTTP request timeout in seconds. Defaults to 30.0.

        Returns:
            pd.DataFrame | None: A pandas DataFrame containing the requested data, with a
            DatetimeIndex localized to the station's timezone. Returns None if no data is found
            or an error occurs.
        """
        start_time_utc = datetime_at_station_in_utc(self.station, start_time)
        end_time_utc = datetime_at_station_in_utc(self.station, end_time)
        bulk_measures_data = bulk_measures(
            station_id=self.station.station_id,
            start_time=start_time_utc,
            end_time=end_time_utc,
            fields=fields,
            timeout=timeout
        )
        df = bulk_measures_to_df(bulk_measures_data, tz=self.station.station_timezone, station_id=self.station.station_id)
        if df is None:
            return None
        return df
    
    def fetch_all_available_data(self, fields: list[str] | None = None, timeout: float = 60.0) -> pd.DataFrame:
        """
        Fetches all available data for the station for the specified fields.

        This method retrieves data from the station's earliest available record up to the present.

        Args:
            fields (list[str], optional): A list of field standard names to retrieve.
                If None, attempts to retrieve all fields available at the station. Defaults to None.
            timeout (float, optional): The HTTP request timeout in seconds for underlying data fetches.
                Defaults to 60.0.

        Returns:
            pd.DataFrame: A pandas DataFrame containing all available data for the specified fields,
            with a DatetimeIndex localized to the station's timezone.
        """
        return all_data_for_station(self.station, fields=fields, timeout=timeout)

    def distance_to_point(self, lat: float, lon: float) -> float:
        """Calculates the great circle distance from the station to a specified point.

        Args:
            lat (float): Latitude of the point.
            lon (float): Longitude of the point.

        Returns:
            float: The distance in meters from the station to the given latitude and longitude.
        """
        lat1, lon1 = self.station.latitude, self.station.longitude
        lat2, lon2 = lat, lon
        R = 6371e3
        phi1 = lat1 * pi / 180
        phi2 = lat2 * pi / 180
        delta_phi = phi2 - phi1
        delta_lambda = (lon2 - lon1) * pi / 180
        a = (sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2)
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c
        return distance
        
    def __repr__(self):
        return f"WisconetStation(station={self.station})"
    
    def __str__(self):
        return f"WisconetStation: {self.station.station_name} ({self.station.station_id})"
    
    def __eq__(self, other):
        if isinstance(other, WisconetStation):
            return self.station == other.station
        return False


class Wisconet:
    """
    A facade class for interacting with the Wisconet API.

    Provides methods to access station information, find nearest stations,
    and retrieve observational data.
    """
    def __init__(self):
        """Initializes the Wisconet API client.

        Upon initialization, it fetches a list of all available Wisconet stations,
        excluding any test stations defined in `NO_DATA_STATION_IDS`.
        """
        self.stations: list[WisconetStation] = [WisconetStation(s) for s in all_stations() if s.station_id not in NO_DATA_STATION_IDS]

    def all_station_names(self) -> list[str]:
        """Retrieves a list of names for all active Wisconet stations.

        Returns:
            list[str]: A list of station names.
        """
        return [station.station.station_name for station in self.stations]

    def nearest_station(self, lat: float, lon: float) -> WisconetStation | None:
        """Finds the closest Wisconet station to a given latitude and longitude.

        Args:
            lat (float): Latitude of the point of interest.
            lon (float): Longitude of the point of interest.

        Returns:
            WisconetStation | None: The `WisconetStation` object for the nearest station,
            or None if no stations are available.
        """
        nearest_station = None
        nearest_distance = float('inf')
        for station in self.stations:
            distance = station.distance_to_point(lat, lon)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_station = station
        return nearest_station

    def nearest_stations(self, lat: float, lon: float, range: float | None = None, n: int | None = 3 ) -> list[tuple[WisconetStation, float]]:
        """
        Finds the nearest stations to a given latitude and longitude.

        Stations are sorted by distance in ascending order.

        Args:
            lat (float): Latitude of the point of interest.
            lon (float): Longitude of the point of interest.
            range (float, optional): The maximum distance (in meters) from the point
                for a station to be included. If None, range is not considered. Defaults to None.
            n (int, optional): The maximum number of nearest stations to return.
                If None, all stations within range (if specified) are returned. Defaults to 3.

        Returns:
            list[tuple[WisconetStation, float]]: A list of tuples, where each tuple contains
            a `WisconetStation` object and its distance (in meters) to the specified point.
            Returns an empty list if no stations meet the criteria.
        """
        nearest_stations = []
        for station in self.stations:
            nearest_stations.append(
                (
                    station, 
                    station.distance_to_point(lat, lon)
                )
            )
        nearest_stations = sorted(nearest_stations, key=lambda x: x[1])
        if range:
            nearest_stations = [s for s in nearest_stations if s[1] <= range]
        if n:
            nearest_stations = nearest_stations[:n]

        return nearest_stations
    
    def get_station(self, 
        station_id: str | int
    ) -> WisconetStation | None:
        """
        Retrieves a specific `WisconetStation` object by its identifier.

        The identifier can be the station's ID (e.g., "ALTN"), slug, or full name.
        The search is case-insensitive.

        Args:
            station_id (str | int): The ID, slug, or name of the station to retrieve.
                If an integer is provided, it's converted to a string.

        Returns:
            WisconetStation | None: The `WisconetStation` object if found, otherwise None.
        """
        station_id = str(station_id)
        for station in self.stations:
            if station.station.station_id.lower() == station_id.lower():
                return station
            if station.station.station_slug.lower() == station_id.lower():
                return station
            if station.station.station_name.lower() == station_id.lower():
                return station
        return None
    
    def get_data(self, 
        station_ids: list[str],
        start_time: datetime,
        end_time: datetime,
        fields: list[str],
        limits: httpx.Limits | None = None
    ) -> pd.DataFrame | None:
        """
        Fetches data for specified fields from multiple stations within a given time range.

        Times are interpreted as being in each respective station's local timezone.
        The resulting DataFrame will have timestamps localized accordingly.

        Args:
            station_ids (list[str]): A list of station identifiers (ID, slug, or name).
            start_time (datetime): The start datetime for the data query. Interpreted as local
                time for each respective station.
            end_time (datetime): The end datetime for the data query. Interpreted as local
                time for each respective station.
            fields (list[str]): A list of field standard names to retrieve.
            limits (httpx.Limits, optional): Custom `httpx.Limits` for underlying asynchronous
                HTTP requests. Useful for controlling connection pooling. Defaults to None.

        Returns:
            pd.DataFrame | None: A pandas DataFrame containing the combined data from all
            requested stations, with DatetimeIndex localized to respective station timezones
            (if data is present for a station). Returns None if no data is found for any station.
        """
        stations = [self.get_station(station_id=station_id) for station_id in station_ids]
        return fetch_data_multiple_stations([x.station for x in stations if x], start_time, end_time, fields, limits)
