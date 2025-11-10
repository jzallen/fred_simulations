from dataclasses import dataclass


@dataclass(slots=True)
class RunResults:
    """Represents download information for a run's results."""

    run_id: int
    url: str

    def to_dict(self) -> dict[str, int | str]:
        """Serialize to dictionary for API responses."""
        return {
            "run_id": self.run_id,
            "url": self.url,
        }
