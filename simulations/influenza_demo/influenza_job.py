from pathlib import Path

from epx import FREDJob, FREDModelConfig, SynthPop

# Update path to reference the local Influenza.fred file
INFLUENZA_FRED_FILE = (Path(__file__).parent / "Influenza.fred").resolve()

influenza_config = FREDModelConfig(
    synth_pop=SynthPop("US_2010.v5", ["Allegheny_County_PA"]),
    start_date="2020-01-01",
    end_date="2020-03-31",
)

influenza_job = FREDJob(
    config=[influenza_config],
    tags=["influenza_job"],
    fred_files=[str(INFLUENZA_FRED_FILE)],
)
