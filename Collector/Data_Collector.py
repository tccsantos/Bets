"""
Código para extrair todos os comentários de vídeos do YouTube

Regras de uso:
-i arquivo csv com cabeçalho:
id,name
com id do vídeo e nome de saída do arquivo

-o diretório dinâmico para onde os arquivos serão salvos

-k chave da API do YouTube


O terminal mostra a quantidade de requisições que foram feitas, não demonstra o tempo para acabar.

Thiago Cortez
"""

import requests
import argparse
import sys
import csv
import json
import os
import time

from argparse import RawTextHelpFormatter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Apoio.my_mongo import data_save_mongo, log_error, close_connection

count = 0
time_list = [1, 2, 5, 15]

def read_options() -> dict[str, str|bool]:
    status = False

    parser = argparse.ArgumentParser(
        description="Basic Usage", formatter_class=RawTextHelpFormatter
    )
    parser.add_argument(
        "-i", "--input", help="CSV input File", required=True, default=""
    )
    parser.add_argument(
        "-o", "--output", help="CSV output Directory or 'mongo' for mongodb", required=True, default=""
    )
    parser.add_argument(
        "-k", "--apikey", help="API key to Youtube", required=True, default=""
    )
    parser.add_argument(
        "-db", "--db_name", help="Nome da base de dados do mongodb", required=False, default=""
    )

    argument = parser.parse_args()

    if argument.input and argument.output and argument.apikey:
        status = True

    if not status:
        print("Maybe you want to use -h for help")
        status = False

    return {"success": status, "input": argument.input, "output": argument.output, "api_key": argument.apikey, "db_name": argument.db_name}

def read_video_ids(file: str) -> list[list[str]]:

    with open(file, "r", encoding='utf8') as arquivo:
        aba = csv.reader(arquivo)
        next(aba)
        video_ids = list(aba)
    
    return video_ids

def respostas(video_id: str, api_key: str, parent_id: str) -> list[dict]:
    pos = 0
    while True:
        try:
            url = f"https://www.googleapis.com/youtube/v3/comments?part=snippet&videoId={video_id}&parentId={parent_id}&key={api_key}"
            response = requests.get(url)
            data = response.json()


            global count
            count += 1
            print(f"Número de requisições: {count}")
            break
        except Exception as e:
            global time_list
            print(f"Erro: {e}\n")
            print(f"Dormindo por {time_list[pos]} minutos")
            time.sleep(time_list[pos] * 60)
            if pos < 3:
                pos += 1
            else:
                print("Falha na requisição de respostas do comentário!!")
                return []

    replies = []
    for item in data['items']:
        # print(item)

        # print(f"\t{reply}")
        # x=input()
        replies.append(item)
        # Verifique se a resposta possui suas próprias respostas (recursivamente)
        # if 'replies' in item:
        #     replies.extend(respostas(video_id, api_key, item['id']))


    return replies

def pipeline(video_id: str, api_key: str) -> list[dict]:
    all_comments = []
    page_token = None
    global count

    while True:
        pos = 0
        while True:
            try:
                url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={video_id}&key={api_key}"
                if page_token:
                    url += f"&pageToken={page_token}"

                count += 1
                print(f"Número de requisições: {count}")

                response = requests.get(url)
                data = response.json()

                break
            except Exception as e:
                global time_list
                print(f"Erro: {e}\n")
                print(f"Dormindo por {time_list[pos]} minutos")
                time.sleep(time_list[pos] * 60)
                if pos < 3:
                    pos += 1
                else:
                    print("Falha na requisição de comentários do vídeo!!")
                    return all_comments
        try:
            for item in data['items']:
                # comment =  get_comment(item)
                # replies = respostas(video_id, api_key,comment.get("id"))
                # x=input()
                all_comments.append(item)
                if item["snippet"]["totalReplyCount"] > 0:
                    replies = respostas(video_id, api_key,item.get("id"))
                    all_comments.extend(replies)
                
                page_token = data.get('nextPageToken')
        except KeyError:
            print(data)
            print(video_id)
            sys.exit(0)

        if not page_token:
            break

    return all_comments

def respostas_generator(video_id: str, api_key: str, parent_id: str):
    pos = 0
    while True:
        try:
            url = f"https://www.googleapis.com/youtube/v3/comments?part=snippet&videoId={video_id}&parentId={parent_id}&key={api_key}"
            response = requests.get(url)
            data = response.json()


            global count
            count += 1
            print(f"Número de requisições (reply): {count}")
            break
        except Exception as e:
            global time_list
            print(f"Erro: {e}\n")
            print(f"Dormindo por {time_list[pos]} minutos")
            time.sleep(time_list[pos] * 60)
            if pos < 3:
                pos += 1
            else:
                print(f"Falha na requisição de respostas do comentário {parent_id} !!")
                log_error(video_id = video_id, error = f"Falha na requisição de respostas do comentário {parent_id} !!")
                data = {"items": []}

    try:
        for item in data['items']:
            # print(item)

            # print(f"\t{reply}")
            # x=input()
            item['_id'] = item['id']
            yield item
            # Verifique se a resposta possui suas próprias respostas (recursivamente)
            # if 'replies' in item:
            #     replies.extend(respostas(video_id, api_key, item['id']))
    except KeyError:
        print("Erro de key durante as respostas")
        print(video_id)
        print(data)
        sys.exit(0)

