import os
import re
import csv
import sys
import json
import argparse
import requests

from tqdm import tqdm
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pprint import pprint


def create_connection(host: str = "localhost", port: int = 27017) -> MongoClient:

        client = MongoClient(host, port)
        
        return client

def processHTML(rawHTML: str) -> dict | None:
    pattern = r"var ytInitialPlayerResponse\s*=\s*"

    match = re.search(pattern, rawHTML)

    if not match:
        return None

    inicio = match.end()

    try:
        response, _ = json.JSONDecoder().raw_decode(rawHTML[inicio:])
        return response
    except json.JSONDecodeError:
        return None

def video_status(video_id: str) -> str:

    short_url = "https://www.youtube.com/shorts/"
    video = requests.get(short_url + video_id)

    processed_response = processHTML(video.text)

    if not processed_response:
        return "Desconhecido"

    playability = processed_response.get("playabilityStatus", {})

    status = playability.get("status", "")
    reason = playability.get("reason", "")

    error_screen = playability.get("errorScreen", {})

    try:
        interstitial = (
            error_screen["playerInterstitialRenderer"]
            ["content"]["interstitialViewModel"]
        )

        title = interstitial.get("title", {}).get("content", "")
        description = interstitial.get("description", {}).get("content", "")

    except (KeyError, TypeError):
        title = ""
        description = ""

    mensagem = f"{reason} {title} {description}".lower()

    if "vídeo privado" in mensagem or "private video" in mensagem:
        return "Privado"

    if "removido pelo usuário" in mensagem:
        return "Removido"

    if status == "OK":
        return "Shorts"

    if status == "LOGIN_REQUIRED":
        return "Login"

    if status in ("ERROR", "UNPLAYABLE"):
        return "Indisponível"

    return "Desconhecido"

def is_short(video_id: str) -> str:

    short_url = "https://www.youtube.com/shorts/"
    video = requests.head(short_url + video_id)

    match video.status_code:

        case 200:

            return video_status(video_id) 

        case 303:

            return "Regular"

        case _:

            raise TypeError(f"Video não foi identificado pois status veio como {video.status_code}")

def pipeline(actual: Collection) -> int:

    erro = 0
    
    query = {
        "kind": "youtube#video",
        "video_type": {"$exists": False}
    }


    files = list(actual.find(query))

    for video in tqdm(
        files,
        total = len(files),
        desc = actual.name
    ):

        try:
            answer = is_short(video["id"])
            
            
            actual.update_one(
                {"_id": video["_id"]},
                {"$set": {
                    "video_type": answer
                    }
                }
            )

        except TypeError:
            erro += 1
            continue

        except Exception as e:
            print(e)
            sys.exit(0)

    return erro

def main():

    client = create_connection()
    db = client["Hijacked"]
    for collection_name in db.list_collection_names():
        actual: Collection = db[collection_name]
        erros = pipeline(actual)
        if erros:
            print(f"A coleção {collection_name} teve {erros} erros!")


if __name__ == "__main__":
    main()
