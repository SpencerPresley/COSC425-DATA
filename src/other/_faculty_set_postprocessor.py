from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass, field
from typing import Any, Dict, TYPE_CHECKING, List, Set, Tuple

from academic_metrics.configs import (
    configure_logging,
    DEBUG,
)

if TYPE_CHECKING:
    from academic_metrics.dataclass_models import CategoryInfo


class FacultyPostprocessor:
    """
    A class responsible for processing and standardizing faculty data across different categories.

    This class provides methods to extract faculty sets from category data, remove near-duplicate names,
    and standardize faculty names to ensure consistency across categories. It utilizes MinHash for estimating
    the similarity between names to effectively identify and remove duplicates. Additionally, it maintains
    a dictionary of name variations to track the most frequent spelling variations of each name.

    Attributes:
        temp_dict (dict): Temporary storage for faculty names and their occurrences.
        faculty_occurence_dict (dict): Tracks occurrences of faculty names across categories.
        processed_sets_list (list): Stores processed faculty sets after deduplication and standardization.
        minhash_util (MinHashUtility): Utility for generating MinHash signatures and comparing them.
        name_variations (dict): Stores NameVariation objects for each normalized faculty name.

    Methods:
        get_temp_dict(): Returns the temporary dictionary containing faculty names and their occurrences.
        extract_faculty_sets(category_dict): Extracts faculty sets from each CategoryInfo object in the provided dictionary.
        remove_near_duplicates(category_dict): Processes each CategoryInfo object to remove near-duplicate faculty names and standardize them.
        standardized_data_update(category_dict, standardized_sets): Updates CategoryInfo objects with standardized faculty sets.
        standardize_faculty(category_dict): Standardizes faculty names across all categories based on the most frequent spelling variations.
        remove_update_faculty(category_dict, faculty_sets_list): Removes near-duplicate faculty names within each faculty set.
        duplicate_postprocessor(faculty_set, faculty_sets, similarity_threshold): Processes a set of faculty names to remove near-duplicates.
        process_name_pair(similarity_threshold, most_frequent_variation, name_signatures, to_remove, n1, n2): Compares two names and determines which to keep.
        name_to_remove(most_frequent_variation, n1, n2, n1_normalized, n2_normalized): Determines which of two names to remove based on their variations.
        get_duplicate_utilities(faculty_set, faculty_sets): Generates utilities needed for duplicate removal.
        generate_signatures(faculty_set): Generates MinHash signatures for each name in a faculty set.
        get_most_frequent_name_variation(faculty_sets_list): Maps each normalized name to its most frequent spelling variation.
        standardize_names_across_sets(faculty_sets_list): Standardizes names in faculty sets based on the most frequent name variation.
    """

    def __init__(self):
        self.logger: logging.Logger = configure_logging(
            module_name=__name__,
            log_file_name="faculty_set_postprocessor",
            log_level=DEBUG,
        )

        self.logger.info("Initializing FacultyPostprocessor...")
        self.temp_dict: Dict[str, Any] = {}
        self.faculty_occurence_dict: Dict[str, Any] = {}
        self.processed_sets_list: List[Set[str]] = (
            []
        )  # List to store processed faculty sets

        self.logger.info("Initializing MinHashUtility...")
        self.minhash_util: MinHashUtility = MinHashUtility(
            num_hashes=100
        )  # Initialize MinHashUtility with 100 hash functions

        self.logger.info("Initializing NameVariation dictionary...")
        self.name_variations: Dict[str, NameVariation] = (
            {}
        )  # Dictionary to store NameVariation objects for each normalized name

    def get_temp_dict(self) -> Dict[str, Any]:
        """Returns the temporary dictionary containing faculty names and their occurrences.

        Returns:
            dict: The temporary dictionary containing faculty names and their occurrences.
        """
        self.logger.info("Returning temporary dictionary...")
        return self.temp_dict

    def extract_faculty_sets(
        self, category_dict: Dict[str, CategoryInfo]
    ) -> List[Set[str]]:
        """
        Extracts the faculty attribute from each CategoryInfo object in the provided dictionary.

        This method iterates over a dictionary of CategoryInfo objects and collects the 'faculty' set from each object.
        These faculty sets are typically used for further processing, such as deduplication or analysis.

        Args:
            category_dict (dict): A dictionary where the keys are category identifiers and the values are CategoryInfo objects.

        Returns:
            list[set]: A list containing the faculty set from each CategoryInfo object.
        """
        self.logger.info("Extracting faculty sets...")
        list_of_faculty_sets: List[Set[str]] = [
            category_info.faculty for category_info in category_dict.values()
        ]
        self.logger.info("Faculty sets extracted.")
        return list_of_faculty_sets

    def remove_near_duplicates(
        self, *, category_dict: Dict[str, CategoryInfo]
    ) -> Dict[str, CategoryInfo]:
        """
        Processes each CategoryInfo object to remove near-duplicate faculty names and standardize them across categories.

        This method orchestrates several steps to enhance the integrity and consistency of faculty data:
        1. Extract faculty sets.
        2. Remove near-duplicate names within each faculty set.
        3. Standardize faculty names across all categories.
        4. Update the category data with cleaned and standardized faculty sets.

        Args:
            category_dict (dict): A dictionary where the keys are category identifiers and the values are CategoryInfo objects.

        Returns:
            dict: The updated dictionary with cleaned and standardized faculty names across all CategoryInfo objects.
        """
        self.logger.info("Removing near-duplicates...")
        # Step 1
        faculty_sets_list: List[Set[str]] = self.extract_faculty_sets(
            category_dict=category_dict
        )
        self.logger.info("Faculty sets extracted.")

        # Step 2
        self.logger.info("Removing near-duplicate faculty names...")
        self.remove_update_faculty(category_dict, faculty_sets_list)
        self.logger.info("Near-duplicate faculty names removed.")

        # Step 3
        self.logger.info("Standardizing faculty names...")
        standardized_sets: List[Set[str]] = self.standardize_faculty(category_dict)
        self.logger.info("Faculty names standardized.")

        # Step 4
        self.logger.info("Updating category data...")
        self.standardized_data_update(category_dict, standardized_sets)
        self.logger.info("Category data updated.")
        return category_dict

    def standardized_data_update(
        self, category_dict: Dict[str, CategoryInfo], standardized_sets: List[Set[str]]
    ) -> None:
        """
        Updates the CategoryInfo objects in the dictionary with standardized faculty sets.

        Args:
            category_dict (dict): A dictionary where the keys are category identifiers and the values are CategoryInfo objects.
            standardized_sets (list[set]): A list of sets containing standardized faculty names.

        This method iterates over the category dictionary and updates each CategoryInfo object with the corresponding standardized faculty set.
        """
        self.logger.info("Updating category data...")
        for (_, category_info), standardized_set in zip(
            category_dict.items(), standardized_sets
        ):
            category_info.faculty = standardized_set
        self.logger.info("Category data updated.")

    def standardize_faculty(
        self, category_dict: Dict[str, CategoryInfo]
    ) -> List[Set[str]]:
        """
        Standardizes faculty names across all categories based on the most frequent spelling variations.

        Args:
            category_dict (dict): A dictionary where the keys are category identifiers and the values are CategoryInfo objects.

        Returns:
            list[set]: A list of sets containing the standardized faculty names across all categories.

        This method extracts updated faculty sets after duplicate removal and standardizes names across all sets based on the most frequent global variation.
        """
        self.logger.info("Standardizing faculty names...")
        updated_faculty_sets: List[Set[str]] = self.extract_faculty_sets(
            category_dict=category_dict
        )
        self.logger.info("Faculty sets extracted.")

        self.logger.info("Standardizing faculty names across all sets...")
        standardized_sets: List[Set[str]] = self.standardize_names_across_sets(
            updated_faculty_sets
        )
        self.logger.info("Faculty names standardized.")

        return standardized_sets

    def remove_update_faculty(
        self, category_dict: Dict[str, CategoryInfo], faculty_sets_list: List[Set[str]]
    ) -> None:
        """
        Removes near-duplicate faculty names within each faculty set based on MinHash similarity.

        Args:
            category_dict (dict): A dictionary where the keys are category identifiers and the values are CategoryInfo objects.
            faculty_sets_list (list[set]): A list containing the faculty set from each CategoryInfo object.

        This method iterates over each category and processes the faculty set to remove near-duplicates, updating the faculty attribute of each CategoryInfo object.
        """
        self.logger.info("Removing near-duplicate faculty names within each set...")
        for _, category_info in category_dict.items():
            final_set: Set[str] = self.duplicate_postprocessor(
                category_info.faculty, faculty_sets_list
            )
            category_info.faculty = final_set
        self.logger.info("Near-duplicate faculty names removed.")

    def duplicate_postprocessor(
        self,
        faculty_set: Set[str] | List[str],
        faculty_sets: List[Set[str]],
        similarity_threshold: float = 0.5,
    ) -> Set[str]:
        """
        Processes a set of faculty names to remove near-duplicate names based on MinHash similarity and most frequent variations.
        This method first generates the necessary utilities for comparison and removal.
        It then compares each name against all others in the set for near duplicates.
        If a name is deemed to be a duplicate based on MinHash similarity and the most frequent variation, it is added to the set of names to be removed.
        Finally, the refined faculty set is returned, excluding any names deemed to be duplicates.

        Args:
            faculty_set (Set[str]): A set of faculty names to be processed.
            faculty_sets (List[Set[str]]): A list of sets of faculty names, where each set contains the faculty names from a different category.
            similarity_threshold (float): The threshold for considering names as duplicates based on MinHash similarity.

        Returns:
            set[str]: The refined faculty set, excluding any names deemed to be duplicates.
        """
        # Generate needed utilities
        # most_frequent_variation is a dictionary that maps each normalized name to its most frequent variation
        # name_signatures is a dictionary that maps each name to its MinHash signature
        # to_remove is a set of names to be removed from the faculty set
        self.logger.info("Generating needed utilities...")
        if not isinstance(faculty_set, set):
            faculty_set = set(faculty_set)

        (
            most_frequent_variation,
            name_signatures,
            to_remove,
        ) = self.get_duplicate_utilities(faculty_set, faculty_sets)
        self.logger.info("Needed utilities generated.")

        # Step 3: Compare each name against all others in the set for near duplicates
        self.logger.info(
            "Comparing each name against all others in the set for near duplicates..."
        )
        for n1 in faculty_set:
            self.logger.info(f"Comparing {n1} against all others in the set...")
            for n2 in faculty_set:
                self.logger.info(f"Comparing {n1} against {n2}...")
                if n1 == n2:
                    self.logger.info(f"{n1} is the same as {n2}, skipping...")
                    continue
                self.logger.info(f"Comparing {n1} and {n2}...")
                self.process_name_pair(
                    similarity_threshold,
                    most_frequent_variation,
                    name_signatures,
                    to_remove,
                    n1,
                    n2,
                )

        self.logger.info("Refining faculty set...")
        refined_fac_set: Set[str] = faculty_set - to_remove
        self.logger.info("Faculty set refined.")
        return refined_fac_set

    def process_name_pair(
        self,
        similarity_threshold: float,
        most_frequent_variation: Dict[str, str],
        name_signatures: Dict[str, List[int]],
        to_remove: Set[str],
        n1: str,
        n2: str,
    ) -> None:
        """
        Compares two names and determines which one to keep based on MinHash similarity and most frequent variation.
        This method first compares the MinHash signatures of the two names to determine their similarity.
        If the similarity exceeds the specified threshold, it then determines which name to remove based on the most frequent variation.
        The name not chosen as the most frequent variation is added to the set of names to be removed.

        Args:
            n1, n2 (str): Names to compare.
            name_signatures (Dict[str, List[int]]): Dictionary of MinHash signatures.
            most_frequent_variation (Dict[str, str]): Dictionary mapping normalized names to their most frequent variations.
            to_remove (Set[str]): Set of names to be removed.
            similarity_threshold (float): Threshold for considering names as duplicates.
        """
        self.logger.info(f"Comparing {n1} and {n2}...")

        self.logger.info(f"Getting MinHash signatures for {n1} and {n2}...")
        signature1: List[int] = name_signatures[n1]
        signature2: List[int] = name_signatures[n2]
        self.logger.info(f"MinHash signatures for {n1} and {n2} retrieved.")

        self.logger.info(f"Comparing MinHash signatures for {n1} and {n2}...")
        similarity: float = self.minhash_util.compare_signatures(signature1, signature2)
        self.logger.info(f"MinHash signatures for {n1} and {n2} compared.")

        # Early exit if the similarity is below the threshold
        self.logger.info(f"Similarity: {similarity}")
        if similarity <= similarity_threshold:
            self.logger.info(f"Similarity is below the threshold, skipping...")
            return

        self.logger.info(f"Normalizing {n1} and {n2}...")
        n1_normalized: str = n1.lower().replace(" ", "")
        n2_normalized: str = n2.lower().replace(" ", "")
        self.logger.info(f"{n1} and {n2} normalized.")

        # Decide which name to keep
        self.logger.info(f"Deciding which name to keep...")
        to_remove.add(
            self.name_to_remove(
                most_frequent_variation, n1, n2, n1_normalized, n2_normalized
            )
        )
        self.logger.info(f"Name to remove decided.")

    def name_to_remove(
        self,
        most_frequent_variation: Dict[str, str],
        n1: str,
        n2: str,
        n1_normalized: str,
        n2_normalized: str,
    ) -> str:
        """
        Determines which of the two names to remove based on their normalized forms and the most frequent variations.
        This method checks if the normalized form of each name matches the most frequent variation.
        If one name matches its most frequent variation and the other does not, the non-matching name is chosen for removal.
        If neither or both names match their most frequent variations, the lexicographically greater name is chosen for removal.

        Args:
            most_frequent_variation (Dict[str, str]): Dictionary mapping normalized names to their most frequent variations.
            n1, n2 (str): Original names to compare.
            n1_normalized, n2_normalized (str): Normalized forms of the names.

        Returns:
            str: The name to be removed.
        """
        self.logger.info(f"Deciding which name to remove...")
        if (
            most_frequent_variation[n1_normalized] == n1
            and most_frequent_variation[n2_normalized] != n2
        ):
            self.logger.info(f"{n2} is the name to remove.")
            return n2
        elif (
            most_frequent_variation[n2_normalized] == n2
            and most_frequent_variation[n1_normalized] != n1
        ):
            self.logger.info(f"{n1} is the name to remove.")
            return n1
        # If none of the above conditions hold, return the lexicographically greater name
        self.logger.info(f"Returning the lexicographically greater name...")
        return n2 if n1 < n2 else n1

    def get_duplicate_utilities(
        self, faculty_set: set[str], faculty_sets: list[set[str]]
    ) -> tuple[Dict[str, str], Dict[str, List[int]], Set[str]]:
        """Generates utilities needed for duplicate removal.

        Args:
            faculty_set (set[str]): A set of faculty names for which to generate MinHash signatures.
            faculty_sets (list[set[str]]): A list of sets of faculty names, where each set contains the faculty names from a different category.

        Returns:
            tuple[Dict[str, str], Dict[str, List[int]], Set[str]]: A tuple containing the most frequent name variation dictionary, the name signatures dictionary, and the set of names to be removed.
        """
        self.logger.info("Generating utilities needed for duplicate removal...")
        most_frequent_variation: Dict[str, str] = self.get_most_frequent_name_variation(
            faculty_sets
        )
        self.logger.info("Most frequent name variation dictionary generated.")

        name_signatures: Dict[str, List[int]] = self.generate_signatures(faculty_set)
        self.logger.info("Name signatures dictionary generated.")

        to_remove: Set[str] = set()
        self.logger.info("Set of names to remove generated.")

        return most_frequent_variation, name_signatures, to_remove

    def generate_signatures(self, faculty_set: Set[str]) -> Dict[str, List[int]]:
        """
        Generates MinHash signatures for each name in the given faculty set.

        This method tokenizes each name into n-grams, computes a MinHash signature for these n-grams, and stores the result.
        A MinHash signature is a compact representation of the set of n-grams and is used to estimate the similarity between sets of names.

        Args:
            faculty_set (set[str]): A set of faculty names for which to generate MinHash signatures.

        Returns:
            dict[str, list[int]]: A dictionary mapping each name in the faculty set to its corresponding MinHash signature.
        """
        self.logger.info(
            "Generating MinHash signatures for each name in the faculty set..."
        )
        # Dictionary comprehension to generate a MinHash signature for each name
        name_signatures: Dict[str, List[int]] = {
            name: self.minhash_util.compute_signature(self.minhash_util.tokenize(name))
            for name in faculty_set
        }
        self.logger.info("MinHash signatures generated.")

        return name_signatures

    def get_most_frequent_name_variation(self, faculty_sets_list) -> Dict[str, str]:
        """
        Creates a dictionary that maps each unique normalized name to the most commonly occurring spelling variation of that name across all provided faculty sets. A 'normalized name' is derived by converting the original name to lowercase and removing all spaces, which helps in identifying different spellings of the same name as equivalent. The 'most frequent variation' refers to the spelling of the name that appears most often in the data, maintaining the original case and spaces.

        Args:
            faculty_sets_list (list of sets): A list where each set contains faculty names from a specific category. Each set is a collection of names that may include various spelling variations.

        Returns:
            most_frequent_variation (Dict[str, str]): A dictionary with normalized names as keys and their most frequent original spelling variations as values.
        """
        # Dictionary to store NameVariation objects for each normalized name
        self.logger.info(
            "Creating dictionary to store NameVariation objects for each normalized name..."
        )
        name_variations: Dict[str, NameVariation] = self.name_variations
        self.logger.info("Dictionary to store NameVariation objects created.")

        # Iterate over each set of faculty names
        self.logger.info("Iterating over each set of faculty names...")
        for faculty_set in faculty_sets_list:
            # Process each name in the set
            self.logger.info(f"Processing names in set: {faculty_set}...")
            for name in faculty_set:
                self.logger.info(f"Processing name: {name}...")
                # Normalize the name by converting to lowercase and removing spaces
                normalized_name: str = name.lower().replace(" ", "")
                self.logger.info(f"Normalized name: {normalized_name}...")

                self.logger.info(f"Checking if normalized name is in dictionary...")
                # If the normalized name is not already in the dictionary, add it with a new NameVariation object
                if normalized_name not in name_variations:
                    self.logger.info(f"Adding normalized name to dictionary...")
                    name_variations[normalized_name] = NameVariation(normalized_name)
                # Add the current variation of the name to the NameVariation object
                self.logger.info(
                    f"Adding current variation of the name to NameVariation object..."
                )
                name_variations[normalized_name].add_variation(name)

        # Create a dictionary to store the most frequent variation for each normalized name
        self.logger.info(
            "Creating dictionary to store the most frequent variation for each normalized name..."
        )
        most_frequent_variation: Dict[str, str] = {
            normalized_name: variation.most_frequent_variation()
            for normalized_name, variation in name_variations.items()
        }
        self.logger.info(
            "Dictionary to store the most frequent variation for each normalized name created."
        )

        return most_frequent_variation

    def standardize_names_across_sets(
        self, faculty_sets_list: List[Set[str]]
    ) -> List[Set[str]]:
        """Standardizes names across all sets by mapping each name to its most frequent variation across all sets.

        Args:
            faculty_sets_list (List[Set[str]]): A list of sets of faculty names, where each set contains the faculty names from a different category.

        Returns:
            List[Set[str]]: A list of sets containing the standardized faculty names across all categories.
        """
        # First, generate the most frequent name variation mapping across all sets
        self.logger.info(
            "Generating the most frequent name variation mapping across all sets..."
        )
        most_frequent_variation: Dict[str, str] = self.get_most_frequent_name_variation(
            faculty_sets_list
        )
        self.logger.info("Most frequent name variation mapping generated.")

        # Then, iterate through each set and standardize names based on the global mapping
        standardized_sets: List[Set[str]] = []
        self.logger.info("Iterating through each set and standardizing names...")
        for faculty_set in faculty_sets_list:
            self.logger.info(f"Standardizing names in set: {faculty_set}...")
            standardized_set: Set[str] = set()
            for name in faculty_set:
                normalized_name: str = name.lower().replace(" ", "")
                self.logger.info(f"Normalized name: {normalized_name}...")
                # Replace the name with its most frequent variation, if available
                standardized_name: str = most_frequent_variation.get(
                    normalized_name, name
                )
                self.logger.info(f"Standardized name: {standardized_name}...")
                standardized_set.add(standardized_name)
            standardized_sets.append(standardized_set)

        return standardized_sets


