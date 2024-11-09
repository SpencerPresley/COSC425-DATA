import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt

# Load data
with open("test_processed_category_data.json", "r") as f:
    data = json.load(f)

# Define categories for each level
top_level_categories = ["Business", "Social sciences"]
mid_level_categories = [
    "Business administration and management",
    "Economics",
    "Public policy analysis",
    "Sociology, demography, and population studies",
    "Social sciences, other",
]
low_level_categories = [
    "Business management and administration",
    "Business administration and management nec",
    "Organizational leadership",
    "Applied economics",
    "Development economics and international development",
    "Public policy analysis, general",
    "Sociology, general",
    "Social sciences nec",
]


# Bar Charts
def create_bar_chart(categories, level_name):
    plt.figure(figsize=(15, 8))
    x = np.arange(len(categories))
    width = 0.35

    tc_counts = [data[cat]["tc_count"] for cat in categories]
    cit_avgs = [data[cat]["citation_average"] for cat in categories]

    plt.bar(x - width / 2, tc_counts, width, label="Total Citations")
    plt.bar(x + width / 2, cit_avgs, width, label="Citation Average")
    plt.xticks(x, categories, rotation=45, ha="right")
    plt.title(f"{level_name} Categories - Citation Metrics")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{level_name.lower()}_level_citations_bar.png")
    plt.close()


# Line Charts
def create_line_chart(categories, level_name):
    plt.figure(figsize=(20, 10))
    plt.plot(
        categories,
        [data[cat]["tc_count"] for cat in categories],
        "o-",
        linewidth=2,
        markersize=10,
        label="Total Citations",
    )
    plt.plot(
        categories,
        [data[cat]["citation_average"] for cat in categories],
        "s-",
        linewidth=2,
        markersize=10,
        label="Citation Average",
    )
    plt.xticks(rotation=45, ha="right")
    plt.title(f"{level_name} Categories - Citation Metrics")
    plt.legend(fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(f"{level_name.lower()}_level_citations_line.png")
    plt.close()


# Create all charts
for categories, level in [
    (top_level_categories, "Top"),
    (mid_level_categories, "Mid"),
    (low_level_categories, "Low"),
]:
    create_bar_chart(categories, level)
    create_line_chart(categories, level)
