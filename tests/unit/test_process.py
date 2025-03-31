import pandas as pd
from datetime import datetime

from wiscopy.interface import Wisconet
from wiscopy.process import bulk_measures_to_df
from wiscopy.data import bulk_measures


def test_bulk_measures_to_df():
    w = Wisconet()
    station = w.get_station("OJNR")
    start_time = datetime(2025, 2, 1)
    end_time = datetime(2025, 2, 2)
    bms = bulk_measures(
        station_id=station.station.station_id,
        start_time=start_time,
        end_time=end_time,
        fields=["60min_dew_point_f_avg"]
    )
    df = bulk_measures_to_df(bms)
    assert isinstance(df, pd.DataFrame), "bulk_measures_to_df did not return a pd.DataFrame"
    assert not df.empty, "bulk_measures_to_df returned an empty DataFrame"
    assert df["standard_name"].iloc[0] == "60min_dew_point_f_avg", "bulk_measures_to_df did not return the expected field value"
    assert "value" in df.columns, "bulk_measures_to_df did not return the expected value column"
