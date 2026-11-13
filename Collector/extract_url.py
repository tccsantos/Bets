import re
import os
import sys
import argparse
import validators
import tldextract

from collections import Counter
from argparse import RawTextHelpFormatter

from math import inf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Apoio.my_mongo import get_all_collections_name_mongo, get_collection_mongo, close_connection
from pymongo.collection import Collection


def	readOptions():

    status = False

    parser = argparse.ArgumentParser(description = "Basic Usage",formatter_class=RawTextHelpFormatter)
    parser.add_argument("-i"	,	"--input"		, help = "Database input File"      , required = True	, default = "")
    parser.add_argument("-o"	,	"--output"		, help = "CSV output Directory"		, required = True	, default = "")
    argument = parser.parse_args()

    if argument.input and argument.output:
        status = True

    if not status:
        print("Maybe you want to use -h for help")
        status = False 

    return {"success":status, "input":argument.input, "output":argument.output}

def pasta(db_name: str):
    collections = get_all_collections_name_mongo(db_name)
    for collection in collections:
        yield get_collection_mongo(collection, db_name)

def contagem(lista):
    c = Counter(lista)
    return c.most_common()

def validar_url(url: str) -> bool:

    # Adiciona protocolo
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Validação básica
    if validators.url(url) is not True:
        return False

    # Extrai domínio
    extraido = tldextract.extract(url)

    # Precisa ter domínio e suffix válidos
    if not extraido.domain or not extraido.suffix:
        return False

    return True

def analise(collection: Collection):
    


    resultado = []
    total = 0
    for data in collection.find({"channel_controller" : {"$exists": False}}):
        
        match data['kind']:

            case 'youtube#comment':
                raw: str = data['snippet']['textOriginal']
            
            case 'youtube#commentThread':
                raw: str = data['snippet']['topLevelComment']['snippet']['textOriginal']

            case 'youtube#video':
                raw: str = data['snippet']['description']

            case _:
                raw = ''
        
        if raw == '':
            continue

        begin = 0

        pattern_url = re.compile(r'\b(?:https?://)?(?:www\.)?'
                                r'[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*'
                                r'\.[a-zA-Z]{2,}'
                                r'(?:/[^\s]*)?')

        while True:
            # inicio = raw.find('#', begin)
            inicio_match = pattern_url.search(raw, begin)
            
            if inicio_match is None:
                break
            
            inicio = inicio_match.start()
            # input("abacaxi")

            match = re.search(r"[\s!?,]+", raw[inicio + 1:])
            
            if match:
                fim = inicio + match.start() + 1
                # print(fim)
            else:
                fim = -1

            begin = fim + 1


            total += 1

            if fim == -1:
                if validar_url(raw[inicio:]):
                    resultado.append((collection.name, data["id"], raw[inicio:]))
                break

            if validar_url(raw[inicio:fim]):
                resultado.append((collection.name, data["id"], raw[inicio:fim]))
            
    # print(total)
    # input(resultado)
    # if not len(resultado):
    #     input("Abacaxi")
    return resultado

def escrita(output, data):
    with open(output + '_url.csv', 'w', encoding='utf8') as arquivo:
        arquivo.write(f'"Channel;Video_id;Url"\n')
        for tup in data:
            row = ';'.join(tup)
            arquivo.write(f'{row}\n')
        arquivo.close()
        print('end')

def main():
    result = readOptions()
    if not result.get("success"):
        print("Erro no envio dos dados, checar argumentos!")
        sys.exit(0)

    inputfile	=	result.get("input")
    outputfile = result.get("output")
    os.makedirs(outputfile, exist_ok=True)

    arquivos = pasta(inputfile)

    links = list()

    total = len(get_all_collections_name_mongo(inputfile))
    actual = 0

    for arquivo in arquivos:

        print(f"\n\tTotal feito: {actual * 100 /total : .2f}%\n")
        actual += 1

        links.extend(analise(arquivo))
        # print(links)
        # reps = contagem(reps)
        print(arquivo.name)
    
    escrita(outputfile + '/' + inputfile, links)

    # print(links)

    print(f"\n\tTotal feito: {actual * 100 /total : .2f}%\n")

    close_connection()



if __name__ == '__main__':
    main()