import ijson
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utilities import Utilities
import logging
from enums import AttributeTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="crossref_authors_extraction.log",
    filemode="w",
)


def get_crossref_ab(file_path: str, output_file_path: str, utils: Utilities):
    items = ijson.items(open(file_path, "r"), "item")
    authors = []
    for i, item in enumerate(items):
        new_authors = utils.get_attributes(item, [AttributeTypes.CROSSREF_AUTHORS])[
            AttributeTypes.CROSSREF_AUTHORS
        ][1]
        authors.extend(new_authors)
        logging.info(
            f"Item {i}: Added {len(new_authors)} authors. Total authors: {len(authors)}"
        )
        if i % 100 == 0:
            logging.info(f"Current authors list size: {sys.getsizeof(authors)} bytes")
    authors_dict = {"authors": authors}
    logging.info(f"Final authors list size: {sys.getsizeof(authors)} bytes")
    logging.info(f"Final authors dict size: {sys.getsizeof(authors_dict)} bytes")

    with open(output_file_path, "w") as file:
        json.dump(authors_dict, file, indent=4)
    logging.info(f"Output file size: {os.path.getsize(output_file_path)} bytes")


if __name__ == "__main__":
    utils = Utilities()
    file_path = "paper-doi-list.json"
    output_file_path = "paper-authors-list.json"
    get_crossref_ab(file_path, output_file_path, utils)
