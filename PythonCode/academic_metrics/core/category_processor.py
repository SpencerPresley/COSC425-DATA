import json
from academic_metrics.data_models import (
    CategoryInfo,
    FacultyStats,
    FacultyInfo,
    ArticleStats,
    ArticleDetails,
)
from academic_metrics.enums import AttributeTypes
import uuid


class CategoryProcessor:
    def __init__(
        self,
        utils: object,
        faculty_department_manager: object,
        warning_manager: object,
    ):
        self.utils: object = utils
        self.warning_manager: object = warning_manager
        self.faculty_department_manager: object = faculty_department_manager
        self.category_counts: dict[str, CategoryInfo] = {}

        # influential stats dictionaries
        self.faculty_stats: dict[str, FacultyStats] = {}
        self.article_stats: dict[str, ArticleStats] = {}
        self.article_stats_obj = ArticleStats()

    def category_finder(self, file_path, crossref_bool):
        if crossref_bool:
            self.run_category_generation_engine(file_path)
        else:
            file_content = None
            with open(file_path, "r") as current_file:
                file_content = current_file.read()
            lines = file_content.splitlines()
            for line in lines:
                if line.startswith("WC"):
                    self.update_category_stats(file_path, file_content, lines)

    def run_category_generation_engine(self, file_path):
        categories = ["math"]
        crossref_items = None
        with open(file_path, "r") as f:
            crossref_items = json.load(f)
        crossref_items["categories"] = categories
        self.update_category_stats(
            file_path=file_path, data=crossref_items, crossref_bool=True
        )

    def call_get_attributes(self, *, data, crossref_bool, lines):
        categories, faculty_members, department_members, title, tc_count = [
            None for i in range(5)
        ]

        if crossref_bool:
            attribute_results = self.utils.get_attributes(
                data,
                [
                    AttributeTypes.CROSSREF_CATEGORIES,
                    AttributeTypes.CROSSREF_AUTHORS,
                    AttributeTypes.CROSSREF_DEPARTMENTS,
                    AttributeTypes.CROSSREF_TITLE,
                    AttributeTypes.CROSSREF_CITATION_COUNT,
                ],
            )

            if attribute_results[AttributeTypes.CROSSREF_CATEGORIES][0]:
                categories = attribute_results[AttributeTypes.CROSSREF_CATEGORIES][1]
            else:
                raise Exception(f"No category found for data: {data}")

            faculty_members = (
                attribute_results[AttributeTypes.CROSSREF_AUTHORS][1]
                if attribute_results[AttributeTypes.CROSSREF_AUTHORS][0]
                else None
            )
            faculty_affiliations = (
                attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][1]
                if attribute_results[AttributeTypes.CROSSREF_DEPARTMENTS][0]
                else None
            )
            title = (
                attribute_results[AttributeTypes.CROSSREF_TITLE][1]
                if attribute_results[AttributeTypes.CROSSREF_TITLE][0]
                else None
            )
            tc_count = (
                attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][1]
                if attribute_results[AttributeTypes.CROSSREF_CITATION_COUNT][0]
                else None
            )

        else:
            attribute_results = self.utils.get_attributes(
                data,
                [
                    AttributeTypes.WC_PATTERN,
                    AttributeTypes.AUTHOR,
                    AttributeTypes.DEPARTMENT,
                    AttributeTypes.TITLE,
                ],
            )

            categories = (
                attribute_results[AttributeTypes.WC_PATTERN][1]
                if attribute_results[AttributeTypes.WC_PATTERN][0]
                else None
            )
            faculty_members = (
                attribute_results[AttributeTypes.AUTHOR][1]
                if attribute_results[AttributeTypes.AUTHOR][0]
                else None
            )
            faculty_affiliations = (
                attribute_results[AttributeTypes.DEPARTMENT][1]
                if attribute_results[AttributeTypes.DEPARTMENT][0]
                else None
            )
            title = (
                attribute_results[AttributeTypes.TITLE][1]
                if attribute_results[AttributeTypes.TITLE][0]
                else None
            )
            tc_count: int = self.get_tc_count(lines)

        return categories, faculty_members, faculty_affiliations, title, tc_count

    def update_category_stats(self, file_path, data, lines=None, crossref_bool=False):
        # get attributes from the file
        categories, faculty_members, faculty_affiliations, title, tc_count = (
            self.call_get_attributes(
                data=data, crossref_bool=crossref_bool, lines=lines
            )
        )

        self.initialize_and_update_categories(file_path, categories)
        faculty_members = self.clean_faculty_members(faculty_members)
        faculty_affiliations = self.clean_faculty_affiliations(faculty_affiliations)

        department_affiliations_list: list[str] = []
        for faculty_member, department_affiliation in faculty_affiliations.items():
            department_affiliations_list.append(department_affiliation)

        # update the category counts dict with the new data
        self.update_faculty_set(categories, faculty_members)
        self.update_department_set(categories, department_affiliations_list)
        self.update_title_set(categories, title)
        self.update_article_set()

        # citation updates related
        self.update_tc_list(
            lines=lines,
            category_counts=self.category_counts,
            categories=categories,
            tc_count=tc_count,
            crossref_bool=crossref_bool,
        )
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
            faculty_affiliations=faculty_affiliations,
            tc_count=tc_count,
            title=title,
            crossref_bool=crossref_bool,
        )

        # update article stats for the category
        self.update_article_stats(
            article_stats=self.article_stats,
            categories=categories,
            title=title,
            tc_count=tc_count,
            faculty_affiliations=faculty_affiliations,
            faculty_members=faculty_members,
            crossref_bool=crossref_bool,
        )
        
        self.update_article_stats_obj(
            title=title,
            tc_count=tc_count,
            faculty_affiliations=faculty_affiliations,
            faculty_members=faculty_members,
        )

    @staticmethod
    def update_faculty_members_stats(
        *,
        faculty_stats: dict[str, FacultyStats],
        categories: list[str],
        faculty_members: list[str],
        faculty_affiliations: dict[str, list[str]],
        tc_count: int,
        title: str,
        crossref_bool: bool = False,
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
                if crossref_bool:
                    if faculty_affiliations.get(faculty_member, None) is not None:
                        member_info.department_affiliations = faculty_affiliations[
                            faculty_member
                        ]
                member_info.total_citations += tc_count
                member_info.article_count += 1

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
        faculty_affiliations: dict[str, list[str]],
        faculty_members: list[str],
        crossref_bool: bool = False,
    ):
        for category in categories:
            if category not in article_stats:
                article_stats[category] = ArticleStats()

            if isinstance(title, str):
                titles = [title]  # Convert to list for consistent processing

            for t in titles:
                if t not in article_stats[category].article_citation_map:
                    article_stats[category].article_citation_map[t] = ArticleDetails()

                article_details = article_stats[category].article_citation_map[t]
                article_details.tc_count += tc_count

                if crossref_bool:
                    for faculty_member in faculty_members:
                        if faculty_member not in article_details.faculty_members:
                            article_details.faculty_members.append(faculty_member)
                        affiliations = faculty_affiliations.get(faculty_member, [])
                        article_details.faculty_affiliations[faculty_member] = (
                            affiliations
                        )
                else:
                    article_details.faculty_members.extend(faculty_members)
                    article_details.faculty_affiliations.update(faculty_affiliations)

        # Remove duplicates from faculty_members
        for category in article_stats:
            for article in article_stats[category].article_citation_map.values():
                article.faculty_members = list(set(article.faculty_members))
                
    def update_article_stats_obj(
        self,
        *,
        title: str,
        tc_count: int,
        faculty_affiliations: dict[str, list[str]],
        faculty_members: list[str],
    ):
        if isinstance(title, str):
            titles = [title]
            
        for t in titles: 
            self.article_stats_obj.article_citation_map[t] = ArticleDetails(
                tc_count=tc_count,
                faculty_members=faculty_members,
                faculty_affiliations=faculty_affiliations,
            )
        
    def update_title_set(self, categories, title):
        if title is not None:
            # print(f"UPDATE TITLE SET\nCATS:{categories}\nTITLE:{title}")
            self.faculty_department_manager.update_title_set(categories, title)

    def update_article_set(self):
        self.faculty_department_manager.update_article_counts(self.category_counts)

    def update_department_set(self, categories, department_members):
        if department_members is not None:
            self.faculty_department_manager.update_department_set_2(
                categories, department_members
            )

    def update_faculty_set(self, categories, faculty_members):
        self.faculty_department_manager.update_faculty_set(categories, faculty_members)

    def clean_faculty_affiliations(self, faculty_affiliations):
        # print(f"\n\nIN CLEAN DEPARTMENT\n\n{faculty_affiliations}")
        department_affiliations: dict[str, str] = {}
        for faculty_member, affiliations in faculty_affiliations.items():
            for affiliation in affiliations:
                if affiliation != "":
                    department_affiliations[faculty_member] = affiliation
        return department_affiliations

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
    def update_tc_list(
        *,
        lines,
        category_counts: dict[str, CategoryInfo],
        categories: list[str],
        tc_count: int,
        crossref_bool: bool = False,
    ):
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
