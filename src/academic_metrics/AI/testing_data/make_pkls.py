import os
import json
import pickle
from typing import List
import logging


def get_directories() -> List[str]:
    logger.info("Getting directories")
    THIS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"THIS_DIRECTORY: {THIS_DIRECTORY}")
    METHOD_EXTRACTION_DIRECTORY = os.path.join(THIS_DIRECTORY, "method_extraction")
    logger.info(f"METHOD_EXTRACTION_DIRECTORY: {METHOD_EXTRACTION_DIRECTORY}")
    SENTENCE_ANALYSIS_DIRECTORY = os.path.join(THIS_DIRECTORY, "sentence_analysis")
    logger.info(f"SENTENCE_ANALYSIS_DIRECTORY: {SENTENCE_ANALYSIS_DIRECTORY}")
    SUMMARY_DIRECTORY = os.path.join(THIS_DIRECTORY, "summary")
    logger.info(f"SUMMARY_DIRECTORY: {SUMMARY_DIRECTORY}")
    logger.info("Returning directories")
    return (METHOD_EXTRACTION_DIRECTORY, SENTENCE_ANALYSIS_DIRECTORY, SUMMARY_DIRECTORY)


def get_files_from_directory(directory_path: str) -> List[str]:
    logger.info(f"Getting files from {directory_path}")
    files_list = [
        f
        for f in os.listdir(directory_path)
        if os.path.isfile(os.path.join(directory_path, f))
    ]
    logger.info(f"Got {len(files_list)} files from {directory_path}")
    return files_list


def load_json_file(file_path: str) -> dict:
    logger.info(f"Loading json file from {file_path}")
    with open(file_path, "r") as f:
        logger.info(f"Loaded json file from {file_path}")
        logger.info(f"Returning json file")
        return json.load(f)


def get_list_of_dicts(directory_path: str, files_list: List[str]) -> List[dict]:
    logger.info(f"Getting list of dicts from {files_list}")
    list_of_dicts = [
        load_json_file(os.path.join(directory_path, file_path))
        for file_path in files_list
    ]
    logger.info(f"Got {len(list_of_dicts)} list of dicts")
    return list_of_dicts


def save_list_of_dicts(
    logger: logging.Logger, list_of_dicts: List[dict], save_path: str
) -> None:
    logger.info(f"Saving list of dicts to {save_path}")
    logger.info(f"List of dicts: {list_of_dicts}")
    with open(save_path, "wb") as f:
        logger.info(f"Dumping list of dicts to {save_path}")
        pickle.dump(list_of_dicts, f)
    logger.info(f"Saved list of dicts to {save_path}")


def make_pkl(logger: logging.Logger, directory_path: str, pkl_file_name: str) -> None:
    files_list = get_files_from_directory(directory_path)
    list_of_dicts = get_list_of_dicts(directory_path, files_list)
    save_path = os.path.join(directory_path, pkl_file_name)
    save_list_of_dicts(logger, list_of_dicts, save_path)


def get_method_extraction_file_list(
    logger: logging.Logger, method_extraction_directory: str
) -> List[str]:
    logger.info(
        f"Getting method extraction file list from {method_extraction_directory}"
    )
    return get_files_from_directory(method_extraction_directory)


def get_sentence_analysis_file_list(
    logger: logging.Logger, sentence_analysis_directory: str
) -> List[str]:
    logger.info(
        f"Getting sentence analysis file list from {sentence_analysis_directory}"
    )
    return get_files_from_directory(sentence_analysis_directory)


def get_summary_file_list(logger: logging.Logger, summary_directory: str) -> List[str]:
    logger.info(f"Getting summary file list from {summary_directory}")
    return get_files_from_directory(summary_directory)


def set_up_logging() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    return logger


def set_log_to_console(log_to_console: bool) -> None:
    LOG_TO_CONSOLE = log_to_console
    logger.addHandler(logging.StreamHandler()) if LOG_TO_CONSOLE else None


if __name__ == "__main__":
    logger = set_up_logging()
    logger.info("Set up logging")
    set_log_to_console(True)
    logger.info("Set LOG_TO_CONSOLE True")
    logger.info("Getting directories")
    (
        method_extraction_directory,
        sentence_analysis_directory,
        summary_directory,
    ) = get_directories()
    logger.info(
        f"Got directories: {method_extraction_directory}, {sentence_analysis_directory}, {summary_directory}"
    )
    logger.info("Getting method extraction file list")
    method_extraction_file_list = get_method_extraction_file_list(
        logger, method_extraction_directory
    )
    logger.info(f"Got method extraction file list: {method_extraction_file_list}")
    logger.info("Getting sentence analysis file list")
    sentence_analysis_file_list = get_sentence_analysis_file_list(
        logger, sentence_analysis_directory
    )
    logger.info(f"Got sentence analysis file list: {sentence_analysis_file_list}")
    logger.info("Getting summary file list")
    summary_file_list = get_summary_file_list(logger, summary_directory)
    logger.info(f"Got summary file list: {summary_file_list}")
    logger.info("Making all pkls")
    make_pkl(logger, method_extraction_directory, "method_extraction.pkl")
    logger.info("Made method extraction pkl")
    make_pkl(logger, sentence_analysis_directory, "sentence_analysis.pkl")
    logger.info("Made sentence analysis pkl")
    make_pkl(logger, summary_directory, "summary.pkl")
    logger.info("Made summary pkl")
    logger.info("Made all pkls")
