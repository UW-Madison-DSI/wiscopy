import httpx
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


class WisconetStation:
    """
    A class to represent a Wisconet station.
    """
    def __init__(self, station: Station):
        self.station: Station = station
        self._fields: list[Field] | None = None
    
    def fields(self) -> list[Field]:
        """
        Get the Field objects available for the station.
        :return: list of Field objects
        """
        if not self._fields:
            self._fields = station_fields(self.station.station_id)
        return self._fields
        
    def get_field_names(self, filter: str | None = None) -> list[str]:
        """
        Get a list of all field names for the station.
        Optionally filter the field names by a substring.
        :param filter: optional substring to filter field names.
        :return: list of field names
        """
        if filter is None:
            return [field.standard_name for field in self.fields()]
        else:
            return [field.standard_name for field in self.fields() if filter in field.standard_name]
    
    def fetch_data(self, start_time: datetime, end_time: datetime, fields: list[str], timeout: float = 30.0) -> pd.DataFrame | None:
        """
        Get field data for the station between two times in station local time.
        returns results in local station time.
        :param start_time: datetime, fetch start time in station local time.
        :param end_time: datetime fetch end time in station local time.
        :param fields: list of Field.standard_name strings of fields to return. From self.get_field_names().
        :param timeout: float, httpx timeout.
        :return: pd.DataFrame or None if no data.
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
        Get all available data for the station and return it as a pandas DataFrame.
        :param fields: optional list of Field.standard_name strings of fields to return. If not specified, returns all fields.
        :param timeout: float, httpx timeout.
        :return: pd.DataFrame
        """
        return all_data_for_station(self.station, fields=fields, timeout=timeout)

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
    A class to represent the Wisconet API.
    """
    def __init__(self):
        self.stations: list[WisconetStation] = [WisconetStation(s) for s in all_stations()]
    
    def all_station_names(self) -> list[str]:
        """
        Get a list of all station names.
        :return: list of station names
        """
        return [station.station.station_name for station in self.stations]
    
    def get_station(self, 
        station_id: str | int
    ) -> WisconetStation | None:
        """
        Instantiate a WisconetStation by its station_id.
        :param station_id: Wisconet station_id, station_slug or station_name e.g "ALTN".
        :return: Station object or None if no matching station found.
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
        Get field data for multiple stations between two times in station local time.
        returns results in local station time.
        :param station_ids: list of Wisconet station_ids, station_slugs or station_names e.g ["ALTN", "MADN"]."
        :param start_time: datetime, fetch start time in station local time.
        :param end_time: datetime fetch end time in station local time.
        :param fields: list of Field.standard_name strings of fields to return. From self.get_field_names().
        :param limits: optional httpx.Limits to use for async requests.
        :return: pd.DataFrame or None if no data.
        """
        stations = [self.get_station(station_id=station_id) for station_id in station_ids]
        return fetch_data_multiple_stations([x.station for x in stations if x], start_time, end_time, fields, limits)
