import os
import pickle
from utilities import Utilities  # for type hinting
from warning_manager import WarningManager  # for type hinting


class FileHandler:
    def __init__(self, utils: Utilities):
        self.utils = utils

    @staticmethod
    def construct_categories(
        *, directory_path, category_processor, warning_manager: WarningManager
    ):
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if FileHandler.check_file_status(file_path=file_path):
                with open(file_path, "r") as current_file:
                    category_processor.category_finder(current_file, file_path)
            else:
                warning_manager.log_warning(
                    "File Verification",
                    f"Could not verify file at: {file_path} as a file. Continuing to next file. From: {__file__}",
                )

    @staticmethod
    def check_file_status(*, file_path) -> bool:
        if os.path.isfile(file_path):
            return True
        return False

    @staticmethod
    def save_dict(file_path: str, cat_dict: dict):
        with open(file_path, "wb") as f:
            pickle.dump(cat_dict, f)
