import os
import sys
import csv
import json
import requests
import asyncio
from time import sleep
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Apoio.my_mongo import get_all_collections_name_mongo, get_collection_mongo


def abacaxi():
    response = requests.get("https://www.googleapis.com/youtube/v3/channels?part=contentDetails")

    print(response.status_code)
    print(response.reason)
    print(response.json())

def process_batch(collection, batch_size: int = 100) -> None:

    query = {
        "kind": "youtube#video",
        "thumbnail_path": {"$exists": True}
    }
    
    cursor = collection.find(query).batch_size(batch_size)

    for doc in cursor:
        print("abacaxi")
        try:
            
            match doc.get("kind"):

                case "youtube#video":
                    
                    collection.update_one(
                        {"_id": doc["_id"]},
                        {
                            "$unset": {
                                "thumbnail_path": ""
                            }
                        }
                    )
                    
                    continue

                case _:
                    raise TypeError("Erro na busca de vídeos")

        except Exception as e:
            print(f"Erro no documento {doc['_id']}: {e}")

    return

def aba():
    collections = get_all_collections_name_mongo("new_era")
    
    total = len(collections)
    actual = 0

    for collection_name in collections:
    
        # print(f"\n\tTotal feito: {actual * 100 /total : .2f}%\n")

        collection = get_collection_mongo(collection_name, "new_era")

        process_batch(collection)

def caminhos():
    dir = "/home/cortex2/Documentos/DMSO/Bets/Imagens"
    name = "-0A6GPX7mNs"
    caminho = dir + "/" + name + ".jpg"

    if os.path.exists(caminho):
        print("Abacaxi")

async def do_work():
    print("Inicio")
    await asyncio.sleep(2)
    print("Fim")

async def main():
    task_1 = asyncio.create_task(do_work())
    task_2 = asyncio.create_task(do_work())

    await task_1
    await task_2

def soma():
    a = 0
    for i in range(4):
        a += i

    print(a)

def contagem():
    
    collections = get_all_collections_name_mongo("bets_12_10_26")

    video_timestamps = []
    
    comment_users = []

    for collection_name in collections:

        collection = get_collection_mongo(collection_name, "bets_12_10_26")

        cursor = collection.find().batch_size(100)

        for doc in cursor:

            if not doc.get("kind"):
                continue
            
            match doc["kind"]:

                case "youtube#channel":
                    continue

                case "youtube#video":
                    video_timestamps.append(doc["snippet"]["publishedAt"][:10])
                
                case "youtube#commentThread":
                    comment_users.append(doc["snippet"]["topLevelComment"]["snippet"]["authorChannelId"]["value"])
                
                case "youtube#comment":
                    comment_users.append(doc["snippet"]["authorChannelId"]["value"])
                
                case _:
                    print(doc)
                    raise TypeError
    
    with open("./video_timestamps.csv", 'w', encoding="utf8") as arquivo:
        for timestamp in video_timestamps:
            arquivo.write(f"{timestamp}\n")

    c = Counter(comment_users)
    op = c.most_common()

    with open("./standard_comenters.csv", 'w', encoding='utf8') as arquivo:
        arquivo.write("Commenter;Score\n")
        for comment in op:
            arquivo.write(f"{comment[0]};{comment[1]}\n")

def link_correction():

    with open("./Collector/12_10_26_classified_domains.csv", 'r', encoding="utf8") as arquivo:
        to_be_corrected = csv.reader(arquivo, delimiter=';')
        next(to_be_corrected)
        to_be_corrected = list(to_be_corrected)

    with open("/home/cortex2/Documentos/DMSO/GRAD/TCC/Links/New/Complete_corrected.csv", 'r', encoding="utf8") as arquivo:
        corrected = csv.reader(arquivo, delimiter=';')
        next(corrected)
        correct = list(corrected)

    correct_dict = {}

    for items in correct:
        correct_dict[items[0]] = (items[2], items[3])

    with open("./Collector/12_10_26_classified_domains_corrected.csv", 'w', encoding="utf8") as arquivo:
        arquivo.write("Domain;Score;Type;Class\n")
        for items in to_be_corrected:
            if sup := correct_dict.get(items[0]):
                arquivo.write(f"{items[0]};{items[1]};{sup[0]};{sup[1]}\n")
            else:
                arquivo.write(f"{';'.join(items)}\n")

def shorts():
    short_id = "D_fsYenku74"
    regular_id = "6QimJiGyXBU"
    deleted_id = "NNDYrGrdP28"
    short_url = "https://www.youtube.com/shorts/"

    bacalhau = requests.head(short_url + short_id)

    print(bacalhau.status_code)

    tilapia = requests.head(short_url + regular_id)

    print(tilapia.status_code)

    atum = requests.head(short_url + deleted_id)
    
    print(atum.status_code)

def same_links():

    with open("./Collector/bets_12_10_26_url.csv", 'r', encoding="utf8") as arquivo:
        aba = csv.reader(arquivo, delimiter=";")
        next(aba)
        links = set(map(lambda x: x[2], aba))

    with open("./Collector/OLD_url/12_10_26_db.json", 'r', encoding="utf8") as arquivo:
        other_links = json.decoder.JSONDecoder().decode(arquivo.read())

    not_in = 0
    found = set()

    for link in other_links.keys():
        if link not in links:
            not_in += 1
        else:
            found.add(link)

    print(not_in)
    print(len(links.difference(found)))

if __name__ == "__main__":
    # aba()
    # caminhos()
    # asyncio.run(main())
    # soma()
    # contagem()
    # link_correction()
    # shorts()
    same_links()
