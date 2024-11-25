import atexit
import json
import logging
import os
from typing import Any, Dict, List, Tuple, TypeAlias

from dotenv import load_dotenv
from pymongo.collection import Collection
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from academic_metrics.configs import (
    configure_logging,
    DEBUG,
)

CollectionData: TypeAlias = List[Dict[str, Any]]
"""Type alias representing a collection of documents from MongoDB.

Each document is represented as a dictionary with string keys and arbitrary values.

Type:
    List[Dict[str, Any]]: A list of dictionaries where each dictionary represents a MongoDB document.
"""

DatabaseSnapshot: TypeAlias = Tuple[CollectionData, CollectionData, CollectionData]
"""Type alias representing a snapshot of all collections in the database.

Contains data from articles, categories, and faculty collections in that order.

Type:
    Tuple[CollectionData, CollectionData, CollectionData]: A tuple containing:
        - article_data (CollectionData): Documents from the articles collection
        - category_data (CollectionData): Documents from the categories collection
        - faculty_data (CollectionData): Documents from the faculty collection
"""


class DatabaseWrapper:
    """A wrapper class for MongoDB operations.

    Attributes:
        logger (logging.Logger): Logger for logging messages.
        client (MongoClient): MongoDB client.
        db (Database): MongoDB database.
        article_collection (Collection): MongoDB collection for article data.
        category_collection (Collection): MongoDB collection for category data.
        faculty_collection (Collection): MongoDB collection for faculty data.

    Methods:
        _test_connection: Test the connection to the MongoDB server.
        get_dois: Get all DOIs from the article collection.
        get_all_data: Get all data from the article, category, and faculty collections.
        insert_categories: Insert multiple categories into the collection.
        update_category: Update an existing category.
        insert_articles: Insert multiple articles into the collection.
        insert_faculty: Insert multiple faculty entries into the collection.
        update_faculty: Update an existing faculty member.
        process: Process data and insert it into the appropriate collection.
        run_all_process: Run the process method for all collections.
        clear_collection: Clear the entire collection.
        close_connection: Close the connection to the MongoDB server.
    """

    def __init__(self, *, db_name: str, mongo_url: str):
        """Initialize the DatabaseWrapper with database name, collection name, and MongoDB URL.

        Args:
            db_name (str): Name of the database.
            mongo_url (str): MongoDB URL.
        """
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="database_setup",
            log_level=DEBUG,
        )

        if not mongo_url:
            print("Url error")
            return
        self.mongo_url = mongo_url
        self.client = MongoClient(self.mongo_url, server_api=ServerApi("1"))
        self.db = self.client[db_name]
        self.article_collection: Collection = self.db["article_data"]
        self.category_collection: Collection = self.db["category_data"]
        self.faculty_collection: Collection = self.db["faculty_data"]
        self._test_connection()
        atexit.register(self.close_connection)

    def _test_connection(self):
        """Test the connection to the MongoDB server."""
        try:
            self.client.admin.command("ping")
            self.logger.info(
                "Pinged your deployment. You successfully connected to MongoDB!"
            )
        except Exception as e:
            self.logger.error(f"Connection error: {e}")

    def get_dois(self) -> List[str]:
        """Get all DOIs from the article collection.

        Returns:
            doi_list (List[str]): List of DOIs.
        """
        articles = self.article_collection.find({})
        doi_list = []
        for article in articles:
            doi_list.append(article["_id"])
        self.logger.info(f"Retrieved DOIs: {doi_list}")
        return doi_list

    def get_all_data(self) -> DatabaseSnapshot:
        """Get all data from the article, category, and faculty collections.

        Returns:
            Tuple[CollectionData, CollectionData, CollectionData]: A tuple containing:
            - articles (CollectionData): Documents from the articles collection

            - categories (CollectionData): Documents from the categories collection

            - faculty (CollectionData): Documents from the faculty collection
        """
        articles: CollectionData = list(self.article_collection.find({}))
        categories: CollectionData = list(self.category_collection.find({}))
        faculty: CollectionData = list(self.faculty_collection.find({}))

        self.logger.info("Retrieved all data from collections.")
        return (articles, categories, faculty)

    def insert_categories(self, category_data: List[Dict[str, Any]]):
        """Insert multiple categories into the collection.

        If a category already exists, add the numbers and extend the lists.

        Args:
            category_data (List[Dict[str, Any]]): List of category data.
        """
        if not category_data:
            self.logger.error("Category data is empty or None")
        for item in category_data:
            existing_data = self.category_collection.find_one({"_id": item["_id"]})
            if existing_data:
                new_item = self.update_category(existing_data, item)
                self.category_collection.update_one(
                    {"_id": item["_id"]}, {"$set": new_item}
                )
                self.logger.info(f"Updated category: {item['_id']}")
            else:
                self.category_collection.insert_one(item)
                self.logger.info(f"Inserted new category: {item['_id']}")

    def update_category(
        self, existing_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update existing category data with new data, handling None values and logging state.

        Args:
            existing_data (dict[str, Any]): Existing category data.
            new_data (dict[str, Any]): New category data.

        Returns:
            existing_data (Dict[str, Any]): Updated category data.
        """
        # ! THESE HAVE TO BE UNION NOT UPDATE
        # ! ALSO USING .GET() SO IT DOESN'T THROW AN ERROR IF THE KEY DOESN'T EXIST
        # ! NOW DOING LIST(SET()) TO CONVERT TO LIST
        # Get DOI lists with None protection
        existing_dois = existing_data.get("doi_list", []) or []
        new_dois = new_data.get("doi_list", []) or []
        self.logger.debug(f"DOIs - Existing: {existing_dois}, New: {new_dois}")

        # Only update if there's no intersection between DOI lists
        if not set(existing_dois).intersection(set(new_dois)):
            self.logger.info(
                f"No DOI intersection found for category {existing_data.get('_id')} - updating data"
            )

            # Calculate new citation average
            scaled_averages = len(existing_dois) * existing_data.get(
                "citation_average", 0
            ) + len(new_dois) * new_data.get("citation_average", 0)
            new_average = scaled_averages / (len(existing_dois) + len(new_dois))
            existing_data["citation_average"] = new_average
            self.logger.debug(f"Updated citation average to: {new_average}")

            # Update numeric counts
            existing_data["faculty_count"] = existing_data.get(
                "faculty_count", 0
            ) + new_data.get("faculty_count", 0)
            existing_data["department_count"] = existing_data.get(
                "department_count", 0
            ) + new_data.get("department_count", 0)
            existing_data["article_count"] = existing_data.get(
                "article_count", 0
            ) + new_data.get("article_count", 0)
            existing_data["tc_count"] = existing_data.get("tc_count", 0) + new_data.get(
                "tc_count", 0
            )

            # Update lists using set operations with None protection
            existing_data["doi_list"] = list(set(existing_dois).union(new_dois))

            existing_data["themes"] = list(
                set(existing_data.get("themes", []) or []).union(
                    new_data.get("themes", []) or []
                )
            )

            existing_data["faculty"] = list(
                set(existing_data.get("faculty", []) or []).union(
                    new_data.get("faculty", []) or []
                )
            )

            existing_data["departments"] = list(
                set(existing_data.get("departments", []) or []).union(
                    new_data.get("departments", []) or []
                )
            )

            existing_data["titles"] = list(
                set(existing_data.get("titles", []) or []).union(
                    new_data.get("titles", []) or []
                )
            )

            self.logger.debug(
                f"Updated counts - Faculty: {existing_data['faculty_count']}, "
                f"Departments: {existing_data['department_count']}, "
                f"Articles: {existing_data['article_count']}, "
                f"TC: {existing_data['tc_count']}"
            )
        else:
            self.logger.info(
                f"DOI intersection found for category {existing_data.get('_id')} - skipping update"
            )

        return existing_data

    def insert_articles(self, article_data: List[Dict[str, Any]]):
        """Insert multiple articles into the collection.

        If an article already exists, merge the new data with the existing data.

        Args:
            article_data (List[Dict[str, Any]]): List of article data.
        """
        for item in article_data:
            try:
                self.article_collection.insert_one(item)
                self.logger.info(f"Inserted new articles: {item['_id']}")
            except Exception as e:
                self.logger.info(f"Duplicate content not adding {e}")

    def insert_faculty(self, faculty_data: List[Dict[str, Any]]):
        """Insert multiple faculty entries into the collection.

        If a faculty member already exists, update the data accordingly.

        Args:
            faculty_data (List[Dict[str, Any]]): List of faculty data.
        """
        for item in faculty_data:
            existing_data = self.faculty_collection.find_one({"_id": item["_id"]})
            if existing_data:
                new_item = self.update_faculty(existing_data, item)
                self.faculty_collection.update_one(
                    {"_id": item["_id"]}, {"$set": new_item}
                )
                self.logger.info(f"Updated faculty: {item['_id']}")
            else:
                self.faculty_collection.insert_one(item)
                self.logger.info(f"Inserted new faculty: {item['_id']}")

    def update_faculty(
        self, existing_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update existing faculty data with new data, handling None values and logging state.

        Args:
            existing_data (Dict[str, Any]): Existing faculty data.
            new_data (Dict[str, Any]): New faculty data.

        Returns:
            existing_data (Dict[str, Any]): Updated faculty data.
        """
        # Get DOI lists with None protection
        existing_dois = existing_data.get("dois", []) or []
        new_dois = new_data.get("dois", []) or []
        self.logger.debug(f"DOIs - Existing: {existing_dois}, New: {new_dois}")

        # Only update if there's no intersection between DOI lists
        if not set(existing_dois).intersection(set(new_dois)):
            self.logger.info(
                f"No DOI intersection found for faculty {existing_data.get('_id')} - updating data"
            )

            # Update numeric values
            existing_data["total_citations"] = existing_data.get(
                "total_citations", 0
            ) + new_data.get("total_citations", 0)

            # Update lists using set operations with None protection
            existing_data["dois"] = list(set(existing_dois).union(new_dois))

            # Handle department affiliations as list
            existing_affiliations = (
                existing_data.get("department_affiliations", []) or []
            )
            new_affiliations = new_data.get("department_affiliations", []) or []
            existing_data["department_affiliations"] = list(
                set(existing_affiliations).union(new_affiliations)
            )

            # Update all set-based fields with None protection
            existing_data["titles"] = list(
                set(existing_data.get("titles", []) or []).union(
                    new_data.get("titles", []) or []
                )
            )

            existing_data["categories"] = list(
                set(existing_data.get("categories", []) or []).union(
                    new_data.get("categories", []) or []
                )
            )

            existing_data["top_level_categories"] = list(
                set(existing_data.get("top_level_categories", []) or []).union(
                    new_data.get("top_level_categories", []) or []
                )
            )

            existing_data["mid_level_categories"] = list(
                set(existing_data.get("mid_level_categories", []) or []).union(
                    new_data.get("mid_level_categories", []) or []
                )
            )

            existing_data["low_level_categories"] = list(
                set(existing_data.get("low_level_categories", []) or []).union(
                    new_data.get("low_level_categories", []) or []
                )
            )

            existing_data["category_urls"] = list(
                set(existing_data.get("category_urls", []) or []).union(
                    new_data.get("category_urls", []) or []
                )
            )

            existing_data["top_category_urls"] = list(
                set(existing_data.get("top_category_urls", []) or []).union(
                    new_data.get("top_category_urls", []) or []
                )
            )

            existing_data["mid_category_urls"] = list(
                set(existing_data.get("mid_category_urls", []) or []).union(
                    new_data.get("mid_category_urls", []) or []
                )
            )

            existing_data["low_category_urls"] = list(
                set(existing_data.get("low_category_urls", []) or []).union(
                    new_data.get("low_category_urls", []) or []
                )
            )

            existing_data["themes"] = list(
                set(existing_data.get("themes", []) or []).union(
                    new_data.get("themes", []) or []
                )
            )

            existing_data["journals"] = list(
                set(existing_data.get("journals", []) or []).union(
                    new_data.get("journals", []) or []
                )
            )

            self.logger.debug(
                f"Updated counts - Citations: {existing_data['total_citations']}, "
                f"DOIs: {len(existing_data['dois'])}"
            )
        else:
            self.logger.info(
                f"DOI intersection found for faculty {existing_data.get('_id')} - skipping update"
            )

        return existing_data

    def process(self, data: List[Dict[str, Any]], collection: str):
        """Process data and insert it into the appropriate collection.

        Args:
            data (List[Dict[str, Any]]): Data to be inserted.
            collection (str): Name of the collection to insert the data into.
        """
        if collection == "article_data":
            self.insert_articles(data)
        elif collection == "category_data":
            self.insert_categories(data)
        elif collection == "faculty_data":
            self.insert_faculty(data)

    def run_all_process(
        self,
        category_data: List[Dict[str, Any]],
        article_data: List[Dict[str, Any]],
        faculty_data: List[Dict[str, Any]],
    ):
        """Process all data and insert it into the appropriate collections.

        Args:
            category_data (List[Dict[str, Any]]): Category data.
            article_data (List[Dict[str, Any]]): Article data.
            faculty_data (List[Dict[str, Any]]): Faculty data.
        """
        self.process(category_data, "category_data")
        self.process(article_data, "article_data")
        self.process(faculty_data, "faculty_data")

    def clear_collection(self):
        """Clear the entire collection."""
        self.category_collection.delete_many({})
        self.article_collection.delete_many({})
        self.faculty_collection.delete_many({})
        self.logger.info("Cleared the entire collection")

    def close_connection(self):
        """Close the connection to the MongoDB server."""
        self.client.close()
        self.logger.info("Connection closed")


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    mongo_url = os.getenv("MONGODB_URL")

    # Handle article data
    with open(
        "../../data/core/output_files/test_processed_article_stats_obj_data.json", "r"
    ) as f:
        article_data = json.load(f)

    # Handle category data
    with open(
        "../../data/core/output_files/test_processed_category_data.json", "r"
    ) as f:
        category_data = json.load(f)

    # Handle faculty data
    with open(
        "../../data/core/output_files/test_processed_global_faculty_stats_data.json",
        "r",
    ) as f:
        faculty_data = json.load(f)

    database = DatabaseWrapper(db_name="Site_Data", mongo_url=mongo_url)
    database.clear_collection()

    database.process(article_data, "article_data")
    database.process(category_data, "category_data")
    database.process(faculty_data, "faculty_data")
