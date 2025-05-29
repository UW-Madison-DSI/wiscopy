from typing import Any
from pydantic import BaseModel, Field as PydanticField
from datetime import datetime

"""
This module defines Pydantic models that represent the data structures
used by the Wisconet API (v1). These models are used for request and
response validation and provide a clear structure for API interactions.

The schema is based on the official Wisconet API documentation:
https://wisconet.wisc.edu/docs
"""

# Base URL for the Wisconet API v1
BASE_URL = "https://wisconet.wisc.edu/api/v1"


class Field(BaseModel):
    """Represents a data field or variable that can be measured at a station."""
    id: int = PydanticField(description="Unique identifier for the field.")
    collection_frequency: str | None = PydanticField(description="Frequency at which data for this field is collected (e.g., '5min', '60min').")
    conversion_type: str | None = PydanticField(description="Type of conversion applied to the raw sensor data, if any.")
    data_type: str | None = PydanticField(description="The data type of the measurement (e.g., 'float', 'integer').")
    final_units: str | None = PydanticField(description="The units of the measurement after any conversions.")
    measure_type: str | None = PydanticField(description="The general type of measurement (e.g., 'Air Temp', 'Wind Speed').")
    qualifier: str | None = PydanticField(description="Qualifier for the measurement, if applicable.")
    sensor: str | None = PydanticField(description="Type or model of the sensor used for this field.")
    source_field: str | None = PydanticField(description="The original field name or identifier from the data source.")
    source_units: str | None = PydanticField(description="The original units of the measurement from the data source.")
    standard_name: str | None = PydanticField(description="A standardized name for the field (e.g., '60min_air_temp_f_avg'). Often used as a primary identifier.")
    units_abbrev: str | None = PydanticField(description="Abbreviated form of the units (e.g., 'F', 'mph').")
    use_for: str | None = PydanticField(description="Indicates the typical use or application of this field.")


class Station(BaseModel):
    """Represents a Wisconet monitoring station and its metadata."""
    id: int = PydanticField(description="Unique numerical identifier for the station.")
    elevation: float | None = PydanticField(description="Elevation of the station, typically in meters.")
    latitude: float | None = PydanticField(description="Latitude of the station in decimal degrees.")
    longitude: float | None = PydanticField(description="Longitude of the station in decimal degrees.")
    city: str | None = PydanticField(description="City where the station is located.")
    county: str | None = PydanticField(description="County where the station is located.")
    location: str | None = PydanticField(description="Textual description of the station's location.")
    region: str | None = PydanticField(description="Geographical or administrative region of the station.")
    state: str | None = PydanticField(description="State where the station is located (e.g., 'WI').")
    station_id: str | None = PydanticField(description="Short, unique textual identifier for the station (e.g., 'ALTN').")
    station_name: str | None = PydanticField(description="Full descriptive name of the station (e.g., 'Arlington').")
    station_slug: str | None = PydanticField(description="URL-friendly version of the station name.")
    station_timezone: str | None = PydanticField(description="The IANA timezone name for the station's local time (e.g., 'America/Chicago').")
    earliest_api_date: datetime | None = PydanticField(description="The earliest date for which data is available from this station via the API.")
    campbell_cloud_id: str | None = PydanticField(description="Identifier related to Campbell Scientific cloud services, if applicable.")
    legacy_id: str | None = PydanticField(description="Legacy identifier for the station, if applicable.")


class ShortMeasure(BaseModel):
    """Represents a concise measurement value at a specific time."""
    station_id: str = PydanticField(description="Identifier of the station where the measurement was taken.")
    standard_name: str = PydanticField(description="Standardized name of the measured field.")
    suffix: int # Typically an integer, but API docs don't specify. Keeping as int.
    value: Any = PydanticField(description="The measured value.")
    collection_time: int = PydanticField(description="Unix timestamp (seconds since epoch) of when the measurement was collected.")
    preceding_value: Any | None = PydanticField(description="The value of the measurement immediately preceding the current one, if available.")
    preceding_time: int | None = PydanticField(description="Unix timestamp of the preceding measurement, if available.")


