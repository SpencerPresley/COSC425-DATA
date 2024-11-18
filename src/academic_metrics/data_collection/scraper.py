import json
import logging
import os
from typing import Any, Dict

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

from academic_metrics.ChainBuilder import ChainManager
from academic_metrics.constants import LOG_DIR_PATH

# # Load environment variables
# load_dotenv()
# api_key = os.getenv("OPENAI_API_KEY")
# client = OpenAI(api_key=api_key)

# # Configure logging
# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     handlers=[logging.FileHandler("scraper.log")],
# )
# logger = logging.getLogger(__name__)

# # Suppress logging for certain libraries
# logging.getLogger("selenium").setLevel(logging.WARNING)
# logging.getLogger("aiohttp").setLevel(logging.WARNING)
# logging.getLogger("openai").setLevel(logging.WARNING)
# logging.getLogger("ChainBuilder").setLevel(logging.DEBUG)
# logging.getLogger("webdriver_manager").setLevel(logging.WARNING)
# logging.getLogger("CrossrefWrapper").setLevel(logging.DEBUG)


# create the cleaner output model
class CleanerOutput(BaseModel):
    abstract: str
    extra_context: Dict[str, Any]


class Scraper:
    def __init__(
        self,
        api_key: str,
    ):
        """
        Initialize the Scraper with API key and logger.

        Args:
            api_key: OpenAI API key
            logger: Optional logger instance
        """
        # self.logger = None
        # # Set up logger
        # if not logger:
        #     self.logger = self.configure_logging(log_file)
        # else:
        #     self.logger = logger
        #     self.logger.setLevel(logging.INFO)

        #     # Add handler if none exists
        #     if not self.logger.handlers:
        #         handler = logging.StreamHandler()
        #         formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        #         handler.setFormatter(formatter)
        #         self.logger.addHandler(handler)

        self.log_file_path = os.path.join(LOG_DIR_PATH, "scraper.log")

        self.logger = logging.getLogger(__name__)
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)

        console_handler = logging.FileHandler(self.log_file_path)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.logger.info("Initializing Scraper")

        # Initialize OpenAI client
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)

        # Initialize Selenium options
        self.options = self._setup_selenium_options()
        self.service = Service(GeckoDriverManager().install())

        self.logger.info("Scraper initialized successfully")

        self.raw_results = []

    @staticmethod
    def configure_logging(log_file: str = "scraper.log") -> logging.Logger:
        """
        Configure logging for the scraper and related libraries.
        This is optional and should only be used when running the scraper standalone.

        Args:
            log_file: Path to the log file

        Returns:
            logging.Logger: Configured logger instance
        """
        # Configure root logger
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file)],
        )

        # Get scraper logger
        logger = logging.getLogger(__name__)

        # Configure levels for external libraries
        logging_levels = {
            "selenium": logging.WARNING,
            "aiohttp": logging.WARNING,
            "openai": logging.WARNING,
            "ChainBuilder": logging.DEBUG,
            "webdriver_manager": logging.WARNING,
            "CrossrefWrapper": logging.DEBUG,
        }

        # Set levels for each library
        for lib, level in logging_levels.items():
            logging.getLogger(lib).setLevel(level)

        return logger

    def _setup_selenium_options(self):
        """Set up Selenium Firefox options."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options

    def setup_chain(self, output_list):
        # instanciate the chain manager
        chain_manager = ChainManager(
            "gpt-4o-mini",
            self.api_key,
        )

        # create a general schema for the model to output text in
        json_schema = """
        {
            "abstract": <this is where you should place the abstract, or "" if one is not found>,
            "extra_context": <this is a dictionary of key value pairs of extra content you find, always make the key indicative of what the extra content in the value is>
        }
        """

        json_example_missing_abstract = """
        {
            "abstract": "",
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
        You are an expert at cleaning text from a website. You will be provided some text and you are to clean it into markdown format and do the following:

        1) Identify if there is an abstract
        2) Pull out any extra content other than the abstract

        You are to format your results in the following json structure:
        {json_structure}

        If you find an abstract you are to put in the abstract section, **if you don't find one put an empty string**.
        
        Here is an example of what to do if you don't find an abstract:
        {json_example_missing_abstract}

        For extra_context you are to put a key value pair of anything else you find. **If you do not find anything else then you are to still make 1 key value pair indicating so**. DO NOT BE LAZY.
        
        You should always find at least 1 extra context key value pair.

        In extra_context be congnizant of what type of element you're putting in there, for example if you find keywords, do you not just provide a string but rather a list of strings that are the keywords. Be mindful of these types of things at all times, do not limit it to this example.

        IMPORTANT: You are to always output your response in the json format provided, if you do not output your response in the format provided you have failed.
        IMPORTANT: DO NOT WRAP YOUR JSON IN ```json\njson content\n``` JUST RETURN THE JSON
        IMPORTANT: The abstract field is required and must always be provided, if you cannot find an abstract STILL PUT AN EMPTY STRING IN THERE.
        IMPORTANT: extra_context IS NOT AN OPTIONAL FIELD YOUR ARE ALWAYS TO PROVIDE AT LEAST ONE KEY VALUE PAIR WITHIN IT. 
        IMPORTANT: ENSURE THAT THE JSON YOU PROVIDE IS VALID JSON. BEFORE RETURNING REVIEW THE JSON YOU HAVE CONSTRUCTED AND FIX ANY ERRORS IF THERE ARE ANY.
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

        return {"abstract": results.abstract, "extra_context": results.extra_context}

    def get_abstract(self, url):
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
                self.logger.debug(f"Fetching URL: {url}")
                # Set up the WebDriver in headless mode
                # options = Options()
                # options.add_argument(
                #     "--headless"
                # )  # headless will prevent the browser instance from displaying
                # options.add_argument("--disable-gpu")  # Disable GPU acceleration
                # options.add_argument(
                #     "--no-sandbox"
                # )  # Bypass OS security model, required for running as root
                # options.add_argument("--disable-dev-shm-usage")
                # # Set up the WebDriver (for Firefox, replace with the path to your downloaded GeckoDriver)
                # # service = Service("/home/usboot/Downloads/geckodriver")
                # service = Service(GeckoDriverManager().install())
                # driver = webdriver.Firefox(service=service, options=options)

                self.logger.debug("Setting up driver")
                try:
                    driver = webdriver.Firefox(
                        service=self.service, options=self.options
                    )
                except Exception as e:
                    self.logger.error(f"Error setting up driver: {e}")
                    return None

                self.logger.debug("Getting page content")
                try:
                    driver.get(url)
                    page_content = driver.page_source
                except Exception as e:
                    self.logger.error(f"Error getting page content: {e}")
                    return None

                self.logger.debug(f"Page content preview:\n\n{page_content[:50]}\n\n")

                self.logger.debug("Quitting driver")
                try:
                    driver.quit()
                except Exception as e:
                    self.logger.error(f"Error quitting driver: {e}")

                self.logger.debug(f"Fetched page content for URL: {url}")

                # Parse the HTML content using BeautifulSoup
                try:
                    self.logger.debug("Initializing BeautifulSoup parser")
                    soup = BeautifulSoup(page_content, "html.parser")
                    self.logger.debug(
                        f"Page parsed. Found {len(soup.find_all())} total elements"
                    )

                    # Debug the structure
                    self.logger.debug(f"Found {len(soup.find_all('meta'))} meta tags")
                    self.logger.debug(f"Found {len(soup.find_all('p'))} paragraph tags")
                    self.logger.debug(f"Found {len(soup.find_all('div'))} div tags")
                except Exception as e:
                    self.logger.error(f"Error parsing HTML content: {e}")
                    return None

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
                # Add the next 80000 tokens after the text we have collected
                output_list.append(
                    page_content[total_tokens : total_tokens + token_end]
                )

                self.logger.debug(
                    f"Added first 100,000 characters of page content for URL: {url}"
                )
                results = self.setup_chain(output_list)
                self.raw_results.append(results)
                abstract = results["abstract"]
                if abstract == "":
                    abstract = None
                extra_context = results["extra_context"]
                print(f"\n\nAbstract:\n{abstract}\n\n")
                print(f"\n\nExtra context:\n{extra_context}\n\n")
                self.logger.debug(f"\n\nAbstract:\n{abstract}\n\n")
                self.logger.debug(
                    f"Successfully processed abstract for DOI {url}\n{abstract}\n\n"
                )

                # If no abstract is found, return None
                return abstract
            except Exception as e:
                self.logger.error(f"Error fetching {url}: {e}")
                return None
        return None

    def save_raw_results(self):
        with open("raw_results.json", "w") as f:
            json.dump(self.raw_results, f)


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("scraper_demo")

    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    # Initialize scraper
    scraper = Scraper(api_key=api_key, logger=logger)

    # Test URL
    test_url = "http://dx.doi.org/10.3197/096327117x14913285800742"
    result = scraper.get_abstract(test_url)

    if result:
        print("Abstract:", result.get("abstract"))
        print("Extra context:", result.get("extra_context"))
