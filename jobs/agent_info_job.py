
from pathlib import Path
from epx import FREDJob, FREDModelConfig, SynthPop


if __name__ == "__main__":

    # create a ModelConfig object
    info_config = FREDModelConfig(
                    synth_pop=SynthPop("US_2010.v5", ["Loving_County_TX"]),
                    start_date="2022-05-10",
                    end_date="2022-05-10",
                )

    # create a FREDJob object using the ModelConfig
    root_dir = Path(__file__).parent.parent
    agent_info_fred_file = root_dir / "simulations" / "agent_info.fred"
    info_job = FREDJob(
        config=[info_config],
        tags=["info_job"],
        fred_files=[agent_info_fred_file]
    )

    # call the `FREDJob.execute()` method
    info_job.execute(300)

    str(info_job.status)