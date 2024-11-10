import json
from academic_metrics.other.in_memory_taxonomy import TAXONOMY_AS_STRING
from typing import Dict, List

# Alias for the taxonomy dictionary structure to be used for type hinting the taxonomy dictionary
TaxonomyDict = Dict[str, Dict[str, List[str]]]


class Taxonomy:
    def __init__(self) -> None:
        self.taxonomy: TaxonomyDict = self._load_taxonomy_from_string(
            TAXONOMY_AS_STRING
        )

    def __str__(self) -> str:
        return json.dumps(self.taxonomy, indent=4)

    @staticmethod
    def _load_taxonomy_from_string(taxonomy_str: str) -> TaxonomyDict:
        return json.loads(taxonomy_str)

    def get_top_categories(self) -> List[str]:
        return list(self.taxonomy.keys())

    def get_mid_categories(self, top_category: str) -> List[str]:
        return list(self.taxonomy[top_category].keys())

    def get_low_categories(self, top_category: str, mid_category: str) -> List[str]:
        return self.taxonomy[top_category][mid_category]

    def get_taxonomy(self) -> TaxonomyDict:
        return self.taxonomy


if __name__ == "__main__":
    taxonomy: Taxonomy = Taxonomy()
    top_categories: List[str] = taxonomy.get_top_categories()
    print(top_categories)
    for top_category in top_categories:
        mid_categories: List[str] = taxonomy.get_mid_categories(top_category)
        print(f"top category: \n{top_category}, \nmid categories: \n{mid_categories}\n")
        for mid_category in mid_categories:
            low_categories: List[str] = taxonomy.get_low_categories(
                top_category, mid_category
            )
            print(
                f"mid category: \n{mid_category}, \nlow categories: \n{low_categories}\n"
            )
        print("\n\n")
