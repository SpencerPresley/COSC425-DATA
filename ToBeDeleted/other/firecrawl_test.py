from langchain_community.document_loaders import FireCrawlLoader
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import json
from typing import Optional

# class FacultyMember(BaseModel):
#     name: str = Field(..., description="The name of the faculty member")
#     position: str = Field(..., description="The position of the faculty member")
#     department: str = Field(..., description="The department of the faculty member")
#     email: Optional[str] = Field(None, description="The email of the faculty member")
#     phone: Optional[str] = Field(None, description="The phone number of the faculty member")

from pydantic import BaseModel, Field
from typing import Dict, List

class FacultyMember(BaseModel):
    name: str = Field(..., description="The name of the faculty member")
    position: str = Field(..., description="The position of the faculty member")
    department: str = Field(..., description="The department of the faculty member")
    email: str | None = Field(None, description="The email of the faculty member")
    phone: str | None = Field(None, description="The phone number of the faculty member")

class AIResponseFormat(BaseModel):
    faculty_members: List[FacultyMember] = Field(..., description="The list of faculty members")
    
load_dotenv()



OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

llm = ChatOpenAI(
    model='gpt-4o-mini',
    api_key=OPENAI_API_KEY
)


json_format = """
    {
        "faculty_members": [
            {
                "name": "Name of the faculty member",
                "position": "Position of the faculty member",
                "department": "Department of the faculty member",
                "email": "Email of the faculty member" | null,
                "phone": "Phone number of the faculty member" | null
            },
            {
                "name": "Name of the faculty member",
                "position": "Position of the faculty member",
                "department": "Department of the faculty member",
                "email": "Email of the faculty member" | null,
                "phone": "Phone number of the faculty member" | null
            },
            ...
        ]
    }
"""

system_prompt_template = PromptTemplate(
    template="""
    You are an AI assistant tasked with taking in markdown formatted text scraped off of a university website and extracting information about faculty members.
    
    The information you are to extract is as follows:
    - Name (name of the faculty member)
    - Position (position of the faculty member)
    - Department (department of the faculty member)
    - Email (email of the faculty member - if available)
    - Phone (phone number of the faculty member - if available)

    You are always to output your response in JSON format.
    The format of the JSON you will output is as follows:
    {json_format}
    
    IMPORTANT: You are always to attempt to output your response in JSON format. If you do output your response in JSON format you have failed.
    IMPORTANT: Remember you are required to always extract the name, position, and department of the faculty members.
    IMPORTANT: You are always to attempt to extract the email and phone number of the faculty members.
    IMPORTANT: In the event the email or phone number cannot be found, you are to set them to None.
    """
)

human_prompt_template = PromptTemplate(
    template="""
    ***EXTRACTED INFORMATION BELOW\n\n***
    {context}
    """
)



prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(system_prompt_template.template),
        HumanMessagePromptTemplate.from_template(human_prompt_template.template)
    ]
)

def spencers_loader_func():
    FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY')
    loader = FireCrawlLoader(
        api_key=FIRECRAWL_API_KEY,
        url='https://www.salisbury.edu/faculty-and-staff/',
        mode='scrape'
    )
    docs = loader.load()
    context = ""
    with open('firecrawl_test_results.md', 'w') as f:
        for doc in docs:
            f.write(f'# {doc.metadata.get("title", "Untitled")}\n\n')
            f.write(f"## {doc.metadata.get('description', 'No description available')}\n\n")
            f.write(f"{doc.page_content}\n\n")
    for doc in docs:
        context += f'# {doc.metadata.get("title", "Untitled")}\n\n'
        context += f"## {doc.metadata.get('description', 'No description available')}\n\n"
        context += f"{doc.page_content}\n\n"
    return context

parser = JsonOutputParser(pydantic_object=AIResponseFormat)

chain = (
    {
        "context": lambda x: x["context"],
        "json_format": lambda x: x["json_format"]
    }
    | prompt
    | llm
    | parser
)

context = spencers_loader_func()
result = chain.invoke({
    "context": context,
    "json_format": json_format
})
print(json.dumps(result, indent=4))

with open('firecrawl_test_results.json', 'w') as f:
    json.dump(result, f, indent=4)