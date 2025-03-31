from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from wiscopy.data import (
    all_stations,
    station_fields,
    bulk_measures,
    all_data_for_station,
)
from wiscopy.schema import Station, Field, BulkMeasures


def test_all_stations():
    """Test that all_stations returns a non-empty list of stations."""
    stations = all_stations()
    assert len(stations) > 0, "Expected non-empty list of stations"
    assert isinstance(stations, list), "Expected stations to be a list"
    assert all(isinstance(station, Station) for station in stations), "Expected all items in stations to be Station objects"


def test_station_fields():
    """Test that station_fields returns a non-empty list of fields."""
    stations = all_stations()
    this_station = stations[0]
    fields = station_fields(this_station.station_id)
    assert len(fields) > 0, "Expected non-empty list of fields"
    assert isinstance(fields, list), "Expected fields to be a list"
    assert all(isinstance(field, Field) for field in fields), "Expected all items in fields to be strings"


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
        fields=[field.standard_name for field in this_station_fields]  # Ensure we pass valid field names
    )
    assert isinstance(bm, BulkMeasures), "Expected BulkMeasures object"
    assert len(bm.data) > 0, "Expected non-empty data list in BulkMeasures"
    assert len(bm.fieldlist) > 0, "Expected non-empty fieldlist in BulkMeasures"
    