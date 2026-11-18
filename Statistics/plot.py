from datetime import datetime
from collections import Counter
import csv
import sys
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Apoio.my_mongo import close_connection, get_all_collections_name_mongo, get_collection_mongo

from pymongo.collection import Collection # Instalar pymongo
from pymongo.errors import CursorNotFound

plt.rcParams.update({
    "font.size": 24,        # fonte padrão
    "axes.titlesize": 24,   # título
    "axes.labelsize": 22,   # nomes dos eixos
    "xtick.labelsize": 20,  # números do eixo X
    "ytick.labelsize": 20,  # números do eixo Y
    "legend.fontsize": 20   # legenda
})

def video():
    datas = []

    with open("./Bets/Collector/video_timestamps.csv", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            datas.append(datetime.strptime(row[0], "%Y-%m-%d"))

    # Conta por trimestre
    contagem = Counter()

    for d in datas:
        trimestre = (d.month - 1) // 3 + 1
        contagem[(d.year, trimestre)] += 1

    # Ordena cronologicamente
    periodos = sorted(contagem.keys())

    x = [f"{ano}-Q{tri}" for ano, tri in periodos]
    y = [contagem[p] for p in periodos]

    idx_2024 = x.index("2024-Q1")
    idx_2026 = x.index("2026-Q3")

    plt.figure(figsize=(10, 5))
    plt.plot(x, y, marker="o")
    plt.xlabel("Trimestre", fontsize=29)
    plt.ylabel("Quantidade", fontsize=29)
    plt.title("Ocorrências por trimestre", fontsize=30)
    plt.xticks(rotation=45, fontsize=28)
    plt.yticks(fontsize=28)
    plt.axvline(
        x=idx_2024,
        color="green",
        linestyle="--",
        linewidth=2,
        label="Legalização"
    )
    plt.axvline(
        x=idx_2026,
        color="red",
        linestyle="--",
        linewidth=2,
        label="Proibição"
    )
    plt.legend(fontsize=20, loc="upper left")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def commenters():

    comentarios = []

    with open("../Bets/Collector/standard_comenters.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            comentarios.append(int(row["Score"]))

    plt.figure(figsize=(10, 6))

    plt.plot(comentarios)

    # Escalas logarítmicas
    plt.xscale("log")
    plt.yscale("log")

    plt.xlabel("Comentários por usuário", fontsize=29)
    plt.ylabel("Número de usuários", fontsize=29)
    plt.title("Distribuição de comentários por usuário", fontsize=30)

    plt.xticks(fontsize=28)
    plt.yticks(fontsize=28)

    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.show()

def sentiment():

    # Dados
    dados = [
        ('negativo', 36860),
        ('positivo', 29341),
        ('neutro', 19890)
    ]

    labels = [item[0] for item in dados]
    sizes = [item[1] for item in dados]

    # Gráfico de pizza
    plt.figure(figsize=(8, 8))
    plt.pie(
        sizes,
        labels=labels,
        autopct='%1.2f%%',
        startangle=90,
        textprops={'fontsize': 26}
    )
    plt.title('Distribuição de Sentimentos', fontsize=30)
    plt.axis('equal')  # Mantém o círculo perfeito

    plt.show()

def sentiment_bar():

    # Dados
    categorias = ['Negativo', 'Positivo', 'Neutro']

    # Quantidades
    antes = [3145, 4112, 3123]
    depois = [33715, 25229, 16767]

    # Totais
    total_antes = sum(antes)
    total_depois = sum(depois)

    # Proporções (%)
    antes_pct = [x / total_antes * 100 for x in antes]
    depois_pct = [x / total_depois * 100 for x in depois]

    x = np.arange(len(categorias))
    largura = 0.35

    plt.figure(figsize=(10, 6))

    bars1 = plt.bar(x - largura/2, antes_pct, largura, label='Antes de 2024')
    bars2 = plt.bar(x + largura/2, depois_pct, largura, label='Depois de 2024')

    plt.xticks(x, categorias, fontsize=24)
    plt.ylabel('Percentual (%)', fontsize=24)
    plt.title('Distribuição dos sentimentos comparando antes e depois da legalização das apostas no Brasil', fontsize=18)
    plt.legend()

    # Escreve os percentuais sobre as barras
    for bar in bars1:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, h + 0.5,
                f'{h:.2f}%', ha='center', fontsize=21)

    for bar in bars2:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, h + 0.5,
                f'{h:.2f}%', ha='center', fontsize=21)

    plt.ylim(0, 50)
    plt.grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
    plt.show()

