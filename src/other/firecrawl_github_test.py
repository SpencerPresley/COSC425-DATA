from langchain_community.document_loaders import FireCrawlLoader
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
)
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import json
from typing import Optional

from pydantic import BaseModel, Field

import requests
import base64
from urllib.parse import urlparse


def parse_github_url(url):
    """Parses your GitHub URL and extracts the repository owner and name."""
    parsed_url = urlparse(url)
    path_segments = parsed_url.path.strip("/").split("/")
    if len(path_segments) >= 2:
        owner, repo = path_segments[0], path_segments[1]
        return owner, repo
    else:
        raise ValueError("Invalid GitHub URL provided!")


def fetch_repo_content(owner, repo, path="", token=None):
    """
    Fetches the content of your GitHub repository.
    """
    base_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(base_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


def get_file_content(file_info):
    """
    Retrieves and decodes the content of files
    """
    if file_info["encoding"] == "base64":
        return base64.b64decode(file_info["content"]).decode("utf-8")
    else:
        return file_info["content"]


def build_directory_tree(owner, repo, path="", token=None, indent=0, file_paths=[]):
    """
    Builds a string representation of the directory tree and collects file paths.
    """
    items = fetch_repo_content(owner, repo, path, token)
    tree_str = ""
    for item in items:
        if ".github" in item["path"].split("/"):
            continue
        if item["type"] == "dir":
            tree_str += "    " * indent + f"[{item['name']}/]\n"
            tree_str += build_directory_tree(
                owner, repo, item["path"], token, indent + 1, file_paths
            )[0]
        else:
            tree_str += "    " * indent + f"{item['name']}\n"
            # Indicate which file extensions should be included in the prompt!
            if item["name"].endswith(
                (".py", ".ipynb", ".html", ".css", ".js", ".jsx", ".rst", ".md")
            ):
                file_paths.append((indent, item["path"]))
    return tree_str, file_paths


def retrieve_github_repo_info(url, token=None):
    """Retrieves and formats repository information, including README, the directory tree,
    and file contents, while ignoring the .github folder.
    """
    owner, repo = parse_github_url(url)

    try:
        readme_info = fetch_repo_content(owner, repo, "README.md", token)
        readme_content = get_file_content(readme_info)
        formatted_string = f"README.md:\n```\n{readme_content}\n```\n\n"
    except Exception as e:
        formatted_string = "README.md: Not found or error fetching README\n\n"

    directory_tree, file_paths = build_directory_tree(owner, repo, token=token)

    formatted_string += f"Directory Structure:\n{directory_tree}\n"

    for indent, path in file_paths:
        file_info = fetch_repo_content(owner, repo, path, token)
        file_content = get_file_content(file_info)
        formatted_string += (
            "\n"
            + "    " * indent
            + f"{path}:\n"
            + "    " * indent
            + "```\n"
            + file_content
            + "\n"
            + "    " * indent
            + "```\n"
        )

    return formatted_string


def run_firecrawl_github_test(repo: str):
    from dotenv import load_dotenv

    load_dotenv()
    # You provide a Github repo URL and a Github personal access token.
    # How to get an access token: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
    github_url = f"https://github.com/{repo}"
    token = os.getenv(
        "GITHUB_TOKEN"
    )  # Github access token (go to Developer Settings to generate one)

    owner, repo = parse_github_url(github_url)
    output_file_name = f"{repo}-formatted-prompt.txt"

    formatted_repo_info = retrieve_github_repo_info(github_url, token=token)
    with open(output_file_name, "w", encoding="utf-8") as file:
        file.write(formatted_repo_info)

    print(f"Repository information has been saved to {output_file_name}")


if __name__ == "__main__":
    repos = ["SpencerPresley/HoyaHacks2025Backend"]
    for repo in repos:
        run_firecrawl_github_test(repo)
