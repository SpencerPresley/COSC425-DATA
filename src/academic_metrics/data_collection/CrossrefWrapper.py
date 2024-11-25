from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Self, Any, Union, List, Dict

import aiohttp

from academic_metrics.configs import (
    configure_logging,
    DEBUG,
)

if TYPE_CHECKING:
    from .scraper import Scraper


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

    Methods:
        fetch_data(session: aiohttp.ClientSession, url: str, headers: dict[str, Any], retries: int, retry_delay: int) -> dict[str, Any] | None: Fetches data from the given URL using aiohttp.
        build_request_url(base_url: str, affiliation: str, from_date: str, to_date: str, n_element: str, sort_type: str, sort_ord: str, cursor: str, has_abstract: bool | None = False) -> str: Builds the request URL for the Crossref API.
        process_items(data: dict[str, Any], from_date: str, to_date: str, affiliation: str | None = "salisbury univ") -> list[dict[str, Any]]: Processes the items fetched from the Crossref API, filtering by date and affiliation.
        _get_last_day_of_month(year: int, month: int) -> int: Returns the last day of the given month in the given year.
        fetch_data_for_multiple_years() -> list[dict[str, Any]]: Fetches data for multiple years asynchronously.
        serialize_to_json(output_file: str) -> None: Serializes the fetched data to a JSON file.
        final_data_process() -> Self: Processes the final data, filling in missing abstracts.
        get_result_list() -> list[dict[str, Any]]: Get the result list
        run_all_process(save_offline: bool = False) -> Union[None, List[Dict[str, Any]]]: Run all data fetching and processing
    """

    def __init__(
        self,
        *,
        scraper: Scraper,
        base_url: str | None = "https://api.crossref.org/works",
        affiliation: str | None = "Salisbury%20University",
        from_year: int | None = 2017,
        to_year: int | None = 2024,
        from_month: int | None = 1,
        to_month: int | None = 12,
        test_run: bool | None = False,
        run_scraper: bool | None = True,
    ) -> Self:
        """
        Initializes the CrossrefWrapper with the given parameters.

        Args:
            base_url (str): The base URL for the Crossref API.
            affiliation (str): The affiliation to filter publications by.
            from_year (int): The starting year for the publication search.
            to_year (int): The ending year for the publication search.
            logger (logging.Logger, optional): Logger for logging messages. Defaults to None.
        """
        self.logger = configure_logging(
            module_name=__name__,
            log_file_name="crossref_wrapper",
            log_level=DEBUG,
        )

        self.scraper = scraper
        self.run_scraper = run_scraper

        # Maximum number of concurrent requests allowed
        self.MAX_CONCURRENT_REQUESTS = 2  # Limit to 2 concurrent tasks at a time

        # Semaphore to control the rate of concurrent requests
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)

        if not isinstance(from_year, int):
            raise ValueError("from_year must be an integer")
        if not isinstance(to_year, int):
            raise ValueError("to_year must be an integer")
        if not isinstance(from_month, int):
            raise ValueError("from_month must be an integer")
        if not isinstance(to_month, int):
            raise ValueError("to_month must be an integer")

        self.from_year = from_year
        self.to_year = to_year
        self.from_month = from_month
        self.to_month = to_month
        self.base_url = base_url
        self.affiliation = affiliation
        self.test_run = test_run

        self.years = [year for year in range(from_year, to_year + 1)]

        # Prevent logger from being affected by parent loggers
        self.logger.propagate = False

        self.data = None

    async def fetch_data(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: dict[str, Any],
        retries: int,
        retry_delay: int,
    ) -> dict[str, Any] | None:
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
        base_url: str,
        affiliation: str,
        from_date: str,
        to_date: str,
        n_element: str,
        sort_type: str,
        sort_ord: str,
        cursor: str,
        has_abstract: bool | None = False,
    ) -> str:
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

    def process_items(
        self,
        data: dict[str, Any],
        from_date: str,
        to_date: str,
        affiliation: str | None = "salisbury univ",
    ) -> list[dict[str, Any]]:
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
        i = 0
        items = data.get("items", None)
        if items is None:
            raise ValueError("No items found in data")

        for item in data.get("items", []):
            # Get published date information
            item_published = item.get("published", None)
            item_date_parts = None
            if item_published is not None:
                item_date_parts = item_published.get("date-parts", None)

            # Skip if no date parts or invalid structure
            if not item_date_parts or not item_date_parts[0]:
                continue

            # Get year and month, defaulting to None if not available
            pub_year = item_date_parts[0][0] if len(item_date_parts[0]) > 0 else None
            pub_month = item_date_parts[0][1] if len(item_date_parts[0]) > 1 else None

            from_year = int(from_date.split("-")[0])
            from_month = int(from_date.split("-")[1])
            to_year = int(to_date.split("-")[0])
            to_month = int(to_date.split("-")[1])

            # Skip if year is missing or outside range
            if pub_year is None or pub_year < from_year or pub_year > to_year:
                continue

            # If same year as bounds, check months
            if pub_year == from_year and (pub_month is None or pub_month < from_month):
                continue
            if pub_year == to_year and (pub_month is None or pub_month > to_month):
                continue

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
    ) -> tuple[list[dict[str, Any]], str | None]:
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

    def _get_last_day_of_month(self, year: int, month: int) -> int:
        """Returns the last day of the given month in the given year. Handles leap years for February.

        Args:
            year (int): The year to check.
            month (int): The month to check.

        Returns:
            int: The last day of the given month in the given year.
        """
        # Handle February for leap years
        if month == 2:
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                return 29
            return 28

        # Handle months with 30 days
        # Months with 30 days: April (4), June (6), September (9), November (11)
        if month in [4, 6, 9, 11]:
            return 30

        # All other months have 31 days
        return 31

    async def fetch_data_for_multiple_years(self) -> list[dict[str, Any]]:
        """Fetches data for multiple years asynchronously.

        Returns:
            final_result (list[dict[str, Any]]): The list of items fetched from the Crossref API.
        """
        # creat the async session and send the tasks to each thread
        async with aiohttp.ClientSession() as session:
            # create the list of tasks to complete
            tasks = []
            for year in self.years:
                # Format dates with leading zeros for months
                from_date = f"{year}-{self.from_month:02d}-01"

                # Format to_date to have the correct last day of the month
                last_day = self._get_last_day_of_month(year, self.to_month)
                to_date = f"{year}-{self.to_month:02d}-{last_day}"

                task = self.acollect_yrange(
                    session=session,
                    from_date=from_date,
                    to_date=to_date,
                )
                tasks.append(task)

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

    def run_afetch_yrange(self) -> Self:
        """Runs the asynchronous data fetch for multiple years.

        Returns:
            self: The instance of the class for method chaining.
        """
        # run the async function chain
        result_list = asyncio.run(self.fetch_data_for_multiple_years())

        # log the num items returned
        self.logger.info(f"Number of items: {len(result_list)}")

        self.result = result_list
        return self

    def serialize_to_json(self, output_file: str) -> None:
        """
        Serializes the fetched data to a JSON file.

        Args:
            output_file (str): The path to the output JSON file.
        """
        with open(output_file, "w") as file:
            json.dump(self.result, fp=file, indent=4)

    def final_data_process(self) -> Self:
        """Processes the final data, filling in missing abstracts.

        Returns:
            self: The instance of the class for method chaining.
        """
        # fill missing abstracts
        num_processed = 0
        items_removed = 0

        self.logger.info("Starting final_data_process")  # Debug log

        if not self.result:  # Check if result exists
            self.logger.error("No result data found")
            return self

        if self.test_run:
            self.result = self.result[:3]
        i = 0
        while i < len(self.result):
            item = self.result[i]
            try:
                self.logger.info("-" * 80)
                self.logger.info(f"Processing URL: {item.get('URL')}")

                abstract, extra_context = self.scraper.get_abstract(item.get("URL"))

                if abstract is None or extra_context is None:
                    self.logger.warning(f"No data returned for URL: {item.get('URL')}")
                    # Remove the item, but don't increment i
                    # We don't increment i as the items in the list will shift left 1 so we want to keep
                    # the same index to check the next item
                    self.result.pop(i)
                    items_removed += 1
                    continue

                self.logger.info(
                    f"\n\nRETURN FROM SCRAPER get_abstract:\nABSTRACT:\n{abstract}\nEXTRA CONTEXT:\n{extra_context}\n\n"
                )
                self.logger.info("-" * 80)

                if "abstract" not in item:
                    item["abstract"] = abstract

                self.logger.info(
                    f"\n\nProcessed {num_processed}/{len(self.result)}\n\n"
                )
                item["extra_context"] = extra_context

                num_processed += 1
                self.logger.info(
                    f"\n\n\nPROCESSED **{i}/{len(self.result)}** ITEMS\n\n\n"
                )
                i += 1

            except Exception as e:
                self.logger.error(
                    f"Error processing URL {item.get('URL')}: {str(e)}"
                    "Popping item from result list and continuing"
                )
                self.result.pop(i)
                items_removed += 1
                continue

        self.logger.info(f"\n\nItems removed: {items_removed}\n\n")
        self.logger.info(
            f"Final data processing complete. Processed {num_processed} abstracts"
        )
        self.scraper.save_raw_results()
        return self

    def get_result_list(self) -> list[dict[str, Any]]:
        """Get the result list

        Returns:
            self.result (list[dict[str, Any]]): The result list
        """
        return self.result

    def run_all_process(
        self, save_offline: bool = False
    ) -> Union[None, List[Dict[str, Any]]]:
        """Run all data fetching and processing

        Args:
            save_offline (bool): Whether to save the offline data.

        Returns:
            Union[None, List[Dict[str, Any]]]: The result list or None
        """
        if save_offline:
            return (
                self.run_afetch_yrange()
                .final_data_process()
                .serialize_to_json("postProcess.json")
            )
        elif not self.run_scraper:
            return self.run_afetch_yrange().get_result_list()
        else:
            return self.run_afetch_yrange().final_data_process().get_result_list()


if __name__ == "__main__":
    wrap = CrossrefWrapper()
    data = wrap.run_all_process().get_data()
