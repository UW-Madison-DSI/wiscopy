# Wiscopy
Python wrapper for [Wisconet](https://wisconet.wisc.edu/). Currently supporting [API v1](https://wisconet.wisc.edu/docs).

## Install

### base install
```bash
pip install wiscopy
```

### install with plotting library dependencies
```bash
pip install 'wiscopy[plot]'
```

## Usage
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

see more examples in notebooks/examples.ipynb


## dev install (contribute!)
### 1. install pixi
See [pixi install guide](https://pixi.sh/latest/advanced/installation/).

### 2. check out from repo
```bash
git clone git@github.com:UW-Madison-DSI/wiscopy.git
cd wiscopy
pixi install
```
