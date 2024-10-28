import os
import json
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.collection import Collection
from typing import List, Dict, Any
import atexit

class DatabaseWrapper:
    def __init__(self, db_name: str, collection_name: str):
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
        
    def insert_articles(self, article_data: Dict[str, Any]):

        article_data = []
        for key, value in article_data.items():
            value["_id"] = key
            article_data.append(value)

        self.insert_data(article_data)

    def close_connection(self):
        self.client.close()
        print("Connection closed")

if __name__ == "__main__":
    with open("article_data.json", "r") as file:
            data = json.load(file)

    database = DatabaseWrapper()

    database.insert_articles(data)

