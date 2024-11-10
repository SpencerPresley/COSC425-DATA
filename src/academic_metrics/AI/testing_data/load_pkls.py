import os
import pickle

THIS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

METHOD_DIRECTORY = os.path.join(THIS_DIRECTORY, "method_extraction")
SENTENCE_DIRECTORY = os.path.join(THIS_DIRECTORY, "sentence_analysis")
SUMMARY_DIRECTORY = os.path.join(THIS_DIRECTORY, "summary")

METHOD_PKL_FILE_NAME = "method_extraction.pkl"
SENTENCE_PKL_FILE_NAME = "sentence_analysis.pkl"
SUMMARY_PKL_FILE_NAME = "summary.pkl"

METHOD_PKL_FILE_PATH = os.path.join(METHOD_DIRECTORY, METHOD_PKL_FILE_NAME)
SENTENCE_PKL_FILE_PATH = os.path.join(SENTENCE_DIRECTORY, SENTENCE_PKL_FILE_NAME)
SUMMARY_PKL_FILE_PATH = os.path.join(SUMMARY_DIRECTORY, SUMMARY_PKL_FILE_NAME)


def load_pkls():
    with open(METHOD_PKL_FILE_PATH, "rb") as f:
        method_extraction_list = pickle.load(f)
    with open(SENTENCE_PKL_FILE_PATH, "rb") as f:
        sentence_analysis_list = pickle.load(f)
    with open(SUMMARY_PKL_FILE_PATH, "rb") as f:
        summary_list = pickle.load(f)
    return method_extraction_list, sentence_analysis_list, summary_list


if __name__ == "__main__":
    method_extraction_list, sentence_analysis_list, summary_list = load_pkls()
    print(method_extraction_list)
    print(sentence_analysis_list)
    print(summary_list)
