import os
import csv
import sys
import time
import argparse
import unicodedata

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pprint import pprint


def create_connection(host: str = "localhost", port: int = 27017) -> MongoClient:

        client = MongoClient(host, port)
        
        return client

def normalize(string: str):
    normalized = unicodedata.normalize('NFD', string)
    return normalized.encode('ascii', 'ignore').decode('utf8').casefold()

def add_data(new_db: Database, new_data: list[dict], collection_name: str) -> None:

    collection = new_db[collection_name]
    
    # pprint(new_data)

    new_data = list(new_data)

    if len(new_data):

        collection.insert_many(new_data)

    return

def add_comments_hijacked(db_name: str, hijacked_db_name: str, client: MongoClient) -> None:

    db = client[db_name]
    hijacked_db = client[hijacked_db_name]

    for channel in hijacked_db.list_collection_names():

        print(f"Iniciando: {channel}")
        
        channel_files = db[normalize(channel)]
        query = {"kind": "youtube#commentThread"}
        sup = channel_files.find(query)
        add_data(hijacked_db, sup, channel)

        query = {"kind": "youtube#comment"}
        sup = channel_files.find(query)
        add_data(hijacked_db, sup, channel)

def main():

    client = create_connection()
    # pprint(id_to_name)
    add_comments_hijacked("bets_12_10_26", "Hijacked", client)


if __name__ == "__main__":
    main()
