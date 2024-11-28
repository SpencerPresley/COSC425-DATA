from __future__ import annotations

import logging
from typing import Dict, TYPE_CHECKING, List, Set

from academic_metrics.configs import (
    configure_logging,
    DEBUG,
)

from academic_metrics.dataclass_models import StringVariation

if TYPE_CHECKING:
    from academic_metrics.dataclass_models import CategoryInfo
    from academic_metrics.utils import MinHashUtility


class BasePostprocessor:
    """
    A class responsible for processing and standardizing attribute data across different categories.

    This class provides methods to extract attribute sets from category data, remove near-duplicate values,
    and standardize attribute values to ensure consistency across categories. It utilizes MinHash for estimating
    the similarity between values to effectively identify and remove duplicates. Additionally, it maintains
    a dictionary of value variations to track the most frequent spelling variations of each value.

    Attributes:
        processed_sets_list (list): Stores processed attribute sets after deduplication and standardization.
        minhash_util (MinHashUtility): Utility for generating MinHash signatures and comparing them.
        value_variations (dict): Stores NameVariation objects for each normalized attribute value.

    Methods:
        extract_sets(category_dict): Extracts the specified attribute from each CategoryInfo object in the provided dictionary.
        remove_near_duplicates(category_dict): Processes each CategoryInfo object to remove near-duplicate attribute values and standardize them.
        standardized_data_update(category_dict, standardized_sets): Updates CategoryInfo objects with standardized attribute sets.
        standardize_attribute(category_dict): Standardizes attribute values across all categories based on the most frequent spelling variations.
        remove_update_attribute(category_dict, attribute_sets_list): Removes near-duplicate attribute values within each attribute set.
        duplicate_postprocessor(attribute_set, attribute_sets, similarity_threshold): Processes a set of attribute values to remove near-duplicates.
        process_value_pair(similarity_threshold, most_frequent_variation, value_signatures, to_remove, v1, v2): Compares two attribute values and determines which to keep.
        value_to_remove(most_frequent_variation, v1, v2, v1_normalized, v2_normalized): Determines which of two attribute values to remove based on their variations.
        get_duplicate_utilities(attribute_set, attribute_sets): Generates utilities needed for duplicate removal.
        generate_signatures(attribute_set): Generates MinHash signatures for each value in an attribute set.
        get_most_frequent_value_variation(attribute_sets_list): Maps each normalized value to its most frequent spelling variation.
        standardize_values_across_sets(attribute_sets_list): Standardizes values in attribute sets based on the most frequent value variation.
    """

    def __init__(
        self, attribute_name: str, minhash_util: MinHashUtility, threshold: float = 0.5
    ):
        self.logger: logging.Logger = configure_logging(
            module_name=__name__,
            log_file_name=f"{attribute_name}_postprocessor",
            log_level=DEBUG,
        )

        self.logger.info(f"Initializing {attribute_name}Postprocessor...")
        self.attribute_name: str = attribute_name
        self.processed_sets_list: List[Set[str]] = (
            []
        )  # List to store processed attribute sets

        self.minhash_util: MinHashUtility = minhash_util
        self.similarity_threshold: float = threshold

        self.logger.info("Initializing StringVariation dictionary...")
        self.string_variations: Dict[str, StringVariation] = (
            {}
        )  # Dictionary to store StringVariation objects for each normalized value

    def extract_sets(self, category_dict: Dict[str, CategoryInfo]) -> List[Set[str]]:
        """
        Extracts the specified attribute from each CategoryInfo object in the provided dictionary.

        This method iterates over a dictionary of CategoryInfo objects and collects the set
        from the attribute specified by self.attribute_name from each object.
        These sets are typically used for further processing, such as deduplication or analysis.

        Args:
            category_dict (Dict[str, CategoryInfo]): A dictionary where the keys are category identifiers
                                 and the values are CategoryInfo objects.

        Returns:
            List[Set[str]]: A list containing the attribute set from each CategoryInfo object.
        """
        self.logger.info(f"Extracting {self.attribute_name} sets...")
        list_of_sets: List[Set[str]] = [
            getattr(category_info, self.attribute_name)
            for category_info in category_dict.values()
        ]
        self.logger.info(f"{self.attribute_name} sets extracted.")
        return list_of_sets

    def remove_near_duplicates(
        self, *, category_dict: Dict[str, CategoryInfo]
    ) -> Dict[str, CategoryInfo]:
        """
        Processes each CategoryInfo object to remove near-duplicate values and standardize
        them across categories.

        This method orchestrates several steps to enhance the integrity and consistency
        of the specified attribute:
        1. Extract sets from each category
        2. Remove near-duplicate values within each set
        3. Standardize values across all categories
        4. Update the category data with cleaned and standardized sets

        Args:
            category_dict (Dict[str, CategoryInfo]): A dictionary where the keys are category
                                                    identifiers and the values are CategoryInfo
                                                    objects.

        Returns:
            Dict[str, CategoryInfo]: The updated dictionary with cleaned and standardized
                                    values across all CategoryInfo objects.
        """
        self.logger.info(f"Removing near-duplicates for {self.attribute_name}...")
        # Step 1
        attribute_sets_list: List[Set[str]] = self.extract_sets(
            category_dict=category_dict
        )
        self.logger.info(f"{self.attribute_name} sets extracted.")

        # Step 2
        self.logger.info(f"Removing near-duplicate {self.attribute_name} values...")
        self.remove_update_attribute(category_dict, attribute_sets_list)
        self.logger.info(f"Near-duplicate {self.attribute_name} values removed.")

        # Step 3
        self.logger.info(f"Standardizing {self.attribute_name} values...")
        standardized_sets: List[Set[str]] = self.standardize_attribute(category_dict)
        self.logger.info(f"{self.attribute_name} values standardized.")

        # Step 4
        self.logger.info(f"Updating category data...")
        self.standardized_data_update(category_dict, standardized_sets)
        self.logger.info(f"Category data updated.")
        return category_dict

    def standardized_data_update(
        self, category_dict: Dict[str, CategoryInfo], standardized_sets: List[Set[str]]
    ) -> None:
        """
        Updates the CategoryInfo objects in the dictionary with standardized sets.

        Args:
            category_dict (Dict[str, CategoryInfo]):
                - A dictionary where the keys are category identifiers
                - and the values are CategoryInfo objects.
            standardized_sets (List[Set[str]]): A list of sets containing standardized values.

        This method iterates over the category dictionary and updates each CategoryInfo
        object with the corresponding standardized set for the specified attribute.
        """
        self.logger.info(f"Updating {self.attribute_name} data...")
        for (_, category_info), standardized_set in zip(
            category_dict.items(), standardized_sets
        ):
            setattr(category_info, self.attribute_name, standardized_set)
        self.logger.info(f"{self.attribute_name} data updated.")

    def standardize_attribute(
        self, category_dict: Dict[str, CategoryInfo]
    ) -> List[Set[str]]:
        """
        Standardizes attribute values across all categories based on the most frequent spelling variations.

        Args:
            category_dict (Dict[str, CategoryInfo]): A dictionary where the keys are category identifiers and the values are CategoryInfo objects.

        Returns:
            List[Set[str]]: A list of sets containing the standardized attribute values across all categories.

        This method extracts updated attribute sets after duplicate removal and standardizes values across all sets based on the most frequent global variation.
        """
        self.logger.info(f"Standardizing {self.attribute_name} values...")
        updated_attribute_sets: List[Set[str]] = self.extract_sets(
            category_dict=category_dict
        )
        self.logger.info(f"{self.attribute_name} sets extracted.")

        self.logger.info(
            f"Standardizing {self.attribute_name} values across all sets..."
        )
        standardized_sets: List[Set[str]] = self.standardize_values_across_sets(
            updated_attribute_sets
        )
        self.logger.info(f"{self.attribute_name} values standardized.")

        return standardized_sets

    def remove_update_attribute(
        self,
        category_dict: Dict[str, CategoryInfo],
        attribute_sets_list: List[Set[str]],
    ) -> None:
        """
        Removes near-duplicate values within each set based on MinHash similarity.

        Args:
            category_dict (Dict[str, CategoryInfo]): A dictionary where the keys are category identifiers
                                                    and the values are CategoryInfo objects.
            attribute_sets_list (List[Set[str]]): A list containing the attribute set
                                           from each CategoryInfo object.

        This method iterates over each category and processes the attribute set to
        remove near-duplicates, updating the specified attribute of each CategoryInfo object.
        """
        self.logger.info(
            f"Removing near-duplicate {self.attribute_name} values within each set..."
        )
        for _, category_info in category_dict.items():
            current_set = getattr(category_info, self.attribute_name)
            final_set: Set[str] = self.duplicate_postprocessor(
                current_set, attribute_sets_list, self.similarity_threshold
            )
            setattr(category_info, self.attribute_name, final_set)
        self.logger.info(f"Near-duplicate {self.attribute_name} values removed.")

    def duplicate_postprocessor(
        self,
        attribute_set: Set[str] | List[str],
        attribute_sets: List[Set[str]],
        similarity_threshold: float = 0.5,
    ) -> Set[str]:
        """
        Processes a set of values to remove near-duplicates based on MinHash similarity and most frequent variations.

        This method first generates the necessary utilities for comparison and removal.
        It then compares each value against all others in the set for near duplicates.
        If a value is deemed to be a duplicate based on MinHash similarity and the most
        frequent variation, it is added to the set of values to be removed.
        Finally, the refined set is returned, excluding any values deemed to be duplicates.

        Args:
            attribute_set (Set[str] | List[str]): A set or list of values to be processed.
            attribute_sets (List[Set[str]]): A list of sets, where each set contains values
                                           from a different category.
            similarity_threshold (float): The threshold for considering values as duplicates
                                        based on MinHash similarity.

        Returns:
            Set[str]: The refined set, excluding any values deemed to be duplicates.
        """
        # Generate needed utilities
        # most_frequent_variation is a dictionary that maps each normalized value to its most frequent variation
        # value_signatures is a dictionary that maps each value to its MinHash signature
        # to_remove is a set of values to be removed from the attribute set
        self.logger.info(
            f"Generating needed utilities for {self.attribute_name} processing..."
        )
        if not isinstance(attribute_set, set):
            attribute_set = set(attribute_set)

        (
            most_frequent_variation,
            value_signatures,
            to_remove,
        ) = self.get_duplicate_utilities(attribute_set, attribute_sets)
        self.logger.info("Needed utilities generated.")

        # Compare each value against all others in the set for near duplicates
        self.logger.info(
            f"Comparing each {self.attribute_name} value against all others..."
        )
        for v1 in attribute_set:
            self.logger.info(f"Comparing {v1} against all others in the set...")
            for v2 in attribute_set:
                self.logger.info(f"Comparing {v1} against {v2}...")
                if v1 == v2:
                    self.logger.info(f"{v1} is the same as {v2}, skipping...")
                    continue
                self.process_value_pair(
                    similarity_threshold,
                    most_frequent_variation,
                    value_signatures,
                    to_remove,
                    v1,
                    v2,
                )

        self.logger.info(f"Refining {self.attribute_name} set...")
        refined_attribute_set: Set[str] = attribute_set - to_remove
        self.logger.info(f"{self.attribute_name} set refined.")
        return refined_attribute_set

    def process_value_pair(
        self,
        similarity_threshold: float,
        most_frequent_variation: Dict[str, str],
        value_signatures: Dict[str, List[int]],
        to_remove: Set[str],
        v1: str,
        v2: str,
    ) -> None:
        """
        Compares two values and determines which one to keep based on MinHash similarity
        and most frequent variation.

        This method first compares the MinHash signatures of the two values to determine
        their similarity. If the similarity exceeds the specified threshold, it then
        determines which value to remove based on the most frequent variation. The value
        not chosen as the most frequent variation is added to the set of values to be removed.

        Args:
            similarity_threshold (float): Threshold for considering values as duplicates.
            most_frequent_variation (Dict[str, str]): Dictionary mapping normalized values
                                                     to their most frequent variations.
            value_signatures (Dict[str, List[int]]): Dictionary of MinHash signatures.
            to_remove (Set[str]): Set of values to be removed.
            v1, v2 (str): Values to compare.
        """
        self.logger.info(f"Comparing {self.attribute_name} values {v1} and {v2}...")

        self.logger.info(f"Getting MinHash signatures for {v1} and {v2}...")
        signature1: List[int] = value_signatures[v1]
        signature2: List[int] = value_signatures[v2]
        self.logger.info(f"MinHash signatures retrieved.")

        self.logger.info(f"Comparing MinHash signatures...")
        similarity: float = self.minhash_util.compare_signatures(signature1, signature2)
        self.logger.info(f"MinHash signatures compared. Similarity: {similarity}")

        # Early exit if the similarity is below the threshold
        if similarity <= similarity_threshold:
            self.logger.info(
                f"Similarity is below threshold ({similarity_threshold}), skipping..."
            )
            return

        self.logger.info(f"Normalizing values...")
        v1_normalized: str = v1.lower().replace(" ", "")
        v2_normalized: str = v2.lower().replace(" ", "")
        self.logger.info(f"Values normalized.")

        # Decide which value to keep
        self.logger.info(f"Deciding which value to keep...")
        to_remove.add(
            self.value_to_remove(
                most_frequent_variation, v1, v2, v1_normalized, v2_normalized
            )
        )
        self.logger.info(f"Value to remove decided.")

    def value_to_remove(
        self,
        most_frequent_variation: Dict[str, str],
        v1: str,
        v2: str,
        v1_normalized: str,
        v2_normalized: str,
    ) -> str:
        """
        Determines which of two values to remove based on their normalized forms and most frequent variations.

        This method checks if the normalized form of each value matches its most frequent variation.
        If one value matches its most frequent variation and the other does not, the non-matching
        value is chosen for removal. If neither or both values match their most frequent variations,
        the lexicographically greater value is chosen for removal.

        Args:
            most_frequent_variation (Dict[str, str]): Dictionary mapping normalized values
                                                     to their most frequent variations.
            v1, v2 (str): Original values to compare.
            v1_normalized, v2_normalized (str): Normalized forms of the values.

        Returns:
            str: The value to be removed.
        """
        self.logger.info(f"Deciding which {self.attribute_name} value to remove...")
        if (
            most_frequent_variation[v1_normalized] == v1
            and most_frequent_variation[v2_normalized] != v2
        ):
            self.logger.info(f"{v2} is the value to remove.")
            return v2
        elif (
            most_frequent_variation[v2_normalized] == v2
            and most_frequent_variation[v1_normalized] != v1
        ):
            self.logger.info(f"{v1} is the value to remove.")
            return v1
        # If none of the above conditions hold, return the lexicographically greater value
        self.logger.info(f"Returning the lexicographically greater value...")

        return v2 if v1 < v2 else v1

    def get_duplicate_utilities(
        self, attribute_set: set[str], attribute_sets: list[set[str]]
    ) -> tuple[Dict[str, str], Dict[str, List[int]], Set[str]]:
        """
        Generates utilities needed for duplicate removal.

        Args:
            attribute_set (set[str]): A set of values for which to generate MinHash signatures.
            attribute_sets (list[set[str]]): A list of sets, where each set contains values
                                           from a different category.

        Returns:
            tuple[Dict[str, str], Dict[str, List[int]], Set[str]]: A tuple containing:
                - most_frequent_variation: Dictionary mapping normalized values to their most frequent variations
                - value_signatures: Dictionary mapping each value to its MinHash signature
                - to_remove: Empty set for collecting values to be removed
        """
        self.logger.info(
            f"Generating utilities needed for {self.attribute_name} processing..."
        )
        most_frequent_variation: Dict[str, str] = self.get_most_frequent_variation(
            attribute_sets
        )
        self.logger.info("Most frequent variation dictionary generated.")

        value_signatures: Dict[str, List[int]] = self.generate_signatures(attribute_set)
        self.logger.info("Value signatures dictionary generated.")

        to_remove: Set[str] = set()
        self.logger.info("Set of values to remove initialized.")

        return most_frequent_variation, value_signatures, to_remove

    def generate_signatures(self, attribute_set: Set[str]) -> Dict[str, List[int]]:
        """
        Generates MinHash signatures for each value in the given set.

        This method tokenizes each value into n-grams, computes a MinHash signature for
        these n-grams, and stores the result. A MinHash signature is a compact representation
        of the set of n-grams and is used to estimate the similarity between sets of values.

        Args:
            attribute_set (set[str]): A set of values for which to generate MinHash signatures.

        Returns:
            dict[str, list[int]]: A dictionary mapping each value to its corresponding
                                 MinHash signature.
        """
        self.logger.info(
            f"Generating MinHash signatures for each {self.attribute_name} value..."
        )
        # Dictionary comprehension to generate a MinHash signature for each value
        value_signatures: Dict[str, List[int]] = {
            value: self.minhash_util.compute_signature(
                self.minhash_util.tokenize(value)
            )
            for value in attribute_set
        }
        self.logger.info(
            f"MinHash signatures for {self.attribute_name} values generated."
        )

        return value_signatures

    def get_most_frequent_variation(
        self, attribute_sets_list: List[Set[str]]
    ) -> Dict[str, str]:
        """
        Creates a dictionary that maps each unique normalized value to its most commonly
        occurring spelling variation across all provided sets.

        A 'normalized value' is derived by converting the original value to lowercase and
        removing all spaces, which helps in identifying different spellings of the same value
        as equivalent. The 'most frequent variation' refers to the spelling of the value that
        appears most often in the data, maintaining the original case and spaces.

        Args:
            attribute_sets_list (List[Set[str]]): A list where each set contains values from
                                                 a specific category. Each set may include
                                                 various spelling variations.

        Returns:
            Dict[str, str]: A dictionary with normalized values as keys and their most
                           frequent original spelling variations as values.
        """
        # Dictionary to store StringVariation objects for each normalized value
        self.logger.info(
            f"Creating dictionary to store {self.attribute_name} variations..."
        )
        value_variations: Dict[str, StringVariation] = self.string_variations
        self.logger.info("Variation dictionary initialized.")

        # Iterate over each set of values
        self.logger.info(f"Processing {self.attribute_name} sets...")
        for attribute_set in attribute_sets_list:
            self.logger.info(f"Processing set: {attribute_set}...")
            for value in attribute_set:
                self.logger.info(f"Processing value: {value}...")
                # Normalize the value
                normalized_value: str = value.lower().replace(" ", "")
                self.logger.info(f"Normalized value: {normalized_value}")

                # Create new StringVariation object if needed
                if normalized_value not in value_variations:
                    self.logger.info(
                        f"Creating new variation tracker for: {normalized_value}"
                    )
                    value_variations[normalized_value] = StringVariation(
                        normalized_value
                    )

                # Track this variation
                value_variations[normalized_value].add_variation(value)
                self.logger.info(f"Variation tracked: {value}")

        # Create dictionary of most frequent variations
        self.logger.info(
            f"Determining most frequent {self.attribute_name} variations..."
        )
        most_frequent_variation: Dict[str, str] = {
            normalized_value: variation.most_frequent_variation()
            for normalized_value, variation in value_variations.items()
        }
        self.logger.info("Most frequent variations determined.")

        return most_frequent_variation

    def standardize_values_across_sets(
        self, attribute_sets_list: List[Set[str]]
    ) -> List[Set[str]]:
        """
        Standardizes values across all sets by mapping each value to its most frequent
        variation across all sets.

        This method first generates a mapping of the most frequent variations for all values,
        then uses this mapping to standardize each value in each set. If a value has no
        recorded frequent variation, it remains unchanged.

        Args:
            attribute_sets_list (List[Set[str]]): A list of sets, where each set contains
                                                 values from a different category.

        Returns:
            List[Set[str]]: A list of sets containing the standardized values across
                           all categories.
        """
        # Generate the most frequent variation mapping across all sets
        self.logger.info(
            f"Generating the most frequent {self.attribute_name} variation mapping..."
        )
        most_frequent_variation: Dict[str, str] = self.get_most_frequent_variation(
            attribute_sets_list
        )
        self.logger.info("Most frequent variation mapping generated.")

        # Iterate through each set and standardize values based on the global mapping
        standardized_sets: List[Set[str]] = []
        self.logger.info(f"Standardizing {self.attribute_name} values across sets...")
        for attribute_set in attribute_sets_list:
            self.logger.info(f"Processing set: {attribute_set}...")
            standardized_set: Set[str] = set()
            for value in attribute_set:
                normalized_value: str = value.lower().replace(" ", "")
                self.logger.info(f"Normalized value: {normalized_value}")
                # Replace the value with its most frequent variation, if available
                standardized_value: str = most_frequent_variation.get(
                    normalized_value, value
                )
                self.logger.info(f"Standardized to: {standardized_value}")
                standardized_set.add(standardized_value)
            standardized_sets.append(standardized_set)
            self.logger.info("Set standardization complete.")

        self.logger.info(f"All {self.attribute_name} sets standardized.")
        return standardized_sets
