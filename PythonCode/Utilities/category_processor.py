from utilities import Utilities  # for type hinting
from My_Data_Classes import CategoryInfo
from generate_aux_stats import FacultyStats, FacultyInfo, ArticleStats

# Imported for type hinting.
# Actual object is passed in to CategoryProcessor's constructor
# via dependency injection.
from faculty_department_manager import FacultyDepartmentManager
from enums import AttributeTypes
from warning_manager import WarningManager  # for type hinting
import json


class CategoryProcessor:
    def __init__(
        self,
        utils: Utilities,
        faculty_department_manager: FacultyDepartmentManager,
        warning_manager: WarningManager,
    ):
        self.utils: Utilities = utils
        self.warning_manager: WarningManager = warning_manager
        self.faculty_department_manager: FacultyDepartmentManager = (
            faculty_department_manager
        )
        self.category_counts: dict[str, CategoryInfo] = {}

        # influential stats dictionaries
        self.faculty_stats: dict[str, FacultyStats] = {}
        self.article_stats: dict[str, ArticleStats] = {}

    def category_finder(self, file_path, crossref_bool):
        if crossref_bool:
            self.run_category_generation_engine(file_path)
        else:
            file_content = None
            with open(file_path, 'r') as current_file:
                file_content = current_file.read()
            lines = file_content.splitlines()
            for line in lines:
                if line.startswith("WC"):
                    self.update_category_stats(file_path, file_content, lines)

    def run_category_generation_engine(self, file_path):
        print(f"path from generation: {file_path}")
        input("press enter to continue")
        categories = ["math"]
        crossref_items = None
        with open(file_path, "r") as f:
            crossref_items = json.load(f)
        print(f"CROSSREFITEMS:\n{crossref_items}")
        input("press enter to continue")
        crossref_items["categories"] = categories
        self.update_category_stats(
            file_path=file_path, data=crossref_items, crossref_bool=True
        )

    def call_get_attributes(self, *, data, crossref_bool, lines):
        categories, faculty_members, department_members, title, tc_count = [None for i in range(5)]

        if crossref_bool:
            attribute_results = (
                self.utils.get_attributes(
                    data,
                    [
                        AttributeTypes.CROSSREF_CATEGORIES,
                        AttributeTypes.CROSSREF_AUTHORS,
                        AttributeTypes.CROSSREF_DEPARTMENTS,
                        AttributeTypes.CROSSREF_TITLE,
                        AttributeTypes.CROSSREF_CITATION_COUNT
                    ]
                )
            )

            if attribute_results[AttributeTypes.CROSSREF_CATEGORIES][0]:
                categories = attribute_results[AttributeTypes.CROSSREF_CATEGORIES][1]
            else:
                raise Exception(f"No category found for data: {data}")

            faculty_members = attribute_results[AttributeTypes.CROSSREF_AUTHORS][1] if attribute_results[AttributeTypes.CROSSREF_AUTHORS][0] else None
            department_members = attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][1] if attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][0] else None
            title = attribute_results[AttributeTypes.CROSSREF_TITLE][1] if attribute_results[AttributeTypes.CROSSREF_TITLE][0] else None
            tc_count = attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][1] if attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][0] else None

        else:
            attribute_results = (
                self.utils.get_attributes(
                    data,
                    [
                        AttributeTypes.WC_PATTERN,
                        AttributeTypes.AUTHOR,
                        AttributeTypes.DEPARTMENT,
                        AttributeTypes.TITLE,
                    ]
                )
            )
                        
            categories = attribute_results[AttributeTypes.WC_PATTERN][1] if attribute_results[AttributeTypes.WC_PATTERN][0] else None
            faculty_members = attribute_results[AttributeTypes.AUTHOR][1] if attribute_results[AttributeTypes.AUTHOR][0] else None
            department_members = attribute_results[AttributeTypes.DEPARTMENT][1] if attribute_results[AttributeTypes.DEPARTMENT][0] else None
            title = attribute_results[AttributeTypes.TITLE][1] if attribute_results[AttributeTypes.TITLE][0] else None
            tc_count: int = self.get_tc_count(lines)

        return categories, faculty_members, department_members, title, tc_count

    def update_category_stats(self, file_path, data, lines=None, crossref_bool=False):
        # get attributes from the file
        print(f"DATA FROM UPDATE CATEGORY: {data}")
        input("press enter to continue...")
        categories, faculty_members, department_members, title, tc_count = (
            self.call_get_attributes(
                data=data, crossref_bool=crossref_bool, lines=lines
            )
        )

        self.initialize_and_update_categories(file_path, categories)
        faculty_members = self.clean_faculty_members(faculty_members)
        department_members = self.clean_department_members(department_members)

        # update the category counts dict with the new data
        self.update_faculty_set(categories, faculty_members)
        self.update_department_set(categories, department_members)
        self.update_article_set()
        self.update_title_set(categories, title)

        # citation updates related
        self.update_tc_list(lines=lines, category_counts=self.category_counts, categories=categories, tc_count=tc_count, crossref_bool=crossref_bool)
        self.update_tc_count(self.category_counts, categories)
        self.set_citation_average(self.category_counts, categories)

        # construct influential stats
        # On the entry take the faculty members we got and then += their total citations
        # += their article count
        # update article citation map
        # look up by name variation, and update name to the key string
        # that way i can match what's in the existing data
        self.update_faculty_members_stats(
            faculty_stats=self.faculty_stats,
            categories=categories,
            faculty_members=faculty_members,
            tc_count=tc_count,
            title=title,
        )

        # update article stats for the category
        self.update_article_stats(
            article_stats=self.article_stats,
            categories=categories,
            title=title,
            tc_count=tc_count,
        )

    @staticmethod
    def update_faculty_members_stats(
        *,
        faculty_stats: dict[str, FacultyStats],
        categories: list[str],
        faculty_members: list[str],
        tc_count: int,
        title: str,
    ):
        # Convert list to set to remove duplicates to avoid double counting
        faculty_members = set(faculty_members)

        # loop through categories
        for category in categories:

            # ensure there's a FacultyStats object for the category and that the category exists
            if category not in faculty_stats:
                faculty_stats[category] = FacultyStats()

            category_faculty_stats = faculty_stats[category].faculty_stats

            for faculty_member in faculty_members:
                if faculty_member not in category_faculty_stats:
                    category_faculty_stats[faculty_member] = FacultyInfo()

                member_info = category_faculty_stats[faculty_member]

                # update members total citations and article count for the category
                member_info.total_citations += tc_count
                member_info.article_count += 1

                # update members average citations for the category
                if member_info.article_count > 0:
                    member_info.average_citations = (
                        member_info.total_citations // member_info.article_count
                    )

                # update the members article citation map for the category
                if isinstance(title, list):
                    for t in title:
                        member_info.citation_map.article_citation_map[t] = tc_count
                elif isinstance(title, str):
                    member_info.citation_map.article_citation_map[title] = tc_count


    @staticmethod
    def update_article_stats(
        *,
        article_stats: dict[str, ArticleStats],
        categories: list[str],
        title: str,
        tc_count: int,
    ):
        for category in categories:
            if category not in article_stats:
                article_stats[category] = ArticleStats()

            if isinstance(title, list):
                for t in title:    
                    article_stats[category].article_citation_map[t] = tc_count
            if isinstance(title, str):
                article_stats[category].article_citation_map[title] = tc_count


    def update_title_set(self, categories, title):
        if title is not None:
            print(f"UPDATE TITLE SET\nCATS:{categories}\nTITLE:{title}")
            self.faculty_department_manager.update_title_set(categories, title)

    def update_article_set(self):
        self.faculty_department_manager.update_article_counts(self.category_counts)

    def update_department_set(self, categories, department_members):
        print(f"\n\nDEPARTMENT MEMBERS\n\n{department_members}")
        input("ayyy")
        if department_members is not None:
            self.faculty_department_manager.update_department_set_2(
                categories, department_members
            )

    def update_faculty_set(self, categories, faculty_members):
        self.faculty_department_manager.update_faculty_set(categories, faculty_members)

    def clean_department_members(self, department_members):
        print(f"\n\nIN CLEAN DEPARTMENT\n\n{department_members}")
        clean_department_members: list[str] = []
        for department_member in department_members:
            if department_member != "":
                clean_department_members.append(department_member)
        return clean_department_members
    
    def initialize_and_update_categories(self, file_path, categories):
        self.initialize_categories(categories=categories)
        self.update_category_counts_files_set(
            categories=categories, file_name=file_path
        )
        return categories

    def clean_faculty_members(self, faculty_members):
        clean_faculty_members: list[str] = []
        for faculty_member in faculty_members:
                if faculty_member != "":
                    clean_faculty_members.append(faculty_member)
        return clean_faculty_members

    def initialize_categories(self, categories):
        for i, category in enumerate(categories):
            # if category starts with 'WC ', remove it
            if category.startswith("WC "):
                categories[i] = category[3:]
                category = categories[i]

            if category not in self.category_counts:
                # Intialize a new CategoryInfo dataclass instance for the given category
                self.category_counts[category] = CategoryInfo()

    def get_faculty_stats(self):
        return self.faculty_stats

    @staticmethod
    def update_tc_list(*, lines, category_counts: dict[str, CategoryInfo], categories: list[str], tc_count: int, crossref_bool: bool = False):
        if crossref_bool:
            for category in categories:
                category_counts[category].tc_list.append(tc_count)
        else:
            for line in lines:
                if line.startswith("TC"):
                    for category in categories:
                        category_counts[category].tc_list.append(int(line[3:]))

    @staticmethod
    def update_tc_count(category_counts, categories):
        for category in categories:
            sum = 0
            for tc in category_counts[category].tc_list:
                sum += tc
            category_counts[category].tc_count = sum

    @staticmethod
    def get_tc_count(lines):
        tc_count = 0
        for line in lines:
            if line.startswith("TC"):
                tc_count += int(line[3:])

        return tc_count

    def update_category_counts_files_set(self, categories, file_name):
        for category in categories:
            if category in self.category_counts:
                self.category_counts[category].files.add(file_name)
            else:
                self.warning_manager.log_warning(
                    "Category Processing",
                    f"Category {category} not found in category_counts. Continuing to next category.",
                )

    @staticmethod
    def set_citation_average(category_counts, categories):
        for category in categories:
            citation_avg = (
                category_counts[category].tc_count
                // category_counts[category].article_count
            )
            category_counts[category].citation_average = citation_avg
