from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict
import logging
from academic_metrics.configs import configure_logging, DEBUG


@dataclass
class StringVariation:
    """
    A data class for tracking different spelling variations of a normalized name and determining the most frequent variation.

    Attributes:
        normalized_name (str): The base form of the name, typically normalized to lower case and stripped of spaces.
        variations (dict[str, int]): A dictionary where keys are variations of the name and values are the counts of how often each variation occurs.

    Methods:
        add_variation(variation: str): Adds a variation of the name to the dictionary or increments its count if it already exists.
        most_frequent_variation(): Returns the variation of the name that occurs most frequently.
    """

    normalized_value: str
    variations: Dict[str, int] = field(default_factory=dict)
    logger: logging.Logger = field(init=False)

    def __post_init__(self):
        """Initialize after dataclass fields are set."""
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="string_variation",
            log_level=DEBUG,
        )

    def add_variation(self, variation: str) -> None:
        """
        Adds a variation of the name to the dictionary or increments its count if it already exists.

        Args:
            variation (str): A specific spelling variation of the name.

        This method modifies the variations dictionary by either adding a new key with a count of 1 or incrementing the count of an existing key.
        """
        # Check if the variation is already in the dictionary and increment its count, otherwise add it with a count of 1
        self.logger.info(
            f"Checking if the variation {variation} is already in the dictionary and incrementing its count..."
        )
        if variation in self.variations:
            self.logger.info(
                f"Variation {variation} already in dictionary, incrementing count..."
            )
            self.variations[variation] += 1
            return
        self.logger.info(
            f"Variation {variation} not in dictionary, adding it with a count of 1..."
        )
        self.variations[variation] = 1

    def most_frequent_variation(self) -> str:
        """
        Returns the variation of the name that occurs most frequently.

        This method finds the key with the highest value in the variations dictionary, which represents the most common spelling variation.
        If the variations dictionary is empty, it raises a ValueError indicating that no variations have been added.

        Returns:
            str: The most frequent variation of the name.

        Raises:
            ValueError: If no variations are found in the dictionary, detailing the normalized name associated with the error.
        """
        # Check if the variations dictionary is empty and raise an error if it is
        self.logger.info(f"Checking if the variations dictionary is empty...")
        if not self.variations:
            self.logger.error(
                f"No variations found for the normalized value: '{self.normalized_value}', raising ValueError..."
            )
            raise ValueError(
                f"No variations found for the normalized value: '{self.normalized_value}'."
            )
        self.logger.info(f"Variations dictionary is not empty.")

        # Return the key (variation) with the maximum value (count) in the variations dictionary
        self.logger.info(
            f"Returning the key (variation) with the maximum value (count) in the variations dictionary..."
        )
        return max(self.variations, key=self.variations.get)
