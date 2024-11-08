import json
import pandas as pd

# Define the paths to your JSON files
json_files = [
    'test_processed_faculty_stats_data.json',
    'test_processed_crossref_article_stats_data.json',
    'test_processed_category_data.json',
    'test_processed_crossref_article_stats_obj_data.json'
]

# Initialize empty DataFrames
df_faculty_stats = pd.DataFrame()
df_article_stats = pd.DataFrame()
df_category_stats = pd.DataFrame()

for file in json_files:
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Process faculty stats data
    if 'faculty_stats' in str(data):
        for category, details in data.items():
            faculty_stats = details.get('faculty_stats', {})
            for faculty_name, stats in faculty_stats.items():
                stats_flat = pd.json_normalize(stats, sep='_')
                stats_flat['faculty_name'] = faculty_name
                stats_flat['category'] = category
                df_faculty_stats = pd.concat([df_faculty_stats, stats_flat], ignore_index=True)
    
    # Process article stats data (by category)
    elif 'article_citation_map' in str(data):
        for category, details in data.items():
            article_citation_map = details.get('article_citation_map', {})
            for doi, article_data in article_citation_map.items():
                article_data_flat = pd.json_normalize(article_data, sep='_')
                article_data_flat['doi'] = doi
                article_data_flat['category'] = category
                df_article_stats = pd.concat([df_article_stats, article_data_flat], ignore_index=True)
    
    # Process article stats data (by DOI)
    elif any(key.startswith('10.') for key in data.keys()):
        for doi, article_data in data.items():
            article_data_flat = pd.json_normalize(article_data, sep='_')
            article_data_flat['doi'] = doi
            df_article_stats = pd.concat([df_article_stats, article_data_flat], ignore_index=True)
    
    # Process category data
    elif 'doi_list' in str(data):
        for category, category_data in data.items():
            category_data_flat = pd.json_normalize(category_data, sep='_')
            category_data_flat['category'] = category
            df_category_stats = pd.concat([df_category_stats, category_data_flat], ignore_index=True)

# Now, we need to merge all DataFrames into one comprehensive DataFrame

# Merge article stats with faculty stats on 'doi' and 'faculty_name'

# Expand 'faculty_members' in df_article_stats
if not df_article_stats.empty and 'faculty_members' in df_article_stats.columns:
    df_article_stats = df_article_stats.explode('faculty_members').rename(columns={'faculty_members': 'faculty_name'})
    # Ensure 'faculty_name' is a string
    df_article_stats['faculty_name'] = df_article_stats['faculty_name'].astype(str)
else:
    df_article_stats['faculty_name'] = None

# Merge df_article_stats with df_faculty_stats on 'faculty_name'
df_merged = pd.merge(df_article_stats, df_faculty_stats, on='faculty_name', how='outer', suffixes=('_article', '_faculty'))

# Combine 'category' columns into one
df_merged['category'] = df_merged['category_article'].combine_first(df_merged['category_faculty'])

# Optionally, drop the old 'category' columns
df_merged = df_merged.drop(columns=['category_article', 'category_faculty'])

# Merge with category stats on 'category'
df_final = pd.merge(df_merged, df_category_stats, on='category', how='outer', suffixes=('', '_category'))

# Drop duplicates
df_final = df_final.drop_duplicates()

# Output the final DataFrame
print("Final Merged DataFrame:")
print(df_final.head())

df_final.to_csv('combined_stats.csv', index=False)