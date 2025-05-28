"""
This module provides utility functions for processing data retrieved from the
Wisconet API, primarily focusing on converting raw API responses into
structured pandas DataFrames and filtering data fields.
"""
import pandas as pd
from enum import Enum
from wiscopy.schema import BulkMeasures, Field as SchemaField # Renamed to avoid conflict
from wiscopy.variables import CollectionFrequency, MeasureType, Units


def filter_fields(fields: list[SchemaField], criteria: list[Enum]) -> list[str]:
    """Filters a list of data fields based on specified criteria.

    Criteria are provided as a list of Enum members from `wiscopy.variables`
    (e.g., `CollectionFrequency.MIN5`, `MeasureType.AIRTEMP`). Fields must
    match all provided criteria of a given type (e.g., if both `Units.CELSIUS`
    and `Units.FAHRENHEIT` are given, no field will match unless it has both,
    which is unlikely).

    Args:
        fields (list[SchemaField]): A list of Pydantic `Field` model objects to filter.
        criteria (list[Enum]): A list of Enum members representing the filtering criteria.
            These should be from Enums like `CollectionFrequency`, `MeasureType`, `Units`.

    Returns:
        list[str]: A list of `standard_name` strings for the fields that match all criteria.
    """
    criteria_type_to_field = {
        CollectionFrequency: "collection_frequency",
        MeasureType: "measure_type",
        Units: "final_units",
    }
    criteria_by_type = {}
    all_criteria_types = list(set([c.__class__ for c in criteria]))
    for criteria_type in all_criteria_types:
        criteria_by_type[criteria_type] = [c.value for c in criteria if isinstance(c, criteria_type)]

    for criteria_type, criteria in criteria_by_type.items():
        if not criteria:
            continue
        fields = [
            field 
            for field in fields 
            if field.model_dump()[criteria_type_to_field[criteria_type]] in criteria
        ]

    return [field.standard_name for field in fields]


def bulk_measures_to_df(
    bms: BulkMeasures,
    tz: str | None = None,
    station_id: str = ""
) -> pd.DataFrame | None:
    """Converts a single `BulkMeasures` object into a pandas DataFrame.

    The resulting DataFrame is indexed by `collection_time` and includes columns
    for the measurement value and all metadata from the `Field` objects.

    Args:
        bms (BulkMeasures): The Pydantic `BulkMeasures` object containing field definitions
            and corresponding data.
        tz (str, optional): An IANA timezone string (e.g., 'US/Central', 'America/Chicago')
            to which the `collection_time` index should be localized. If None,
            the index will be in UTC. Defaults to None.
        station_id (str, optional): If provided, a column named 'station_id' with this
            value will be added to the DataFrame. Defaults to "".

    Returns:
        pd.DataFrame | None: A pandas DataFrame representing the bulk measures.
        Returns None if the input `BulkMeasures` object results in an empty DataFrame.
    """
    field_lookup = {field.id: field for field in bms.fieldlist}
    rows = []
    for collection in bms.data:
        collection_datetime = pd.to_datetime(collection.collection_time, unit="s")
        for measure in collection.measures:
            field_id = measure[0]
            value = measure[1]
            field = field_lookup[field_id]
            row = {
                "collection_time": collection_datetime,
                "value": value,
            } | {k: v for k, v in field.model_dump().items()}
            rows.append(row)
    
    df = pd.DataFrame(rows)
    
    if df.empty:
        return None
    
    if station_id:
        df["station_id"] = station_id
    
    if tz:
        df["collection_time"] = pd.to_datetime(df["collection_time"], utc=True).dt.tz_convert(tz)
    else:
        df["collection_time"] = pd.to_datetime(df["collection_time"], utc=True)
    
    df.set_index("collection_time", inplace=True)
    return df


def multiple_bulk_measures_to_df(
    bulk_measures_list: list[BulkMeasures],
    tz: str | None = None,
    station_id: str = ""
) -> pd.DataFrame | None:
    """Converts a list of `BulkMeasures` objects into a single pandas DataFrame.

    This function iterates through each `BulkMeasures` object, converts it to a
    DataFrame using `bulk_measures_to_df`, and then concatenates the results.

    Args:
        bulk_measures_list (list[BulkMeasures]): A list of Pydantic `BulkMeasures` objects.
        tz (str, optional): An IANA timezone string (e.g., 'US/Central') to localize
            the `collection_time` index of each DataFrame before concatenation.
            If None, times will be in UTC. Defaults to None.
        station_id (str, optional): If provided, a 'station_id' column with this value
            will be added to each individual DataFrame before concatenation.
            Useful if all `BulkMeasures` objects are from the same station.
            Defaults to "".

    Returns:
        pd.DataFrame | None: A single pandas DataFrame combining data from all input
        objects. Returns None if the combined list of DataFrames is empty.
    """
    dfs = []
    for bm in bulk_measures_list:
        df = bulk_measures_to_df(bm, tz=tz, station_id=station_id)
        if df is not None:
            dfs.append(df)
    if not dfs:
        return None
    return pd.concat(dfs)
