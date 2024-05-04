# Python 3.9.5
# PythonCode/Utilities/generate_aux_stats.py

# This script will generate auxiliary statistics for the WoS data
# such as influential faculty, influential articles, etc.

# Python libraries
import json
from dataclasses import dataclass, field, asdict
from typing import Set, List

# Custom libraries
from utilities import Utilities
from My_Data_Classes import CategoryInfo


class GenerateAuxStats:
    def __init__(self, *, split_files_path: str, cat_data: dict[str, CategoryInfo]):
        self.utils = Utilities()
        self.split_files_path: str = split_files_path
        self.cat_data: dict[str, CategoryInfo] = cat_data
        self.aux_stats: dict[str,]

    # returns a dictionary of auxiliary statistics
    def get_aux_stats_dict():
        pass

    # Methods to generate auxiliary statistics
    @staticmethod
    def generate_aux_stats(path: str):
        pass

    @staticmethod
    def generate_influential_faculty():
        pass

    @staticmethod
    def generate_influential_articles():
        pass


@dataclass
class FacultyArticleStats:
    article_citation_map: dict[str, int] = field(default_factory=dict)


@dataclass
class FacultyStats:
    total_citations: int = 0
    article_count: int = 0
    average_citations: int = 0
    article_citation_map = FacultyArticleStats()
