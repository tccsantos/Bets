"""
Código para extrair todos os comentários e dados de todos os vídeos de uma lista de canais

Regras de uso:
-i Arquivo CSV com os ids dos canais para serem coletados

-k Arquivo CSV com as chaves da API do YouTube

-db Nome da base de dados para armazenamento

Código feito para MongoDB com conexão local!

Thiago Cortez
"""


import os
import csv
import sys
import time
import argparse
import requests
import unicodedata

from typing import NoReturn
from pymongo import MongoClient
from pymongo.errors import InvalidOperation
from argparse import RawTextHelpFormatter
from itertools import chain, islice
from functools import partial

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class Mongo_writer():

    def __init__(self, db_name) -> None:
        self.__client = self.__create_connection()
        self.__db = db_name
        self.__actual_collection = None
        self.__vulnerable_status = False
        self.__repeated = set()
        self.__nextpage = None
        self.__support_collection = "DB_STATS"
        self.__operations = []

    @staticmethod
    def __create_connection(host: str = "localhost", port: int = 27017) -> MongoClient:

        client = MongoClient(host, port)
        
        return client

    @staticmethod
    def __chunks(iterable, size=100):
        iterator = iter(iterable)
        for first in iterator:
            yield chain([first], islice(iterator, size - 1))

    def __check(self, files, data):
        for comment in data:
            if comment["_id"] in self.__repeated or files.find_one({"_id": comment["_id"]}):
                continue

            self.__repeated.add(comment["_id"])
            yield comment

    def __close_connection(self) -> None:
        self.__client.close()

    def check_channel_completion(self, channel_id) -> tuple[dict[str, bool], dict[str, str]]:

        db = self.__client[self.__db]

        for channel in db.list_collection_names():

            # print(channel)
            channel_files = db[channel]
            query = {"channel_controller": {"$exists": True}}
            sup = channel_files.find_one(query)

            if sup is None:
                self.panic(f"Documento de apoio não encontrado em {channel}")

            if not sup["channel_id"] == channel_id:
                # print(sup["channel_id"], channel_id)
                continue

            self.__actual_collection = channel
            self.__vulnerable_status = True

            completed = sup["status"] == "COMPLETE"
            channel_completion = sup["channel"]["status"] == "COMPLETE"
            playlist_completion = sup["playlist"]["status"] == "COMPLETE"

            playlist_id = sup["channel"]["playlist_id"]
            videos_ids  = sup["playlist"]["videos_id"]
            playlist_last_page = sup["playlist"]["nextPage"]

            return {
                "completed"             : completed,
                "channel_completion"    : channel_completion,
                "playlist_completion"   : playlist_completion
            }, {
                "playlist_id"       : playlist_id,
                "video_ids"         : videos_ids,
                "playlist_last_page": playlist_last_page
            }

        return {
                "completed"             : False,
                "channel_completion"    : False,
                "playlist_completion"   : False
            }, {
                "playlist_id"       : "",
                "video_ids"         : "",
                "playlist_last_page": ""
            }

    def check_video_completion(self, video_id) -> tuple[dict[str, bool], str]:
        if self.__actual_collection is None:
            self.panic("Sem coleção atual!! (119)")

        db = self.__client[self.__db]
        files = db[self.__actual_collection]

        query = {"channel_controller": {"$exists": True}}
        sup = files.find_one(query)

        if sup is None:
            self.panic(f"Onde está o documento de apoio da coleção {self.__actual_collection} (128)")

        video_completion = not files.find_one({"_id": {"$eq": video_id}}) is None

        completed = sup["videos"]["video_id"] != video_id and video_completion

        nextPage = sup["videos"]["nextPage"]

        return {
            "completed": completed,
            "video_completion": video_completion
        }, nextPage

    def new_channel(self, channel_id, channel_name: str, data: dict, playlist_id: str) -> bool:

        try:
            self.__actual_collection = channel_name
            
            db = self.__client[self.__db]
            files = db[self.__actual_collection]

            files.insert_one({
                "channel_controller": self.__support_collection,
                "status": "INCOMPLETE",
                "channel_id": channel_id,
                "channel": {
                    "status": "COMPLETE",
                    "playlist_id": playlist_id
                },
                "playlist": {
                    "status": "INCOMPLETE",
                    "nextPage": "",
                    "videos_id": []
                },
                "videos": {
                    "video_id": "",
                    "nextPage": ""
                }
            })

            files.insert_one(data)
        
        except Exception as e:
            self.panic(f"Não fomos capaz de adicionar novo canal: {e}")

        return True

    def add_playlist(self, video_ids: list[str]) -> list[str]:
        if self.__actual_collection is None:
            self.panic("Sem coleção atual!! (177)")

        db = self.__client[self.__db]
        files = db[self.__actual_collection]

        query = {"channel_controller": {"$exists": True}}
        sup = files.find_one(query)

        if sup is None:
            self.panic(f"Onde está o documento de apoio da coleção {self.__actual_collection} (186)")

        playlist = sup["playlist"]["videos_id"]

        full = set(playlist).union(set(video_ids))

        playlist = list(full)

        files.update_one(
            {"_id": sup["_id"]},
            {"$set": {"playlist.videos_id": playlist}}
        )

        return playlist

    def playlist_finish(self) -> bool:
        if self.__actual_collection is None:
            self.panic("Sem coleção atual!! (203)")

        db = self.__client[self.__db]
        files = db[self.__actual_collection]

        query = {"channel_controller": {"$exists": True}}
        sup = files.find_one(query)

        if sup is None:
            self.panic(f"Onde está o documento de apoio da coleção {self.__actual_collection} (212)")

        files.update_one(
            {"_id": sup["_id"]},
            {"$set": {"playlist.status": "COMPLETE"}}
        )

        self.__vulnerable_status = False
        self.__nextpage = None

        return True

    def add_video(self, data, video_id: str) -> bool:
        if self.__actual_collection is None:
            self.panic("Sem coleção atual!! (226)")

        db = self.__client[self.__db]
        files = db[self.__actual_collection]

        query = {"channel_controller": {"$exists": True}}
        sup = files.find_one(query)

        if sup is None:
            self.panic(f"Onde está o documento de apoio da coleção {self.__actual_collection} (235)")

        files.update_one(
            {"_id": sup["_id"]},
            {"$set": {"videos.video_id": video_id}}
        )

        files.insert_one(data)

        return True

    def add_comments(self, comments: list[dict]) -> bool:
        if self.__actual_collection is None:
            self.panic("Sem coleção atual!! (248)")

        db = self.__client[self.__db]
        files = db[self.__actual_collection]

        # print("Abacaxi")
        for c in self.__chunks(comments):
            # print("Inserção de um chunk")
            if self.__vulnerable_status:
                # print("vulneravel: inicio")
                validated = self.__check(files, c)
                # print("vulneravel: meio")
                try:
                    files.insert_many(validated)
                except InvalidOperation as e:
                    if str(e) != "No operations to execute":
                        raise
                # print("vulneravel: fim")
            else:
                # print("Normal: inicio")
                try:
                    files.insert_many(c)
                except InvalidOperation as e:
                    if str(e) != "No operations to execute":
                        raise
                # print("Normal: fim")

        # print("Pera")
        return True

    def video_finish(self) -> bool:
        if self.__actual_collection is None:
            self.panic("Sem coleção atual!! (264)")

        db = self.__client[self.__db]
        files = db[self.__actual_collection]

        query = {"channel_controller": {"$exists": True}}
        sup = files.find_one(query)

        if sup is None:
            self.panic(f"Onde está o documento de apoio da coleção {self.__actual_collection} (273)")

        files.update_one(
            {"_id": sup["_id"]},
            {"$set": {"videos.video_id": ""}}
        )

        self.__vulnerable_status = False
        self.__nextpage = None

        return True

    def channel_completion(self) -> bool:
        if self.__actual_collection is None:
            self.panic("Sem coleção atual!! (284)")

        db = self.__client[self.__db]
        files = db[self.__actual_collection]

        query = {"channel_controller": {"$exists": True}}
        sup = files.find_one(query)

        if sup is None:
            self.panic(f"Onde está o documento de apoio da coleção {self.__actual_collection} (293)")

        files.update_one(
            {"_id": sup["_id"]},
            {"$set": {"status": "COMPLETE"}}
        )

        self.__actual_collection = None
        self.__vulnerable_status = False
        self.__nextpage = None

        return True

    def sleep_protocol(self) -> None:

        # print("Fim do expediente, preparando-me para dormir...")

        print("Indo dormir, boa noite!")
        try:
            for i in range(8):
                time.sleep(60*60)
                print(f"Horas dormidas: {i + 1}")
        except KeyboardInterrupt:
            print("Interrompendo sono mais cedo!")

        print("De volta ao trabalho!")

    def panic(self, error: str | None = None) -> NoReturn:

        if not error is None:
            print(error)

        my_mail(assunto="Entrei em panico", texto="Perdão, chefe. Algo aconteceu e eu entrei em pânico")

        sys.exit(0)

