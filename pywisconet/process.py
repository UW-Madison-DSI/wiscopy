import pandas as pd
from enum import Enum
from pywisconet.schema import BulkMeasures, Field
from pywisconet.variables import CollectionFrequency, MeasureType, Units


def filter_fields(fields: list[Field], criteria: list[Enum]) -> list[str]:
    """
    Filter Fields by criteria.
    :param fields: list of Field objects.
    :param criteria: list of variable Enum objects.
    :return: list of Field.standard_name strings matching all criteria.
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


def bulk_measures_to_df(bms: BulkMeasures) -> pd.DataFrame:
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
    return pd.DataFrame(rows)
