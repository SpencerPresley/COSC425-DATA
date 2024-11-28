from academic_metrics.DB.DatabaseSetup import DatabaseWrapper

from dotenv import load_dotenv
import os

load_dotenv()

mongodb_url = os.getenv("MONGODB_URL")
db = DatabaseWrapper(db_name="Site_Data", mongo_url=mongodb_url)

db.clear_collection()
db.close_connection()
