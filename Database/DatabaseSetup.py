import os
import json
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.collection import Collection
from typing import List, Dict, Any
import atexit

"""
Needed additions:
    - Function to get list of urls from the databsae
    - function to get a single article
    - functionality to add category data
    - ability to query statistics for both and ability to add remove and check for elements 
"""


class DatabaseWrapper:
    def __init__(self, *, db_name: str, collection_name: str):
        load_dotenv()
        self.mongo_url = os.getenv("MONGODB_URL")
        self.client = MongoClient(self.mongo_url, server_api=ServerApi("1"))
        self.db = self.client[db_name]
        self.collection: Collection = self.db[collection_name]
        self._test_connection()
        atexit.register(self.close_connection)

    def _test_connection(self):
        try:
            self.client.admin.command("ping")
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(f"Connection error: {e}")

    def insert_item(self, data: Dict[str, Any]):
        try:
            self.collection.insert_one(data)
            print("Insert Complete for one item")
        except Exception as e:
            print(f"Insert failed: {e}")

    def insert_data(self, data: List[Dict[str, Any]]):
        try:
            self.collection.insert_many(data)
            print("Data inserted successfully")
        except Exception as e:
            print(f"Insert error: {e}")

    def update_data(self, query: Dict[str, Any], update: Dict[str, Any]):
        try:
            self.collection.update_many(query, {"$set": update})
            print("Data updated successfully")
        except Exception as e:
            print(f"Update error: {e}")

    def find_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            return list(self.collection.find(query))
        except Exception as e:
            print(f"Find error: {e}")
            return []

    def show_all(self):
        self.collection.find_all()
    
    def delete_all(self):
        try:
            self.collection.delete_many({})
            print("All documents deleted successfully")
        except Exception as e:
            print(f"Delete all error: {e}")

    def close_connection(self):
        self.client.close()
        print("Connection closed")


class ArticleDatabase(DatabaseWrapper):
    def __init__(self, db_name: str, collection_name: str):
        super().__init__(db_name=db_name, collection_name=collection_name)

    def insert_articles(self, article_data: Dict[str, Any]):
        data = []
        for key, value in article_data.items():
            value["_id"] = value['url']
            data.append(value)

        self.insert_data(data)

    def insert_article(self, identifier: str, article: Dict[str, Any]):
        article["_id"] = identifier
        self.insert_item(article)

class CategoryDatabase(DatabaseWrapper):
    def __init__(self, db_name: str, collection_name: str):
        super().__init__(db_name=db_name, collection_name=collection_name)

    def insert_categories(self, category_data: Dict[str, Any]):
        data = []
        for key, value in category_data.items():
            value["name"] = key
            data.append(value)

        self.insert_data(data)


if __name__ == "__main__":
    with open("article_data.json", "r") as file:
        data = json.load(file)

    database = ArticleDatabase(db_name='Site_Data', collection_name='article_data')

    database.delete_all()

    database.insert_articles(data)

    # with open("category_data.json", "r") as f:
    #     cat_data = json.load(fp=f)

    # cat_database = CategoryDatabase(db_name="Site_Data", collection_name='category_data')

    # cat_database.insert_categories(cat_data)

