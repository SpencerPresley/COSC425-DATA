import json
import os
import logging
from pydantic import BaseModel
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from dotenv import load_dotenv
from openai import OpenAI
from selenium.webdriver.firefox.options import Options
from academic_metrics.ChainBuilder import ChainManager
from typing import Any, Dict, Optional

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("scraper.log")],
)
logger = logging.getLogger(__name__)

# Suppress logging for certain libraries
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("ChainBuilder").setLevel(logging.WARNING)


# create the cleaner output model
class CleanerOutput(BaseModel):
    abstract: str
    extra_context: Dict[str, Any]


def setup_chain(output_list):
    # instanciate the chain manager
    chain_manager = ChainManager("gpt-4o-mini", api_key)

    # create a general schema for the model to output text in
    json_schema = """
    {
        "abstract": <this is where you should place the abstract, or "" if one is not found>,
        "extra_context": <this is a dictionary of key value pairs of extra content you find, always make the key indicative of what the extra content in the value is>
    }
    """

    # create the system prompt
    system_prompt = """
    You are an expert at cleaning text from a website. You will be provided some text and you are to clean it into markdown format and do the following:

    1) Identify if there is an abstract
    2) Pull out any extra content other than the abstract

    You are to format your results in the following json structure:
    {json_structure}

    If you find an abstract you are to put in the abstract section, if you don't find one put an empty string.

    For extra_context you are to put a key value pair of anything else you find. If you do not find anything else then you are to still make 1 key value pair indicating so. DO NOT BE LAZY.

    In extra_context be congnizant of what type of element you're putting in there, for example if you find keywords, do you not just provide a string but rather a list of strings that are the keywords. Be mindful of these types of things at all times, do not limit it to this example.

    IMPORTANT: You are to always output your response in the json format provided, if you do not output your response in the format provided you have failed.
    IMPORTANT: DO NOT WRAP YOUR JSON IN ```json\njson content\n``` JUST RETURN THE JSON
    IMPORTANT: The abstract and has_abstract fields ARE REQUIRED AND MUST ALWAYS BE PROVIDED, if you cannot find an abstract STILL PUT AN EMPTY STRING IN THERE.
    IMPORTANT: extra_context IS NOT AN OPTIONAL FIELD YOUR ARE ALWAYS TO PROVIDE AT LEAST ONE KEY VALUE PAIR WITHIN IT. 
    """
    # setup ability to pass the list into the prompt
    human_prompt = """
    Output list:
    {output_list}
    """

    # add the chain
    chain_manager.add_chain_layer(
        system_prompt=system_prompt,
        human_prompt=human_prompt,
        ignore_output_passthrough_key_name_error=True,
        parser_type="pydantic",
        return_type="json",
        pydantic_output_model=CleanerOutput,
    )

    prompt_variables = {"output_list": str(output_list), "json_structure": json_schema}

    results = chain_manager.run(prompt_variables_dict=prompt_variables)

    results_dict = json.loads(results)

    return results_dict


def get_abstract(url):
    """
    Fetches and processes the abstract from a given URL.

    This function uses Selenium to fetch the content of the provided URL in headless mode.
    It then parses the HTML content using BeautifulSoup and attempts to find the abstract
    in common HTML tags such as <meta>, <p>, <div>, <article>, and <span>. The collected
    content is processed using a chain of prompts managed by the ChainManager.

    Args:
        url (str): The URL of the web page to fetch the abstract from.

    Returns:
        Optional[dict]: A dictionary containing the processed abstract and additional context,
                        or None if no abstract is found or an error occurs.

    Raises:
        Exception: Logs any exceptions that occur during the fetching and processing of the URL.

    Example:
        data = get_abstract('http://dx.doi.org/10.3197/096327117x14913285800742')
        print(data)
    """
    if url:
        try:
            logger.debug(f"Fetching URL: {url}")
            # Set up the WebDriver in headless mode
            options = Options()
            options.add_argument(
                "--headless"
            )  # headless will prevent the browser instance from displaying
            options.add_argument("--disable-gpu")  # Disable GPU acceleration
            options.add_argument(
                "--no-sandbox"
            )  # Bypass OS security model, required for running as root
            options.add_argument("--disable-dev-shm-usage")
            # Set up the WebDriver (for Firefox, replace with the path to your downloaded GeckoDriver)
            service = Service("/home/usboot/Downloads/geckodriver")
            driver = webdriver.Firefox(service=service, options=options)

            driver.get(url)
            page_content = driver.page_source
            driver.quit()
            logger.debug(f"Fetched page content for URL: {url}")

            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(page_content, "html.parser")

            # Attempt to find the abstract in common locations
            output_list = []

            # 1. <meta> tags
            try:
                meta_names = ["citation_abstract", "description", "og:description"]
                text = ""
                for name in meta_names:
                    meta_tag = soup.find("meta", attrs={"name": name})
                    if meta_tag and "content" in meta_tag.attrs:
                        output_list.append(meta_tag["content"])
                        text += meta_tag["content"]
                logger.info(f"Finished processing meta tags")
            except Exception as e:
                logger.error(f"Error processing meta tags: {e}")

            # 2. <p> tags
            try:
                p_tags = soup.find_all("p")
                for p in p_tags:
                    if "abstract" in p.get_text().lower():
                        output_list.append(p.get_text())
                logger.info(f"Finished processing paragraph tags")
            except Exception as e:
                logger.error(f"Error processing paragraph tags: {e}")

            # 3. <div> tags with specific classes or IDs
            try:
                div_classes = ["abstract", "article-abstract", "summary"]
                for class_name in div_classes:
                    div_tags = soup.find_all("div", class_=class_name)
                    for div_tag in div_tags:
                        output_list.append(div_tag.get_text())
                logger.info(f"Finished processing div tags")
            except Exception as e:
                logger.error(f"Error processing div tags: {e}")

            # 4. <article> tags
            try:
                article_tags = soup.find_all("article")
                for article_tag in article_tags:
                    output_list.append(article_tag.get_text())
                logger.info(f"Finished processing article tags")
            except Exception as e:
                logger.error(f"Error processing article tags: {e}")

            # 5. <span> tags
            try:
                span_tags = soup.find_all("span")
                for span_tag in span_tags:
                    output_list.append(span_tag.get_text())
                logger.info(f"Finished processing span tags")
            except Exception as e:
                logger.error(f"Error processing span tags: {e}")

            # get the number of tokens scraped so far
            try:
                total_tokens = 0
                for item in output_list:
                    total_tokens += len(item)
                token_end = 100000 - total_tokens
                logger.info(
                    f"Total tokens calculated: {total_tokens}, tokens remaining: {token_end}"
                )
            except Exception as e:
                logger.error(f"Error calculating total tokens: {e}")
            # Add the next 80000 tokens after the text we have collected
            output_list.append(page_content[total_tokens : total_tokens + token_end])

            logger.debug(
                f"Added first 100,000 characters of page content for URL: {url}"
            )
            Abstract = setup_chain(output_list)
            logger.debug(f"Successfully processed abstract for DOI {url}")

            # If no abstract is found, return None
            return Abstract
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    return None


# Example usage
if __name__ == "__main__":
    # test the get abstract function on a single doi link
    data = get_abstract("http://dx.doi.org/10.3197/096327117x14913285800742")

    # print the data
    print(data)

    # print the type
    print(type(data))
