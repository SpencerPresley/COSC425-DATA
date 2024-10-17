import os
import pickle
from academic_metrics.utils.utilities import Utilities  # for type hinting
from academic_metrics.utils.warning_manager import WarningManager  # for type hinting


class FileHandler:
    """
    A class for handling file operations such as checking file status, saving dictionaries, and constructing categories.

    Attributes:
        utils (Utilities): The utilities to be used for file handling.
        category_processor (CategoryProcessor): The category processor to be used for processing the categories.
        warning_manager (WarningManager): The warning manager to be used for managing the warnings.
        crossref_bool (bool): Whether the files are crossref files.

    Methods:
        construct_categories(self, *, directory_path, category_processor, warning_manager, crossref_bool):
            Constructs the categories for the given directory path.
        check_file_status(self, *, file_path) -> bool:
            Checks if the file at the given path is a file.
        save_dict(self, file_path: str, cat_dict: dict):
            Saves the given dictionary to the specified file path.

    Summary:
        This class provides methods for file handling operations such as checking file status, saving dictionaries, and constructing categories.
    """

    def __init__(self, utils: Utilities):
        """
        Initializes the FileHandler class with the provided utilities.

        Args:
            utils (Utilities): The utilities to be used for file handling.

        Summary:
            This method initializes the FileHandler class with the provided utilities.
        """
        self.utils = utils

    def construct_categories(
        self,
        *,
        directory_path,
        category_processor,
        warning_manager: WarningManager,
        crossref_bool,
    ):
        """
        Constructs the categories for the given directory path.

        Args:
            directory_path (str): The path to the directory containing the files (WoS export or crossref api files after splitting)
            category_processor (CategoryProcessor): The category processor to be used for processing the categories.
            warning_manager (WarningManager): The warning manager to be used for managing the warnings.
            crossref_bool (bool): Whether the files are crossref files.

        ! NOTE: Currently has tight coupling with the CategoryProcessor and WarningManager classes. This will be loosened in the future.
        """
        # print(f"Dir: {directory_path}, Cat: {category_processor}, warning: {warning_manager}, crossrefbool: {crossref_bool}")
        self.category_processor = category_processor
        if not os.path.exists(directory_path):
            raise Exception(
                f"Directory: {directory_path} does not exist. Check that you had a valid input file path and output file path, as well as a input file inside of the input file path directory in the initalization of WosClassification class."
            )

        for f in os.listdir(directory_path):
            path = os.path.expanduser(os.path.join(directory_path, f))
            if FileHandler.check_file_status(file_path=path):
                self.category_processor.category_finder(path, crossref_bool)
            else:
                warning_manager.log_warning(
                    "File Verification",
                    f"Could not verify file at: {f} as a file. Continuing to next file. From: {__file__}",
                )

    @staticmethod
    def check_file_status(*, file_path) -> bool:
        """
        Checks if the file at the given path is a file.

        Args:
            file_path (str): The path to the file to be checked.

        Returns:
            bool: True if the file exists and is a file, False otherwise.
        """
        if os.path.isfile(file_path):
            return True
        return False

    @staticmethod
    def save_dict(file_path: str, cat_dict: dict):
        """
        Saves the given dictionary to the specified file path.

        Args:
            file_path (str): The path to the file where the dictionary will be saved.
            cat_dict (dict): The dictionary to be saved.

        Summary:
            This method saves the given dictionary to the specified file path.
            It uses the pickle module to serialize the dictionary and save it to the file.
        """
        with open(file_path, "wb") as f:
            pickle.dump(cat_dict, f)