class Requester():

    def __init__(self, api_file: str, writer: Mongo_writer) -> None:
        self.__actual_api_key = 0
        self.__keys = self.__get_keys(api_file)
        self.__writer = writer

    def __get_keys(self, api_file: str) -> list[str]:

        with open(api_file, 'r', encoding='utf8') as arquivo:
            aba = csv.reader(arquivo)
            keys = list(aba)

        return [key[0] for key in keys]

    def __get_actual_api_key(self) -> str:
        return self.__keys[self.__actual_api_key]

    def __change_key(self):
        self.__actual_api_key = (self.__actual_api_key + 1) % len(self.__keys)
        
        if not self.__actual_api_key:
            self.__writer.sleep_protocol()

    def panic(self, erro: str | None = None) -> NoReturn:
        self.__writer.panic(erro)

    def requesting(self, original_url: str, next_token: str | None = None) -> dict:

        counter = 1

        while True:

            url = original_url + f"&key={self.__get_actual_api_key()}"
            try:

                if not next_token is None and next_token != "":
                    url += f"&pageToken={next_token}"

                # print(f"Número de requisições: {count}")
                # print(url)
                # sys.exit(0)
        
                response = requests.get(url)
                data = response.json()
        
            except Exception as e:
                # log_error(video_id = video_id, error = f"Falha na requisição de comentários do vídeo na {num_pagina}-página!! Nenhum comentário em diante foi coletado")
                # page_token = None
                if counter >= 20:
                    self.panic(f"Não consegui requisitar: {url}")
                counter += 1
                time.sleep(60*counter)
                continue

            if response.status_code == 403:
                if data["error"]["errors"][0]["reason"] != "quotaExceeded":
                    if data["error"]["errors"][0]["reason"] == "commentsDisabled":
                        print("Video sem comentários")
                    return {}

                # print(url)
                self.__change_key()
                continue

            if not response.ok:
                self.panic(f"A API falhou: {url} \n\n{data}")

            return data


