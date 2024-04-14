''' 
Author: Cole Barbes
Last edited: 03/27/2024
Analyze abstracts to determine a set of categories
'''
import openai
import random
import os
import json

# from dotenv import load_dotenv

# load_dotenv('/home/cole/.openai')

API_KEY = os.getenv('OPENAI_API_KEY')
class ResearchTaxonomy:
    def __init__(self, abstracts, prompt_num=0, file_name="Taxonomy.json"):
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
        self.prompt = [f"""
        You are an expert constructing a category taxonomy from an abstract to output JSON. \
        Given a list of predefined categories and topics \
        Please find a hierarchy of topics 
        Output the taxonomy in JSON\
        <Parent Category> : <Child Category>, <Child Category> \
        This should be a concise category like Computer Science
        Only give about 5 or 6 categories, they should be categories from this site https://arxiv.org/category_taxonomy\
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
        This function creates a taxonomy of a list of abstracts and outputs to json
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
                    {'role':'user', 'content': value['abstract']},
                ]

                output_taxonomy = self.get_response(messages=messages)
                json_output[key] = json.loads(output_taxonomy)
            json.dump(json_output, file, indent=4)
        print("Taxonomy of abstract Complete")
    
    def get_individual_taxonomy(self, abstractData, title):
        with open(self.file_name, 'w') as file:
            json_output = {}
            messages = [
                {'role':'system', 'content':self.prompt[self.prompt_num]},
                {'role':'user', 'content': abstractData['abstract']},
            ]

            output_taxonomy = self.get_response(messages=messages)
            json_output[title] = json.loads(output_taxonomy)
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
        for title, value in self.AbstractDict.items():
            # create a prompt for the model
            messages = [
                {'role':'system', 'content':self.prompt[1]},
                {'role':'user', 'content': value['abstract']},
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
    outFile = input("Please enter the output files name: ")
    Tester = ResearchTaxonomy(data, file_name=outFile)
    # Tester.get_taxonomy_abstracts()
    Tester.get_individual_taxonomy(data['Probability puppets'], title='Probability puppets')
    # Taxonomy_Dict = Tester.get_categories()
    # with open('taxonomyExample.json', 'w') as file:
    #     json.dump(Taxonomy_Dict, file, indent=4)