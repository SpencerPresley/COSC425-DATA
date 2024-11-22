import atexit
import json
import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from pymongo.collection import Collection
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from academic_metrics.configs import (
    configure_logging,
    DEBUG,
)

# Setup logging
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
# )


class DatabaseWrapper:
    """
    A wrapper class for MongoDB operations.
    """

    def __init__(self, *, db_name: str, mongo_url: str):
        """
        Initialize the DatabaseWrapper with database name, collection name, and MongoDB URL.
        """
        # self.logger = logging.getLogger(__name__)

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
        """
        Test the connection to the MongoDB server.
        """
        try:
            self.client.admin.command("ping")
            self.logger.info(
                "Pinged your deployment. You successfully connected to MongoDB!"
            )
        except Exception as e:
            self.logger.error(f"Connection error: {e}")

    def get_dois(self):
        articles = self.article_collection.find({})
        doi_list = []
        for article in articles:
            doi_list.append(article["_id"])
        self.logger.info(f"Retrieved DOIs: {doi_list}")
        return doi_list

    def get_all_data(self):
        articles = self.article_collection.find({})
        categories = self.category_collection_collection.find({})
        faculty = self.faculty_collection.find({})

        self.logger.info("Retrieved all data from collections.")
        return [articles, categories, faculty]

    def insert_categories(self, category_data: List[Dict[str, Any]]):
        """
        Insert multiple categories into the collection.
        If a category already exists, add the numbers and extend the lists.
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
        self, existing_data: dict[str, Any], new_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update existing category data with new data, handling None values and logging state."""
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
        """
        Insert multiple articles into the collection.
        If an article already exists, merge the new data with the existing data.
        """
        for item in article_data:
            try:
                self.article_collection.insert_one(item)
                self.logger.info(f"Inserted new articles: {item['_id']}")
            except Exception as e:
                self.logger.info(f"Duplicate content not adding {e}")

    def insert_faculty(self, faculty_data: List[Dict[str, Any]]):
        """
        Insert multiple faculty entries into the collection.
        If a faculty member already exists, update the data accordingly.
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

    def update_faculty(self, existing_data, new_data):
        if not set(existing_data.get("dois", [])).intersection(
            set(new_data.get("dois", []))
        ):
            existing_data["total_citations"] += new_data["total_citations"]
            existing_data["department_affiliations"].append(
                new_data["department_affiliations"]
            )
            existing_data["dois"].append(new_data["dois"])
            existing_data["titles"] = set(existing_data["titles"]).update(
                new_data["titles"]
            )
            existing_data["categories"] = set(existing_data["categories"]).update(
                new_data["categories"]
            )
            existing_data["top_level_categories"] = set(
                existing_data["top_level_categories"]
            ).update(new_data["top_level_categories"])
            existing_data["mid_level_categories"] = set(
                existing_data["mid_level_categories"]
            ).update(new_data["mid_level_categories"])
            existing_data["low_level_categories"] = set(
                existing_data["low_level_categories"]
            ).update(new_data["low_level_categories"])
            existing_data["category_urls"] = set(existing_data["category_urls"]).update(
                new_data["category_urls"]
            )
            existing_data["top_category_urls"] = set(
                existing_data["top_category_urls"]
            ).update(new_data["top_category_urls"])
            existing_data["mid_category_urls"] = set(
                existing_data["mid_category_urls"]
            ).update(new_data["mid_category_urls"])
            existing_data["low_category_urls"] = set(
                existing_data["low_category_urls"]
            ).update(new_data["low_category_urls"])
            existing_data["themes"] = set(existing_data["themes"]).update(
                new_data["themes"]
            )
            existing_data["journals"] = set(existing_data["journals"]).update(
                new_data["journals"]
            )

        self.logger.info(f"Updated faculty data for: {existing_data['_id']}")
        return existing_data

    def process(self, data, collection):
        if collection == "article_data":
            self.insert_articles(data)
        elif collection == "category_data":
            self.insert_categories(data)
        elif collection == "faculty_data":
            self.insert_faculty(data)

    def run_all_process(self, category_data, article_data, faculty_data):
        self.process(category_data, "category_data")
        self.process(article_data, "article_data")
        self.process(faculty_data, "faculty_data")

    def clear_collection(self):
        self.category_collection.delete_many({})
        self.article_collection.delete_many({})
        self.faculty_collection.delete_many({})
        self.logger.info("Cleared the entire collection")

    def close_connection(self):
        """
        Close the connection to the MongoDB server.
        """
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
