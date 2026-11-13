import os
import csv
import sys
import time
import argparse

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pprint import pprint


def create_connection(host: str = "localhost", port: int = 27017) -> MongoClient:

        client = MongoClient(host, port)
        
        return client

def hijacked(db_name: str, client: MongoClient) -> dict:

    db: Database = client[db_name]

    id_to_name = {}

    for channel in db.list_collection_names():
        channel_files = db[channel]
        any_video = channel_files.find_one()
        # pprint(any_video["snippet"]["channelId"])
        # input()
        id_to_name[any_video["snippet"]["channelId"]] = channel

    return id_to_name

def copy_data(db, hijacked_db, hijacked_collection_name, collection_name) -> list[dict]:

    collection: Collection = db[collection_name]
    hijacked_collection: Collection = hijacked_db[hijacked_collection_name]
    # print(collection_name)
    # print(hijacked_collection_name)

    return_list = []
    updated_ids = set()
    
    cursor = hijacked_collection.find()

    errors = 0

    for doc in cursor:
        video = collection.find_one({
                "kind": "youtube#video",
                "id": doc["id"]
                })

        updated_ids.add(doc["id"])

        if not video:
            # print(collection_name)
            # print(hijacked_collection_name)
            # print(doc["id"])

            # input()
            errors += 1
            continue
        video["dataset"] = doc["dataset"]
        return_list.append(video)


    if errors:
        print(collection_name)
        print(errors)

    return_list.extend([doc for doc in collection.find({
                "kind": "youtube#video",
                }) if doc["id"] not in updated_ids])

    return return_list

def add_data(new_db: Database, new_data: list[dict], collection_name: str) -> None:

    collection = new_db[collection_name]
    
    # pprint(new_data)

    collection.insert_many(new_data)

    return

def new_hijacked(db_name: str, hijacked_db_name: str, new_db_name: str, client: MongoClient, id_to_name: dict[str, str]) -> None:

    db = client[db_name]
    hijacked_db = client[hijacked_db_name]
    new_db = client[new_db_name]

    for channel in db.list_collection_names():
        channel_files = db[channel]
        query = {"channel_controller": {"$exists": True}}
        sup = channel_files.find_one(query)
        if collection_name := (id_to_name.get(sup["channel_id"])):
            new_data = copy_data(db, hijacked_db, collection_name, channel)
            add_data(new_db, new_data, collection_name)

def main():

    client = create_connection()
    id_to_name = hijacked("Version_EX", client)
    # pprint(id_to_name)
    new_hijacked("bets_12_10_26", "Version_EX", "Hijacked", client, id_to_name)


if __name__ == "__main__":
    main()
