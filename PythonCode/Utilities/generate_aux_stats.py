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

# for NameVariation object access and type hinting
from faculty_set_postprocessor import NameVariation


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
class FacultyInfo:
    total_citations: int = 0
    article_count: int = 0
    average_citations: int = 0
    citation_map: FacultyArticleStats = field(default_factory=FacultyArticleStats)


@dataclass
class FacultyStats:
    faculty_stats: dict[str, FacultyInfo] = field(default_factory=dict)

    def refine_faculty_stats(
        self, *, faculty_name_unrefined: str, name_variations: dict[str, NameVariation]
    ):
        # grab the normalized name for the unrefined variation
        refined_faculty_name = self.get_refined_faculty_name(
            faculty_name_unrefined, name_variations
        )

        # update dictionary key from unrefined name to refined name
        self.faculty_stats[refined_faculty_name] = self.faculty_stats.pop(
            faculty_name_unrefined
        )

    def get_refined_faculty_name(self, unrefined_name, name_variations):
        # Iterate over each normalized name and its corresponding NameVariation object
        for normalized_name, name_variation in name_variations.items():
            # Check if the unrefined name is a variation in the NameVariation object
            if unrefined_name in name_variation.variations:
                # Return the most frequent variation as the refined name
                return name_variation.most_frequent_variation()
        # If no matching variation is found, return the unrefined name as a fallback
        return unrefined_name

    def to_dict(self) -> dict:
        # Utilize asdict utility from dataclasses, then change sets to lists
        data_dict = asdict(self)

        # Exclude 'files' from the dictionary
        if "files" in data_dict:
            del data_dict["files"]

        # Convert sets to lists for JSON serialization
        for key, value in data_dict.items():
            if isinstance(value, Set):
                data_dict[key] = list(value)
        return data_dict


@dataclass
class ArticleStats:
    article_citation_map: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        # Utilize asdict utility from dataclasses, then change sets to lists
        data_dict = asdict(self)

        # Exclude 'files' from the dictionary
        if "files" in data_dict:
            del data_dict["files"]

        # Convert sets to lists for JSON serialization
        for key, value in data_dict.items():
            if isinstance(value, Set):
                data_dict[key] = list(value)
        return data_dict


# article title: citation count
