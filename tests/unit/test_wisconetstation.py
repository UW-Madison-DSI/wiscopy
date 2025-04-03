import pytest

from wiscopy.data import all_stations
from wiscopy.interface import WisconetStation
from utilities import within


@pytest.mark.parametrize(
    "station_name, lat, lon, expected_distance",
    [
        ("Maple", 43.0747, -89.3841, 435_070),
        ("Verona", 43.0747, -89.3841, 13_580),
    ]
)
def test_wisconetstation_distance(station_name, lat, lon, expected_distance):
    stations = all_stations()
    specific_station = [s for s in stations if s.station_name.lower() == station_name.lower()][0]
    s = WisconetStation(specific_station)
    distance = s.distance(lat, lon)
    assert isinstance(distance, float), "Expected distance to be a float"
    assert distance >= 0, "Expected distance to be non-negative"
    assert within(distance, expected_distance, 50), f"Expected delta distance to be less then 50"