class ShortSummary(BaseModel):
    """Provides a brief summary of recent measurements for a station."""
    station: Station = PydanticField(description="The station object for which this summary applies.")
    latest_collection: int = PydanticField(description="Unix timestamp of the latest data collection for any field at this station.")
    daily: ShortMeasure = PydanticField(description="Summary of daily measurements.")
    current: ShortMeasure = PydanticField(description="The most current (latest) measurement available.")
    hourly: ShortMeasure = PydanticField(description="Summary of hourly measurements.")


class StationStatus(BaseModel):
    """Represents the operational status of a Wisconet station."""
    message: str = PydanticField(description="A human-readable status message.")
    station: Station = PydanticField(description="The station object this status refers to.")
    field_counts: Any | None = PydanticField(description="Counts or statistics related to data fields, structure may vary.")
    latest_date: str = PydanticField(description="Date of the latest data collection in string format (e.g., 'YYYY-MM-DD HH:MM:SS').")
    hours_since_last_collection: int = PydanticField(description="Number of hours since the last data collection from this station.")
    status: str = PydanticField(description="A general status indicator (e.g., 'active', 'inactive').")
    latest_collection_time: int = PydanticField(description="Unix timestamp of the most recent data collection.")


class AnnotatedMeasure(BaseModel):
    """Represents a measurement value along with its detailed field metadata."""
    standard_name: str = PydanticField(description="Standardized name of the measured field.")
    value: Any = PydanticField(description="The measured value.")
    preceding_time: int | None = PydanticField(description="Unix timestamp of the preceding measurement, if available.")
    suffix: str # API docs show as string, e.g. related to aggregation like "avg"
    field: Field = PydanticField(description="The full Field object providing metadata for this measurement.")
    station_id: str = PydanticField(description="Identifier of the station where the measurement was taken.")
    preceding_value: Any | None = PydanticField(description="The value of the measurement immediately preceding the current one, if available.")
    collection_time: int = PydanticField(description="Unix timestamp of when the measurement was collected.")


class DataByTime(BaseModel):
    """Groups multiple measurements that were collected at the same time."""
    collection_time: int = PydanticField(description="Unix timestamp for this group of measurements.")
    measures: list[list[str | int | float]] = PydanticField(description="A list of measurements. Each inner list typically contains [field_id, value].")


class BulkMeasures(BaseModel):
    """Represents a collection of measurements for multiple fields over a time range."""
    fieldlist: list[Field] = PydanticField(description="A list of Field objects that defines the fields included in the 'data'.")
    data: list[DataByTime] = PydanticField(description="A list of DataByTime objects, each representing measurements at a specific timestamp.")


class SimpleValue(BaseModel):
    """Represents a simple field-value pair with units."""
    field: str = PydanticField(description="Name or identifier of the field.")
    units: Any = PydanticField(description="Units of the value. Can be a string or other type as per API.")


class CollectionTimeByField(BaseModel):
    """Stores the earliest and latest collection times for a specific field."""
    field: Field = PydanticField(description="The field for which collection times are specified.")
    earliest_collection_time: int = PydanticField(description="Unix timestamp of the earliest available measurement for this field.")
    latest_collection_time: int = PydanticField(description="Unix timestamp of the latest available measurement for this field.")


class CollectionTimes(BaseModel):
    """Summarizes the overall data collection time range for a station and by field."""
    byField: list[CollectionTimeByField] = PydanticField(description="A list providing collection time ranges for each individual field.")
    earliest_collection_time: int = PydanticField(description="The earliest Unix timestamp of any measurement available from the station across all fields.")
    latest_collection_time: int = PydanticField(description="The latest Unix timestamp of any measurement available from the station across all fields.")
