# Agent Info Demo

This demo showcases how to collect demographic information about agents in a FRED simulation.

## Files

- `agent_info.fred` - FRED model file that defines conditions to collect agent demographics
- `agent_info_job.py` - Python job definition that configures and runs the simulation

## Usage

The job can be imported and executed:

```python
from simulations.agent_info_demo.agent_info_job import info_job
info_job.execute(timeout=300)
```

This simulation collects:
- Agent age
- Agent race
- Agent sex

The data is captured in shared tables that are output at each simulation interval.
