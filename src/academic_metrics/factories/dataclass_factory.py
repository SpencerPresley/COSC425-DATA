import logging
import os
from dataclasses import dataclass
from typing import Dict, Type

from academic_metrics.constants import LOG_DIR_PATH
from academic_metrics.enums import DataClassTypes


class DataClassFactory:
    """Factory for creating and managing dataclass instances.

    This class provides centralized creation, registration, and management of dataclasses
    used throughout the application. It maintains a registry of dataclass types and
    handles their instantiation with proper initialization.

    Attributes:
        _registry (Dict[str, Type[dataclass]]): Internal registry mapping dataclass types to their classes.
        logger (logging.Logger): Logger instance for this class.
        log_file_path (str): Path to the log file.

    Public Methods:
        register_dataclass: Decorator to register a dataclass with the factory.
        get_dataclass: Creates a new instance of a registered dataclass.
        is_registered: Checks if a dataclass type is registered.
    """

    _registry: Dict[str, Type[dataclass]] = {}

    def __init__(self):
        """Initialize the DataClassFactory with logging configuration.

        Sets up both file and console handlers for logging factory operations.
        """
        # Set up logger
        self.log_file_path = os.path.join(LOG_DIR_PATH, "dataclass_factory.log")

        self.logger = logging.getLogger(__name__)
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    @classmethod
    def register_dataclass(cls, dataclass_type: DataClassTypes):
        """
        Decorator to register a dataclass with the factory.

        Args:
            dataclass_type (DataClassTypes): The type of dataclass to register.

        Example:
            @DataClassFactory.register_dataclass(DataClassTypes.CATEGORY_INFO)
            class CategoryInfo:
                ...
        """

        def decorator(data_class: Type):
            # Apply the @dataclass decorator if not already applied
            # if not hasattr(data_class, '__dataclass_fields__'):
            #     data_class = dataclass(data_class)
            # Register the dataclass using the enum value as the key
            cls._registry[dataclass_type.value] = data_class
            return data_class

        return decorator

    @classmethod
    def get_dataclass(
        cls, dataclass_type: DataClassTypes, **init_params
    ) -> Type[dataclass]:
        """
        Creates a new instance of the registered dataclass.

        Args:
            dataclass_type (DataClassTypes): The enum type of the dataclass to create
            **init_params: Parameters to initialize the dataclass

        Returns:
            An instance of the requested dataclass

        Raises:
            ValueError: If no dataclass is registered for the given type

        Example:
            category_info = DataClassFactory.get_dataclass(
                DataClassTypes.CATEGORY_INFO,
                category_name="Computer Science"
            )
        """
        data_class = cls._registry.get(dataclass_type.value)

        if not data_class:
            raise ValueError(f"No dataclass registered for type: {dataclass_type}")

        # First create instance with no params to ensure proper initialization
        instance = data_class()

        # Then set any provided parameters
        if init_params:
            instance.set_params(init_params)

        return instance

    @classmethod
    def is_registered(cls, dataclass_type: DataClassTypes) -> bool:
        """
        Check if a dataclass type is registered.

        Args:
            dataclass_type (DataClassTypes): The enum type to check

        Returns:
            bool: True if the dataclass is registered, False otherwise
        """
        return dataclass_type.value in cls._registry
