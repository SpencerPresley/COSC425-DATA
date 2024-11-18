from abc import ABC
from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, List, Set


@dataclass
class AbstractBaseDataClass(ABC):
    """
    Abstract base class for all data model classes providing common functionality.

    Methods:
        to_dict: Converts the dataclass to a dictionary, handling Set conversion for JSON serialization.
        set_params: Sets the parameters from a dictionary, handling type conversions.
    """

    def to_dict(self, exclude_keys: List[str] | None = None) -> dict:
        """
        Converts the dataclass to a dictionary, handling Set conversion for JSON serialization.

        Returns:
            dict: A dictionary representation of the dataclass.
        """
        data_dict = asdict(self)

        # Remove excluded keys if any
        if exclude_keys:
            for key in exclude_keys:
                data_dict.pop(key, None)

        def convert_sets(obj):
            if isinstance(obj, dict):
                return {k: convert_sets(v) for k, v in obj.items()}
            elif isinstance(obj, Set):
                return list(obj)
            return obj

        # Convert sets to lists, including those in nested dicts
        return convert_sets(data_dict)

    def set_params(self, params: Dict[str, Any], debug: bool = False) -> None:
        """
        Updates the dataclass fields, merging sets and handling nested updates.

        It handles:
        - Converting lists to sets for fields annotated as Set
        - Merging sets instead of overwriting
        - Ignoring keys that don't match attributes
        - Handling nested dataclass updates

        Args:
            params (Dict[str, Any]): A dictionary of parameters to update the dataclass fields.

        Examples:
            >>> class MyClass(AbstractBaseDataClass):
            ...     items: Set[str] = field(default_factory=set)
            >>> obj = MyClass()
            >>> obj.set_params({"items": ["a", "b"]})
            >>> obj.set_params({"items": ["c", "d"]})
            >>> sorted(list(obj.items))  # Contains all items
            ['a', 'b', 'c', 'd']
        """
        # Get fields from the concrete class, not the base class
        if debug:
            print(
                f"AbstractBaseDataClass.set_params called on {self.__class__.__name__}"
            )
            input()
            print(f"Fields: {fields(self.__class__)}")
            input()

        field_types = {field.name: field.type for field in fields(self.__class__)}
        if debug:
            print(f"Field types: {field_types}")
            input()
        for key, value in params.items():
            if debug:
                print(f"Processing {key} = {value}")
                input()
            if hasattr(self, key) and value is not None:
                current_value = getattr(self, key)
                if debug:
                    print(f"Current value of {key}: {current_value}")
                    input()

                # Handle Set fields
                if key in field_types and field_types[key] == Set[str]:
                    if debug:
                        print(f"{key} is a Set[str] field")
                        input()
                    # Convert input to set if needed
                    if isinstance(value, (List, Set)):
                        new_value = set(value)
                    else:
                        new_value = {str(value)}

                    # Merge with existing set
                    if isinstance(current_value, Set):
                        current_value.update(new_value)
                    else:
                        setattr(self, key, new_value)

                # Handle other fields normally
                else:
                    if debug:
                        print(f"{key} is not a Set[str] field")
                        input()
                    setattr(self, key, value)
