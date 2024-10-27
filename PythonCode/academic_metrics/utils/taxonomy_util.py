import json
import os

class Taxonomy:
    def __init__(self):
        self.taxonomy = {}
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "..", "data")
        taxonomy_path = os.path.join(data_dir, "core", "taxonomy", "taxonomy.json")
        with open(taxonomy_path, "r") as f:
            self.taxonomy = json.load(f)
            
    def __str__(self):
        return json.dumps(self.taxonomy, indent=4)

    def get_top_categories(self):
        return list(self.taxonomy.keys())

    def get_mid_categories(self, top_category):
        return list(self.taxonomy[top_category].keys())

    def get_low_categories(self, top_category, mid_category):
        return self.taxonomy[top_category][mid_category]


if __name__ == "__main__":
    taxonomy = Taxonomy()
    print(taxonomy.get_top_categories())
