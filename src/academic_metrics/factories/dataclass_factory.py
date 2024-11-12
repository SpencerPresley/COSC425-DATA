from typing import Type, Dict, Any
from dataclasses import dataclass
from academic_metrics.enums import DataClassTypes


class DataClassFactory:
    """
    A factory class for creating, getting, and managing dataclass instances.
    Provides centralized creation and registration of dataclasses.
    """

    _registry: Dict[str, Type[dataclass]] = {}

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
