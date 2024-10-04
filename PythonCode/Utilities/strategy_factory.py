from enums import AttributeTypes
from warning_manager import WarningManager  # for type hinting


class StrategyFactory:
    _strategies = {}

    @classmethod
    def register_strategy(
        cls,
        *attribute_types: AttributeTypes,
    ):
        def decorator(strategy_class):
            for attribute_type in attribute_types:
                cls._strategies[attribute_type] = strategy_class
            return strategy_class

        return decorator

    @classmethod
    def get_strategy(
        cls, attribute_type: AttributeTypes, warning_manager: WarningManager
    ):
        strategy_class = cls._strategies.get(attribute_type)
        if not strategy_class:
            raise ValueError(f"No strategy found for attribute type: {attribute_type}")
        return strategy_class(warning_manager)
