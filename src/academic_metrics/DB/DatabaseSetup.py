import os
import json
import logging
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.collection import Collection
from typing import List, Dict, Any
import atexit

from academic_metrics.constants import LOG_DIR_PATH


class DatabaseWrapper:
    """
    A wrapper class for MongoDB operations.
    """

    def __init__(self, *, db_name: str, collection_name: str, mongo_url: str):
        """
        Initialize the DatabaseWrapper with database name, collection name, and MongoDB URL.
        """
        self.log_file_path = os.path.join(LOG_DIR_PATH, "database_wrapper.log")
        self.logger = logging.getLogger(__name__)
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(self.log_file_path)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.mongo_url = mongo_url
        self.client = MongoClient(self.mongo_url, server_api=ServerApi("1"))
        self.db = self.client[db_name]
        self.collection: Collection = self.db[collection_name]
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

    def clear_collection(self):
        confirm = input(
            "Are you absolutely sure you want to delete the entire collection? (yes/no): "
        )
        if confirm.lower() == "yes":
            self.collection.delete_many({})
            self.logger.info(f"Cleared the entire collection")
        else:
            self.logger.info("Canceled the clear!")

    def close_connection(self):
        """
        Close the connection to the MongoDB server.
        """
        self.client.close()
        self.logger.info("Connection closed")


class ArticleDatabase(DatabaseWrapper):
    """
    A specialized DatabaseWrapper for handling articles.
    """

    def __init__(self, db_name: str, collection_name: str):
        """
        Initialize the ArticleDatabase with database name and collection name.
        """
        super().__init__(
            db_name=db_name,
            collection_name=collection_name,
            mongo_url=os.getenv("MONGODB_URL"),
        )

    def insert_articles(self, article_data: List[Dict[str, Any]]):
        """
        Insert multiple articles into the collection.
        If an article already exists, merge the new data with the existing data.
        """
        for article in article_data:
            existing_article = self.collection.find_one({"_id": article["_id"]})
            if existing_article:
                self.update_article(existing_article, article)
                self.collection.update_one(
                    {"_id": article["_id"]}, {"$set": existing_article}
                )
                self.logger.info(f"Updated existing article: {article['title']}")
            else:
                self.collection.insert_one(article)
                self.logger.info(f"Inserted new article: {article['title']}")

    def update_article(self, existing_data: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Update existing article data with new data.
        """
        # Example: Update tc_count and themes
        existing_data["tc_count"] = new_data.get(
            "tc_count", existing_data.get("tc_count", 0)
        )
        existing_data["themes"] = list(
            set(existing_data.get("themes", []) + new_data.get("themes", []))
        )
        # Add more fields as needed


class CategoryDatabase(DatabaseWrapper):
    """
    A specialized DatabaseWrapper for handling categories.
    """

    def __init__(self, db_name: str, collection_name: str):
        """
        Initialize the CategoryDatabase with database name and collection name.
        """
        super().__init__(
            db_name=db_name,
            collection_name=collection_name,
            mongo_url=os.getenv("MONGODB_URL"),
        )

    def insert_categories(self, category_data: List[Dict[str, Any]]):
        """
        Insert multiple categories into the collection.
        If a category already exists, add the numbers and extend the lists.
        """
        for item in category_data:
            existing_category = self.collection.find_one({"_id": item["_id"]})
            if existing_category:
                self.update_category(existing_category, item)
                self.collection.update_one(
                    {"_id": item["_id"]}, {"$set": existing_category}
                )
                self.logger.info(f"Updated existing category: {item['category_name']}")
            else:
                self.collection.insert_one(item)
                self.logger.info(f"Inserted new category: {item['category_name']}")

    def update_category(self, existing_data: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Update existing category data with new data.
        """
        numeric_fields = [
            "faculty_count",
            "department_count",
            "article_count",
            "tc_count",
            "citation_average",
        ]
        for field in numeric_fields:
            existing_data[field] += new_data.get(field, 0)

        list_fields = ["doi_list", "themes"]
        for field in list_fields:
            existing_list = set(existing_data.get(field, []))
            new_list = set(new_data.get(field, []))
            existing_data[field] = list(existing_list.union(new_list))


class FacultyDatabase(DatabaseWrapper):
    """
    A specialized DatabaseWrapper for handling faculty data.
    """

    def __init__(self, db_name: str, collection_name: str):
        """
        Initialize the FacultyDatabase with database name and collection name.
        """
        super().__init__(
            db_name=db_name,
            collection_name=collection_name,
            mongo_url=os.getenv("MONGODB_URL"),
        )

    def insert_faculty(self, faculty_data: List[Dict[str, Any]]):
        """
        Insert multiple faculty entries into the collection.
        If a faculty member already exists, update the data accordingly.
        """
        for item in faculty_data:
            # The data is in the format: { "Faculty Name": { ... } }
            for faculty_name, faculty_info in item.items():
                existing_faculty = self.collection.find_one({"name": faculty_name})
                if existing_faculty:
                    # Update existing faculty data
                    self.update_faculty(existing_faculty, faculty_info)
                    self.collection.update_one(
                        {"name": faculty_name}, {"$set": existing_faculty}
                    )
                    self.logger.info(f"Updated existing faculty: {faculty_name}")
                else:
                    # Insert new faculty data
                    faculty_info["name"] = (
                        faculty_name  # Ensure the name field is present
                    )
                    self.collection.insert_one(faculty_info)
                    self.logger.info(f"Inserted new faculty: {faculty_name}")

    def update_faculty(self, existing_data: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Update existing faculty data with new data.
        """
        # Update counts
        existing_data["total_citations"] += new_data.get("total_citations", 0)
        existing_data["article_count"] += new_data.get("article_count", 0)
        if existing_data["article_count"] > 0:
            existing_data["average_citations"] = (
                existing_data["total_citations"] / existing_data["article_count"]
            )
        else:
            existing_data["average_citations"] = 0

        # Update lists and deduplicate
        list_fields = ["titles", "dois", "department_affiliations"]
        for field in list_fields:
            existing_list = set(existing_data.get(field, []))
            new_list = set(new_data.get(field, []))
            existing_data[field] = list(existing_list.union(new_list))

        # Update doi_citation_map
        existing_doi_citation_map = existing_data.get("doi_citation_map", {})
        new_doi_citation_map = new_data.get("doi_citation_map", {})
        for doi, citation in new_doi_citation_map.items():
            existing_doi_citation_map[doi] = (
                existing_doi_citation_map.get(doi, 0) + citation
            )
        existing_data["doi_citation_map"] = existing_doi_citation_map


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    mongo_url = os.getenv("MONGODB_URL")

    # Handle article data
    with open(
        "../../data/core/output_files/test_processed_article_stats_obj_data.json", "r"
    ) as f:
        article_data = json.load(f)

    article_db = ArticleDatabase(db_name="Site_Data", collection_name="article_data")
    # article_db.clear_collection()
    article_db.insert_articles(article_data)

    # Handle category data
    with open(
        "../../data/core/output_files/test_processed_category_data.json", "r"
    ) as f:
        category_data = json.load(f)

    category_db = CategoryDatabase(db_name="Site_Data", collection_name="category_data")
    # category_db.clear_collection()
    category_db.insert_categories(category_data)

    # Handle faculty data
    with open(
        "../../data/core/output_files/test_processed_faculty_stats_data.json", "r"
    ) as f:
        faculty_data = json.load(f)

    faculty_db = FacultyDatabase(db_name="Site_Data", collection_name="faculty_data")
    # faculty_db.clear_collection()
    faculty_db.insert_faculty(faculty_data)
