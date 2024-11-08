import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from datetime import datetime
import json

# Read the data
with open('test_processed_category_data.json', 'r') as f:
    category_data = json.load(f)
with open('test_processed_crossref_article_stats_obj_data.json', 'r') as f:
    article_data = json.load(f)

# Style selection
for i, style in enumerate(plt.style.available):
    print(f"{i}: {style}")
style = input("Select a style: ")
plt.style.use(plt.style.available[int(style)])

# 1. Research Impact Timeline
plt.figure(figsize=(12, 6))
dates = []
citations = []
titles = []

for doi, article in article_data.items():
    date = datetime.strptime(article['date_published_online'], '%Y-%m-%d')
    dates.append(date)
    citations.append(article['tc_count'])
    titles.append(article['title'] if isinstance(article['title'], str) else article['title'][0])

plt.scatter(dates, citations, s=100, alpha=0.6)
plt.xlabel('Publication Date')
plt.ylabel('Citations')
plt.title('Research Impact Over Time')
# Annotate points with high citations
for i, (date, cite, title) in enumerate(zip(dates, citations, titles)):
    if cite > 20:  # Only label highly cited papers
        plt.annotate(title[:30] + '...', (date, cite), 
                    xytext=(10, 10), textcoords='offset points')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 2. Category Network Graph
plt.figure(figsize=(12, 6))
G = nx.Graph()

# Add nodes (categories)
for category in category_data:
    G.add_node(category, size=category_data[category]['tc_count'])

# Add edges (shared papers)
for cat1 in category_data:
    for cat2 in category_data:
        if cat1 < cat2:  # Avoid duplicates
            shared_papers = len(set(category_data[cat1]['doi_list']) & 
                              set(category_data[cat2]['doi_list']))
            if shared_papers > 0:
                G.add_edge(cat1, cat2, weight=shared_papers)

# Draw the network
pos = nx.spring_layout(G, k=1, iterations=50)
node_sizes = [G.nodes[node]['size'] * 20 for node in G.nodes()]
edge_weights = [G.edges[edge]['weight'] * 2 for edge in G.edges()]

nx.draw_networkx_nodes(G, pos, node_size=node_sizes, alpha=0.7)
nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.4)
nx.draw_networkx_labels(G, pos, font_size=8)

plt.title('Research Category Network\n(Node size = total citations, Edge thickness = shared papers)')
plt.axis('off')
plt.tight_layout()
plt.show()

# 3. Impact Distribution
plt.figure(figsize=(12, 6))
impact_data = pd.DataFrame.from_dict(category_data, orient='index')
impact_data = impact_data.sort_values('citation_average', ascending=True)

# Create horizontal bar chart
plt.barh(range(len(impact_data)), impact_data['citation_average'])
plt.yticks(range(len(impact_data)), impact_data.index, fontsize=8)
plt.xlabel('Average Citations per Paper')
plt.title('Research Impact by Category')
plt.tight_layout()
plt.show()