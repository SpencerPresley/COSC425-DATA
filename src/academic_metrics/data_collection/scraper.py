import json
import logging
import time
import os
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

from academic_metrics.ChainBuilder import ChainManager
from academic_metrics.configs import (
    configure_logging,
    DEBUG,
)


# create the cleaner output model
class CleanerOutput(BaseModel):
    """Pydantic model for the cleaner output.

    Attributes:
        page_content (str): The page content.
        extra_context (Dict[str, Any]): The extra context.
    """

    page_content: str
    extra_context: Dict[str, Any]


class Scraper:
    """Scraper class for fetching and processing abstracts from URLs.

    Attributes:
        api_key (str): The OpenAI API key.
        client (OpenAI): The OpenAI client.
        options (Options): The Selenium options.
        service (Service): The Selenium service.
        raw_results (list[dict[str, Any]]): The raw results.

    Methods:
        _setup_selenium_options(): Set up Selenium Firefox options.
        setup_chain(output_list: list[str]) -> dict[str, Any] | None: Set up and run the chain.
        get_abstract(url: str, return_raw_output: bool | None = False) -> tuple[str | None, dict[str, Any] | None]: Fetch and process the abstract from a given URL.
        save_raw_results(): Save the raw results to a JSON file.
    """

    def __init__(
        self,
        api_key: str,
    ):
        """Initialize the Scraper with API key and logger.

        Args:
            api_key (str): The OpenAI API key.
        """
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="scraper",
            log_level=DEBUG,
        )

        self.logger.info("Initializing Scraper")

        # Initialize OpenAI client
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)

        # Initialize Selenium options
        self.options = self._setup_selenium_options()
        self.service = Service(GeckoDriverManager().install())

        self.logger.info("Scraper initialized successfully")

        self.raw_results = []

        self.page_load_timeout = 30  # seconds
        self.script_timeout = 30  # seconds
        self.max_retries = 3
        self.base_retry_delay = 5  # seconds
        self.max_delay = 125  # seconds

    def _setup_selenium_options(self):
        """Set up Selenium Firefox options.

        Returns:
            options (Options): The Selenium options.
        """
        options: Options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options

    def setup_chain(self, output_list: List[str]) -> Dict[str, Any] | None:
        """Set up and run the chain.

        Args:
            output_list (List[str]): The output list.

        Returns:
            Dict[str, Any] | None: The result of the chain.
        """
        # instanciate the chain manager
        # google_api_key = os.getenv("GOOGLE_API_KEY")
        import time
        import threading

        start_time = time.time()
        stop_timer = threading.Event()

        def print_elapsed_time():
            while not stop_timer.is_set():
                elapsed = time.time() - start_time
                self.logger.info(f"Waiting for LLM response... {elapsed:.1f}s elapsed")
                time.sleep(5)

        llm_kwargs = {
            "request_timeout": 300.0,  # 5 minutes
            "max_retries": 3,
        }

        chain_manager = ChainManager(
            llm_model="gpt-4o-mini",
            api_key=self.api_key,
            llm_kwargs=llm_kwargs,
        )

        # create a general schema for the model to output text in
        json_schema = """
        {
            "page_content": <this is where you should place all text found on the page or "" if one is not found>,
            "extra_context": <this is a dictionary of key value pairs of extra content you find, always make the key indicative of what the extra content in the value is>
        }
        """

        json_example_missing_abstract = """
        {
            "page_content": "",
            "extra_context": {
                "keywords": ["keyword1", "keyword2", "keyword3"],
                "authors": ["author1", "author2", "author3"],
                "date": "2024-01-01",
                ...
            }
        }
        """

        # create the system prompt
        system_prompt = """
        You are an expert at parsing HTML and extracting text off the page and formatting it in a structured way. You will be provided HTML and you are to do the following:

        1) Find all text on the page and format it into markdown.
        2) Find any extra context available on the page such as keywords, authors, date, journal, etc.
        
        You are to format your results in the following json structure:
        {json_structure}

        If you find page content you are to put in the page_content section, **if you don't find any page content put an empty string**.
        
        Here is an example of what to do if you don't find any page content:
        {json_example_missing_abstract}

        For extra_context you are to put a key value pair of anything else you find. **If you do not find anything else then you are to still make 1 key value pair indicating so**. DO NOT BE LAZY.
        
        You should always find at least 1 extra context key value pair.

        In extra_context be congnizant of what type of element you're putting in there, for example if you find keywords, do you not just provide a string but rather a list of strings that are the keywords. Be mindful of these types of things at all times, do not limit it to this example.

        IMPORTANT: You are to always output your response in the json format provided, if you do not output your response in the format provided you have failed.
        IMPORTANT: DO NOT WRAP YOUR JSON IN ```json\njson content\n``` JUST RETURN THE JSON
        IMPORTANT: The page_content field is required and must always be provided, if you cannot find any page content STILL PUT AN EMPTY STRING IN THERE.
        IMPORTANT: extra_context IS NOT AN OPTIONAL FIELD YOUR ARE ALWAYS TO PROVIDE AT LEAST ONE KEY VALUE PAIR WITHIN IT. 
        IMPORTANT: ENSURE THAT THE JSON YOU PROVIDE IS VALID JSON. BEFORE RETURNING REVIEW THE JSON YOU HAVE CONSTRUCTED AND FIX ANY ERRORS IF THERE ARE ANY.
        """

        # setup ability to pass the list into the prompt
        human_prompt = """
        Output list:
        {output_list}
        """

        self.logger.info("Starting LLM processing...")

        timer_thread = threading.Thread(target=print_elapsed_time)
        timer_thread.start()

        try:
            # add the chain
            chain_manager.add_chain_layer(
                system_prompt=system_prompt,
                human_prompt=human_prompt,
                output_passthrough_key_name="raw_output",
                parser_type="pydantic",
                pydantic_output_model=CleanerOutput,
            )

            prompt_variables = {
                "output_list": str(output_list),
                "json_structure": json_schema,
                "json_example_missing_abstract": json_example_missing_abstract,
            }

            results = chain_manager.run(prompt_variables_dict=prompt_variables)[
                "raw_output"
            ]

            return {
                "abstract": results.page_content,
                "extra_context": results.extra_context,
            }
        except Exception as e:
            self.logger.error(f"LLM processing failed: {str(e)}")
            return None

        finally:
            stop_timer.set()
            timer_thread.join()
            elapsed_time = time.time() - start_time
            self.logger.info(f"LLM processing completed in {elapsed_time:.2f} seconds")

    def get_abstract(self, url, return_raw_output: bool | None = False):
        """
        Fetches and processes the abstract from a given URL.

        This function uses Selenium to fetch the content of the provided URL in headless mode.
        It then parses the HTML content using BeautifulSoup and attempts to find the abstract
        in common HTML tags such as <meta>, <p>, <div>, <article>, and <span>. The collected
        content is processed using a chain of prompts managed by the ChainManager.

        Args:
            url (str): The URL of the web page to fetch the abstract from.

        Returns:
            (abstract: str | None, extra_context: dict[str, Any] | None):
            - The processed abstract and additional context,
            - or None if no abstract is found or an error occurs.
        """
        driver = None
        retry_count: int = 0
        if url:
            while retry_count < self.max_retries:
                try:
                    self.logger.debug(f"Fetching URL: {url}")

                    self.logger.debug("Setting up driver")
                    try:
                        driver = webdriver.Firefox(
                            service=self.service, options=self.options
                        )
                        driver.set_page_load_timeout(self.page_load_timeout)
                        driver.set_script_timeout(self.script_timeout)
                    except Exception as e:
                        self.logger.error(f"Error setting up driver: {e}")
                        return None

                    self.logger.debug("Getting page content")
                    try:
                        driver.get(url)
                        page_content = driver.page_source
                    except Exception as e:
                        self.logger.error(f"Error getting page content: {e}")
                        retry_count += 1
                        if retry_count >= self.max_retries:
                            self.logger.error(
                                f"Max retries ({self.max_retries}) reached for URL: {url}"
                            )
                            return None

                        # Calculate exponential delay: 5s, 25s, 125s
                        # 5^2 = 25, 5^3 = 125
                        current_delay = min(
                            self.max_delay, self.base_retry_delay ** (retry_count + 1)
                        )
                        self.logger.info(
                            f"Retrying in {current_delay} seconds... Attempt {retry_count + 1} of {self.max_retries}"
                        )
                        time.sleep(current_delay)
                        continue

                    self.logger.debug(
                        f"Page content preview:\n\n{page_content[:50]}\n\n"
                    )

                    # self.logger.debug("Quitting driver")
                    # try:
                    #     driver.quit()
                    # except Exception as e:
                    #     self.logger.error(f"Error quitting driver: {e}")

                    self.logger.debug(f"Fetched page content for URL: {url}")

                    # Parse the HTML content using BeautifulSoup
                    try:
                        self.logger.debug("Initializing BeautifulSoup parser")
                        soup = BeautifulSoup(page_content, "html.parser")
                        self.logger.debug(
                            f"Page parsed. Found {len(soup.find_all())} total elements"
                        )

                        # Debug the structure
                        self.logger.debug(
                            f"Found {len(soup.find_all('meta'))} meta tags"
                        )
                        self.logger.debug(
                            f"Found {len(soup.find_all('p'))} paragraph tags"
                        )
                        self.logger.debug(f"Found {len(soup.find_all('div'))} div tags")
                    except Exception as e:
                        self.logger.error(f"Error parsing HTML content: {e}")
                        return None

                    # Attempt to find the abstract in common locations
                    output_list = []

                    # 1. <meta> tags
                    try:
                        meta_names = [
                            "citation_abstract",
                            "description",
                            "og:description",
                        ]
                        text = ""
                        for name in meta_names:
                            meta_tag = soup.find("meta", attrs={"name": name})
                            if meta_tag and "content" in meta_tag.attrs:
                                output_list.append(meta_tag["content"])
                                text += meta_tag["content"]
                        self.logger.info("Finished processing meta tags")
                    except Exception as e:
                        self.logger.error(f"Error processing meta tags: {e}")

                    # 2. <p> tags
                    try:
                        p_tags = soup.find_all("p")
                        for p in p_tags:
                            if "abstract" in p.get_text().lower():
                                output_list.append(p.get_text())
                        self.logger.info("Finished processing paragraph tags")
                    except Exception as e:
                        self.logger.error(f"Error processing paragraph tags: {e}")

                    # 3. <div> tags with specific classes or IDs
                    try:
                        div_classes = ["abstract", "article-abstract", "summary"]
                        for class_name in div_classes:
                            div_tags = soup.find_all("div", class_=class_name)
                            for div_tag in div_tags:
                                output_list.append(div_tag.get_text())
                        self.logger.info("Finished processing div tags")
                    except Exception as e:
                        self.logger.error(f"Error processing div tags: {e}")

                    # 4. <article> tags
                    try:
                        article_tags = soup.find_all("article")
                        for article_tag in article_tags:
                            output_list.append(article_tag.get_text())
                        self.logger.info("Finished processing article tags")
                    except Exception as e:
                        self.logger.error(f"Error processing article tags: {e}")

                    # 5. <span> tags
                    try:
                        span_tags = soup.find_all("span")
                        for span_tag in span_tags:
                            output_list.append(span_tag.get_text())
                        self.logger.info("Finished processing span tags")
                    except Exception as e:
                        self.logger.error(f"Error processing span tags: {e}")

                    # get the number of tokens scraped so far
                    try:
                        total_tokens = 0
                        for item in output_list:
                            total_tokens += len(item)
                        token_end = 100000 - total_tokens
                        self.logger.info(
                            f"Total tokens calculated: {total_tokens}, tokens remaining: {token_end}"
                        )
                    except Exception as e:
                        self.logger.error(f"Error calculating total tokens: {e}")

                    if return_raw_output:
                        total_words = sum(len(item.split()) for item in output_list)
                        estimated_tokens = total_words * 0.75
                        total_characters = sum(len(item) for item in output_list)
                        self.logger.info(f"Total words: {total_words}")
                        self.logger.info(f"Total characters: {total_characters}")
                        self.logger.info(f"Estimated tokens: {estimated_tokens}")
                        return (
                            output_list,
                            total_words,
                            estimated_tokens,
                            total_characters,
                        )

                    results = self.setup_chain(output_list)

                    if results is None:
                        return None, None

                    self.raw_results.append(results)
                    abstract = results["abstract"]
                    if abstract == "":
                        # If no abstract is found, return None and extra context
                        # Don't return extra context as sometimes an abstract is not found
                        # as the url is to a book or some non-academic research article item
                        return None, None
                    extra_context = results["extra_context"]
                    self.logger.debug(f"\n\nAbstract:\n{abstract}\n\n")
                    self.logger.debug(
                        f"Successfully processed abstract for DOI {url}\n{abstract}\n\n"
                    )

                    # Abstract and extra context found
                    return abstract, extra_context

                except Exception as e:
                    self.logger.error(f"Error fetching {url}: {e}")
                    return None, None

                finally:
                    if driver:
                        self.logger.debug("Quitting driver")
                        try:
                            driver.quit()
                        except Exception as e:
                            self.logger.error(f"Error quitting driver: {e}")
        return None, None

    def save_raw_results(self):
        """Save the raw results to a JSON file."""
        with open("raw_results.json", "w") as f:
            json.dump(self.raw_results, f)


# Example usage
if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    scraper = Scraper(api_key=api_key)
    abstract, extra_context = scraper.get_abstract(
        "http://dx.doi.org/10.1111/hequ.12450"
    )
    print(abstract)
    print(extra_context)
