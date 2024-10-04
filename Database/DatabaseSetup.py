import datetime  # This will be needed later
import os
import json
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from models import CategoryName, Category, CategoryOut
from pprint import pprint

load_dotenv()
mongodb_url = os.getenv("MONGODB_URL")


class DatabaseSetup:
    def __init__(self, mongo_url: str):
        client = MongoClient(mongodb_url, server_api=ServerApi("1"))
        # Send a ping to confirm a successful connection
        try:
            client.admin.command("ping")
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)

    def dump_category_data(self, category_data: list[dict]):
        client = MongoClient(mongodb_url, server_api=ServerApi("1"))
        db = client["Site_Data"]
        collection = db["Categories"]
        collection.insert_many(category_data)
        print("Data inserted successfully")
        client.close

    def update_category_data(self):
        pass


if __name__ == "__main__":
    with open("processed_category_data.json", "r") as file:
        data = json.load(file)

    db_setup = DatabaseSetup(mongodb_url)

    category_data = []
    for key, value in data.items():
        value["name"] = key
        db_output = CategoryOut(**value)
        category_data.append(db_output.dict())

    db_setup.dump_category_data(category_data)
