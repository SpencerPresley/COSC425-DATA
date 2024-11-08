"""
This script compares publication titles from Digital Measures (DM) and Web of Science (WoS) datasets. It loads titles from both sources, compares them using exact and fuzzy matching, and provides statistics on the overlap and differences between the two datasets. The script also includes utility functions for data processing and visualization.
"""

import os
import json
import glob
import re
from datasketch import MinHash, MinHashLSH
from typing import Set, Dict, List, Any, Tuple
import requests
from academic_metrics.strategies import StrategyFactory
from academic_metrics.utils import WarningManager
import time
from tqdm import tqdm
import sys
from urllib.parse import quote


def query_crossref(
    title: str, max_retries: int = 3, delay: int = 2
) -> Tuple[Dict[str, Any], float]:
    # Convert the title to lowercase except for the first letter of the first word
    words = title.split()
    if words:
        title = (
            words[0].capitalize() + " " + " ".join(word.lower() for word in words[1:])
        )

    # Hardcoded parameters for the specific title

    # Properly encode the title, author, and journal for a URL
    encoded_title = quote(title)

    # Construct the query URL with additional parameters
    url = f"https://api.crossref.org/works?query.title={encoded_title}"
    print(f"Querying Crossref API for title: {title}")
    print(f"URL: {url}")
    input("Press Enter to continue...")

    start_time = time.time()
    for attempt in range(max_retries):
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # print(f"Response: {data['message']['items'][0]['title']}")
            # input("Press Enter to continue...")
            # print(f"Response: {json.dumps(data, indent=4)}")
            # Check if 'items' list is present in the response
            if "message" in data and "items" in data["message"]:
                items = data["message"]["items"]
                if items:
                    with open("items_test.json", "w") as f:
                        json.dump(items[0], f, indent=4)
                    # print(f"Items: {json.dumps(items[0], indent=4)}")
                    # input("Press Enter to continue...")
                    return (
                        json.dumps(items[0], indent=4),
                        time.time() - start_time,
                    )  # Return the first item and query time
            return (
                {},
                time.time() - start_time,
            )  # Return an empty dict and query time if no items are found
        else:
            print(
                f"Attempt {attempt + 1} failed with status code {response.status_code}. Retrying in {delay} seconds..."
            )
            time.sleep(delay)

    print(f"Failed to retrieve data for title: {title} after {max_retries} attempts.")
    return {}, time.time() - start_time


def save_results_to_file(results: List[Dict[str, Any]], file_path: str) -> None:
    # Read existing data
    # print(f"Results: {results}")
    # input("Press Enter to continue...")
    # print(f"Saving results to file: {file_path}")
    # input("Press Enter to continue...")
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            try:
                existing_data = json.load(file)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []
    existing_data_len = len(existing_data)
    print(f"Existing data length before: {existing_data_len}")
    # Extract items from results and append to existing data
    # new_items = []
    for result in results:
        existing_data.append(json.loads(result))

    existing_data_len_after = len(existing_data)
    print(f"Existing data length after: {existing_data_len_after}")
    print(f"Difference: {existing_data_len_after - existing_data_len}")

    with open(file_path, "w") as file:
        json.dump(existing_data, file, indent=4)


def load_titles_from_reformatted_files(directory_path: str) -> Set[str]:
    """
    Load titles from JSON files in the specified directory.

    Args:
        directory_path (str): Path to the directory containing JSON files.

    Returns:
        set: A set of unique titles from all JSON files in the directory.
    """
    titles_set: Set[str] = set()
    json_files: List[str] = glob.glob(os.path.join(directory_path, "*.json"))
    for file_path in tqdm(
        json_files, desc="Loading titles from reformatted files", position=0, leave=True
    ):
        with open(file_path, "r") as f:
            data: Dict[str, Any] = json.load(f)
            titles_set.update(data)

    return titles_set


def load_titles_from_processed_category_data(file_path: str) -> Set[str]:
    """
    Load titles from a processed category data JSON file.

    Args:
        file_path (str): Path to the processed category data JSON file.

    Returns:
        set: A set of unique titles from the processed category data.
    """
    with open(file_path, "r") as f:
        data: Dict[str, Any] = json.load(f)
    titles_set: Set[str] = set()
    for category, info in tqdm(
        data.items(),
        desc="Loading titles from processed category data",
        position=0,
        leave=True,
    ):
        titles_set.update(info["titles"])
    return titles_set


def aggressive_regularize(s: str) -> str:
    """
    Aggressively regularize a string by removing all non-alphanumeric characters and converting to lowercase.

    Args:
        s (str): The input string to regularize.

    Returns:
        str: The regularized string.
    """
    return re.sub(r"\W+", "", s.lower())


