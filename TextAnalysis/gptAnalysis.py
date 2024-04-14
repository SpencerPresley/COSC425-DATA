''' 
Author: Cole Barbes
Last edited: 03/27/2024
Analyze abstracts to determine a set of categories
'''
import openai
import random
import os
import json
from dotenv import load_dotenv

load_dotenv('/home/cole/.openai')

API_KEY = os.getenv('OPENAI_API_KEY')

# Here we define the various prompts we will need within this framework of analysis functions

format = """ "Top-Level-Category" : { "mid-level-category": "low-level-category", "..."} """

format2 = """{
    'Computer Science': {
        'Machine Learning': 'Supervised Learning, Unsupervised Learning', 
        'Natural Language Processing': 'Named Entity Recognition, Sentiment Analysis', 
        'Computer Vision': 'Object Detection, Image Segmentation', 
        'Algorithms': 'Sorting Algorithms, Graph Algorithms'
    }, 
    'Health and Medicine': {
        'Public Health': 'Epidemiology, Health Policy', 
        'Medical Research': 'Clinical Trials, Genetics', 
        'Mental Health': 'Depression, Anxiety Disorders'
    }, 
    'Physics': {
        'Quantum Mechanics': 'Quantum Entanglement, Wave-Particle Duality', 
        'Astrophysics': 'Black Holes, Dark Matter', 
        'Condensed Matter Physics': 'Superconductivity, Semiconductors'
    }
}
"""

format_final = """{
    "Upper Level Categories" : [
        "Computer Science", 
        "Health and Medicine", 
        "Physics"
    ],
    "Mid-Level Categories" : [
        "Machine Learning",
        "Natural Language Processing",
        "Computer Vision",
        "Algorithms',
    ],
    "Themes" : [
        "Supervised Learning", 
        "Unsupervised Learning", 
        "Named Entity Recognition", 
        "Sentiment Analysis", 
        "Object Detection", 
        "Image Segmentation"
        "Sorting Algorithms", 
        "Graph Algorithms"
    ]
}
"""
class ResearchTaxonomy:
    def __init__(self, abstracts, prompt_num=0, file_name="Taxonomy.json"):
        self.prompt = [f"""
        You are an expert constructing a category taxonomy from an abstract to output JSON. \
        Given a list of predefined categories and topics \
        Please find a hierarchy of topics 
        Output the taxonomy in JSON\
        <Parent Category> : <Child Category>, <Child Category> \
        This should be a concise category like Computer Science
        Only give about 5 or 6 categories, they should be categories from this site https://arxiv.org/category_taxonomy\
        The caregories should not be sentences
        Here is an example taxonomy:
        machine learning 1st level
        learning paradigms 2nd level
        cross validation 2nd level -> supervised learning 3rd level, unsupervised learning 3rd level
        heres how it should look{format_final}""",
        """You are an expert at creating a taxonomy of categories for a collection of abstracts. Given an abstract form 3 JSON objects for Upper Level Categories, Middle level categories, Themes: {"Upper_level" : ["Medicine", "Computer Science", "Biology"] "Mid_level" : ["Cardiology", "Artificial Intelligence", "Marine Biology"] "Themes" : ["Heart Transplants","Large Language Models", "Marine Organisms"]}Take categories from the following websites: https://arxiv.org/category_taxonomy"""] 
        self.AbstractDict = abstracts
        self.prompt_num = prompt_num if prompt_num <= len(self.prompt) else 0
        self.file_name=file_name

    def get_response(self, messages, model='gpt-3.5-turbo', temperature=0.5, max_tokens=500):
        """
        This function prompts the openai api and returns the output
        Parameters: The message in open ai format, the model, the temperature, and the maximum token size
        Return: The output content in human readable format
        """
        response = openai.chat.completions.create(
            model=model,
            messages = messages, 
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    
    def get_taxonomy_abstracts(self):
        """
        This function creates a taxonomy of a random list of abstracts and outputs to json
        parameters: The abstract list, the prompt and the number of abstracts
        print to json file
        """
        # with open(file_name, 'r') as infile:
        #     json_output = json.load(infile)
        with open(self.file_name, 'w') as file:
            json_output = {}
            for key, value in self.AbstractDict.items():
                messages = [
                    {'role':'system', 'content':self.prompt[self.prompt_num]},
                    {'role':'user', 'content': key},
                ]

                output_taxonomy = self.get_response(messages=messages)
                json_output[key] = json.loads(output_taxonomy)
            json.dump(json_output, file, indent=4)
        print("Taxonomy of abstract Complete")
    
    def get_reduced_taxonomy(self):
        """
        Function to reduce category taxonomy 
        Category_Dict : {"upper level" : "mid-level" : {"low-level":"theme"}}
        """
        print()

    def get_categories(self):
        """
        Collect a large taxonomy based on a the abstract knowledge base
        """
        Upper_category_set = set()
        mid_category_set = set()
        theme_set = set()
        for abstract, value in self.AbstractDict.items():
            # create a prompt for the model
            messages = [
                {'role':'system', 'content':self.prompt[1]},
                {'role':'user', 'content': abstract},
            ]
            output_taxonomy = self.get_response(messages=messages)
            # load the dictionary
            temp_dict = json.loads(output_taxonomy)
            # load all the categories into their respective sets
            [Upper_category_set.add(i) for i in temp_dict["Upper_level"]]
            [mid_category_set.add(i) for i in temp_dict["Mid_level"]]
            [theme_set.add(i) for i in temp_dict["Themes"]]
        # return a dictionary of the categories for later use 
        return {"Upper":list(Upper_category_set), "Mid":list(mid_category_set), "Theme":list(theme_set)}


if __name__ == "__main__":
    file_path = input("Please enter the path to the data file: ")
    with open(file_path, 'r') as file:
        data = json.load(file)
    Tester = ResearchTaxonomy(data, file_name="NewTaxonomy.json")
    #Tester.get_taxonomy_abstracts()
    Taxonomy_Dict = Tester.get_categories()
    with open('taxonomyExample.json', 'w') as file:
        json.dump(Taxonomy_Dict, file, indent=4)