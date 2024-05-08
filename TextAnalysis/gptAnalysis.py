""" 
Author: Cole Barbes
Last edited: 03/27/2024
Analyze abstracts to determine a set of categories
"""

import openai
import random
import os
import json
import re


class ResearchTaxonomy:
    def __init__(self, prompt_num=0, file_name="Taxonomy.json", data_needed=False):
        if(data_needed == True):
            self.inFile = input("Please enter the path to the abstract file: ")
            with open(self.inFile, "r") as file:
                self.AbstractDict = json.load(file)
        format_final = """
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
                "Object Detection", { "hello world " : ["yuck"]} 
                "Image Segmentation"
                "Sorting Algorithms", 
                "Graph Algorithms"
            ]
        """
        # set of prompts for the class to use, more can be added when instanciated
        self.prompt = [
            f"""
        You are an expert constructing a category taxonomy from an abstract\
        The output Must be in JSON, do not output this with ```json ``` around the JSON\
        Given a list of predefined categories and topics \
        Please find a hierarchy of topics 
        <Parent Category> : <Child Category>, <Child Category> \
        This should be a concise category like Computer Science
        Only give about 5 or 6 categories, they should be categories from this site https://arxiv.org/category_taxonomy\
        heres how it should look {format_final}""",
            """You are an expert at creating a taxonomy of categories for a collection of abstracts. Given an abstract form 3 JSON objects for Upper Level Categories, Middle level categories, Themes: {"Upper_level" : ["Medicine", "Computer Science", "Biology"] "Mid_level" : ["Cardiology", "Artificial Intelligence", "Marine Biology"] "Themes" : ["Heart Transplants","Large Language Models", "Marine Organisms"]}Take categories from the following websites: https://arxiv.org/category_taxonomy""",
            """
                Using the category given to you, go to wikipedia https://www.wikipedia.org/ 
                and grab a definition for the category. This definition should be in direct correlation to the category.
                output the quote as follows in JSON format.
                Education :{
                        "Definition": "Education is the transmission of knowledge, skills, and character traits and manifests in various forms. Formal education occurs within a structured institutional framework, such as public schools, following a curriculum. Non-formal education also follows a structured approach but occurs outside the formal schooling system, while informal education entails unstructured learning through daily experiences. ",
                        "source": "wikipedia"
                } 
            """
        ]
        # set the prompt number
        self.prompt_num = prompt_num if prompt_num <= len(self.prompt) else 0
        # set the file name
        self.file_name = file_name

        if data_needed is True:
            self.get_taxonomy_abstracts()

    def get_response(
        self, messages, model="gpt-3.5-turbo", temperature=0.5, max_tokens=1000
    ):
        """
        This function prompts the openai api and returns the output
        Parameters: The message in open ai format, the model, the temperature, and the maximum token size
        Return: The output content in human readable format
        """
        response = openai.chat.completions.create(
            model=model,
            messages=messages,
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
        with open(self.file_name, "a") as file:
            json_output = {}
            for key, value in self.AbstractDict.items():
                messages = [
                    {"role": "system", "content": self.prompt[self.prompt_num]},
                    {"role": "user", "content": value["abstract"]},
                ]

                output_taxonomy = self.get_response(messages=messages)
                # test the output to be sure that it is correct
                try:
                    json_output[key] = json.loads(output_taxonomy)
                except json.JSONDecodeError:
                    # use a regex to fix the string
                    cleaned_json = re.sub(
                        r"^```json\s*|\s*```$", "", output_taxonomy
                    ).strip()
            json.dump(json_output, file, indent=4)
        print("Taxonomy of abstract Complete")
        return json_output

    def get_individual_taxonomy(self, abstractData, title, outputType="file"):
        """
        This function gets an individual publications taxonomy
        parameters needed: the abstracts data should be as follows in a dictionary { "title":"..."{
        "abstract":"...",
        "categories":"...",
        }}
        optionally, you can set whether
        """
        json_output = {}
        messages = [
            {"role": "system", "content": self.prompt[self.prompt_num]},
            {"role": "user", "content": abstractData},
        ]

        output_taxonomy = self.get_response(messages=messages)
        print(output_taxonomy)
        json_output[title] = json.loads(output_taxonomy)
        print("Taxonomy of abstract Complete")
        if outputType.lower() == "file":
            with open(self.file_name, "w") as file:
                json.dump(json_output, file, indent=4)
        return json_output

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
                {"role": "system", "content": self.prompt[1]},
                {"role": "user", "content": value["abstract"]},
            ]
            output_taxonomy = self.get_response(messages=messages)
            # load the dictionary
            temp_dict = json.loads(output_taxonomy)
            # load all the categories into their respective sets
            [Upper_category_set.add(i) for i in temp_dict["Upper_level"]]
            [mid_category_set.add(i) for i in temp_dict["Mid_level"]]
            [theme_set.add(i) for i in temp_dict["Themes"]]
        # return a dictionary of the categories for later use
        return {
            "Upper": list(Upper_category_set),
            "Mid": list(mid_category_set),
            "Theme": list(theme_set),
        }

    def add_theme_taxonomy(self, fileName):
        """
        Function to add themes to the taxonomy
        """
        with open(fileName, "r") as file:
            categoryDict = json.load(file)

        with open(self.file_name, "r") as file:
            result_dict = file.read()
            result_dict = json.loads(result_dict)

        categoryList = list(categoryDict.keys())

        for category in categoryList:
            for title in categoryDict[category]["titles"]:
                if title in result_dict:
                    categoryDict[category]["themes"] = result_dict[title]["Themes"]

        with open("output_data.json", "w") as file:
            json.dump(categoryDict, file, indent=4)

        return categoryDict

    def get_definition(self, fileName):
        with open(fileName, "r") as file:
            categoryDict = json.load(file)

        for category, value in categoryDict.items():
            json_output = {}
            messages = [
                {"role": "system", "content": self.prompt[2]},
                {"role": "user", "content": category},
            ]
            output_taxonomy = self.get_response(messages=messages)
            #print(category, " ", output_taxonomy)
            try:
                    value['definition'] = json.loads(output_taxonomy)
            except json.JSONDecodeError:
                # use a regex to fix the string
                cleaned_json = re.sub(
                    r"^```json\s*|\s*```$", "", output_taxonomy
                ).strip()
        
        with open("definition_output.json", "w") as file:
            json.dump(categoryDict, file, indent=4)

        

if __name__ == "__main__":
    Tester = ResearchTaxonomy(data_needed=False)
    filePath = input("Please enter the path to the file containing the taxonomy: ")
    type = input("Would you like to add the themes to the taxonomy? ")
    if type == "yes":
        Tester.add_theme_taxonomy(fileName=filePath)
    else:
        Tester.get_definition(fileName=filePath)
