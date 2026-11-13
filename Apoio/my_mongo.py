from pymongo import MongoClient
from itertools import chain,islice

from pymongo.collection import Collection

import os

repeated = set()

client = None

def create_connection(host: str = "localhost", port: int = 27017) -> MongoClient:
    global client

    if client != None:
        return client
    
    client = MongoClient(host, port)
    
    return client

def close_connection() -> None:
    global client

    if client != None:
        client.close()
        client = None

    return

def chunks(iterable, size=10000):
    iterator = iter(iterable)
    for first in iterator:
        yield chain([first], islice(iterator, size - 1))

def check(files, comments):

    global repeated

    for comment in comments:

        if comment["_id"] in repeated or files.find_one({"_id": comment["_id"]}):
            log_error(comment["_id"], "repeated")
            print("Item repetido")
            continue

        repeated.add(comment["_id"])
        yield comment

def data_save_mongo(file_name: str, comments: list, db_name: str = "teste") -> None:
    
    client = create_connection()
    db = client[db_name]
    
    files = db[file_name]

    for c in chunks(comments):
        validated = check(files, c)
        files.insert_many(validated)
        global repeated
        repeated = set()

actual_video = ""

def get_collection_mongo(collection_name: str, db_name: str = "teste") -> Collection:
    
    client = create_connection()
    
    db = client[db_name]
    
    return db[collection_name]

def get_all_collections_name_mongo(db_name: str = "teste") -> list[str]:
    
    client = create_connection()
    
    db = client[db_name]
    
    return db.list_collection_names()

def delete_file_mongo(query: dict, collection_name: str, db_name: str = "teste") -> None:
    
    client = create_connection()
    
    db = client[db_name]
    
    collect = db[collection_name]

    collect.delete_one(query)

    return

def delete_collection_mongo(collection_name: str, db_name: str = "teste") -> None:
    
    client = create_connection()
    
    db = client[db_name]
    
    collect = db[collection_name]

    db.drop_collection(collect)

    return

def log_error(error: str, video_id: str = "repeated") -> None:
    if video_id == "repeated":
        os.makedirs("./log_error", exist_ok=True)
        with open("./log_error/" + video_id + ".txt", 'a', encoding='utf8') as arquivo:
            arquivo.write(error + "\n")
        return
    
    global actual_video

    if video_id == actual_video:
        with open("./log_error/" + video_id + ".txt", 'a', encoding='utf8') as arquivo:
            arquivo.write(error)
    else:
        actual_video = video_id
        os.makedirs("./log_error", exist_ok=True)
        with open("./log_error/" + video_id + ".txt", 'w', encoding='utf8') as arquivo:
            arquivo.write(error + "\n")

def main():
    log_error("abacaxi", "bom dia")
    log_error("abacaxi", "bom tarde")
    log_error("pera", "bom noite")
    log_error("pera", "bom madrugada")


if __name__ == "__main__":
    main()
