import pytest
import pandas as pd
from datetime import datetime
from wiscopy.interface import Wisconet


@pytest.mark.parametrize(
    "station_ids, start_time, end_time, fields",
    [
        (["maple", "arlington"], datetime(2025, 1, 1), datetime(2025, 2, 1), ["60min_air_temp_f_avg"]),
        (["maple", "arlington"], "2025-01-01T00:00:00", "2025-02-01T00:00:00", ["60min_air_temp_f_avg"]),
        (["maple", "arlington"], "2025-01-01", "2025-02-01", ["60min_air_temp_f_avg"]),
        (["maple", "kwiktrip"], "2025-01-01", "2025-02-01", ["60min_air_temp_f_avg"]),
    ]
)
def test_wisconet_get_data(station_ids, start_time, end_time, fields):
    w = Wisconet()
    df = w.get_data(
        station_ids=station_ids,
        start_time=start_time,
        end_time=end_time,
        fields=fields
    )
    real_station_ids = [x.station.station_id for x in [w.get_station(station_id=station_id) for station_id in station_ids] if x]
    station_count = len(real_station_ids)
    days = (pd.Timestamp(end_time) - pd.Timestamp(start_time)).days
    station_tzs = [x.station.station_timezone for x in [w.get_station(station_id=station_id) for station_id in station_ids] if x]
    assert df is not None, "Expected a DataFrame"
    assert not df.empty, "Expected a non-empty DataFrame"
    assert len(df) == station_count * days * 24, "Expected DataFrame to have the correct number of rows"
    assert df.index.name == "collection_time", "Expected collection_time index"
    assert str(df.index.tz) == station_tzs[0], "Expected returned df index collection_time to be in station timezone"
    assert "station_id" in df.columns, "Expected returned df to have a 'station_id' column"
    assert "value" in df.columns, "Expected returned df to have a 'value' column"
    assert set(df.station_id.unique().tolist()) == set(real_station_ids), "Expected station_id column to contain each real requested station"