def another_sentiment():

    # ----------------------------
    # Dados de exemplo
    # ----------------------------
    # np.random.seed(42)

    # datas = pd.date_range("2014-01-01", "2014-08-22")

    # n = len(datas)

    # positivos = np.random.randint(200, 800, n)
    # negativos = np.random.randint(100, 700, n)
    # neutros = np.random.randint(150, 500, n)

    # print(neutros)

    # return


    # # Simulando aumento durante a Copa
    # mask = (datas >= "2014-06-01") & (datas <= "2014-07-15")

    # positivos[mask] += np.random.randint(1000, 8000, mask.sum())
    # negativos[mask] += np.random.randint(500, 5000, mask.sum())
    # neutros[mask] += np.random.randint(200, 1500, mask.sum())

    db_name = "Version5"

    collections = get_all_collections_name_mongo(db_name)

    query = {"sentimento": {"$exists": True}}

    sentimento = []

    for collection_name in collections:

        collection = get_collection_mongo(collection_name, db_name)

        cursor = collection.find(query).batch_size(50)

        for doc in cursor:

            try:
            
                match doc["kind"]:

                    case "youtube#video":
                        # video_timestamp: str = doc['snippet']['publishedAt'][:10]
                        continue
                    
                    case "youtube#commentThread":
                        comment_timestamp: str = doc['snippet']['topLevelComment']['snippet']['publishedAt'][:10]
                    
                    case "youtube#comment":
                        comment_timestamp: str = doc['snippet']['publishedAt'][:10]
                    
                    case _:
                        raise TypeError("Não foi possível encontrar o comentário")


                sentimento.append((comment_timestamp, doc['sentimento']))

            except Exception as e:
                print(f"Erro no documento {doc['_id']}: {e}")
        

    df = pd.DataFrame(sentimento, columns=["data", "sentimento"])

    # Garante que a coluna é datetime
    df["data"] = pd.to_datetime(df["data"])

    # Conta quantos comentários de cada sentimento existem por dia
    df = (
        df.groupby(["data", "sentimento"])
        .size()
        .unstack(fill_value=0)
    )

    # Cria um índice diário completo
    idx = pd.date_range(df.index.min(), df.index.max(), freq="D")

    # Adiciona os dias faltantes com zero comentários
    df = df.reindex(idx, fill_value=0)

    # Opcional: nomeia novamente o índice
    df.index.name = "data"

    df = (
        df
        .resample("W")
        .sum()
    )

    datas = df.index

    print(df.head())

    positivos = df["positivo"]
    neutros = df["neutro"]
    negativos = df["negativo"]

    total = positivos + neutros + negativos

    perc_pos = (positivos / total * 100).fillna(0)
    perc_neu = (neutros / total * 100).fillna(0)
    perc_neg = (negativos / total * 100).fillna(0)


    # ----------------------------
    # Figura
    # ----------------------------

    inicio = "2022-12-01"
    fim = datas[-1]

    plt.rcParams.update({
        "font.size": 24,        # fonte padrão
        "axes.titlesize": 24,   # título
        "axes.labelsize": 22,   # nomes dos eixos
        "xtick.labelsize": 20,  # números do eixo X
        "ytick.labelsize": 20,  # números do eixo Y
        "legend.fontsize": 20   # legenda
    })


    fig, ax = plt.subplots(figsize=(15,6))

    # fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

    # Áreas de fundo
    # ax.axhspan(0, 12000, color="#eaf4fb")
    # ax.axhspan(-12000, 0, color="#f8eaea")

    max_y = max(positivos.max(), negativos.max())
    lim = math.ceil(max_y / 100) * 100

    ax.set_ylim(-lim, lim)

    ax.axhspan(0, lim, color="#eaf4fb")
    ax.axhspan(-lim, 0, color="#f8eaea")

    # Positivos
    ax.fill_between(
        datas,
        0,
        positivos,
        color="#2b8cbe",
        alpha=0.85,
        label="Positivo"
    )

    # Negativos
    ax.fill_between(
        datas,
        0,
        -negativos,
        color="#d7301f",
        alpha=0.85,
        label="Negativo"
    )

    # Linha dos neutros
    ax.plot(
        datas,
        neutros,
        color="black",
        linewidth=2.5,
        label="Neutro"
    )

    # Linha de referência
    ax.axhline(0, color="black", linewidth=1)

    # Eventos
    for d in ["2018-12-12", "2023-12-29"]:
        ax.axvline(pd.Timestamp(d), ls="--", color="gray")

    # Faixas
    ax.axvspan(datas[0], pd.Timestamp("2018-12-12"),
            color="green", alpha=0.08)

    ax.axvspan(pd.Timestamp("2018-12-12"),
            pd.Timestamp("2023-12-29"),
            color="gold", alpha=0.10)

    ax.axvspan(pd.Timestamp("2023-12-29"),
            datas[-1],
            color="orange", alpha=0.08)

    ax.set_ylabel("Número de Comentários")

    ax.set_title("Sentimentos ao longo do tempo (Volume)")

    ax.legend(loc="upper left")

    x = pd.Timestamp("2023-12-29")

    ax.annotate(
        "Legalização",
        xy=(x, 0),              # ponto da linha
        xytext=(10, 40),        # deslocamento do texto
        textcoords="offset points",
        rotation=90,
        va="bottom",
        ha="center",
        fontsize=14,
        color="gray",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
    )

    ax.set_xlim(pd.Timestamp(inicio), pd.Timestamp(fim))

    plt.tight_layout()
    plt.show()

    # =====================================================
    # Calcula as porcentagens
    # =====================================================

    df = (
        df
        .resample("ME")
        .sum()
    )

    datas = df.index

    positivos = df["positivo"]
    neutros = df["neutro"]
    negativos = df["negativo"]

    total = positivos + neutros + negativos

    perc_pos = positivos / total * 100
    perc_neu = neutros / total * 100
    perc_neg = negativos / total * 100

    # =====================================================
    # Cria apenas o gráfico inferior
    # =====================================================

    fig, ax = plt.subplots(figsize=(14, 2.8))

    ax.stackplot(
        datas,
        perc_neg,
        perc_neu,
        perc_pos,
        labels=["Negativo", "Neutro", "Positivo"],
        colors=["#C0504D", "#BDBDBD", "#3A9FBF"],
        alpha=0.95
    )

    ax.set_ylim(0, 100)

    ax.set_ylabel("%")

    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])

    ax.legend(
        loc="upper left",
        frameon=True,
        ncol=1,
        labelspacing=0.8
    )

    ax.grid(axis="y", alpha=0.3)

    ax.set_xlim(pd.Timestamp(inicio), pd.Timestamp(fim))

    x = pd.Timestamp("2023-12-29")

    ax.axvline(x, ls="--", color="gray")

    ax.annotate(
        "Legalização",
        xy=(x, 0),              # ponto da linha
        xytext=(10, 40),        # deslocamento do texto
        textcoords="offset points",
        rotation=90,
        va="bottom",
        ha="center",
        fontsize=14,
        color="gray",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
    )

    # fig.text(
    #     0.5, 0.5,
    #     "Volume (acima) vs Percentual (abaixo)",
    #     ha="center",
    #     va="center",
    #     fontsize=16,
    #     backgroundcolor="white"
    # )

    ax.set_title("Sentimentos ao longo do tempo (Porcentagem)")

    plt.tight_layout()
    plt.show()

