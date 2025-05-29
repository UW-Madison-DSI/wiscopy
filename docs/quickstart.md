# Quick Start Guide

This guide will help you get Wiscopy installed and running quickly.

## Installation

You can install Wiscopy using pip or conda.

### From PyPI

#### Base Install

To install `wiscopy` from [PyPI](https://pypi.org/project/wiscopy/) run:

```bash
python -m pip install wiscopy
```

#### Install with Plotting Dependencies

If you want to use the plotting functionalities, you can install `wiscopy` with the `plot` extra:

```bash
python -m pip install 'wiscopy[plot]'
```

### From conda-forge

To install and add `wiscopy` to a project from [conda-forge](https://github.com/conda-forge/wiscopy-feedstock) with [Pixi](https://pixi.sh/), from the project directory run:

```bash
pixi add wiscopy
```

To install into a particular conda environment with `conda`, in the activated environment run:

```bash
conda install --channel conda-forge wiscopy
```

## Basic Usage

Here's a simple example to fetch data from multiple stations, create a Pandas DataFrame, and plot it.

```python
import nest_asyncio  # needed to run wiscopy in a notebook
import hvplot.pandas  # needed for df.hvplot()
import holoviews as hv
from datetime import datetime
from wiscopy.interface import Wisconet

# Apply nest_asyncio if running in a Jupyter notebook
# nest_asyncio.apply() # Uncomment if in a notebook environment

# Initialize Wisconet API interface
w = Wisconet()

# Define parameters for data retrieval
station_ids = ["maple", "arlington"]
start_time = "2025-01-01" # Use a valid recent date for testing if needed
end_time = "2025-02-01"   # Use a valid recent date for testing if needed
fields = ["60min_air_temp_f_avg"] # Check available fields if this one is not current

# Fetch data
df = w.get_data(
    station_ids=station_ids,
    start_time=start_time,
    end_time=end_time,
    fields=fields
)

# Print or display the DataFrame
print(df.head())

# Plotting (requires 'plot' extras and a suitable environment)
# Ensure you have hvplot and a backend like bokeh installed
# hv.extension('bokeh')
# hv.plotting.bokeh.element.ElementPlot.active_tools = ["box_zoom"]
#
# if not df.empty:
#     plot = df.hvplot(
#         y="value",
#         by="station_id",
#         title=fields[0],
#         ylabel=df.final_units.iloc[0] if not df.empty and 'final_units' in df.columns else "Value",
#         grid=True,
#         rot=90,
#     )
#     print("Plotting...")
#     # In a script, you might need to save or show the plot explicitly
#     # hvplot.show(plot) 
# else:
#     print("No data returned, skipping plot.")
```

**Note on Running in Notebooks:**
If you are running this code in a Jupyter notebook or a similar IPython environment, you might need to uncomment and run `nest_asyncio.apply()` at the beginning of your script. This is because `wiscopy` uses `asyncio` for concurrent data fetching, and notebooks have their own event loop.

**Note on Plotting:**
The plotting part of the example uses `hvplot`. Ensure you have installed the necessary plotting dependencies (`wiscopy[plot]`) and that you are in an environment where plots can be rendered (like a Jupyter notebook or a script that saves the plot to a file). The example dates might be in the future; adjust them to a recent valid range for actual data retrieval.
