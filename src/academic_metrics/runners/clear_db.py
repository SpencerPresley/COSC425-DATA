from dotenv import load_dotenv
import os
from academic_metrics.DB import DatabaseWrapper


if __name__ == "__main__":
    load_dotenv()
    mongodb_url = os.getenv("MONGODB_URL")
    db = DatabaseWrapper(
        db_name="Site_Data",
        mongo_url=mongodb_url,
    )
    db.clear_collection()
