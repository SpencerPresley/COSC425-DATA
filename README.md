# COSC425-DATA  

A repository which implements data collection of a University's academic research articles within a given time period and classifies them into categories defined by the NSF PhD research focus areas taxonomy then provides:

- Data on an article level
- Data on individual authors
- Data on category level

Currently the data is outputted in JSON format. There exists a script for converting the JSON to an Excel file but is currently somewhat finnicky.  

A more thorough offline file formatting will be implemented in the future.  

## How to install

### For non-development

1. Install the package `pip install academic-metrics`
2. Create a `.env` file in the root directory and add your OpenAI API key: `OPENAI_API_KEY=<your_openai_api_key>`  
3. Create a script `run_pipeline.py` in the root directory and add the following:  

    ```python
    from academic_metrics.runners.pipeline import PipelineRunner

    runner = PipelineRunner(ai_api_key=os.getenv("OPENAI_API_KEY"))
    runner.run_pipeline()
    ```  

### For development
1. Clone the repository:  
    - HTTPS: `git clone https://github.com/SpencerPresley/COSC425-DATA.git`
    - SSH: `git clone git@github.com:SpencerPresley/COSC425-DATA.git`
2. Navigate into the project root directory `cd COSC425-DATA` and run the setup script `python setup_environment.py`:  
    - This will install the academic_metrics package in editable mode and configure the pre-commit in `.git/hooks`
    - The git hook will format the code on commit using black

## Note

As of 11/9/2024 the pipeline runs off input files in `src/academic_metrics/data/core/input_files`  

Shortly integration of the crossref API code will be made in `academic_metrics/runners/pipeline.py` so that you can pass in your school name, data range, etc. to get your own data outputted.  

Integration for writing to a mongoDB database is currently implemented only for our use case, future integration will allow two modes:  

1. Offline output files to `src/academic_metrics/data/core/output_files`
    - In this mode the API for crossref will still work but the output files will be saved locally rather to a database.  
2. Database support. For this you will have to create a `.env` file in the root directory and add the following:  
    - `MONGO_URI=<your_mongo_uri>`
    - `MONGO_DB_NAME=<your_mongo_db_name>`
    - `MONGO_COLLECTION_NAME=<your_mongo_collection_name>`