def grafico_barras():
    # Dados
    dados = [
        ('G3', 7036, '30.81%'),
        ('G6', 7277, '31.86%'),
        ('G1', 6413, '28.08%'),
        ('G4', 1142, '5.00%'),
        ('G2', 786, '3.44%'),
        ('G5', 186, '0.81%')
    ]

    labels = [item[0] for item in dados]
    sizes = [item[1] for item in dados]
    porcentagens = [item[2] for item in dados]

    colors = [
        '#1f77b4',  # G3 - azul
        '#ff7f0e',  # G5 - laranja
        '#2ca02c',  # G1 - verde
        '#d62728',  # G4 - vermelho
        '#9467bd',  # G2 - roxo
        '#8c564b'   # G6 - marrom
    ]

    plt.figure(figsize=(10, 6))

    barras = plt.bar(labels, sizes, color=colors)

    plt.ylim(0, max(sizes) * 1.2)

    # Adiciona os valores e percentuais acima das barras
    for barra, valor, pct in zip(barras, sizes, porcentagens):
        plt.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + 120,
            f'{valor}\n({pct})',
            ha='center',
            va='bottom',
            fontsize=22
        )

    plt.title('Distribuição dos Grupos', fontsize=22)
    plt.xlabel('Grupos', fontsize=26)
    plt.ylabel('Quantidade', fontsize=26)
    plt.xticks(fontsize=24)
    plt.yticks(fontsize=24)

    plt.grid(axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.show()

def topico_bar():

    # Dados
    dados1 = [
        ('G6', 767),
        ('G1', 437),
        ('G3', 285),
        ('G4', 66),
        ('G2', 65),
        ('G5', 6)
    ]

    dados2 = [
        ('G3', 6751),
        ('G6', 6510),
        ('G1', 5976),
        ('G4', 1076),
        ('G2', 721),
        ('G5', 180)
    ]

    # Ordem dos grupos
    grupos = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6']

    # Dicionários
    dict1 = dict(dados1)
    dict2 = dict(dados2)

    # Totais
    total1 = sum(dict1.values())
    total2 = sum(dict2.values())

    # Proporções (%)
    prop1 = [100 * dict1[g] / total1 for g in grupos]
    prop2 = [100 * dict2[g] / total2 for g in grupos]

    # Barras
    x = np.arange(len(grupos))
    largura = 0.35

    plt.figure(figsize=(10,6))

    bars1 = plt.bar(x - largura/2, prop1, largura,
                    color='steelblue', label='Antes da legalização')

    bars2 = plt.bar(x + largura/2, prop2, largura,
                    color='orange', label='Depois da legalização')

    plt.xticks(x, grupos, fontsize=22)
    plt.ylabel('Proporção (%)', fontsize=23)
    plt.title('Distribuição dos tópicos comparando antes e depois da legalização', fontsize=26)
    plt.legend(loc="upper left")

    # Escreve o percentual em cima de cada barra
    for bar in bars1:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2,
                h + 0.5,
                f'{h:.1f}%',
                ha='center', fontsize=20)

    for bar in bars2:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2,
                h + 0.5,
                f'{h:.1f}%',
                ha='center', fontsize=20)

    plt.ylim(0, 55)
    plt.grid(axis='y', linestyle='--', alpha=0.4)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    commenters()
    # video()
    # sentiment()
    # sentiment_bar()
    # another_sentiment()
    # grafico_barras()
    # topico_bar()
    pass