def normalize(string: str):
    normalized = unicodedata.normalize('NFD', string)
    return normalized.encode('ascii', 'ignore').decode('utf8').casefold()

def read_options() -> dict[str, str|bool]:
    status = False

    parser = argparse.ArgumentParser(
        description="Basic Usage", formatter_class=RawTextHelpFormatter
    )
    parser.add_argument(
        "-i", "--input", help="Arquivo CSV com o id dos canais", required=True, default=""
    )
    parser.add_argument(
        "-k", "--apikey", help="Arquivo CSV com as chaves da API do YouTube", required=True, default=""
    )
    parser.add_argument(
        "-db", "--db_name", help="Nome da base de dados do mongodb", required=True, default=""
    )

    argument = parser.parse_args()

    if argument.input and argument.db_name and argument.apikey:
        status = True

    if not status:
        print("Maybe you want to use -h for help")
        status = False

    return {"success": status, "input": argument.input, "api_key": argument.apikey, "db_name": argument.db_name}

def read_video_ids(file: str) -> list[str]:

    with open(file, "r", encoding='utf8') as arquivo:
        aba = csv.reader(arquivo)
        channel_ids = list(aba)
    
    return [channel_id[0] for channel_id in channel_ids]

def get_data():
    data = read_options()
        
    if not data.get("success"):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)

    api_key = data.get("api_key")
    if not isinstance(api_key, str):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)

    db_name = data.get("db_name")
    if not isinstance(db_name, str):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)
    
    channel_file = data.get("input")
    if not isinstance(channel_file, str):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)
    
    channel_ids = read_video_ids(channel_file)

    return api_key, db_name, channel_ids

