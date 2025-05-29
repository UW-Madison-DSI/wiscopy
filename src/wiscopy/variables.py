"""
This module defines Enumeration types used to represent controlled vocabularies
for various metadata fields in the Wisconet API, such as collection frequencies,
measurement types, and units. These enums help ensure consistency and provide
clear choices when filtering or interpreting data.
"""
from enum import Enum


class CollectionFrequency(Enum):
    """Specifies the frequency at which data is typically collected or aggregated."""
    MIN5 = "5min" #: Data collected every 5 minutes.
    MIN60 = "60min" #: Data collected or aggregated hourly.
    DAILY = "daily" #: Data aggregated daily.


class MeasureType(Enum):
    """Categorizes the general type of environmental measurement."""
    AIRTEMP = 'Air Temp' #: Air temperature.
    BATTERY = 'Battery' #: Battery voltage or status.
    DEW_POINT = 'Dew Point' #: Dew point temperature.
    LEAF_WETNESS ='Leaf Wetness' #: Leaf wetness sensor reading.
    RAIN = 'Rain' #: Precipitation amount.
    RELATIVE_HUMIDITY = 'Relative Humidity' #: Relative humidity.
    SOIL_MOISTURE = 'Soil Moisture' #: Soil moisture content.
    SOIL_TEMP = 'Soil Temp' #: Soil temperature.
    WIND_SPEED = 'Wind Speed' #: Wind speed.
    CANOPY_WETNESS = 'Canopy Wetness' #: Canopy wetness sensor reading.
    PRESSURE = 'Pressure' #: Atmospheric pressure.
    WIND_DIR = 'Wind Dir' #: Wind direction.
    SOLAR_RADIATION = 'Solar Radiation' #: Solar radiation intensity.
    OTHER_CALCULATED = 'Other Calculated' #: Other types of calculated measurements.


class Units(Enum):
    """Defines the standard units for various measurements."""
    CELSIUS = 'celsius' #: Degrees Celsius.
    VOLTS = 'volts' #: Volts, typically for battery measurements.
    MV = 'mv' #: Millivolts.
    HST = 'hst' #: Hours, possibly for sunshine duration or similar. (Historically "Hours Sun Time")
    MILLIMETERS = 'millimeters' #: Millimeters, typically for precipitation.
    PCT = 'pct' #: Percentage, for relative humidity or soil moisture.
    METERSPERSECOND = 'meters/sec' #: Meters per second, for wind speed.
    MILLIBARS = 'millibars' #: Millibars, for atmospheric pressure.
    HOURS = 'hours' #: Hours, generic duration.
    DEGREES = 'degrees' #: Degrees, typically for wind direction or angles.
    SECONDS = 'seconds' #: Seconds, generic duration.
    KILOJOULES = 'kilojoules' #: Kilojoules, typically for energy (e.g., solar radiation).
    FAHRENHEIT = 'fahrenheit' #: Degrees Fahrenheit.
    INCHES = 'inches' #: Inches, typically for precipitation.
    MPH = 'mph' #: Miles per hour, for wind speed.
    DIR = 'Dir' #: Cardinal direction (e.g., N, S, E, W), for wind direction.
    WPM2 = 'W/m\u00B2' #: Watts per square meter, for solar radiation.
    MB = 'mb' #: Millibars, alternative for pressure (synonymous with MILLIBARS).
    KWHPM2 = 'kWh/m\u00B2' #: Kilowatt-hours per square meter, for solar energy accumulation.
