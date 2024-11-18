import logging
import os
import warnings
from typing import List


class CustomWarning(Warning):
    """
    Custom warning class to store warning details.

    Args:
        Warning (str): _description_

    Attributes:
        category (str): The category of the warning.
        message (str): The message of the warning.
        entry_id (str, optional): The entry ID of the warning. Defaults to None.

    Methods:
        __init__(self, category: str, message: str, entry_id: str = None):
            Initializes the CustomWarning class with the provided category, message, and entry ID.

    Summary:
        This class is a custom warning class that is used to store warning details.
        It is used to store warning details in a structured way.
    """

    def __init__(self, category: str, message: str, entry_id: str = None):
        """
        Initializes the CustomWarning class with the provided category, message, and entry ID.

        Args:
            category (str): The category of the warning.
            message (str): The message of the warning.
            entry_id (str, optional): The entry ID of the warning. Defaults to None.

        Summary:
            This method initializes the CustomWarning class with the provided category, message, and entry ID.
        """
        self.category: str = category
        self.message: str = message
        self.entry_id: str = entry_id
        super().__init__(self.message)


class WarningManager:
    """
    Class to manage warnings.

    Attributes:
        warning_count (int): The number of warnings.
        warnings (list): A list of warnings.

    Methods:
        log_warning(self, category: str, warning_message: str, entry_id: str = None) -> CustomWarning:
            Logs a warning with the provided category, message, and entry ID.

            Args:
                category (str): The category of the warning.
                warning_message (str): The message of the warning.
                entry_id (str, optional): The entry ID of the warning. Defaults to None.

            Returns:
                CustomWarning: The warning that was logged.

        display_warning_summary(self):
            Displays the summary of the warnings.

            Args:
                None

            Returns:
                None

    Summary:
        This class is used to manage warnings.
        It is used to store warnings in a list and display the summary of the warnings.
    """

    def __init__(self):
        """
        Initializes the WarningManager class.

        Args:
            None

        Summary:
            This method initializes the WarningManager class.
        """
        # Set up logger
        current_dir: str = os.path.dirname(os.path.abspath(__file__))
        log_file_path: str = os.path.join(current_dir, "warning_manager.log")
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Add handler if none exists
        if not self.logger.handlers:
            handler: logging.FileHandler = logging.FileHandler(log_file_path)
            handler.setLevel(logging.DEBUG)
            formatter: logging.Formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.warning_count: int = 0
        self.warnings: List[CustomWarning] = []

    def log_warning(
        self, category: str, warning_message: str, entry_id: str = None
    ) -> CustomWarning:
        """
        Logs a warning with the provided category, message, and entry ID.

        Args:
            category (str): The category of the warning.
            warning_message (str): The message of the warning.
            entry_id (str, optional): The entry ID of the warning. Defaults to None.

        Returns:
            CustomWarning: The warning that was logged.
        """
        warning = CustomWarning(category, warning_message, entry_id)
        warnings.warn(warning)
        self.warning_count += 1
        self.warnings.append(warning)
        return warning

    def display_warning_summary(self):
        """
        Displays the summary of the warnings.

        Args:
            None

        Returns:
            None

        Summary:
            This method displays the summary of the warnings.
            It displays the category, message, and entry ID of the warning.
        """
        if self.warning_count > 0:
            print(f"\nWarning Summary ({self.warning_count} warnings):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning.category}: {warning.message[:50]}...")

            user_input: str = input(
                "\nEnter a number to see full warning details, or press Enter to continue: "
            )
            if user_input.isdigit() and 1 <= int(user_input) <= len(self.warnings):
                warning: CustomWarning = self.warnings[int(user_input) - 1]
                print("\nFull Warning Details:")
                print(f"Category: {warning.category}")
                print(f"Message: {warning.message}")
                print(f"Entry ID: {warning.entry_id}")
