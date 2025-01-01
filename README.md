# COSC425-DATA

An AI-powered toolkit for collecting and classifying academic research publications. The system:

- Collects publication data from Crossref API based on institutional affiliation
- Uses LLMs to classify research into NSF PhD research focus areas
- Extracts and analyzes themes and methodologies from abstracts
- Generates comprehensive analytics at article, author, and category levels
- Stores results in MongoDB, local JSON files, and optionally Excel files

## Features

- **Data Collection**: Automated fetching of publications via Crossref API
- **AI Classification**: LLM-powered analysis of research abstracts
- **Multi-level Analytics**:
  - Article-level metrics and classifications
  - Author/faculty publication statistics
  - Category-level aggregated data
- **Flexible Storage**: MongoDB integration, local JSON output, and optionally Excel files
- **Configurable Pipeline**: Customizable date ranges, models, and processing options

## Documentation and example site built using the Salisbury University data from 2009-2024

[Documentation](https://cosc425-data.readthedocs.io/en/latest/)

[Example Site](https://ai-taxonomy-front.vercel.app/)

> Note: The source code for the example site is available [here](https://github.com/cbarbes1/AITaxonomy-Front).

## Installation

### 0. External Setup

Recommended to use `python 3.12` as that is the version used for development and has not been tested on other versions.

Setting up mongod:

To see instructions on how to install and run mongod see the [MongoDB documentation](https://www.mongodb.com/docs/manual/installation/).

If you have struggles setting up mongodb, google, youtube, and chatgpt are your friends.

The installation is rather easy, just follow the instructions and you should be able to get it running.

To find the name of your db you can run `mongosh` and then `show dbs` to see a list of all the databases on your server.

To create a new db with a custom name you can run `use <db_name>`.

Collection creation is handled by the system, you do not need to create them.

### 1. Clone the repository

**HTTPS**:

```bash
git clone https://github.com/SpencerPresley/COSC425-DATA.git
```

**SSH**:

```bash
git clone git@github.com:SpencerPresley/COSC425-DATA.git
```

### 2. Create and activate a virtual environment

**venv**:

```bash
python -m venv venv 
source venv/bin/activate
```

**conda**:

```bash
conda create -n cosc425 python=3.12
conda activate cosc425
```

### 3. Install package in development mode

> Note: This handles dependencies and installs the package in development mode. You do not need to install requirements.txt

```bash
cd COSC425-DATA
pip install -e .
```

### 4. Set up environment variables

Create a `.env` file in the COSC425-DATA directory with the following variables:

```bash
OPENAI_API_KEY="your_openai_api_key"
LOCAL_MONGODB_URI="your_local_mongodb_url"
```

If you want to export your data to a live MongoDB instance, you can set the MONGO_URL environment variable:

```bash
OPENAI_API_KEY="your_openai_api_key"
MONGO_URL="your_mongodb_url"
```

## Usage

### Option 1 - Using the CLI (Recommended)

> Note: This method is recommended as when you pass in the date ranges by arguments the script processes the data one month at a time and saves the results. This reduces the risk of freezing up the system, the freezing usually occurs when OpenAI is processing too many requests in too short of a time. The system handles retries and timeouts, but it's better to avoid them.

For this option, you'll need to navigate to the `COSC425-DATA/src/academic_metrics/runners/` directory and run the `pipeline.py` script.

Assuming you're still in the `COSC425-DATA` directory, run this command:

```bash
cd src/academic_metrics/runners/
```

Then you'll want to run the `pipeline.py`, to do this there are a few command line arguments you can pass in.

To see a full list you can run:

```bash
python pipeline.py --help
```

To run it you will need to pass in the following arguments:

- `--from-month` - The month to start collecting data from, defaults to 1
- `--to-month` - The month to end collecting data on, defaults to 12
- `--from-year` - The year to start collecting data from, defaults to 2024
- `--to-year` - The year to end collecting data on, defaults to 2024
- `--db-name` - The name of the database to use (required)
- `--crossref-affiliation` - The affiliation to use for the Crossref API, defaults to Salisbury University (required)

If you want to save the data to excel files you can pass in the `--as-excel` argument.

> Note: The `--as-excel` argument is an additional action, it doesn't remove the the saving to other data formats.

Example:

Say you want to collect data for every month from 2019 to 2024 for Salisbury University and save it to excel files. You would run the following command:

```bash
python pipeline.py --from-month=1 --to-month=12 --from-year=2019 --to-year=2024 --crossref-affiliation="Salisbury University" --as-excel --db-name=Your_Database_Name
```

The default AI model used for all parts is `gpt-4o-mini`. If you want to use a different model you can use the following arguments:

- `--pre-classification-model` - The model to use for the pre-classification step
- `--classification-model` - The model to use for the classification step
- `--theme-model` - The model to use for the theme extraction step

> Note: This process consumes a lot of tokens, during testing we found that using `gpt-4o-mini` was the most cost effective and provided good results. If you want to use a larger model like `gpt-4o` you can do so, but be warned it will run through your tokens very quickly. If you do use a larger model I recommend you start with a smaller date range and work your way up.

Here's how you would run the pipeline using the larger `gpt-4o` model:

```bash
python pipeline.py --from-month=1 --to-month=12 --from-year=2019 --to-year=2024 --crossref-affiliation="Salisbury University" --**as**-excel --db-name=Your_Database_Name --pre-classification-model=gpt-4o --classification-model=gpt-4o --theme-model=gpt-4o
```

### Option 2 - Your own script (Not recommended)

Create a script to run the pipeline with your desired configuration. You can see the documentation here for configuration options:

[PipelineRunner documentation](https://cosc425-data.readthedocs.io/en/latest/runners.html#academic_metrics.runners.pipeline.PipelineRunner)

In the script, you can use the `PipelineRunner` and run it like so:

```python
from academic_metrics.runners.pipeline import PipelineRunner

import os
from dotenv import load_dotenv

load_dotenv()

pipeline = PipelineRunner(
    ai_api_key=os.getenv("OPENAI_API_KEY"),
    crossref_affiliation="The university whose data you want to collect and classify",
    date_from_month=1,
    date_to_month=12,
    date_from_year=2022, # Or any start year you want
    date_to_year=2024, # Or any end year you want
    mongodb_url=os.getenv("LOCAL_MONGO_URL"), # Or "MONGO_URL" if you want to export to a live MongoDB instance
    db_name="Your database name",
    pre_classification_model="an OpenAI model", # Default is gpt-4o-mini
    classification_model="an OpenAI model", # Default is gpt-4o-mini
    theme_model="an OpenAI model", # Default is gpt-4o-mini
)
```

**Run the pipeline**:

```python
pipeline.run_pipeline()
```

Full code so you can copy and paste it into your own script:

```python
from academic_metrics.runners.pipeline import PipelineRunner

import os
from dotenv import load_dotenv

load_dotenv()

pipeline = PipelineRunner(
    ai_api_key=os.getenv("OPENAI_API_KEY"),
    crossref_affiliation="The university whose data you want to collect and classify",
    date_from_month=1,
    date_to_month=12,
    date_from_year=2022, # Or any start year you want
    date_to_year=2024, # Or any end year you want
    mongodb_url=os.getenv("LOCAL_MONGO_URL"), # Or "MONGO_URL" if you want to export to a live MongoDB instance
    db_name="Your database name",
    pre_classification_model="an OpenAI model", # Default is gpt-4o-mini
    classification_model="an OpenAI model", # Default is gpt-4o-mini
    theme_model="an OpenAI model", # Default is gpt-4o-mini
)

pipeline.run_pipeline()
```

> Note: Running it this way does not allow for saving the data to excel files. If you want to save the data to excel files you can do it via importing the function from `pipeline.py` and calling it at the end of the script.
>
> Critical Note: If you are running this in your own script the entire date range is performed in one go. This is a lot of data to process and it will take a while. If you want to process the data one month at a time, use the CLI method.

Code:

```python
from academic_metrics.runners.pipeline import PipelineRunner, make_excel

import os
from dotenv import load_dotenv

load_dotenv()

pipeline = PipelineRunner(
    ai_api_key=os.getenv("OPENAI_API_KEY"),
    crossref_affiliation="The university whose data you want to collect and classify",
    date_from_month=1,
    date_to_month=12,
    date_from_year=2022, # Or any start year you want
    date_to_year=2024, # Or any end year you want
    mongodb_url=os.getenv("LOCAL_MONGO_URL"), # Or "MONGO_URL" if you want to export to a live MongoDB instance
    db_name="Your database name",
    pre_classification_model="an OpenAI model", # Default is gpt-4o-mini
    classification_model="an OpenAI model", # Default is gpt-4o-mini
    theme_model="an OpenAI model", # Default is gpt-4o-mini
)

pipeline.run_pipeline()

db = DatabaseWrapper(
    db_name="Your database name",
    mongo_url=os.getenv("LOCAL_MONGO_URL")
)

make_excel(db)
```
