import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from wiscopy.data import (
    all_stations,
    station_fields,
    bulk_measures,
    datetime_at_station_in_utc,
)
from wiscopy.schema import Station, Field, BulkMeasures


SAMPLE_FIELDS_JSON = [
    {
        "id": 1,
        "standard_name": "5min_air_temp_f_avg",
        "use_for": "",
        "measure_type": "Air Temp",
        "qualifier": "avg",
        "sensor": "",
        "source_field": "airtemp_c_avg@Table5",
        "data_type": "float",
        "source_units": "celsius",
        "final_units": "fahrenheit",
        "units_abbrev": "f",
        "conversion_type": "c2f",
        "collection_frequency": "5min",
    }
]


def _mock_client(status_code: int, json_data=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else []
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get.return_value = response
    return client


@pytest.mark.parametrize(
    "input_datetime, expected_datetime",
    [
        ("2021-01-01T00:00:00", datetime(2021, 1, 1, 6, 0, tzinfo=timezone.utc)),
        (datetime(2021, 1, 1), datetime(2021, 1, 1, 6, 0, tzinfo=timezone.utc)),
    ],
)
def test_datetime_at_station_in_utc(input_datetime, expected_datetime):
    stations = all_stations()
    this_station = stations[0]
    station_dt_utc = datetime_at_station_in_utc(station=this_station, dt=input_datetime)
    assert isinstance(station_dt_utc, datetime), "Expected datetime object"
    assert station_dt_utc.tzinfo == timezone.utc, (
        "Expected returned datetime object to be in UTC timezone"
    )


def test_all_stations():
    """Test that all_stations returns a non-empty list of stations."""
    stations = all_stations()
    assert len(stations) > 0, "Expected non-empty list of stations"
    assert isinstance(stations, list), "Expected stations to be a list"
    assert all(isinstance(station, Station) for station in stations), (
        "Expected all items in stations to be Station objects"
    )


def test_station_fields():
    """Test that station_fields returns a non-empty list of fields."""
    stations = all_stations()
    this_station = stations[0]
    fields = station_fields(this_station.station_id)
    assert len(fields) > 0, "Expected non-empty list of fields"
    assert isinstance(fields, list), "Expected fields to be a list"
    assert all(isinstance(field, Field) for field in fields), (
        "Expected all items in fields to be strings"
    )


def test_station_fields_fallback_to_all_fields():
    """When the station-specific endpoint returns non-200, falls back to the all-fields endpoint."""
    first = _mock_client(404)
    second = _mock_client(200, SAMPLE_FIELDS_JSON)
    with patch("wiscopy.data.httpx.Client", side_effect=[first, second]):
        fields = station_fields("NONEXISTENT")
    assert isinstance(fields, list)
    assert len(fields) == 1
    assert all(isinstance(f, Field) for f in fields)
    assert fields[0].standard_name == "5min_air_temp_f_avg"


def test_station_fields_fallback_to_cached_fields():
    """When both HTTP endpoints fail, falls back to loading fields from the local JSON cache."""
    first = _mock_client(404)
    second = _mock_client(503)
    with patch("wiscopy.data.httpx.Client", side_effect=[first, second]):
        fields = station_fields("NONEXISTENT")
    assert isinstance(fields, list)
    assert len(fields) > 0
    assert all(isinstance(f, Field) for f in fields)


def test_bulk_measures():
    """Test that bulk_measures returns a non-empty BulkMeasures object."""
    stations = all_stations()
    this_station = stations[0]
    this_station_fields = station_fields(this_station.station_id)
    end_time = datetime.now() - timedelta(days=1)
    start_time = end_time - timedelta(days=1)
    bm = bulk_measures(
        station_id=this_station.station_id,
        start_time=start_time,
        end_time=end_time,
        fields=[
            field.standard_name for field in this_station_fields
        ],  # Ensure we pass valid field names
    )
    assert isinstance(bm, BulkMeasures), "Expected BulkMeasures object"
    assert len(bm.data) > 0, "Expected non-empty data list in BulkMeasures"
    assert len(bm.fieldlist) > 0, "Expected non-empty fieldlist in BulkMeasures"