def pipeline_generator(video_id: str, api_key: str):
    page_token = None
    global count
    global time_list
    num_pagina = 0
    pos = 0

    while True:
        try:
            url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,status&id={video_id}&key={api_key}"

            count += 1
            num_pagina += 1
            print(f"Número de requisições: {count}")
            # print(url)
            # sys.exit(0)

            response = requests.get(url)
            data = response.json()

            break
        except Exception as e:
            print(f"Erro: {e}\n")
            print(f"Dormindo por {time_list[pos]} minutos")
            time.sleep(time_list[pos] * 60)
            if pos < 3:
                pos += 1
            else:
                print("Falha na requisição de comentários do vídeo!!")
                log_error(video_id = video_id, error = f"Falha na requisição de comentários do vídeo na {num_pagina}-página!! Nenhum comentário em diante foi coletado")
                page_token = None
                data = None
                break

    try:
        # print(data)
        item = data['items'][0]
        item['_id'] = item['id']
        yield item
    except KeyError:
        print(video_id, "\n")
        print(data)
        print("\n\nParando com erro possível de API")
        sys.exit(0)
    except IndexError:
        log_error(video_id=video_id, error="Video tirado do ar!!")
        print("Video inexistente, pulando")
        return

    while True:
        pos = 0
        while True:
            try:
                url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={video_id}&key={api_key}"
                if page_token:
                    url += f"&pageToken={page_token}"

                count += 1
                num_pagina += 1
                print(f"Número de requisições: {count}")

                response = requests.get(url)
                data = response.json()

                break
            except Exception as e:
                print(f"Erro: {e}\n")
                print(f"Dormindo por {time_list[pos]} minutos")
                time.sleep(time_list[pos] * 60)
                if pos < 3:
                    pos += 1
                else:
                    print("Falha na requisição de comentários do vídeo!!")
                    log_error(video_id = video_id, error = f"Falha na requisição de comentários do vídeo na {num_pagina}-página!! Nenhum comentário em diante foi coletado")
                    page_token = None
                    data = None
                    break
                    
        try:
            if data != None:
                for item in data['items']:
                    # comment =  get_comment(item)
                    # replies = respostas(video_id, api_key,comment.get("id"))
                    # x=input()
                    item['_id'] = item['id']
                    # print(json.dumps(item ,ensure_ascii=False))
                    # input("Continue: ")
                    yield item
                    if item["snippet"]["totalReplyCount"] > 0:
                        replies = respostas_generator(video_id, api_key,item.get("id"))
                        for reply in replies:
                            yield reply
                
                page_token = data.get('nextPageToken')
                # print(f"PAGE_TOKEN = {page_token}")
        except KeyError:
            try:
                if data['error']['errors'][0]['reason'] == 'commentsDisabled':
                    print("Video com comentários desabilitados, pulando!")
                    log_error(video_id=video_id, error="Video com comentários desabilitados")
                    return
            except Exception as e:
                pass

            print(data)
            print(video_id)
            log_error(video_id = video_id, error = f"Erro na formatação dos dados na {num_pagina}-página. Segue abaixo:\n\n {data}\n\n")
            print("\n\nParando com erro possível de API")
            sys.exit(0)
            

        if not page_token:
            break

def data_save_file(dir_name: str, file_name: str, comments: list) -> None:

    os.makedirs("./" + dir_name, exist_ok=True)

    with open("./" + dir_name + "/" + file_name + ".json", 'w', encoding='utf8') as arquivo:
        raw = json.dumps(comments, ensure_ascii=False)
        arquivo.write(raw)

def main():
    data = read_options()

    if not data.get("success"):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)

    api_key: str = data.get("api_key")
    output_dir: str = data.get("output")
    video_ids = read_video_ids(data.get("input"))
    db_name: str = data.get("db_name")

    # print(video_ids)
    # print(api_key)

    # data_save_file(output_dir, "video_id[0]", [{"abacaxi" : 1, "Jujubá": 3}, "Great_Pineapple"])

    total = len(video_ids)
    actual = 0
    skip = True

    for video_id in video_ids:
        print(f"\n\tTotal feito: {actual * 100 /total : .2f}%\n")
        actual += 1
        if video_id[0] == "___________":
            skip = False
            print("Ponto de parada encontrado!")
            continue
        if skip:
            continue
        # comments = pipeline(video_id[0], api_key)
        comments = pipeline_generator(video_id[0], api_key)
        # print(list(comments))
        # sys.exit(1)
        if output_dir.lower() != "mongo":
            data_save_file(output_dir, video_id[1], comments)
        else:
            data_save_mongo(video_id[1], comments, db_name if db_name != "" else "teste")
    
    print(f"\n\tTotal feito: {actual * 100 /total : .2f}%\n")
    close_connection()


if __name__ == "__main__":
    main()
