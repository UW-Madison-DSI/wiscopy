from datetime import datetime
from wiscopy.interface import Wisconet


def test_wisconet_get_data():
    w = Wisconet()
    df = w.get_data(
        station_ids=["maple", "arlington"],
        start_time=datetime(2025, 1, 1),
        end_time=datetime(2025, 2, 1),
        fields=["60min_air_temp_f_avg"]
    )
    assert df is not None, "Expected a DataFrame"
    assert not df.empty, "Expected a non-empty DataFrame"
    assert df.index.name == "collection_time", "Expected collection_time index"
    assert "station_id" in df.columns, "Expected station_id column"
    assert "value" in df.columns, "Expected value column"
    assert set(df.station_id.unique().tolist()) == {"MAPL", "ALTN"}, "Expected station_id column has two correct stations present"
