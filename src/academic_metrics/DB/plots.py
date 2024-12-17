import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle


def plot_category_counts():
    # Get the current file's directory and construct path to JSON
    current_dir = Path(__file__).parent
    json_path = current_dir / "category_data.json"

    # Read and process the data
    df = pd.read_json(json_path)

    # Group by category_name and sum the article_count
    category_counts = (
        df.groupby("category_name")["article_count"].sum().sort_values(ascending=False)
    )
    top_10_categories = category_counts.head(10)

    # Create the plot with PowerPoint dimensions
    plt.figure(figsize=(13.33, 7.5), facecolor="none")
    ax = plt.gca()
    ax.set_facecolor("none")

    # Plot all categories with rounded bars and spacing
    x = np.arange(len(category_counts))
    bars = plt.bar(
        x,
        category_counts.values,
        width=0.6,
        bottom=0,
        capstyle="round",
        edgecolor="none",
    )

    # Customize the plot with Times New Roman
    plt.rcParams["font.family"] = "Times New Roman"
    plt.ylabel("# of Articles", fontsize=12, fontfamily="Times New Roman")
    plt.title(
        "Article Count by Category", fontsize=14, pad=20, fontfamily="Times New Roman"
    )

    # Set up horizontal grid lines every 10 units
    max_y = max(category_counts.values)
    plt.gca().yaxis.set_major_locator(plt.MultipleLocator(10))
    plt.grid(axis="y", linestyle="-", alpha=0.2)

    # Create table data for legend with proper formatting
    table_data = []
    for cat, count in top_10_categories.items():
        table_data.append([cat, f"{count:,d}"])

    # Calculate needed width for the widest category name
    max_cat_len = max(len(str(cat)) for cat in top_10_categories.index)

    # Create the table with specific column widths
    # Position the table inside the plot area
    table = plt.table(
        cellText=table_data,
        loc="upper right",
        bbox=[0.65, 0.6, 0.33, 0.35],  # Adjust to keep table inside plot
        colWidths=[0.8, 0.2],
    )  # Wider first column for category names

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)

    # Style each cell individually
    light_blue = "#E6F3FF"  # Light blue color
    for (row, col), cell in table._cells.items():
        cell.set_text_props(fontfamily="Times New Roman")
        cell.set_facecolor(light_blue)
        cell.set_edgecolor("white")  # White borders for spacing effect
        cell.set_linewidth(2.0)  # Thicker borders for more visible spacing
        cell.PAD = 0.1  # Add padding inside cells

        # Set text alignment
        if col == 0:  # Category names
            cell.get_text().set_horizontalalignment("left")
        else:  # Count values
            cell.get_text().set_horizontalalignment("right")

    # Remove x-axis label and ticks
    plt.xticks([])
    ax.set_xlabel("")

    # Maximize plot area
    plt.margins(x=0.01)

    # Save the plot with transparency
    plt.savefig("category_counts.png", dpi=300, bbox_inches="tight", transparent=True)
    plt.close()


if __name__ == "__main__":
    plot_category_counts()
