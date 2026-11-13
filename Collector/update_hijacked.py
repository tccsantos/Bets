import os
import csv
import sys
import time
import argparse
from datetime import datetime

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pprint import pprint


def create_connection(host: str = "localhost", port: int = 27017) -> MongoClient:

        client = MongoClient(host, port)
        
        return client

def get_last_date(collection: Collection) -> datetime| None:
    cursor = collection.find({"dataset": "gambling"})

    dates = []
    
    for doc in cursor:

        dates.append(datetime.strptime(doc["snippet"]["publishedAt"][:10], "%Y-%m-%d"))


    if len(dates):
    
        return max(dates)

    else:
        return None

def update_dates(collection: Collection, gambling_date: datetime) -> None:

    cursor = collection.find({"dataset": {"$exists": False}})

    for doc in cursor:

        if datetime.strptime(doc["snippet"]["publishedAt"][:10], "%Y-%m-%d") > gambling_date:
            dataset = "gambling"
        else:
            dataset = "regular"

        
        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "dataset": dataset
                }
            }
        )
        
def main():

    client = create_connection()
    db = client["Hijacked"]
    for collection_name in db.list_collection_names():
        gambling_date = get_last_date(db[collection_name])
        if gambling_date:
            print(f"Iniciando {collection_name}")
            update_dates(db[collection_name], gambling_date)
        else:
            print(f"Erro: {collection_name}")
    


if __name__ == "__main__":
    main()
