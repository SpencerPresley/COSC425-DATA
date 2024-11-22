from dotenv import load_dotenv
import os
import json

from academic_metrics.DB import DatabaseWrapper
from academic_metrics.constants import OUTPUT_FILES_DIR_PATH


if __name__ == "__main__":
    load_dotenv()
    mongodb_url = os.getenv("MONGODB_URL")
    db = DatabaseWrapper(
        db_name="Site_Data",
        mongo_url=mongodb_url,
    )

    with open(OUTPUT_FILES_DIR_PATH / "test_processed_category_data.json", "r") as f:
        category_data = json.load(f)

    with open(
        OUTPUT_FILES_DIR_PATH / "test_processed_global_faculty_stats_data.json", "r"
    ) as f:
        faculty_data = json.load(f)

    with open(
        OUTPUT_FILES_DIR_PATH / "test_processed_article_stats_obj_data.json", "r"
    ) as f:
        article_data = json.load(f)

    db.insert_categories(category_data)
    db.insert_faculty(faculty_data)
    db.insert_articles(article_data)
