import os
import pickle
from utilities import Utilities  # for type hinting
from warning_manager import WarningManager  # for type hinting


class FileHandler:
    def __init__(self, utils: Utilities):
        self.utils = utils

    def construct_categories(
        self,
        *,
        directory_path,
        category_processor,
        warning_manager: WarningManager,
        crossref_bool,
    ):
        print(f"Dir: {directory_path}, Cat: {category_processor}, warning: {warning_manager}, crossrefbool: {crossref_bool}")
        self.category_processor = category_processor
        if not os.path.exists(directory_path):
            raise Exception(f"Directory: {directory_path} does not exist. Check that you had a valid input file path and output file path, as well as a input file inside of the input file path directory in the initalization of WosClassification class.")
        
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
        if os.path.isfile(file_path):
            return True
        return False

    @staticmethod
    def save_dict(file_path: str, cat_dict: dict):
        with open(file_path, "wb") as f:
            pickle.dump(cat_dict, f)
