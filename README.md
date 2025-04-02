# Wiscopy
Python wrapper for [Wisconet](https://wisconet.wisc.edu/). Currently supporting [API v1](https://wisconet.wisc.edu/docs).

## Install

### From PyPI

#### base install

To install `wiscopy` from [PyPI](https://pypi.org/project/wiscopy/) run

```
python -m pip install wiscopy
```

#### install with plotting library dependencies

```
python -m pip install 'wiscopy[plot]'
```

### From conda-forge

To install and add `wiscopy` to a project from [conda-forge](https://github.com/conda-forge/wiscopy-feedstock) with [Pixi](https://pixi.sh/), from the project directory run

```
pixi add wiscopy
```

and to install into a particular conda environment with [`conda`](https://docs.conda.io/projects/conda/), in the activated environment run

```
conda install --channel conda-forge wiscopy
```

## Usage

### Fetch data from multiple stations, create a Dataframe, and plot.
```python
import nest_asyncio
import hvplot.pandas  # needed for df.hvplot()
import holoviews as hv
from datetime import datetime
from wiscopy.interface import Wisconet

hv.extension('bokeh')
hv.plotting.bokeh.element.ElementPlot.active_tools = ["box_zoom"]
nest_asyncio.apply()  # needed to run in notebook

w = Wisconet()
df = w.get_data(
    station_ids=["maple", "arlington"],
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 2, 1),
    fields=["60min_air_temp_f_avg"]
)
df.hvplot(
    y="value",
    by="station_id",
    title="60min_air_temp_f_avg",
    ylabel=df.final_units.iloc[0],
    grid=True,
    rot=90,
)

```
![Specific data over a specific time period](./notebooks/specific_data_specific_time.png)

### More examples
see more examples in [notebooks/examples.ipynb](https://github.com/UW-Madison-DSI/wiscopy/blob/main/notebooks/examples.ipynb), or run

```
pixi run start
```

## Wisconet

### Current stations
Wisconet's [list of current stations](https://wisconet.wisc.edu/stations.html) shows all active station names. You can get that list of strings via the API as follows:
```python
from wiscopy.interface import Wisconet

w = Wisconet()
station_names = w.all_station_names()
```

Wisconet also provides a [map](https://wisconet.wisc.edu/maps.html) of those stations with a dropdown menu including some of the currently available fields/variables. You can determine the fields available per station from the API with:

```python
from wiscopy.interface import Wisconet

w = Wisconet()
station_names = w.all_station_names()
this_station = w.get_station(station_names[0])
fields = this_station.get_field_names()
```


## dev install (contribute!)
### 1. install pixi
See [pixi install guide](https://pixi.sh/latest/advanced/installation/).

### 2. check out from repo
```bash
git clone git@github.com:UW-Madison-DSI/wiscopy.git
```

### 3. install local editable version
```bash
cd wiscopy
pixi install
```
