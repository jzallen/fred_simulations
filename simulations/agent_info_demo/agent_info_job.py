from pathlib import Path

from epx import FREDJob, FREDModelConfig, SynthPop

# Update path to reference the local agent_info.fred file
AGENT_INFO_FRED_FILE = Path(__file__).parent / "agent_info.fred"

info_config = FREDModelConfig(
    synth_pop=SynthPop("US_2010.v5", ["Loving_County_TX"]),
    start_date="2022-05-10",
    end_date="2022-05-10",
)

info_job = FREDJob(
    config=[info_config],
    tags=["info_job"],
    fred_files=[AGENT_INFO_FRED_FILE],
)
