import json

with open("test_processed_crossref_article_stats_obj_data.json", "r") as f:
    data = json.load(f)

url_list = [article['url'] for article in data.values()]

# Write to JSON file with indentation
with open("article_urls.json", "w") as f:
    json.dump(url_list, f, indent=4)