from academic_metrics.DB.DatabaseSetup import DatabaseWrapper, DatabaseSnapshot
import os
from dotenv import load_dotenv
import json

load_dotenv()


def get_all_data(db_setup: DatabaseWrapper) -> DatabaseSnapshot:
    return db_setup.get_all_data()


if __name__ == "__main__":
    MONGODB_URL = os.getenv("MONGODB_URL")
    db = DatabaseWrapper(db_name="Site_Data", mongo_url=MONGODB_URL)

    (
        articles,
        categories,
        faculty,
    ) = db.get_all_data()

    with open("article_data.json", "w") as f:
        json.dump(articles, f, indent=4)
    with open("category_data.json", "w") as f:
        json.dump(categories, f, indent=4)
    with open("faculty_data.json", "w") as f:
        json.dump(faculty, f, indent=4)
