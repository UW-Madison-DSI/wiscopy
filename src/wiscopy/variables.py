from enum import Enum


class CollectionFrequency(Enum):
    MIN5 = "5min"
    MIN60 = "60min"
    DAILY = "daily"


class MeasureType(Enum):
    AIRTEMP = 'Air Temp' 
    BATTERY = 'Battery' 
    DEW_POINT = 'Dew Point' 
    LEAF_WETNESS ='Leaf Wetness' 
    RAIN = 'Rain'
    RELATIVE_HUMIDITY = 'Relative Humidity' 
    SOIL_MOISTURE = 'Soil Moisture' 
    SOIL_TEMP = 'Soil Temp' 
    WIND_SPEED = 'Wind Speed'
    CANOPY_WETNESS = 'Canopy Wetness' 
    PRESURE = 'Pressure' 
    WIND_DIR = 'Wind Dir' 
    SOLAR_RADIATION = 'Solar Radiation'
    OTHER_CALCULATED = 'Other Calculated'


class Units(Enum):
    CELSIUS = 'celsius' 
    VOLTS = 'volts' 
    MV = 'mv' 
    HST = 'hst' 
    MILLIMETERS = 'millimeters' 
    PCT = 'pct'
    METERSPERSECOND = 'meters/sec'
    MILLIBARS = 'millibars' 
    HOURS = 'hours'
    DEGREES = 'degrees' 
    SECONDS = 'seconds' 
    KILOJOULES = 'kilojoules'
    FAHRENHEIT = 'fahrenheit'
    INCHES = 'inches'
    MPH = 'mph'
    DIR = 'Dir'
    WPM2 = 'W/m\u00B2' 
    MB = 'mb' 
    KWHPM2 = 'kWh/m\u00B2'
