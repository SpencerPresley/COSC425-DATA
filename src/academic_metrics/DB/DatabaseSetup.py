import os
import json
import logging
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.collection import Collection
from typing import List, Dict, Any
import atexit

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DatabaseWrapper:
    """
    A wrapper class for MongoDB operations.
    """

    def __init__(self, *, db_name: str, collection_name: str, mongo_url: str):
        """
        Initialize the DatabaseWrapper with database name, collection name, and MongoDB URL.
        """
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
            logging.info(
                "Pinged your deployment. You successfully connected to MongoDB!"
            )
        except Exception as e:
            logging.error(f"Connection error: {e}")

    def clear_collection(self):
        self.collection.delete_many({})

    def close_connection(self):
        """
        Close the connection to the MongoDB server.
        """
        self.client.close()
        logging.info("Connection closed")


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
        try:
            self.collection.insert_many(article_data)
            logging.info(f"Inserted the articles given {len(article_data)}")
        except Exception as e:
            logging.info(f"Exception occurred {e}")

    def insert_article(self, article: Dict[str, Any]):
        """
        Insert a single article into the collection.
        If the article already exists, merge the new data with the existing data.
        """
        try:
            self.collection.insert_one(article)
            logging.info(f"Inserted new article: {article['title']}")
        except Exception as e:
            logging.info(f"Article already exists: {article['title']}")


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
            existing_category = self.collection.find_one(
                {"category_name": item["category_name"]}
            )
            if existing_category:
                # Add numbers and extend lists
                for k, v in item.items():
                    if isinstance(v, list):
                        existing_category[k].extend(v)
                    elif isinstance(v, (int, float)):
                        existing_category[k] += v
                    else:
                        existing_category[k] = v
                self.collection.update_one(
                    {"category_name": item["category_name"]},
                    {"$set": existing_category},
                )
                logging.info(f"Updated existing category: {item['category_name']}")
            else:
                self.collection.insert_one(item)
                logging.info(f"Inserted new category: {item['category_name']}")


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
    article_db.clear_collection()
    article_db.insert_articles(article_data)

    # Handle category data
    with open(
        "../../data/core/output_files/test_processed_category_data.json", "r"
    ) as f:
        category_data = json.load(f)

    category_db = CategoryDatabase(db_name="Site_Data", collection_name="category_data")
    category_db.clear_collection()
    category_db.insert_categories(category_data)
