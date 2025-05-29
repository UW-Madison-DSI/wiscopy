# User Guide

Welcome to the Wiscopy User Guide. This guide provides detailed information on how to use Wiscopy to interact with the Wisconet API.

## Introduction

Wiscopy is a Python library designed to simplify fetching environmental data from the [Wisconsin environmental mesonet API (Wisconet)](https://wisconet.wisc.edu/). It handles API communication, data parsing, and provides data in a convenient pandas DataFrame format.

Key features include:
- Easy-to-use interface for specifying stations, date ranges, and data fields.
- Automatic data formatting into pandas DataFrames.
- Transparent concurrent requests for fetching large datasets efficiently.

## The `Wisconet` Class

The primary way to interact with Wiscopy is through the `Wisconet` class from the `wiscopy.interface` module.

```python
from wiscopy.interface import Wisconet

# Initialize the client
w = Wisconet()
```

By default, `Wisconet()` initializes without any specific authentication, as the public Wisconet API typically doesn't require it for read access.

## Fetching Data (`get_data`)

The most important method is `get_data()`, which retrieves data for specified stations, time periods, and fields.

```python
df = w.get_data(
    station_ids=["maple", "arlington"], # List of station IDs or a single ID string
    start_time="2024-01-01",          # Start date (YYYY-MM-DD or datetime object)
    end_time="2024-01-02",            # End date (YYYY-MM-DD or datetime object)
    fields=["60min_air_temp_f_avg", "10m_wind_speed_mph_avg"], # List of field names
    # Optional parameters:
    # dataframe_orient="records"      # Default, or "columns"
    # station_id_col_name="station_id" # Default column name for station ID
    # variable_col_name="variable"     # Default column name for variable/field
    # value_col_name="value"           # Default column name for the data value
    # units_col_name="units"           # Default column name for units
    # final_units_col_name="final_units" # Default column name for final units after conversion
)

print(df.head())
```

**Parameters for `get_data()`:**
- `station_ids` (required): A string or a list of strings representing the station IDs.
- `start_time` (required): The start of the data period. Can be a string in `YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS` format, or a Python `datetime` object.
- `end_time` (required): The end of the data period. Same format as `start_time`.
- `fields` (required): A string or a list of strings representing the data fields (variables) you want to fetch.
- `dataframe_orient`: (Optional) The orientation of the resulting DataFrame, similar to pandas `DataFrame.to_dict()` orientation. Defaults to `"records"`.
- `station_id_col_name`, `variable_col_name`, `value_col_name`, `units_col_name`, `final_units_col_name`: (Optional) Allow customization of column names in the output DataFrame.

The method returns a pandas DataFrame with the requested data, typically including columns for station ID, timestamp, variable name, value, and units.

## Discovering Stations and Fields

Wiscopy provides methods to help you find available stations and data fields.

### Listing All Station Names

To get a list of all available Wisconet station names:

```python
station_names = w.all_station_names()
print(station_names[:5]) # Print first 5 station names
```

### Getting Station Details

You can retrieve more detailed information about a specific station using `get_station()`:

```python
# Assuming 'maple' is a valid station ID from all_station_names()
if "maple" in w.all_station_names():
    maple_station = w.get_station("maple")
    print(f"Station Name: {maple_station.name}")
    print(f"Station ID: {maple_station.id}")
    print(f"Location: {maple_station.location}") # May include lat, lon, elevation

    # List available fields/variables for this station
    available_fields = maple_station.get_field_names()
    print("Available fields for Maple station:", available_fields[:5]) # Print first 5
else:
    print("Station 'maple' not found.")
```
The `get_station()` method returns a `WisconetStation` object (or similar, depending on implementation details found in `wiscopy.data` or `wiscopy.schema`) which contains details about the station and its available data fields.

### Understanding Field Information
Each field typically has associated metadata like its description, units, etc. The `get_field_names()` method on a station object gives you the identifiers for these fields. The actual structure of field information can be explored by inspecting the objects returned by Wiscopy.

## Data Structure

The DataFrame returned by `get_data()` is structured for ease of use in data analysis and plotting. A typical structure includes:
- `datetime`: Timestamp for the observation.
- `station_id`: Identifier of the station.
- `variable`: Name of the measured variable (field).
- `value`: The actual data value.
- `units`: Original units of the measurement.
- `final_units`: Units after any conversion (often same as `units`).

Example:
```
                    datetime station_id                  variable      value final_units      units
0 2024-01-01 00:00:00      maple  60min_air_temp_f_avg  30.50         F          F
1 2024-01-01 00:00:00      maple  10m_wind_speed_mph_avg   5.20       MPH        MPH
...
```

## Error Handling

Wiscopy may raise exceptions for various reasons, such as network issues, invalid API requests (e.g., bad station ID, invalid date range), or unexpected API responses.
It's good practice to wrap API calls in `try...except` blocks:

```python
try:
    df = w.get_data(
        station_ids=["invalid_station_id"],
        start_time="2024-01-01",
        end_time="2024-01-02",
        fields=["some_field"]
    )
except Exception as e: # Replace with more specific exceptions if known
    print(f"An error occurred: {e}")
```
Refer to the API Reference for details on specific exceptions Wiscopy might raise.

## Advanced Usage

### Concurrency
Wiscopy handles concurrent API requests automatically when you request data for multiple stations or many fields/time periods. This is done using `asyncio` and `httpx` behind the scenes, making data retrieval faster. You generally don't need to manage this yourself.

### Customizing HTTP Client
For advanced scenarios like setting custom headers, timeouts, or using a proxy, you can pass a pre-configured `httpx.AsyncClient` instance to the `Wisconet` constructor:
```python
import httpx

custom_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
w_custom = Wisconet(client=custom_client)
```

## Best Practices
- **Be mindful of API rate limits** (if any are enforced by Wisconet). Fetch only the data you need.
- **Validate station IDs and field names** using the discovery methods before making large data requests.
- **Specify reasonable date ranges.** Requesting many years of high-frequency data in a single call might be slow or lead to very large DataFrames.
