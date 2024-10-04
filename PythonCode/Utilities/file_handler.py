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
        crossref_bool
    ):
        if len(os.list(directory_path)) < 1:
            raise Exception(f"Directory at: {directory_path} contains no files.")
        
        call_make_files = True if len(os.list(directory_path)) == 1 else False

        if call_make_files:
            if crossref_bool:
                self.utils.make_files(path_to_file=file_path, output_dir=directory_path, crossref_bool = crossref_bool)
            else:
                self.utils.make_files(path_to_file=file_path, output_dir=directory_path)

        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            
            if FileHandler.check_file_status(file_path=file_path):

                with open(file_path, "r") as current_file:
                    category_processor.category_finder(current_file, file_path, crossref_bool)
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
