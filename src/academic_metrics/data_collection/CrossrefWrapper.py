from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from .scraper import Scraper

from academic_metrics.constants import LOG_DIR_PATH


class CrossrefWrapper:
    """
    A wrapper class for interacting with the Crossref API to fetch and process publication data.

    Attributes:
        base_url (str): The base URL for the Crossref API.
        affiliation (str): The affiliation to filter publications by.
        from_year (int): The starting year for the publication search.
        to_year (int): The ending year for the publication search.
        logger (logging.Logger): Logger for logging messages.
        MAX_CONCURRENT_REQUESTS (int): Maximum number of concurrent requests allowed.
        semaphore (asyncio.Semaphore): Semaphore to control the rate of concurrent requests.
        years (list): List of years to fetch data for.
        data (dict): Data fetched from the Crossref API.
    """

    def __init__(
        self,
        *,
        scraper: Scraper,
        base_url: str = "https://api.crossref.org/works",
        affiliation: str = "Salisbury%20University",
        from_year: int = 2017,
        to_year: int = 2024,
    ):
        """
        Initializes the CrossrefWrapper with the given parameters.

        Args:
            base_url (str): The base URL for the Crossref API.
            affiliation (str): The affiliation to filter publications by.
            from_year (int): The starting year for the publication search.
            to_year (int): The ending year for the publication search.
            logger (logging.Logger, optional): Logger for logging messages. Defaults to None.
        """
        # Set up logger
        self.log_file_path = os.path.join(LOG_DIR_PATH, "crossref_wrapper.log")
        self.logger = logging.getLogger(__name__)
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.scraper = scraper

        # Maximum number of concurrent requests allowed
        self.MAX_CONCURRENT_REQUESTS = 2  # Limit to 2 concurrent tasks at a time

        # Semaphore to control the rate of concurrent requests
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)

        self.from_year = from_year
        self.to_year = to_year
        self.base_url = base_url
        self.affiliation = affiliation

        self.years = [year for year in range(from_year, to_year + 1)]

        # Prevent logger from being affected by parent loggers
        self.logger.propagate = False

        self.data = None

    async def fetch_data(self, session, url, headers, retries, retry_delay):
        """
        Fetches data from the given URL using aiohttp.

        Args:
            session (aiohttp.ClientSession): The aiohttp session to use for the request.
            url (str): The URL to fetch data from.
            headers (dict): Headers to include in the request.
            retries (int): Number of retries in case of failure.
            retry_delay (int): Delay between retries in seconds.

        Returns:
            dict: The JSON data fetched from the URL, or None if an error occurs.
        """
        num_iter = 0
        while num_iter < retries:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 429:
                        retry_after = retry_delay
                        self.logger.debug(
                            f"Hit request limit, retrying in {retry_after} seconds..."
                        )
                        await asyncio.sleep(retry_after)
                        num_iter += 1
                        continue
                    elif response.status == 200:
                        logging.info("Getting data from response...")
                        data = await response.json()
                        return data
                    else:
                        self.logger.error(
                            f"Unexpected status {response.status} for URL: {url}"
                        )
                        return None
            except aiohttp.ClientError as e:
                self.logger.error(f"Network error: {e}")
                return None
        self.logger.warning(f"Exceeded max retries for URL: {url}")
        return None

    def build_request_url(
        self,
        base_url,
        affiliation,
        from_date,
        to_date,
        n_element,
        sort_type,
        sort_ord,
        cursor,
        has_abstract=False,
    ):
        """
        Builds the request URL for the Crossref API.

        Args:
            base_url (str): The base URL for the Crossref API.
            affiliation (str): The affiliation to filter publications by.
            from_date (str): The starting date for the publication search.
            to_date (str): The ending date for the publication search.
            n_element (str): Number of elements to fetch per request.
            sort_type (str): The type of sorting to apply.
            sort_ord (str): The order of sorting (asc or desc).
            cursor (str): The cursor for pagination.
            has_abstract (bool, optional): Whether to filter for publications with abstracts. Defaults to False.

        Returns:
            str: The constructed request URL.
        """
        ab_state = ""
        if has_abstract:
            ab_state = ",has-abstract:1"

        return f"{base_url}?query.affiliation={affiliation}&filter=from-pub-date:{from_date},until-pub-date:{to_date}{ab_state}&sort={sort_type}&order={sort_ord}&rows={n_element}&cursor={cursor}"

    def process_items(self, data, from_date, to_date, affiliation="salisbury univ"):
        """
        Processes the items fetched from the Crossref API, filtering by date and affiliation.

        Args:
            data (dict): The data fetched from the Crossref API.
            from_date (str): The starting date for the publication search.
            to_date (str): The ending date for the publication search.
            affiliation (str, optional): The affiliation to filter publications by. Defaults to "salisbury univ".

        Returns:
            list: The filtered list of items.
        """
        filtered_data = []
        for item in data.get("items", []):
            if item["published"]["date-parts"][0][0] >= int(
                from_date.split("-")[0]
            ) and item["published"]["date-parts"][0][0] <= int(to_date.split("-")[0]):
                count = 0
                for author in item.get("author", []):
                    for affil in author.get("affiliation", []):
                        if affiliation in affil.get("name", "").lower():
                            count += 1
                if count > 0:
                    filtered_data.append(item)

        return filtered_data

    async def acollect_yrange(
        self,
        session: aiohttp.ClientSession,
        from_date: str = "2018-01-01",
        to_date: str = "2024-10-09",
        n_element: str = "1000",
        sort_type: str = "relevance",
        sort_ord: str = "desc",
        cursor: str = "*",
        retries: int = 5,
        retry_delay: int = 3,
    ):
        """
        Collects data for a range of years asynchronously.

        Args:
            session (aiohttp.ClientSession): The aiohttp session to use for the request.
            from_date (str): The starting date for the publication search.
            to_date (str): The ending date for the publication search.
            n_element (str): Number of elements to fetch per request.
            sort_type (str): The type of sorting to apply.
            sort_ord (str): The order of sorting (asc or desc).
            cursor (str): The cursor for pagination.
            retries (int): Number of retries in case of failure.
            retry_delay (int): Delay between retries in seconds.

        Returns:
            tuple: A tuple containing the list of items and the next cursor.
        """
        self.logger.info("Starting Crf_dict_cursor_async function")
        item_list = []
        processed_papers = 0
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Rommel Center",
            "mailto": "cbarbes1@gulls.salisbury.edu",
        }

        async with self.semaphore:
            req_url = self.build_request_url(
                self.base_url,
                self.affiliation,
                from_date,
                to_date,
                n_element,
                sort_type,
                sort_ord,
                cursor,
            )
            self.logger.debug(f"Request URL: {req_url}")

            data = await self.fetch_data(
                session, req_url, headers, retries, retry_delay
            )
            if data is None:
                return (None, None)

            data = data.get("message", {})
            if data == {}:
                logging.debug("No data to process")
                return (None, None)
            total_docs = data.get("total-results", 0)
            if total_docs == 0:
                logging.debug("No docs to process")
                return (None, None)
            self.logger.info(f"Processing API Pages from {from_date} to {to_date}")

            while processed_papers < total_docs:
                filtered_data = self.process_items(data, from_date, to_date)

                item_list.extend(filtered_data)
                processed_papers += len(filtered_data)

                cursor = data.get("next-cursor", None)
                if cursor is None:
                    break

                req_url = self.build_request_url(
                    self.base_url,
                    self.affiliation,
                    from_date,
                    to_date,
                    n_element,
                    sort_type,
                    sort_ord,
                    cursor,
                )
                data = await self.fetch_data(
                    session, req_url, headers, retries, retry_delay
                )
                if data is None:
                    break

                data = data.get("message", {})
                if filtered_data == []:
                    break
                await asyncio.sleep(3)

        self.logger.info("Processing Complete")
        return (item_list, cursor)

    async def fetch_data_for_multiple_years(self):
        """
        Fetches data for multiple years asynchronously.

        Returns:
            list: The list of items fetched from the Crossref API.
        """
        # creat the async session and send the tasks to each thread
        async with aiohttp.ClientSession() as session:
            # create the list of tasks to complete
            tasks = [
                self.acollect_yrange(
                    session, from_date=f"{year}-01-01", to_date=f"{year}-12-31"
                )
                for year in self.years
            ]

            # get the start time
            start_time = time.time()
            # await for the execution of each thread to finish
            results = await asyncio.gather(*tasks)

            final_result = []

            # create the result list
            for result, _ in results:
                if result is not None:
                    final_result.extend(result)

            end_time = time.time()

            # log the time it took
            self.logger.info(
                f"All data fetched. This took {end_time - start_time} seconds"
            )

            return final_result

    def run_afetch_yrange(self):
        """
        Runs the asynchronous data fetch for multiple years.

        Returns:
            list: The list of items fetched from the Crossref API.
        """
        # run the async function chain
        result_list = asyncio.run(self.fetch_data_for_multiple_years())

        # log the num items returned
        self.logger.info(f"Number of items: {len(result_list)}")

        self.result = result_list
        return self

    def serialize_to_json(self, output_file):
        """
        Serializes the fetched data to a JSON file.

        Args:
            output_file (str): The path to the output JSON file.
        """
        with open(output_file, "w") as file:
            json.dump(self.result, fp=file, indent=4)

    def final_data_process(self):
        """
        Processes the final data, filling in missing abstracts.
        """
        # fill missing abstracts
        num_processed = 0
        items_removed = 0

        self.logger.info("Starting final_data_process")  # Debug log

        if not self.result:  # Check if result exists
            self.logger.error("No result data found")
            return self

        missing_abstracts = [item for item in self.result if "abstract" not in item]
        total_missing = len(missing_abstracts)
        self.logger.info(f"\n\nTotal missing abstracts: {total_missing}\n\n")

        if total_missing == 0:
            self.logger.info("No missing abstracts found")
            return self

        for item in missing_abstracts:
            if "abstract" not in item:
                try:
                    self.logger.info("-" * 80)
                    self.logger.info(f"Processing URL: {item.get('URL')}")

                    abstract = self.scraper.get_abstract(item.get("URL"))
                    self.logger.info(
                        f"\n\nRETURN FROM SCRAPER get_abstract: {abstract}\n\n"
                    )
                    self.logger.info("-" * 80)

                    if abstract:  # Check if data was returned
                        item["abstract"] = abstract
                        print(f"\n\nAbstract:\n{item['abstract']}\n\n")
                        num_processed += 1
                        self.logger.info(
                            f"\n\nProcessed {num_processed}/{total_missing}\n\n"
                        )
                    else:
                        # If abstract is not found item cannot be classified thus cannot be processed
                        # So remove it from the result list
                        self.result.remove(item)
                        items_removed += 1
                        self.logger.warning(
                            f"No data returned for URL: {item.get('URL')}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error processing URL {item.get('URL')}: {str(e)}"
                    )
                    continue

        self.logger.info(f"\n\nItems removed: {items_removed}\n\n")
        self.logger.info(
            f"Final data processing complete. Processed {num_processed} abstracts"
        )
        self.scraper.save_raw_results()
        return self

    def get_result_list(self):
        """
        Get the result list
        """
        return self.result

    def run_all_process(self, save_offline: bool = False):
        """
        Run all data fetching and processing
        """
        if save_offline:
            return (
                self.run_afetch_yrange()
                .final_data_process()
                .serialize_to_json("postProcess.json")
            )
        return self.run_afetch_yrange().final_data_process().get_result_list()


if __name__ == "__main__":
    wrap = CrossrefWrapper()  # create the wrapper
    data = wrap.run_all_process().get_data()
