"""Gateways for external service integration.

Gateways handle communication with external services like AWS Batch.
They differ from repositories which handle database persistence.
"""

from epistemix_platform.gateways.interfaces import ISimulationRunner
from epistemix_platform.gateways.simulation_runner import AWSBatchSimulationRunner


__all__ = ["ISimulationRunner", "AWSBatchSimulationRunner"]
