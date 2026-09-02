import sys
import requests
import argparse

from argparse import RawTextHelpFormatter
from pymongo.collection import Collection
from Apoio.my_mongo import get_all_collections_name_mongo, get_collection_mongo


def read_options() -> dict[str, str|bool]:
    status = False

    parser = argparse.ArgumentParser(
        description="Basic Usage", formatter_class=RawTextHelpFormatter
    )
    parser.add_argument(
        "-db", "--db_name", help="Nome da base de dados do mongodb", required=True, default=""
    )

    parser.add_argument(
        "-dir", "--directory_name", help="Nome do diretório para download das imagens", required=True, default=""
    )

    argument = parser.parse_args()

    if argument.db_name and argument.directory_name:
        status = True

    if not status:
        print("Maybe you want to use -h for help")
        status = False

    return {"success": status, "db_name": argument.db_name, "directory_name": argument.directory_name}

def get_data():
    data = read_options()
        
    if not data.get("success"):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)

    db_name = data.get("db_name")
    if not isinstance(db_name, str):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)

    dir = data.get("directory_name")
    if not isinstance(dir, str):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)

    return db_name, dir

def download(url: str, dir: str, name: str) -> str|None:
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()

        caminho = dir + "/" + name + ".jpg"

        with open(caminho, "wb") as arquivo:
            arquivo.write(resposta.content)

        return caminho

    except Exception:
        return None

def resolution_choice(video_urls: dict) -> str|None:
    max_res  = video_urls.get("maxres")
    if not max_res is None:
        return max_res["url"]
    
    high     = video_urls.get("high")
    if not high is None:
        return high["url"]
    
    medium   = video_urls.get("medium")
    if not medium is None:
        return medium["url"]
    
    default  = video_urls.get("default")
    if not default is None:
        return default["url"]
    
    standard = video_urls.get("standard")
    if not standard is None:
        return standard["url"]

    return None
    
def process_batch(dir: str, collection: Collection, batch_size: int = 100) -> None:

    query = {
        "kind": "youtube#video",
        "thumbnail_path": {"$exists": False}
    }
    
    cursor = collection.find(query).batch_size(batch_size)

    for doc in cursor:
        try:
            
            match doc.get("kind"):

                case "youtube#video":
                    video_urls = doc["snippet"]["thumbnails"]
                    video_url = resolution_choice(video_urls)
                    if video_url is None:
                        continue

                    name = doc["id"]
                    caminho = download(video_url, dir, name)
                    if caminho is None:
                        raise TypeError("Erro no download da Thumbnail")

                    collection.update_one(
                        {"_id": doc["_id"]},
                        {
                            "$set": {
                                "thumbnail_path": caminho
                            }
                        }
                    )
                    continue

                case _:
                    raise TypeError("Erro na busca de vídeos")

        except Exception as e:
            print(f"Erro no documento {doc['_id']}: {e}")

    return

def main():
    db_name, dir = get_data()

    collections = get_all_collections_name_mongo(db_name)

    total = len(collections)
    actual = 0

    for collection_name in collections:
    
        print(f"\n\tTotal feito: {actual * 100 /total : .2f}%\n")

        collection = get_collection_mongo(collection_name, db_name)

        process_batch(dir, collection)

        actual += 1


if __name__ == "__main__":
    main()