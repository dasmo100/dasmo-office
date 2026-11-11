from abc import ABC, abstractmethod
import logging
from typing import Any, Dict


class BaseAgent(ABC):
    """Abstract base class defining the standard interface for all AI pipeline agents."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = logging.getLogger(f"app.agents.{name}")

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's dedicated stage in the YouTube Short generation pipeline.

        Args:
            input_data: Dictionary containing pipeline context and artifacts.

        Returns:
            Dictionary containing updated context and generated artifacts.
        """
        pass
