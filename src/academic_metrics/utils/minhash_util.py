from __future__ import annotations
import random

from typing import List, Tuple, Set, TYPE_CHECKING
from academic_metrics.configs import configure_logging, DEBUG

if TYPE_CHECKING:
    import logging


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

    def __init__(self, num_hashes: int, large_prime: int | None = 999983):
        """
        Initialize the MinHashUtility with the specified number of hash functions.

        Args:
            num_hashes (int): The number of hash functions to use for MinHash calculations.
            large_prime (int): The large prime number to use for hashing. Default is 999983.
        """
        self.logger: logging.Logger = configure_logging(
            module_name=__name__,
            log_file_name=f"minhash_util",
            log_level=DEBUG,
        )

        self.logger.info(
            f"Initializing MinHashUtility with {num_hashes} hash functions..."
        )

        self.num_hashes: int = num_hashes  # Number of hash functions to use for MinHash
        self.logger.info(f"Number of hash functions set to {num_hashes}.")

        self.large_prime: int = large_prime  # large prime number used for hashing
        self.logger.info(f"Large prime number set to {large_prime}.")

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

        n_grams: Set[str] = set()  # Set to store unique n-grams
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
        coefficients: List[Tuple[int, int]] = (
            []
        )  # List to store pairs of coefficients (a, b)
        self.logger.info(f"Coefficients list created.")

        # Generate a pair of coefficients for each hash function
        self.logger.info(f"Generating a pair of coefficients for each hash function...")
        for _ in range(self.num_hashes):
            a: int = random.randint(
                1, self.large_prime - 1
            )  # Randomly choose multiplier coefficient
            b: int = random.randint(
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

        hash_fns: List[callable] = []
        self.logger.info(f"Hash functions list created.")

        for _ in range(self.num_hashes):
            self.logger.info(f"Generating hash function {_}...")
            a: int = random.randint(
                1, self.large_prime - 1
            )  # Randomly choose multiplier coefficient
            self.logger.info(f"Multiplier coefficient {a} generated.")
            b: int = random.randint(
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
        signature: List[int] = [float("inf")] * self.num_hashes
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
            hashed_values: List[int] = [
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
