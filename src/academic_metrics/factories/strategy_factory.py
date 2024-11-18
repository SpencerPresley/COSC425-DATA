from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from academic_metrics.constants import LOG_DIR_PATH
from academic_metrics.enums import AttributeTypes
from academic_metrics.utils import WarningManager

if TYPE_CHECKING:
    from academic_metrics.strategies import AttributeExtractionStrategy


class StrategyFactory:
    """
    A factory class for managing and retrieving attribute extraction strategies.

    This class provides a mechanism to register and retrieve different strategies for extracting attributes from data entries. It uses a dictionary to map attribute types to their corresponding strategy classes, allowing for flexible and dynamic strategy management.

    Attributes:
        _strategies (dict): A class-level dictionary that maps attribute types to their corresponding strategy classes.

    Methods:
        - register_strategy(*attribute_types): Registers a strategy class for one or more attribute types.
        - get_strategy(attribute_type, warning_manager): Retrieves the strategy class for a given attribute type and initializes it with a warning manager.

    Usage:
        add a strategy to the factory:
        StrategyFactory.register_strategy(AttributeTypes.TITLE)(TitleExtractionStrategy)

        add the enum to enums.py

        get a strategy from the factory:
        get_attributes() in utilities.py will then use this factory to get the strategy for a given attribute type.
    """

    _strategies = {}

    def __init__(self):
        # Set up logger
        self.log_file_path: str = os.path.join(LOG_DIR_PATH, "strategy_factory.log")
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler: logging.FileHandler = logging.FileHandler(self.log_file_path)
            formatter: logging.Formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    @classmethod
    def register_strategy(
        cls,
        *attribute_types: AttributeTypes,
    ):
        """
        Registers a strategy class for one or more attribute types.

        This method is used to associate a strategy class with specific attribute types. The strategy class
        is stored in the _strategies dictionary, allowing it to be retrieved later based on the attribute type.

        Args:
            *attribute_types (AttributeTypes): One or more attribute types to associate with the strategy class.

        Returns:
            function: A decorator function that registers the strategy class.
        """

        def decorator(strategy_class):
            for attribute_type in attribute_types:
                cls._strategies[attribute_type] = strategy_class
            return strategy_class

        return decorator

    @classmethod
    def get_strategy(
        cls, attribute_type: AttributeTypes, warning_manager: WarningManager
    ):
        """
        Retrieves the strategy class for a given attribute type and initializes it with a warning manager.

        This method looks up the strategy class associated with the specified attribute type in the _strategies
        dictionary. If a strategy class is found, it is instantiated with the provided warning manager and returned.

        Args:
            attribute_type (AttributeTypes): The attribute type for which to retrieve the strategy class.
            warning_manager (WarningManager): An instance of WarningManager to be passed to the strategy class.

        Returns:
            object: An instance of the strategy class associated with the specified attribute type.

        Raises:
            ValueError: If no strategy is found for the specified attribute type.
        """
        strategy_class: AttributeExtractionStrategy = cls._strategies.get(
            attribute_type
        )
        if not strategy_class:
            raise ValueError(f"No strategy found for attribute type: {attribute_type}")
        return strategy_class(warning_manager)
