from dataclasses import dataclass, asdict, fields
from typing import Any, Dict, Set, List
from abc import ABC


@dataclass
class AbstractBaseDataClass(ABC):
    """
    Abstract base class for all data model classes providing common functionality.

    Methods:
        to_dict: Converts the dataclass to a dictionary, handling Set conversion for JSON serialization.
        set_params: Sets the parameters from a dictionary, handling type conversions.
    """

    def to_dict(self) -> dict:
        """
        Converts the dataclass to a dictionary, handling Set conversion for JSON serialization.

        Returns:
            dict: A dictionary representation of the dataclass.
        """
        data_dict = asdict(self)
        # Convert sets to lists for JSON serialization
        for key, value in data_dict.items():
            if isinstance(value, Set):
                data_dict[key] = list(value)
        return data_dict

    def set_params(self, params: Dict[str, Any]) -> None:
        """
        This method takes in a dictionary of parameters and updates the dataclass fields accordingly.

        It handles:
        - Converting lists to sets for fields annotated as Set
        - Ignoring keys that don't match attributes
        - Handling nested dataclass updates

        Args:
            params (Dict[str, Any]): A dictionary of parameters to update the dataclass fields.
        """
        # Get field types from dataclass
        field_types = {field.name: field.type for field in fields(self)}

        for key, value in params.items():
            if hasattr(self, key):
                # Handle conversion of lists to sets where needed
                if field_types[key] == Set[str] and isinstance(value, (List, Set)):
                    value = set(value)
                # Handle empty values
                elif value is None and field_types[key] == Set[str]:
                    value = set()
                elif value is None and field_types[key] == List[str]:
                    value = []
                setattr(self, key, value)
