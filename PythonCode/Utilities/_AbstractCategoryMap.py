import os

import sys
sys.path.append('/home/cole/Desktop/COSC425-DATA/')

from GeneralUtilities.file_ops.file_ops import FileOps
from typing import Tuple

class AbstractCategoryMap:
    def __init__(self, Utilities_obj: object, *, dir_path: str):
        self.utilities = Utilities_obj
        self.dir_path = dir_path
        self.file_ops = FileOps(output_dir="~/Desktop/COSC425-DATA/PythonCode/Utilities/")
        self.results = self.map_abstract_categories(dir_path=self.dir_path)
        self.file_ops.write_json("abstracts_to_categories.json", self.results)

    def map_abstract_categories(self, *, dir_path: str):
        results = {}
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if not os.path.isfile(file_path):
                continue

            file_content = self.file_ops.read_file(file_path)
            attributes = self.utilities.get_attributes(
                file_content, ["abstract", "wc_pattern", "title"]
            )

            abstract, categories, title = self.extract_abstract_and_categories(attributes=attributes)
            if abstract:
                results[abstract] = {
                    'title': title,
                    'categories': categories
                }

        return results

   
    @staticmethod
    def extract_abstract_and_categories(*, attributes):
        abstract = attributes["abstract"][1] if attributes["abstract"][0] else None
        categories = attributes["wc_pattern"][1] if attributes["wc_pattern"][0] else []
        title = attributes["title"][1] if attributes["title"][0] else None
        return abstract, categories, title