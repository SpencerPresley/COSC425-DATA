from utilities import Utilities
import warnings
from My_Data_Classes import CategoryInfo
from generate_aux_stats import FacultyStats, FacultyInfo, ArticleStats

# Imported for type hinting.
# Actual object is passed in to CategoryProcessor's constructor
# via dependency injection.
from faculty_department_manager import FacultyDepartmentManager


class CategoryProcessor:
    def __init__(self, utils, faculty_department_manager):
        self.utils: Utilities = utils
        self.faculty_department_manager: FacultyDepartmentManager = (
            faculty_department_manager
        )
        self.category_counts: dict[str, CategoryInfo] = {}

        # influential stats dictionaries
        self.faculty_stats: dict[str, FacultyStats] = {}
        self.article_stats: dict[str, ArticleStats] = {}

    def category_finder(self, current_file, file_path):
        file_content = current_file.read()
        lines = file_content.splitlines()
        for line in lines:
            if line.startswith("WC"):
                self.update_category_stats(file_path, file_content, lines)

    def update_category_stats(self, file_path, file_content, lines):
        # get attributes from the file
        attribute_results = self.get_attributes(file_content)
        categories = self.get_categories(file_path, attribute_results)
        faculty_members = self.get_faculty_members(attribute_results)
        department_members = self.get_department_members(attribute_results)
        title = self.get_title(attribute_results)

        # update the category counts dict with the new data
        self.update_faculty_set(categories, faculty_members)
        self.update_department_set(categories, department_members)
        self.update_article_set()
        self.update_title_set(categories, title)

        # citation related
        tc_count: int = self.get_tc_count(lines)
        self.update_tc_list(lines, self.category_counts, categories)
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
        self.update_article_stats(article_stats=self.article_stats, categories=categories, title=title, tc_count=tc_count)

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
                member_info.citation_map.article_citation_map[title] = tc_count
                
    @staticmethod
    def update_article_stats(*, article_stats: dict[str, ArticleStats], categories: list[str], title: str, tc_count: int):
        for category in categories:
            if category not in article_stats:
                article_stats[category] = ArticleStats()
            article_stats[category].article_citation_map[title] = tc_count
        
    def update_title_set(self, categories, title):
        if title is not None:
            self.faculty_department_manager.update_title_set(categories, title)

    def get_title(self, attribute_results):
        title = attribute_results["title"][1] if attribute_results["title"][0] else None

        return title

    def update_article_set(self):
        self.faculty_department_manager.update_article_counts(self.category_counts)

    def update_department_set(self, categories, department_members):
        if department_members is not None:
            self.faculty_department_manager.update_department_set_2(
                categories, department_members
            )

    def update_faculty_set(self, categories, faculty_members):
        self.faculty_department_manager.update_faculty_set(categories, faculty_members)

    def get_department_members(self, attribute_results):
        department_members = (
            attribute_results["department"][1]
            if attribute_results["department"][0]
            else None
        )

        return department_members

    def get_attributes(self, file_content):
        attributes_to_retrieve = ["author", "department", "wc_pattern", "title"]
        attribute_results = self.utils.get_attributes(
            entry_text=file_content, attributes=attributes_to_retrieve
        )

        return attribute_results

    def get_categories(self, file_path, attribute_results):
        categories = attribute_results["wc_pattern"][1]
        self.initialize_categories(categories=categories)
        self.update_category_counts_files_set(
            categories=categories, file_name=file_path
        )
        return categories

    def get_faculty_members(self, attribute_results):
        faculty_members: list[str] = []
        if attribute_results["author"][0]:
            for attribute in attribute_results["author"][1]:
                if attribute != "":
                    faculty_members.append(attribute)
        return faculty_members

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
    def update_tc_list(lines, category_counts, categories):
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
                warnings.warn(
                    f"Warning: Category {category} not found in category_counts. Continuing to next category."
                )

    @staticmethod
    def set_citation_average(category_counts, categories):
        for category in categories:
            citation_avg = (
                category_counts[category].tc_count
                // category_counts[category].article_count
            )
            category_counts[category].citation_average = citation_avg
