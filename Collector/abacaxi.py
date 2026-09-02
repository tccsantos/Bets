import requests

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

if __name__ == "__main__":
    aba()