def channel_request(my_requester: Requester, channel_id: str) -> dict|None:
        
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails&id={channel_id}"

    data = my_requester.requesting(url)

    try:
        # print(data)
        item = data['items'][0]
        item['_id'] = item['id']
        return item

    # except KeyError:
    #     print(channel_id, "\n")
    #     print(data)
    #     print("\n\nParando com erro possível de API")
    #     sys.exit(0)

    except IndexError:
        # log_error(video_id=channel_id, error="Video tirado do ar!!")
        print("Canal Não encontrado")
        return None

    except Exception as e:
        # my_requester.panic(f"Não consegui extrair o canal: {data}")
        print("Erro Desconhecido")
        return None

def playlist_request(my_requester: Requester, playlist_id: str, next_page: str | None = None):

    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={playlist_id}&maxResults=50"

    while True:

        data = my_requester.requesting(url, next_page)

        try:
            # print(data)

            for item in data['items']:
                yield item["contentDetails"]["videoId"]

            next_page = data.get("nextPageToken")
            if next_page is None:
                break
            

        except Exception:
            my_requester.panic(f"Erro ao extraír os dados da playlist: {data}")

def video_request(my_requester: Requester, video_id: str):

    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,status&id={video_id}"

    data = my_requester.requesting(url)

    try:
        # print(data)
        item = data['items'][0]
        item['_id'] = item['id']
        return item

    # except KeyError:
    #     print(channel_id, "\n")
    #     print(data)
    #     print("\n\nParando com erro possível de API")
    #     sys.exit(0)

    except IndexError:
        # log_error(video_id=channel_id, error="Video tirado do ar!!")
        print("Video não encontrado")
        return None

def replies_request(my_requester: Requester, video_id: str, comment_id: str):

    url = f"https://www.googleapis.com/youtube/v3/comments?part=snippet&videoId={video_id}&parentId={comment_id}&maxResults=100"
        
    next_page = None

    repeated = set()

    while True:

        data = my_requester.requesting(url, next_page)

        try:
            # print(data)

            for item in data['items']:
                item['_id'] = item['id']
                if item['_id'] in repeated:
                    continue
                repeated.add(item['_id'])
                yield item

            next_page = data.get("nextPageToken")
            if next_page is None:
                break
            
        except Exception:
            my_requester.panic(f"Erro ao extraír os dados das replies: {data}")

def comments_request(my_requester: Requester, video_id: str, next_page: str | None = None):

    url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={video_id}&maxResults=100"

    i = 0

    repeated = set()

    while True:

        data = my_requester.requesting(url, next_page)
        i += 1
        # print("Ainda estou vivo!", i%10)

        if data != {}:
            try:
                # print(data)

                for item in data['items']:
                    item['_id'] = item['id']
                    if item['_id'] in repeated:
                        continue
                    repeated.add(item['_id'])
                    yield item

                    if item["snippet"]["totalReplyCount"] > 0:
                        for reply in replies_request(my_requester, video_id, item.get("id")):
                            yield reply

                next_page = data.get("nextPageToken")
                if next_page is None:
                    break
                
            except Exception:
                my_requester.panic(f"Erro ao extraír os dados dos comentários: {data}") 
        else:
            break 

