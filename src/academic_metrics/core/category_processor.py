from __future__ import annotations
import shortuuid

from typing import TYPE_CHECKING, List
from academic_metrics.data_models import (
    CategoryInfo,
    FacultyStats,
    GlobalFacultyStats,
    FacultyInfo,
    CrossrefArticleStats,
    CrossrefArticleDetails,
)
from academic_metrics.enums import AttributeTypes

if TYPE_CHECKING:
    from academic_metrics.utils import Utilities
    from academic_metrics.utils import WarningManager
    from academic_metrics.core import FacultyDepartmentManager


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
        self.category_data: dict[str, CategoryInfo] = {}

        # influential stats dictionaries
        self.faculty_stats: dict[str, FacultyStats] = {}
        self.global_faculty_stats: dict[str, GlobalFacultyStats] = {}
        self.article_stats: dict[str, CrossrefArticleStats] = {}
        self.article_stats_obj = CrossrefArticleStats()

    def process_data_list(self, data: list[dict]):
        for item in data:
            self.update_category_stats(data=item)

    def call_get_attributes(self, *, data):
        attribute_results = self.utils.get_attributes(
            data,
            [
                AttributeTypes.CROSSREF_CATEGORIES,
                AttributeTypes.CROSSREF_AUTHORS,
                AttributeTypes.CROSSREF_DEPARTMENTS,
                AttributeTypes.CROSSREF_TITLE,
                AttributeTypes.CROSSREF_CITATION_COUNT,
                AttributeTypes.CROSSREF_ABSTRACT,
                AttributeTypes.CROSSREF_LICENSE_URL,
                AttributeTypes.CROSSREF_PUBLISHED_PRINT,
                AttributeTypes.CROSSREF_PUBLISHED_ONLINE,
                AttributeTypes.CROSSREF_JOURNAL,
                AttributeTypes.CROSSREF_URL,
                AttributeTypes.CROSSREF_DOI,
                AttributeTypes.CROSSREF_THEMES,
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
        abstract = (
            attribute_results[AttributeTypes.CROSSREF_ABSTRACT][1]
            if attribute_results[AttributeTypes.CROSSREF_ABSTRACT][0]
            else None
        )
        license_url = (
            attribute_results[AttributeTypes.CROSSREF_LICENSE_URL][1]
            if attribute_results[AttributeTypes.CROSSREF_LICENSE_URL][0]
            else None
        )
        date_published_print = (
            attribute_results[AttributeTypes.CROSSREF_PUBLISHED_PRINT][1]
            if attribute_results[AttributeTypes.CROSSREF_PUBLISHED_PRINT][0]
            else None
        )
        date_published_online = (
            attribute_results[AttributeTypes.CROSSREF_PUBLISHED_ONLINE][1]
            if attribute_results[AttributeTypes.CROSSREF_PUBLISHED_ONLINE][0]
            else None
        )
        journal = (
            attribute_results[AttributeTypes.CROSSREF_JOURNAL][1]
            if attribute_results[AttributeTypes.CROSSREF_JOURNAL][0]
            else None
        )
        download_url = (
            attribute_results[AttributeTypes.CROSSREF_URL][1]
            if attribute_results[AttributeTypes.CROSSREF_URL][0]
            else None
        )
        doi = (
            attribute_results[AttributeTypes.CROSSREF_DOI][1]
            if attribute_results[AttributeTypes.CROSSREF_DOI][0]
            else None
        )
        themes = (
            attribute_results[AttributeTypes.CROSSREF_THEMES][1]
            if attribute_results[AttributeTypes.CROSSREF_THEMES][0]
            else None
        )
        return (
            categories,
            faculty_members,
            faculty_affiliations,
            title,
            tc_count,
            abstract,
            license_url,
            date_published_print,
            date_published_online,
            journal,
            download_url,
            doi,
            themes,
        )

    def update_category_stats(self, data):
        # get attributes from the file
        (
            categories,
            faculty_members,
            faculty_affiliations,
            title,
            tc_count,
            abstract,
            license_url,
            date_published_print,
            date_published_online,
            journal,
            download_url,
            doi,
            themes,
        ) = self.call_get_attributes(data=data)

        (
            top_level_categories,
            mid_level_categories,
            low_level_categories,
            all_categories,
        ) = self.initialize_categories(categories)
        faculty_members = self.clean_faculty_members(faculty_members)
        faculty_affiliations = self.clean_faculty_affiliations(faculty_affiliations)

        all_affiliations: set[str] = set()
        for faculty_member, department_affiliation in faculty_affiliations.items():
            if isinstance(department_affiliation, set):
                all_affiliations.update(department_affiliation)
            elif isinstance(department_affiliation, list):
                all_affiliations.update(department_affiliation)
            elif isinstance(department_affiliation, str):
                all_affiliations.add(department_affiliation)

        # update the category counts dict with the new data
        self.update_faculty_set(all_categories, faculty_members)
        self.update_department_set(all_categories, all_affiliations)
        self.update_title_set(all_categories, title)
        self.update_article_set()

        # citation updates related
        self.update_tc_list(
            category_data=self.category_data,
            categories=all_categories,
            tc_count=tc_count,
        )
        self.update_tc_count(self.category_data, all_categories)
        self.set_citation_average(self.category_data, all_categories)

        if themes is not None:
            self.update_themes_set(
                category_data=self.category_data,
                categories=all_categories,
                themes=themes,
            )

        self.update_id_for_category_data(
            category_data=self.category_data, categories=all_categories
        )

        # construct influential stats
        # On the entry take the faculty members we got and then += their total citations
        # += their article count
        # update article citation map
        # look up by name variation, and update name to the key string
        # that way i can match what's in the existing data
        self.update_faculty_members_stats(
            faculty_stats=self.faculty_stats,
            categories=all_categories,
            faculty_members=faculty_members,
            faculty_affiliations=faculty_affiliations,
            tc_count=tc_count,
            title=title,
            doi=doi,
        )

        self.update_global_faculty_stats(
            global_faculty_stats=self.global_faculty_stats,
            categories=all_categories,
            top_level_categories=top_level_categories,
            mid_level_categories=mid_level_categories,
            low_level_categories=low_level_categories,
            faculty_members=faculty_members,
            faculty_affiliations=faculty_affiliations,
            tc_count=tc_count,
            title=title,
            doi=doi,
            journal=journal,
            themes=themes,
        )

        self.update_doi_list(categories=all_categories, doi=doi)

        # update article stats for the category
        self.update_article_stats(
            article_stats=self.article_stats,
            categories=all_categories,
            title=title,
            tc_count=tc_count,
            faculty_affiliations=faculty_affiliations,
            faculty_members=faculty_members,
            abstract=abstract,
            license_url=license_url,
            date_published_print=date_published_print,
            date_published_online=date_published_online,
            journal=journal,
            download_url=download_url,
            doi=doi,
        )

        self.update_article_stats_obj(
            title=title,
            tc_count=tc_count,
            faculty_affiliations=faculty_affiliations,
            faculty_members=faculty_members,
            abstract=abstract,
            license_url=license_url,
            date_published_print=date_published_print,
            date_published_online=date_published_online,
            journal=journal,
            download_url=download_url,
            doi=doi,
            themes=themes,
            top_level_categories=top_level_categories,
            mid_level_categories=mid_level_categories,
            low_level_categories=low_level_categories,
            categories=all_categories,
        )

    def update_global_faculty_stats(
        self,
        global_faculty_stats,
        categories,
        top_level_categories,
        mid_level_categories,
        low_level_categories,
        faculty_members,
        faculty_affiliations,
        tc_count,
        title,
        doi,
        journal,
        themes,
    ):
        faculty_members = set(faculty_members)

        for faculty_member in faculty_members:
            if faculty_member not in global_faculty_stats:
                global_faculty_stats[faculty_member] = GlobalFacultyStats(
                    name=faculty_member,
                )

            glb_fac_stat = global_faculty_stats[faculty_member]
            glb_fac_stat._id = "-".join(faculty_member.lower().split())
            glb_fac_stat.total_citations += tc_count
            glb_fac_stat.article_count += 1
            glb_fac_stat.average_citations = (
                glb_fac_stat.total_citations / glb_fac_stat.article_count
            )
            glb_fac_stat.dois.add(doi)

            if isinstance(title, list):
                glb_fac_stat.titles.update(title)
            else:
                glb_fac_stat.titles.add(title)
            if isinstance(categories, list):
                glb_fac_stat.categories.update(categories)
            else:
                glb_fac_stat.categories.add(categories)

            if isinstance(categories, list):
                glb_fac_stat.category_ids.update(
                    shortuuid.uuid(category) for category in categories
                )
            else:
                glb_fac_stat.category_ids.add(shortuuid.uuid(categories))

            if isinstance(top_level_categories, list):
                glb_fac_stat.top_level_categories.update(top_level_categories)
            else:
                glb_fac_stat.top_level_categories.add(top_level_categories)
            if isinstance(mid_level_categories, list):
                glb_fac_stat.mid_level_categories.update(mid_level_categories)
            else:
                glb_fac_stat.mid_level_categories.add(mid_level_categories)
            if isinstance(low_level_categories, list):
                glb_fac_stat.low_level_categories.update(low_level_categories)
            else:
                glb_fac_stat.low_level_categories.add(low_level_categories)
            if isinstance(journal, list):
                glb_fac_stat.journals.update(journal)
            else:
                glb_fac_stat.journals.add(journal)
            if isinstance(themes, list):
                glb_fac_stat.themes.update(themes)
            else:
                glb_fac_stat.themes.add(themes)

            if faculty_member in faculty_affiliations:
                if isinstance(faculty_affiliations[faculty_member], set):
                    glb_fac_stat.department_affiliations.update(
                        faculty_affiliations[faculty_member]
                    )
                elif isinstance(faculty_affiliations[faculty_member], list):
                    glb_fac_stat.department_affiliations.update(
                        faculty_affiliations[faculty_member]
                    )
                elif isinstance(faculty_affiliations[faculty_member], str):
                    glb_fac_stat.department_affiliations.add(
                        faculty_affiliations[faculty_member]
                    )

            glb_fac_stat.citation_map[doi] = tc_count

    @staticmethod
    def update_faculty_members_stats(
        *,
        faculty_stats: dict[str, FacultyStats],
        categories: list[str],
        faculty_members: list[str],
        faculty_affiliations: dict[str, list[str]],
        tc_count: int,
        title: str,
        doi: str,
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
                id_name_category = (
                    faculty_member.lower().replace(" ", "-")
                    + "_"
                    + shortuuid.uuid(category)
                )
                member_info._id = id_name_category
                member_info.name = faculty_member
                member_info.category = category
                member_info.category_id = shortuuid.uuid(category)

                # update members total citations and article count for the category
                if faculty_affiliations.get(faculty_member, None) is not None:
                    if isinstance(faculty_affiliations[faculty_member], set):
                        member_info.department_affiliations.update(
                            faculty_affiliations[faculty_member]
                        )
                    elif isinstance(faculty_affiliations[faculty_member], list):
                        member_info.department_affiliations.update(
                            faculty_affiliations[faculty_member]
                        )
                    elif isinstance(faculty_affiliations[faculty_member], str):
                        member_info.department_affiliations.add(
                            faculty_affiliations[faculty_member]
                        )

                member_info.total_citations += tc_count
                member_info.article_count += 1

                if member_info.article_count > 0:
                    member_info.average_citations = (
                        member_info.total_citations / member_info.article_count
                    )

                if isinstance(title, list):
                    member_info.titles.update(title)
                else:
                    member_info.titles.add(title)

                member_info.dois.add(doi)

                # update the members article citation map for the category
                if isinstance(doi, list):
                    for d in doi:
                        member_info.doi_citation_map[d] = tc_count
                elif isinstance(doi, str):
                    member_info.doi_citation_map[doi] = tc_count

    @staticmethod
    def update_article_stats(
        *,
        article_stats: dict[str, CrossrefArticleStats],
        categories: list[str],
        title: str,
        tc_count: int,
        faculty_affiliations: dict[str, list[str]],
        faculty_members: list[str],
        abstract: str = None,
        license_url: str = None,
        date_published_print: str = None,
        date_published_online: str = None,
        journal: str = None,
        download_url: str = None,
        doi: str = None,
    ):
        for category in categories:
            if category not in article_stats:
                article_stats[category] = CrossrefArticleStats()

            if doi not in article_stats[category].article_citation_map:
                article_stats[category].article_citation_map[
                    doi
                ] = CrossrefArticleDetails()

            article_details = article_stats[category].article_citation_map[doi]
            article_details.title = title
            article_details.tc_count = tc_count
            if abstract is not None:
                article_details.abstract = abstract
            if license_url is not None:
                article_details.license_url = license_url
            if date_published_print is not None:
                article_details.date_published_print = date_published_print
            if date_published_online is not None:
                article_details.date_published_online = date_published_online
            if journal is not None:
                article_details.journal = journal
            if download_url is not None:
                article_details.download_url = download_url
            if doi is not None:
                article_details.doi = doi

            for faculty_member in faculty_members:
                article_details.faculty_members.add(faculty_member)
            article_details.faculty_affiliations = (
                faculty_affiliations if faculty_affiliations is not None else {}
            )

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
        abstract: str = None,
        license_url: str = None,
        date_published_print: str = None,
        date_published_online: str = None,
        journal: str = None,
        download_url: str = None,
        doi: str = None,
        themes: list[str] = None,
        top_level_categories: list[str] = None,
        mid_level_categories: list[str] = None,
        low_level_categories: list[str] = None,
        categories: list[str] = None,
    ):
        titles = []
        if isinstance(title, str):
            titles = [title]
        else:
            titles = title

        for title in titles:
            self.article_stats_obj.article_citation_map[doi] = CrossrefArticleDetails(
                _id=doi,
                title=title,
                tc_count=tc_count,
                faculty_members=faculty_members,
                faculty_affiliations=faculty_affiliations,
                abstract=abstract if abstract is not None else "",
                license_url=license_url if license_url is not None else "",
                date_published_print=(
                    date_published_print if date_published_print is not None else ""
                ),
                date_published_online=(
                    date_published_online if date_published_online is not None else ""
                ),
                journal=journal if journal is not None else "",
                download_url=download_url if download_url is not None else "",
                doi=doi if doi is not None else "",
                themes=themes if themes is not None else [],
                top_level_categories=(
                    top_level_categories if top_level_categories is not None else []
                ),
                mid_level_categories=(
                    mid_level_categories if mid_level_categories is not None else []
                ),
                low_level_categories=(
                    low_level_categories if low_level_categories is not None else []
                ),
                categories=categories if categories is not None else [],
                category_ids=(
                    [shortuuid.uuid(category) for category in categories]
                    if categories is not None
                    else []
                ),
            )

    def update_title_set(self, categories, title):
        if title is not None:
            # print(f"UPDATE TITLE SET\nCATS:{categories}\nTITLE:{title}")
            self.faculty_department_manager.update_title_set(categories, title)

    def update_doi_list(self, categories, doi):
        if doi is not None:
            self.faculty_department_manager.update_doi_list(categories, doi)

    def update_article_set(self):
        self.faculty_department_manager.update_article_counts(self.category_data)

    def update_department_set(self, categories, department_members):
        if department_members is not None:
            self.faculty_department_manager.update_departments(
                categories, department_members
            )

    def update_faculty_set(self, categories, faculty_members):
        self.faculty_department_manager.update_faculty_set(categories, faculty_members)

    def clean_faculty_affiliations(self, faculty_affiliations):
        # print(f"\n\nIN CLEAN DEPARTMENT\n\n{faculty_affiliations}")
        department_affiliations: dict[str, str] = {}
        for faculty_member, affiliations in faculty_affiliations.items():
            department_affiliations[faculty_member] = affiliations
        return department_affiliations

    def clean_faculty_members(self, faculty_members):
        clean_faculty_members: list[str] = []
        for faculty_member in faculty_members:
            if faculty_member != "":
                clean_faculty_members.append(faculty_member)
        return clean_faculty_members

    def initialize_categories(self, categories):
        top_level_categories = []
        mid_level_categories = []
        low_level_categories = []
        for category_level in ["top", "mid", "low"]:
            for category in categories.get(category_level, []):
                if category not in self.category_data:
                    self.category_data[category] = CategoryInfo(category_name=category)
                if category_level == "top":
                    top_level_categories.append(category)
                elif category_level == "mid":
                    mid_level_categories.append(category)
                elif category_level == "low":
                    low_level_categories.append(category)
        return (
            top_level_categories,
            mid_level_categories,
            low_level_categories,
            list(self.category_data.keys()),
        )

    def get_faculty_stats(self):
        return self.faculty_stats

    @staticmethod
    def update_tc_list(
        *,
        category_data: dict[str, CategoryInfo],
        categories: list[str],
        tc_count: int,
    ):
        for category in categories:
            category_data[category].tc_list.append(tc_count)

    @staticmethod
    def update_tc_count(category_data, categories):
        for category in categories:
            sum = 0
            for tc in category_data[category].tc_list:
                sum += tc
            category_data[category].tc_count = sum

    @staticmethod
    def get_tc_count(lines):
        tc_count = 0
        for line in lines:
            if line.startswith("TC"):
                tc_count += int(line[3:])

        return tc_count

    @staticmethod
    def set_citation_average(category_data, categories):
        for category in categories:
            citation_avg = (
                category_data[category].tc_count / category_data[category].article_count
            )
            category_data[category].citation_average = citation_avg

    @staticmethod
    def update_themes_set(category_data, categories, themes):
        for category in categories:
            if category in category_data:
                category_data[category].themes.update(themes)

    @staticmethod
    def update_id_for_category_data(category_data, categories):
        for category in categories:
            category_data[category]._id = shortuuid.uuid(category)