class MinHashUtility:
    """
    A utility class for performing MinHash calculations to estimate the similarity between sets of data.

    This class provides methods for generating hash functions, tokenizing strings into n-grams, computing MinHash signatures,
    and comparing these signatures to estimate the similarity between sets. The MinHash technique is particularly useful
    in applications where exact matches are not necessary, but approximate matches are sufficient, such as duplicate
    detection, document similarity, and clustering.

    Attributes:
        num_hashes (int): The number of hash functions to use in MinHash calculations, affecting the accuracy and
                          performance of the similarity estimation.
        large_prime (int): A large prime number used as the modulus in hash functions to minimize collisions.
        hash_fns (list[callable]): A list of pre-generated hash functions used for computing MinHash signatures.

    Methods:
        tokenize(string, n): Tokenizes a string into n-grams.
        generate_coefficients(): Generates random coefficients for hash functions.
        generate_hash_functions(): Creates a list of hash functions based on generated coefficients.
        compute_signature(tokens): Computes the MinHash signature for a set of tokens.
        compare_signatures(signature1, signature2): Compares two MinHash signatures and returns their estimated similarity.

    The class utilizes linear hash functions of the form h(x) = (a * x + b) % large_prime, where 'a' and 'b' are randomly
    generated coefficients. This approach helps in reducing the likelihood of hash collisions and ensures a uniform
    distribution of hash values.

    Example usage:
        minhash_util = MinHashUtility(num_hashes=200)
        tokens = minhash_util.tokenize("example string", n=3)
        signature = minhash_util.compute_signature(tokens)
        # Further operations such as comparing signatures can be performed.

    More on MinHash: https://en.wikipedia.org/wiki/MinHash
    """

    def __init__(self, num_hashes: int):
        """
        Initialize the MinHashUtility with the specified number of hash functions.

        Args:
            num_hashes (int): The number of hash functions to use for MinHash calculations.
        """
        self.logger.info(
            f"Initializing MinHashUtility with {num_hashes} hash functions..."
        )

        self.num_hashes: int = num_hashes  # Number of hash functions to use for MinHash
        self.logger.info(f"Number of hash functions set to {num_hashes}.")

        self.large_prime: int = 999983  # large prime number used for hashing
        self.logger.info(f"Large prime number set to 999983.")

        self.hash_fns: List[callable] = (
            self.generate_hash_functions()
        )  # List of hash functions
        self.logger.info("Hash functions generated.")

    def tokenize(self, string: str, n: int = 3) -> Set[str]:
        """
        Tokenize the given string into n-grams to facilitate the identification of similar strings.

        N-grams are contiguous sequences of 'n' characters extracted from a string. This method is useful in various
        applications such as text similarity, search, and indexing where the exact match is not necessary, but approximate
        matches are useful.

        More on n-grams: https://en.wikipedia.org/wiki/N-gram

        Args:
            string (str): The string to be tokenized.
            n (int): The length of each n-gram. Default is 3.

        Returns:
            set: A set containing unique n-grams derived from the input string.

        Raises:
            ValueError: If 'n' is greater than the length of the string or less than 1.
        """
        # If the n-gram length is invalid, raise a ValueError
        self.logger.info(f"Checking if n-gram length is valid...")
        if n > len(string) or n < 1:
            self.logger.error(f"N-gram length is invalid, raising ValueError...")
            raise ValueError(
                "The n-gram length 'n' must be between 1 and the length of the string."
            )

        n_grams: set = set()  # Set to store unique n-grams
        self.logger.info(f"N-grams set created.")

        # Loop through the string to extract n-grams
        self.logger.info(f"Looping through the string to extract n-grams...")
        for i in range(len(string) - n + 1):
            n_gram: str = string[i : i + n]
            n_grams.add(n_gram)

        self.logger.info(f"N-grams extracted.")

        return n_grams

    def generate_coeeficients(self) -> List[Tuple[int, int]]:
        """
        Generate a list of tuples, each containing a pair of coefficients (a, b) used for hash functions.

        Each tuple consists of:
        - a (int): A randomly chosen multiplier coefficient.
        - b (int): A randomly chosen additive coefficient.

        These coefficients are used in the linear hash functions for MinHash calculations.

        Returns:
            list[tuple[int, int]]: A list of tuples, where each tuple contains two integers (a, b).
        """
        coefficients: list = []  # List to store pairs of coefficients (a, b)
        self.logger.info(f"Coefficients list created.")

        # Generate a pair of coefficients for each hash function
        self.logger.info(f"Generating a pair of coefficients for each hash function...")
        for _ in range(self.num_hashes):
            a = random.randint(
                1, self.large_prime - 1
            )  # Randomly choose multiplier coefficient
            b = random.randint(
                0, self.large_prime - 1
            )  # Randomly choose additive coefficient
            coefficients.append((a, b))

        self.logger.info(f"Coefficients list populated.")

        return coefficients

    def generate_hash_functions(self) -> List[callable]:
        """
        Generate a list of linear hash functions for use in MinHash calculations.

        Each hash function is defined by a unique pair of coefficients (a, b) and is created using a factory function.
        These hash functions are used to compute hash values for elements in a set, which are essential for estimating
        the similarity between sets using the MinHash technique.

        The hash functions are of the form: h(x) = (a * x + b) % large_prime, where 'large_prime' is a large prime number
        used to reduce collisions in hash values.

        Overview of hash functions: https://en.wikipedia.org/wiki/Hash_function

        Returns:
            list: A list of lambda functions, each representing a linear hash function.
        """
        self.logger.info(f"Generating a list of linear hash functions...")

        def _hash_factory(a, b) -> callable:
            """
            Factory function to create a hash function with specified coefficients.

            Args:
                a (int): The multiplier coefficient in the hash function.
                b (int): The additive coefficient in the hash function.

            Returns:
                callable: A lambda function that takes an integer x and returns (a * x + b) % large_prime.
            """
            # Defines a hash function with coefficients a, b
            self.logger.info(f"Defining hash function with coefficients {a} and {b}...")
            return lambda x: (a * x + b) % self.large_prime

        hash_fns: list = []
        self.logger.info(f"Hash functions list created.")

        for _ in range(self.num_hashes):
            self.logger.info(f"Generating hash function {_}...")
            a = random.randint(
                1, self.large_prime - 1
            )  # Randomly choose multiplier coefficient
            self.logger.info(f"Multiplier coefficient {a} generated.")
            b = random.randint(
                0, self.large_prime - 1
            )  # Randomly choose additive coefficient
            self.logger.info(f"Additive coefficient {b} generated.")
            hash_fns.append(_hash_factory(a, b))
            self.logger.info(f"Hash function {_} generated.")

        return hash_fns

    def compute_signature(self, tokens: Set[int]) -> List[int]:
        """
        Compute MinHash signature for a set of tokens.
        A MinHash signature consists of the minimum hash value produced by each hash function across all tokens,
        which is used to estimate the similarity between sets of data.

        Detailed explanation of MinHash and its computation: https://en.wikipedia.org/wiki/MinHash

        Args:
            tokens (set[int]): A set of hashed tokens for which to compute the MinHash signature.

        Returns:
            list[int]: A list of minimum hash values, representing the MinHash signature.
        """
        # Initialize the signature with infinity values, which will later be replaced by the minimum hash values found.
        self.logger.info(f"Initializing signature with infinity values...")
        signature: list[int] = [float("inf")] * self.num_hashes
        self.logger.info(f"Signature initialized.")

        # Iterate over each token to compute its hash values using predefined hash functions
        self.logger.info(
            f"Iterating over each token to compute its hash values using predefined hash functions..."
        )
        for token in tokens:
            self.logger.info(f"Computing hash values for token {token}...")

            # Compute hash values for the token using each hash function
            self.logger.info(
                f"Computing hash values for token {token} using each hash function..."
            )
            hashed_values: list[int] = [
                hash_fn(hash(token)) for hash_fn in self.hash_fns
            ]
            self.logger.info(f"Hash values computed for token {token}.")

            # Update the signature by keeping the minimum hash value for each hash function
            self.logger.info(
                f"Updating the signature by keeping the minimum hash value for each hash function..."
            )
            for i in range(self.num_hashes):
                signature[i] = min(signature[i], hashed_values[i])
            self.logger.info(f"Signature updated.")

        self.logger.info(f"MinHash signature computed.")
        return signature

    def compare_signatures(self, signature1: List[int], signature2: List[int]) -> float:
        """
        Compare two MinHash signatures and return their similarity.
        The similarity is calculated as the fraction of hash values that are identical in the two signatures,
        which estimates the Jaccard similarity of the original sets from which these signatures were derived.

        This method is based on the principle that the more similar the sets are, the more hash values they will share,
        thus providing a proxy for the Jaccard index of the sets.

        More on estimating similarity with MinHash: https://en.wikipedia.org/wiki/Jaccard_index#MinHash

        Args:
            signature1 (list[int]): The MinHash signature of the first set, represented as a list of integers.
            signature2 (list[int]): The MinHash signature of the second set, represented as a list of integers.

        Returns:
            float: The estimated similarity between the two sets, based on their MinHash signatures.

        Raises:
            AssertionError: If the two signatures do not have the same length.
        """
        # Ensure both signatures are of the same length to compare them correctly
        self.logger.info(
            f"Ensuring both signatures are of the same length to compare them correctly..."
        )
        assert len(signature1) == len(
            signature2
        ), "Signatures must be of the same length."
        self.logger.info(f"Signatures are of the same length.")

        # Count the number of positions where the two signatures have the same hash value
        self.logger.info(
            f"Counting the number of positions where the two signatures have the same hash value..."
        )
        matching: int = sum(1 for i, j in zip(signature1, signature2) if i == j)
        self.logger.info(f"Number of matching positions counted.")

        # Calculate the similarity as the ratio of matching positions to the total number of hash functions
        self.logger.info(
            f"Calculating the similarity as the ratio of matching positions to the total number of hash functions..."
        )
        similarity: float = matching / len(signature1)
        self.logger.info(f"Similarity calculated.")
        return similarity


