from fastapi import FastAPI, HTTPException, Query
from models import Article
from database import collection
from bson import ObjectId
from typing import List, Dict

app = FastAPI()


@app.get("/articles/")
async def get_articles(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=1000)
):
    articles = await collection.find().skip(skip).limit(limit).to_list(limit)
    articles_dict = {}
    for article in articles:
        article_id = str(article["_id"])
        articles_dict[article_id] = article
    return articles_dict


@app.get("/articles/{doi}")
async def get_article(doi: str):
    doi = doi.replace("-", "/")
    article = await collection.find_one({"_id": doi})
    article["_id"] = str(article["_id"])
    return article
