import json
import re
import os

current_file_location = os.path.dirname(os.path.abspath(__file__))


class TitleExtractor:
    def __init__(self, json_file_path, output_file_name):
        self.json_file_path = json_file_path
        self.output_file_name = output_file_name
        self.citation_count = 0
        self.match_count = 0
        self.non_match_count = 0
        self.non_match_titles = []
        self.titles = []

        if not os.path.exists(self.json_file_path):
            raise FileNotFoundError(f"File not found: {self.json_file_path}")

        self.data = self.load_json_data()

        output_dir = os.path.dirname(self.output_file_name)
        os.makedirs(output_dir, exist_ok=True)

    def load_json_data(self):
        with open(self.json_file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def extract_titles(self):
        category_name = list(self.data.keys())[0]
        for item in self.data[category_name]:
            if "Citation" in item:
                self.citation_count += 1
                citation = item["Citation"]
                title = self.extract_title_from_citation(citation)
                if title:
                    self.match_count += 1
                    self.titles.append(title)
                else:
                    self.non_match_count += 1
                    self.non_match_titles.append(citation)
        return self.titles

    def extract_title_from_citation(self, citation):
        # Remove content in square brackets
        citation = re.sub(r"\[.*?\]", "", citation)

        # Remove URLs
        citation = re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "",
            citation,
        )

        # Try to match the title (including all-caps titles)
        patterns = [
            r"\(\d{4}\)\.\s*(.*?)\.\s*(?:[A-Z][a-z]+\s+)+",
            r"\(\d{4}\)\.\s*(.*?)(?:\.\s*(?:https?://|www\.|\[|$))",
            r"\(\d{4}\)\.\s*([A-Z\s]+)\.",  # For all-caps titles
            r"\(\d{4}\)\.\s*(.*?)\.",  # Fallback pattern
            r"\(in press\)\.\s*(.*?)\.",  # For "in press" citations
        ]

        for pattern in patterns:
            match = re.search(pattern, citation)
            if match:
                title = match.group(1).strip()
                # Convert all-caps titles to title case
                if title.isupper():
                    title = title.title()
                return title

        return None

    def get_titles(self):
        return self.extract_titles()

    def save_titles_to_json(self):
        with open(self.output_file_name, "w", encoding="utf-8") as file:
            json.dump(self.titles, file, indent=4, ensure_ascii=False)

    def print_stats(self):
        print(f"Total Citations Processed: {self.citation_count}")
        print(f"Matches Found: {self.match_count}")
        print(f"Non-Matches: {self.non_match_count}")
        if self.non_match_count > 0:
            print("Non-matching citations:")
            for citation in self.non_match_titles:
                print(citation)


# Usage for Economics
economics_json_path = os.path.abspath(
    os.path.join(current_file_location, "..", "..", "json_data", "Economics.json")
)
economics_output_path = os.path.abspath(
    os.path.join(current_file_location, "reformattedFiles", "economics_output.json")
)

# Usage for Accounting and Legal Studies
accounting_json_path = os.path.abspath(
    os.path.join(
        current_file_location,
        "..",
        "..",
        "json_data",
        "Accounting-and-Legal-Studies.json",
    )
)
accounting_output_path = os.path.abspath(
    os.path.join(current_file_location, "reformattedFiles", "accounting_output.json")
)

# Usage for Finance
finance_json_path = os.path.abspath(
    os.path.join(current_file_location, "..", "..", "json_data", "Finance.json")
)
finance_output_path = os.path.abspath(
    os.path.join(current_file_location, "reformattedFiles", "finance_output.json")
)

# Usage for Information and Decision Sciences
ids_json_path = os.path.abspath(
    os.path.join(
        current_file_location,
        "..",
        "..",
        "json_data",
        "Information-and-Decision-Sciences.json",
    )
)
ids_output_path = os.path.abspath(
    os.path.join(current_file_location, "reformattedFiles", "ids_output.json")
)

# Usage for Management
management_json_path = os.path.abspath(
    os.path.join(current_file_location, "..", "..", "json_data", "Management.json")
)
management_output_path = os.path.abspath(
    os.path.join(current_file_location, "reformattedFiles", "management_output.json")
)

# Usage for Marketing
marketing_json_path = os.path.abspath(
    os.path.join(current_file_location, "..", "..", "json_data", "Marketing.json")
)
marketing_output_path = os.path.abspath(
    os.path.join(current_file_location, "reformattedFiles", "marketing_output.json")
)

# Process all six JSON files
for json_path, output_path in [
    (economics_json_path, economics_output_path),
    (accounting_json_path, accounting_output_path),
    (finance_json_path, finance_output_path),
    (ids_json_path, ids_output_path),
    (management_json_path, management_output_path),
    (marketing_json_path, marketing_output_path),
]:
    try:
        extractor = TitleExtractor(json_path, output_path)
        titles = extractor.get_titles()
        extractor.save_titles_to_json()
        print(f"\nProcessing {os.path.basename(json_path)}:")
        extractor.print_stats()
    except FileNotFoundError as e:
        print(e)