def process_titles(titles: Set[str]) -> Set[str]:
    """
    Process a set of titles by applying aggressive regularization to each title.

    Args:
        titles (set): A set of titles to process.

    Returns:
        set: A set of processed titles.
    """
    return set(
        aggressive_regularize(title)
        for title in tqdm(titles, desc="Processing titles", position=0, leave=True)
    )


def compare_datasets(
    dm_titles: Set[str], wos_titles: Set[str]
) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Compare two sets of titles and find exact matches, titles only in DM, and titles only in WoS.

    Args:
        dm_titles (set): Set of titles from Digital Measures.
        wos_titles (set): Set of titles from Web of Science.

    Returns:
        tuple: A tuple containing three sets:
            - exact_matches: Titles that match exactly between DM and WoS.
            - only_in_dm: Titles that are only in DM.
            - only_in_wos: Titles that are only in WoS.
    """
    dm_regularized: Set[str] = process_titles(dm_titles)
    wos_regularized: Set[str] = process_titles(wos_titles)

    exact_matches: Set[str] = dm_regularized.intersection(wos_regularized)
    only_in_dm: Set[str] = dm_regularized - wos_regularized
    only_in_wos: Set[str] = wos_regularized - dm_regularized

    return exact_matches, only_in_dm, only_in_wos


def find_similar_titles(
    dm_titles: Set[str],
    wos_titles: Set[str],
    threshold: float = 0.8,
    crossref: bool = False,
) -> Set[str]:
    """
    Find similar titles between DM and WoS datasets using MinHash LSH.

    Args:
        dm_titles (set): Set of titles from Digital Measures.
        wos_titles (set): Set of titles from Web of Science.
        threshold (float): Similarity threshold for considering titles as similar (default: 0.8).

    Returns:
        set: A set of similar titles found in both datasets.
    """
    lsh: MinHashLSH = MinHashLSH(threshold=threshold, num_perm=128)
    index_prefix: str = "wos" if not crossref else "crossref"

    wos_titles_list: List[str] = list(wos_titles)
    for idx, title in enumerate(
        tqdm(wos_titles_list, desc="Indexing WoS titles", position=0, leave=True)
    ):
        m: MinHash = MinHash(num_perm=128)
        for d in aggressive_regularize(title):
            m.update(d.encode("utf8"))
        lsh.insert(f"{index_prefix}_{idx}", m)

    similar_titles: Set[str] = set()
    for dm_title in tqdm(
        dm_titles, desc="Finding similar titles", position=0, leave=True
    ):
        m: MinHash = MinHash(num_perm=128)
        for d in aggressive_regularize(dm_title):
            m.update(d.encode("utf8"))
        result: List[str] = lsh.query(m)
        if result:
            similar_titles.add(dm_title)

    return similar_titles


def display_titles_only_in_dm(
    final_only_in_dm: Set[str], dm_titles_set: Set[str], wos_or_crossref_str: str
) -> None:
    """
    Display titles that are only present in the Digital Measures dataset.

    Args:
        final_only_in_dm (set): Set of regularized titles only in DM after comparison.
        dm_titles_set (set): Original set of DM titles.

    Returns:
        None
    """
    print(
        f"\nThe titles that Digital Measures has but {wos_or_crossref_str} does not, e.g., the titles we are missing:"
    )
    for title in tqdm(
        dm_titles_set, desc="Displaying titles only in DM", position=0, leave=True
    ):
        if aggressive_regularize(title) in final_only_in_dm:
            print(f"- {title}")


def print_fancy_box(message: str) -> None:
    """
    Print a message in a fancy box with centered text and padding.

    Args:
        message (str): The message to be displayed in the fancy box.

    Returns:
        None
    """
    lines: List[str] = message.split("\n")
    max_line_length: int = max(len(line) for line in lines)
    box_width: int = max_line_length + 10  # Add extra padding

    print("\n╔" + "═" * box_width + "╗")
    print("║" + " " * box_width + "║")  # Add empty line for top padding

    for line in lines:
        padding: int = (box_width - len(line)) // 2
        print(
            "║" + " " * padding + line + " " * (box_width - len(line) - padding) + "║"
        )

    print("║" + " " * box_width + "║")  # Add empty line for bottom padding
    print("╚" + "═" * box_width + "╝\n")

    with open(
        os.path.join(
            os.path.dirname(__file__),
            "static_output_files",
            "REAL_verification_results_SUMMARY.txt",
        ),
        "w",
    ) as f:
        print("\n╔" + "═" * box_width + "╗", file=f)
        print("║" + " " * box_width + "║", file=f)  # Add empty line for top padding

        for line in lines:
            padding: int = (box_width - len(line)) // 2
            print(
                "║"
                + " " * padding
                + line
                + " " * (box_width - len(line) - padding)
                + "║",
                file=f,
            )

        print("║" + " " * box_width + "║", file=f)  # Add empty line for bottom padding
        print("╚" + "═" * box_width + "╝\n", file=f)


def do_dm_verification(crossref: bool = False, second_run: bool = False) -> None:
    """
    Main function to execute the comparison between Digital Measures and Web of Science datasets.

    This function loads titles from both datasets, performs comparisons, finds similar titles,
    calculates statistics, and displays the results.

    Args:
        None

    Returns:
        None
    """
    if crossref:
        print(f"Analysis for Crossref API\n\n")
    else:
        print(f"\n\nAnalysis for Web of Science Export\n\n")

    reformatted_files_dir: str = os.path.join(
        os.path.dirname(__file__), "reformattedFiles"
    )
    processed_category_data_file: str = os.path.join(
        os.path.dirname(__file__), "static_output_files", "processed_category_data.json"
    )
    test_processed_category_data_file: str = os.path.join(
        os.path.dirname(__file__), "test_processed_category_data.json"
    )

    wos_or_crossref_str: str = (
        "Web of Science Export" if not crossref else "Crossref API"
    )

    dm_titles_set: Set[str] = load_titles_from_reformatted_files(reformatted_files_dir)
    wos_titles_set: Set[str] = set()
    if crossref:
        wos_titles_set: Set[str] = load_titles_from_processed_category_data(
            test_processed_category_data_file
        )
    else:
        wos_titles_set: Set[str] = load_titles_from_processed_category_data(
            processed_category_data_file
        )

    print(f"Initial Digital Measures titles: {len(dm_titles_set)}")
    print(f"Initial {wos_or_crossref_str} titles: {len(wos_titles_set)}")

    exact_matches, only_in_dm, only_in_wos = compare_datasets(
        dm_titles_set, wos_titles_set
    )

    print("\nInitial comparison:")
    print(f"Exact matches: {len(exact_matches)}")
    print(
        f"Only in Digital Measures: {len(only_in_dm)} = {len(dm_titles_set)} - {len(exact_matches)}"
    )
    print(
        f"Only in {wos_or_crossref_str}: {len(only_in_wos)} = {len(wos_titles_set)} - {len(exact_matches)}"
    )
    print(
        f"\n\nQuerying Crossref API for titles in Digital Measures that are not present in the initial {wos_or_crossref_str} dataset..."
    )

    print("\nSearching for similar titles...")
    similar_titles: Set[str] = find_similar_titles(
        only_in_dm, only_in_wos, threshold=0.8, crossref=crossref
    )
    print(f"Similar titles found: {len(similar_titles)}")

    final_common_set: Set[str] = exact_matches.union(
        set(aggressive_regularize(title) for title in similar_titles)
    )
    final_only_in_dm: Set[str] = only_in_dm - set(
        aggressive_regularize(title) for title in similar_titles
    )
    final_only_in_wos: Set[str] = only_in_wos - set(
        aggressive_regularize(title) for title in similar_titles
    )

    print("\nFinal results:")
    print(
        f"Final common set: {len(final_common_set)} = {len(exact_matches)} + {len(similar_titles)}"
    )
    print(
        f"Final only in Digital Measures: {len(final_only_in_dm)} = {len(only_in_dm)} - {len(similar_titles)}"
    )
    print(
        f"Final only in {wos_or_crossref_str}: {len(final_only_in_wos)} = {len(only_in_wos)} - {len(similar_titles)}"
    )

    total_unique: int = (
        len(final_common_set) + len(final_only_in_dm) + len(final_only_in_wos)
    )
    print(
        f"\nTotal unique titles: {total_unique} = {len(final_common_set)} + {len(final_only_in_dm)} + {len(final_only_in_wos)}"
    )

    dm_exclusive_percentage: float = (len(final_only_in_dm) / len(dm_titles_set)) * 100
    wos_exclusive_percentage: float = (
        len(final_only_in_wos) / len(wos_titles_set)
    ) * 100

    print(
        f"\nPercentage of Digital Measures titles not in {wos_or_crossref_str}: {dm_exclusive_percentage:.2f}% = ({len(final_only_in_dm)} / {len(dm_titles_set)}) * 100"
    )
    print(
        f"Percentage of {wos_or_crossref_str} titles not in Digital Measures: {wos_exclusive_percentage:.2f}% = ({len(final_only_in_wos)} / {len(wos_titles_set)}) * 100"
    )

    percent_wos_has_from_dm: float = 100 - (
        (len(final_only_in_dm) / len(dm_titles_set)) * 100
    )
    print(
        f"Percent of Digital Measures titles that {wos_or_crossref_str} has: {percent_wos_has_from_dm:.2f}%"
    )

    display_titles_only_in_dm(final_only_in_dm, dm_titles_set, wos_or_crossref_str)

    summary = (
        "SUMMARY\n\n"
        f"The {wos_or_crossref_str} export technique is only missing {dm_exclusive_percentage:.2f}% "
        f"of the titles that Digital Measures has.\n\n"
        f"This means that the {wos_or_crossref_str} export technique only lacks 1 out of every "
        f"{1 / dm_exclusive_percentage * 100:.0f} titles that DM has."
    )
    print_fancy_box(summary)

    if crossref and len(final_only_in_dm) > 0:
        # Query Crossref API for titles in Digital Measures that are not present in the initial {wos_or_crossref_str} dataset
        crossref_results = []
        estimated_time_per_query = None

        title_to_exclude = "Reporting Cash Receipts over $10,000"
        dm_titles_set = {
            title
            for title in dm_titles_set
            if aggressive_regularize(title) != aggressive_regularize(title_to_exclude)
        }
        final_only_in_dm = {
            title
            for title in final_only_in_dm
            if aggressive_regularize(title) != aggressive_regularize(title_to_exclude)
        }

        # Inform the user about the exclusion
        print(
            f"The paper '{title_to_exclude}' is published in the Tax Adviser, which does not provide a DOI. It is considered a professional magazine/trade publication rather than an academic journal."
        )

        with tqdm(
            total=len(final_only_in_dm),
            desc="Querying Crossref API",
            position=0,
            leave=True,
        ) as pbar:
            if not second_run:
                if len(final_only_in_dm) > 0:
                    for i, title in enumerate(final_only_in_dm):
                        # Find the original title from dm_titles_set that matches the regularized title
                        original_title = next(
                            (
                                t
                                for t in dm_titles_set
                                if aggressive_regularize(t) == title
                            ),
                            None,
                        )
                        if original_title:
                            result, query_time = query_crossref(original_title)
                            if result:
                                crossref_results.append(result)

                        if i == 0:
                            estimated_time_per_query = query_time * (
                                len(final_only_in_dm) - i + 1
                            )

                        pbar.update(1)
                        if estimated_time_per_query:
                            pbar.set_postfix(
                                {
                                    "Estimated time left": f"{(len(final_only_in_dm) - pbar.n) * estimated_time_per_query:.0f}s"
                                }
                            )

                    # Save crossref results to a file in 'input_files' directory via appending to the current file there
                    crossref_file_path = os.path.join(
                        os.path.dirname(__file__),
                        "input_files",
                        "2017-2024-paper-doi-list.json",
                    )
                    save_results_to_file(crossref_results, crossref_file_path)

                    # Run WosClassification with the new data
                    strategy_factory = StrategyFactory()
                    warning_manager = WarningManager()

                    input_dir_path = "./input_files"
                    output_dir_path = "./crossref_split_files"
                    input_dir_path = os.path.expanduser(input_dir_path)
                    output_dir_path = os.path.expanduser(output_dir_path)
                    # Instantiate the orchestrator class
                    wos_classifiction = WosClassification(
                        input_dir_path=input_dir_path,
                        output_dir_path=output_dir_path,
                        strategy_factory=strategy_factory,
                        warning_manager=warning_manager,
                        crossref_run=True,
                        make_files=True,
                        extend=True,
                    )

                    print(
                        f"second_run: {second_run}, crossref_results: {len(crossref_results)}"
                    )
                    input("Press Enter to continue...")

                    # call main again to run the analysis on the updated data
                    # Only call main again if there are new results to process and it's not the second run
                    if crossref_results and not second_run:
                        print("Calling main again for the second run.")
                        do_dm_verification(crossref=True, second_run=True)
                    else:
                        print("Stopping recursion.")


def run_dm_verification() -> None:
    """
    Run the Digital Measures verification process for both Crossref and Web of Science.

    This function orchestrates the entire process, including data loading, comparison,
    and analysis, for both Crossref and Web of Science datasets."""
    crossref: bool = True
    do_dm_verification(crossref=crossref)
    do_dm_verification(crossref=False)