def my_mail(assunto: str, texto: str) -> None:

    # Configurações do e-mail
    email_remetente = "thiagocortez14@gmail.com"
    # Cole aqui a sua Senha de App de 16 dígitos (sem espaços)
    senha_app = "adgx ytyk hrtn xdwy"
    email_destinatario = "tccsantos@unifesp.br"

    # Criando a estrutura da mensagem
    msg = MIMEMultipart()
    msg['From'] = email_remetente
    msg['To'] = email_destinatario
    msg['Subject'] = assunto

    # Corpo do e-mail
    corpo = texto
    msg.attach(MIMEText(corpo, 'plain'))

    servidor = None

    # Conectando com o servidor SMTP do Gmail
    try:
        print("Conectando ao servidor...")
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()  # Inicia a criptografia TLS
        
        # Fazendo login
        servidor.login(email_remetente, senha_app)
        
        # Enviando o e-mail
        servidor.send_message(msg)
        print("E-mail enviado com sucesso!")
        
    except Exception as e:
        print(f"Erro ao enviar o e-mail: {e}")
        
    finally:
        if not servidor is None:
            servidor.quit()

def main():

    api_key, db_name, channel_ids = get_data()

    writer = Mongo_writer(db_name)

    my_requester = Requester(api_key, writer)

    total = len(channel_ids)
    actual = 0
    checkpoints = {0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100}

    for channel_id in channel_ids:
        try:
            print(f"\n\tTotal feito: {actual * 100 /total : .2f}%\n")
            actual += 1

            check = (actual * 100) // total

            if check in checkpoints:
                my_mail(
                    assunto="Quanto já foi feito do seu trabalho",
                    texto=f"Oi, Thiago!\n\nEstou passando para te falar que seu trabalho está {actual * 100 /total : .2f}%.\n\nContinuarei dando o meu melhor para terminar logo.\n\nAtenciosamente, seu código."
                )
                checkpoints.discard(check)

            status, params = writer.check_channel_completion(channel_id)

            if status["completed"]:
                continue
            # print(status)

            if status["channel_completion"]:
                playlist_id = params["playlist_id"]
                name = None
            else:
                channel = channel_request(my_requester, channel_id)
                if channel is None:
                    continue

                playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
                name = normalize(channel["snippet"]["title"])
                writer.new_channel(channel_id, name, channel, playlist_id)

            if status["playlist_completion"]:
                video_ids: list[str] = params["video_ids"]
            else:
                playlist = playlist_request(my_requester, playlist_id, params["playlist_last_page"])
                video_ids = writer.add_playlist(playlist)
                writer.playlist_finish()

            i = 0
            try:
                size = len(video_ids)//10
                if not size:
                    size += 1
            except:
                size = 50

            for video_id in video_ids:
                status, next_page = writer.check_video_completion(video_id)
                i += 1

                try:
                    if not i%size:
                        if name is None:
                            print("Ainda processando vídeos do último canal")
                        else:
                            print(f"Ainda processando vídeos do canal {name}")
                except Exception:
                    pass

                if status["completed"]:
                    continue

                if not status["video_completion"]:
                    video = video_request(my_requester, video_id)
                    if video is None:
                        continue
                    writer.add_video(video, video_id)

                comments = comments_request(my_requester, video_id, next_page)
                # print(type(comments))
                writer.add_comments(comments)
                writer.video_finish()

            writer.channel_completion()

        except Exception as e:
            my_mail(assunto = "Erro de continuidade", texto = f"Pulei um canal inteiro porque algo aconteceu\n: {e}")
        


if __name__ == "__main__":
    for i in range(3):
        try:
            main()
        except Exception as e:
            my_mail(assunto = "Erro desconhecido", texto = f"Algo me parou, perdão. Pelo menos o senhor poderá ver o erro: {e}")
        my_mail(assunto="Repetição", texto=f"Repetindo pela {i+1} vez")