@dataclass
class NameVariation:
    """
    A data class for tracking different spelling variations of a normalized name and determining the most frequent variation.

    Attributes:
        normalized_name (str): The base form of the name, typically normalized to lower case and stripped of spaces.
        variations (dict[str, int]): A dictionary where keys are variations of the name and values are the counts of how often each variation occurs.

    Methods:
        add_variation(variation: str): Adds a variation of the name to the dictionary or increments its count if it already exists.
        most_frequent_variation(): Returns the variation of the name that occurs most frequently.
    """

    normalized_name: str

    # Default factory for variations ensures it starts as an empty dict.
    variations: Dict[str, int] = field(default_factory=dict)

    def add_variation(self, variation: str) -> None:
        """
        Adds a variation of the name to the dictionary or increments its count if it already exists.

        Args:
            variation (str): A specific spelling variation of the name.

        This method modifies the variations dictionary by either adding a new key with a count of 1 or incrementing the count of an existing key.
        """
        # Check if the variation is already in the dictionary and increment its count, otherwise add it with a count of 1
        self.logger.info(
            f"Checking if the variation {variation} is already in the dictionary and incrementing its count..."
        )
        if variation in self.variations:
            self.logger.info(
                f"Variation {variation} already in dictionary, incrementing count..."
            )
            self.variations[variation] += 1
            return
        self.logger.info(
            f"Variation {variation} not in dictionary, adding it with a count of 1..."
        )
        self.variations[variation] = 1

    def most_frequent_variation(self) -> str:
        """
        Returns the variation of the name that occurs most frequently.

        This method finds the key with the highest value in the variations dictionary, which represents the most common spelling variation.
        If the variations dictionary is empty, it raises a ValueError indicating that no variations have been added.

        Returns:
            str: The most frequent variation of the name.

        Raises:
            ValueError: If no variations are found in the dictionary, detailing the normalized name associated with the error.
        """
        # Check if the variations dictionary is empty and raise an error if it is
        self.logger.info(f"Checking if the variations dictionary is empty...")
        if not self.variations:
            self.logger.error(
                f"No variations found for the normalized name: '{self.normalized_name}', raising ValueError..."
            )
            raise ValueError(
                f"No variations found for the normalized name: '{self.normalized_name}'."
            )
        self.logger.info(f"Variations dictionary is not empty.")

        # Return the key (variation) with the maximum value (count) in the variations dictionary
        self.logger.info(
            f"Returning the key (variation) with the maximum value (count) in the variations dictionary..."
        )
        return max(self.variations, key=self.variations.get)
